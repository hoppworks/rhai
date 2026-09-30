#!/usr/bin/env python3
"""Run the frozen optional-package MSRV proof inside run_scoped's private runtime."""
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

REPO = pathlib.Path('/Users/hoppworks/projects/rhai-optional-msrv-proof')
SOURCE_REV = '0c2dda12bd53d2a3477bea1ff98ea66ad0ab1fab'
LOCK_CANDIDATE = REPO / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
EVIDENCE = REPO / '.scratch/optional-msrv-proof/evidence'
RUSTUP = pathlib.Path('/Users/hoppworks/.cargo/bin/rustup')
RUNTIME = pathlib.Path(os.environ['AGENT_RUNTIME_DIR'])
RUSTUP_HOME = RUNTIME / 'rustup-home'
CARGO_HOME = RUNTIME / 'cargo-home'
SOURCE = RUNTIME / 'source'
TARGET = RUNTIME / 'target'
SAMPLE_LOG = EVIDENCE / 'storage-samples.tsv'
HARD_KIB = 2 * 1024 * 1024
PREEMPT_KIB = 1536 * 1024
DEADLINE_UTC = datetime(2026, 9, 30, 17, 5, 0, tzinfo=timezone.utc).timestamp()
MAX_FIXTURE_PROCESSES = 16
FEATURES = 'testing-environ,sys,net,metadata'
TARGETS = ['sys_policy', 'sys_env', 'sys_fs', 'net_connect', 'net_listen', 'net_reads', 'net_writes', 'net_metadata']
CONTROL = 'test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving'

EVIDENCE.mkdir(parents=True, exist_ok=True)
deadline = time.monotonic() + max(0, DEADLINE_UTC - time.time())
sample_stop = threading.Event()
sample_peak = 0
process_peak = 0
sample_lock = threading.Lock()


def emit(message):
    print(message, flush=True)


def runtime_kib():
    out = subprocess.check_output(['du', '-sk', str(RUNTIME)], text=True)
    return int(out.split()[0])


def owned_descendant_count():
    output = subprocess.check_output(['ps', '-axo', 'pid=,ppid='], text=True)
    parents = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2:
            parents[int(fields[0])] = int(fields[1])
    descendants = set()
    frontier = [os.getpid()]
    while frontier:
        parent = frontier.pop()
        children = [pid for pid, ppid in parents.items() if ppid == parent and pid not in descendants]
        descendants.update(children)
        frontier.extend(children)
    return len(descendants)


def custody_stop(reason, exit_code):
    (EVIDENCE / 'STOP-REASON.txt').write_text(reason + '\n')
    emit('CUSTODY_STOP: ' + reason)
    active = active_process[0]
    if active is not None and active.poll() is None:
        try:
            active.terminate()
        except ProcessLookupError:
            pass
    # run_scoped owns the whole process group and removes it after this exit.
    os._exit(exit_code)


def sampler():
    global sample_peak, process_peak
    with SAMPLE_LOG.open('w', buffering=1) as out:
        out.write('utc_epoch\tkib\n')
        process_log = (EVIDENCE / 'process-samples.tsv').open('w', buffering=1)
        process_log.write('utc_epoch\towned_descendants\n')
        while not sample_stop.wait(1):
            try:
                size = runtime_kib()
                process_count = owned_descendant_count()
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                custody_stop(f'resource sampler failed: {type(exc).__name__}: {exc}', 89)
            with sample_lock:
                sample_peak = max(sample_peak, size)
                process_peak = max(process_peak, process_count)
            out.write(f'{time.time():.3f}\t{size}\n')
            process_log.write(f'{time.time():.3f}\t{process_count}\n')
            if process_count > MAX_FIXTURE_PROCESSES:
                custody_stop(f'owned descendant process count {process_count} exceeded {MAX_FIXTURE_PROCESSES}', 87)
            if size >= PREEMPT_KIB:
                custody_stop(f'sampled private runtime size {size} KiB reached 1.5 GiB preemptive ceiling', 86)
            if time.time() >= DEADLINE_UTC:
                custody_stop('fixed 2026-09-30 17:05:00 UTC execution deadline reached', 88)


active_process = [None]
sampler_thread = threading.Thread(target=sampler, name='runtime-storage-sampler', daemon=True)


def run(label, command, env=None, expected=None, control=False):
    if time.monotonic() >= deadline or time.time() >= DEADLINE_UTC:
        raise TimeoutError('fixed 2026-09-30 17:05:00 UTC execution deadline reached')
    if not sampler_thread.is_alive():
        sampler_thread.start()
    log = EVIDENCE / f'{label}.log'
    emit(f'COMMAND {label}: {" ".join(command)}')
    emit(f'LOG {log}')
    with log.open('w', buffering=1) as stream:
        proc = subprocess.Popen(command, cwd=SOURCE, env=env or BASE_ENV,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
        active_process[0] = proc
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(line)
                stream.write(line)
                if time.monotonic() >= deadline or time.time() >= DEADLINE_UTC:
                    proc.terminate()
                    raise TimeoutError('fixed 2026-09-30 17:05:00 UTC execution deadline reached during command')
            status = proc.wait()
        finally:
            active_process[0] = None
    size = runtime_kib()
    with sample_lock:
        sampled_max = max(sample_peak, size)
    emit(f'STATUS {label}: {status}')
    emit(f'PRIVATE_RUNTIME_SAMPLED_STORAGE {label}: {size} KiB; sampled maximum {sampled_max} KiB (1 s du -sk samples)')
    if size >= HARD_KIB or sampled_max >= HARD_KIB:
        raise RuntimeError(f'hard private-storage ceiling reached: {max(size, sampled_max)} KiB')
    if expected is not None and status != expected:
        raise RuntimeError(f'{label}: expected exit {expected}, got {status}')
    if control:
        text = log.read_text(errors='replace')
        if 'running 1 test' not in text or 'test result: FAILED' not in text:
            raise RuntimeError('wrong-expectation control did not execute and fail the targeted test assertion')
        if 'left: "abc"' not in text or 'right: "wrong expectation"' not in text:
            raise RuntimeError('wrong-expectation control lacked the expected assertion values')
    if label == 'restored-targeted-test':
        text = log.read_text(errors='replace')
        if 'running 1 test' not in text or 'test result: ok. 1 passed' not in text:
            raise RuntimeError('restored targeted test did not show exactly one passing assertion test')
    if label.startswith('fixture-'):
        text = log.read_text(errors='replace')
        counts = [int(value) for value in re.findall(r'running (\d+) tests?\b', text)]
        if not counts or max(counts) < 1:
            raise RuntimeError(f'{label}: no nonzero test count found in test harness output')
        emit(f'TARGET_TEST_COUNT {label.removeprefix("fixture-")}: {sum(counts)}')
    return status


try:
    if subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip() != SOURCE_REV:
        raise RuntimeError('checkout HEAD differs from immutable authorized source')
    if subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain=v1', '--untracked-files=no'], text=True).strip():
        raise RuntimeError('checkout is dirty; source archive would not represent the approved frozen tree')
    if not LOCK_CANDIDATE.is_file():
        raise RuntimeError(f'missing accepted lock candidate: {LOCK_CANDIDATE}')
    arch = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', '--show-toplevel'], text=True).strip()
    del arch
    RUSTUP_HOME.mkdir()
    CARGO_HOME.mkdir()
    SOURCE.mkdir()
    archive = subprocess.run(['git', '-C', str(REPO), 'archive', SOURCE_REV], check=True, stdout=subprocess.PIPE)
    subprocess.run(['tar', '-x', '-C', str(SOURCE)], input=archive.stdout, check=True)
    shutil.copy2(LOCK_CANDIDATE, SOURCE / 'Cargo.lock')
    lock_hash = hashlib.sha256((SOURCE / 'Cargo.lock').read_bytes()).hexdigest()
    shutil.copy2(SOURCE / 'Cargo.lock', EVIDENCE / 'Cargo.lock.candidate')
    BASE_ENV = dict(os.environ)
    BASE_ENV.update({
        'RUSTUP_HOME': str(RUSTUP_HOME),
        'CARGO_HOME': str(CARGO_HOME),
        'CARGO_TARGET_DIR': str(TARGET),
        'CARGO_BUILD_JOBS': '2',
        'CARGO_INCREMENTAL': '0',
        'CARGO_PROFILE_DEV_DEBUG': '0',
        'CARGO_PROFILE_TEST_DEBUG': '0',
        'RUSTFLAGS': '-C debuginfo=0',
    })
    for key in ('RUSTC', 'RUSTDOC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_HOME_CONFIG', 'RUSTUP_TOOLCHAIN'):
        BASE_ENV.pop(key, None)
    emit(f'SOURCE_REVISION {SOURCE_REV}')
    emit(f'PRIVATE_RUNTIME {RUNTIME}')
    emit(f'PRIVATE_RUSTUP_HOME {RUSTUP_HOME}')
    emit(f'PRIVATE_CARGO_HOME {CARGO_HOME}')
    emit(f'LOCK_CANDIDATE {LOCK_CANDIDATE} sha256={lock_hash}')
    emit(f'LOCK_IDENTITY {SOURCE / "Cargo.lock"} sha256={lock_hash}')
    emit(f'NATIVE_TARGET {subprocess.check_output(["uname", "-sm"], text=True).strip()}')
    emit(f'PROOF_LIMITS absolute_deadline_utc=2026-09-30T17:05:00Z remaining_seconds={max(0, int(DEADLINE_UTC-time.time()))} two_cargo_jobs debug=0 incremental=0 storage_preempt_kib={PREEMPT_KIB} storage_hard_kib={HARD_KIB} owned_descendants<={MAX_FIXTURE_PROCESSES}')
    emit(f'INITIAL_PRIVATE_STORAGE {runtime_kib()} KiB')

    status = run('toolchain-install', [str(RUSTUP), 'toolchain', 'install', '1.77.2', '--profile', 'minimal', '--no-self-update'], env=BASE_ENV, expected=0)
    toolchain = RUSTUP_HOME / 'toolchains' / '1.77.2-aarch64-apple-darwin' / 'bin'
    if not toolchain.is_dir():
        raise RuntimeError(f'expected native Darwin arm64 toolchain directory missing: {toolchain}')
    cargo = toolchain / 'cargo'
    rustc = toolchain / 'rustc'
    rustdoc = toolchain / 'rustdoc'
    BASE_ENV['PATH'] = str(toolchain) + os.pathsep + BASE_ENV.get('PATH', '')
    BASE_ENV['RUSTC'] = str(rustc)
    BASE_ENV['RUSTDOC'] = str(rustdoc)
    for label, binary in [('rustc-version', rustc), ('cargo-version', cargo)]:
        run(label, [str(binary), '--version', '--verbose'], expected=0)
    if '1.77.2' not in subprocess.check_output([str(rustc), '--version'], text=True):
        raise RuntimeError('direct private rustc is not version 1.77.2')
    if '1.77.2' not in subprocess.check_output([str(cargo), '--version'], text=True):
        raise RuntimeError('direct private cargo is not version 1.77.2')

    common = [str(cargo), 'test', '--locked', '--features', FEATURES]
    run('compile-test-targets', common + ['--no-run'] + sum((['--test', name] for name in TARGETS), []), expected=0)

    wrong_env = dict(BASE_ENV)
    wrong_env['RHAI_FILE_READ_WRONG_EXPECTATION'] = '1'
    wrong_status = run('wrong-expectation-control', common + ['--test', 'sys_fs', CONTROL, '--', '--exact', '--nocapture', '--test-threads=1'], env=wrong_env, expected=101, control=True)
    emit(f'WRONG_EXPECTATION_CONTROL_EXIT {wrong_status}; assertion verified left=abc right=wrong expectation')

    run('restored-targeted-test', common + ['--test', 'sys_fs', CONTROL, '--', '--exact', '--nocapture', '--test-threads=1'], expected=0)
    for name in TARGETS:
        run(f'fixture-{name}', common + ['--test', name, '--', '--test-threads=1', '--nocapture'], expected=0)
    shutil.copy2(SOURCE / 'Cargo.lock', EVIDENCE / 'Cargo.lock')
    emit(f'EXPORTED_FINAL_LOCK {EVIDENCE / "Cargo.lock"} sha256={hashlib.sha256((EVIDENCE / "Cargo.lock").read_bytes()).hexdigest()}')
    emit('ACCEPTED: Rust 1.77.2 native Darwin arm64 strict Engine/OS fixtures with sys+net+metadata; negative control failed for expected assertion and restored test passed.')
except BaseException as exc:
    emit(f'PROOF_STOP: {type(exc).__name__}: {exc}')
    raise
finally:
    sample_stop.set()
    if sampler_thread.is_alive():
        sampler_thread.join(timeout=2)
    try:
        emit(f'FINAL_PRIVATE_STORAGE_BEFORE_WRAPPER_CLEANUP {runtime_kib()} KiB')
        emit(f'PEAK_OWNED_DESCENDANTS_SAMPLED {process_peak} (1 s ps PID/PPID ancestry samples)')
    except Exception as exc:
        emit(f'FINAL_STORAGE_SAMPLE_UNAVAILABLE {exc}')
