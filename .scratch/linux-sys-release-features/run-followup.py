#!/usr/bin/env python3
"""Run the approved native Linux sys feature matrix in a private scoped runtime."""
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

STAGE = pathlib.Path(os.environ['PROOF_STAGE'])
SOURCE_REV = 'e1db9baafaaf30d94085f0cc6f661f363399f193'
ARCHIVE_SHA256 = 'c934633c7889e4a427a87d557bbc578146e4db641c4fde2c93ff3fd4f047aa47'
EVIDENCE = STAGE / 'evidence'
RUNTIME = pathlib.Path(os.environ['AGENT_RUNTIME_DIR'])
RUSTUP_HOME = pathlib.Path('/root/.rustup')
CARGO_HOME = RUNTIME / 'cargo-home'
SOURCE = RUNTIME / 'source'
TARGET = RUNTIME / 'target'
SAMPLE_LOG = EVIDENCE / 'storage-samples.tsv'
HARD_KIB = 2 * 1024 * 1024
PREEMPT_KIB = 1536 * 1024
DEADLINE_UTC = datetime(2026, 9, 30, 18, 5, 14, tzinfo=timezone.utc).timestamp()
MAX_FIXTURE_PROCESSES = 16
TARGETS = ['sys_env', 'sys_fs', 'sys_policy']
FEATURE_ROWS = [
    'testing-environ,sys',
    'testing-environ,sys,sync',
    'testing-environ,sys,no_index',
    'testing-environ,sys,metadata,serde',
    'testing-environ,sys,only_i32,no_float',
    'testing-environ,sys,unchecked',
    'testing-environ,sys,no_index,sync,metadata',
    'testing-environ,sys,f32_float',
]
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
    output = subprocess.check_output(['ps', '-e', '-o', 'pid=,ppid='], text=True)
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


def process_identity(pid):
    try:
        raw = (pathlib.Path('/proc') / str(pid) / 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()  # starts at stat field 3
        cmdline = (pathlib.Path('/proc') / str(pid) / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
        return f'{pid}\t{fields[1]}\t{fields[2]}\t{fields[19]}\t{cmdline}'
    except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError):
        return None


def record_process(label, pid):
    row = process_identity(pid)
    if row is None:
        # A short version command can exit between Popen returning and /proc
        # sampling. Preserve that fact without inventing a live identity.
        with (EVIDENCE / 'process-identities.tsv').open('a') as out:
            out.write(f'{label}\t{pid}\t<unknown>\t<unknown>\t<unknown>\t<exited-before-identity-sample>\n')
            out.flush()
            os.fsync(out.fileno())
        return
    actual_group = int(row.split('\t')[2])
    owned_group = os.getpgid(0)
    if actual_group != owned_group:
        raise RuntimeError(f'{label} pid={pid} escaped scoped process group {owned_group}: pgid={actual_group}')
    with (EVIDENCE / 'process-identities.tsv').open('a') as out:
        out.write(label + '\t' + row + '\n')
        out.flush()
        os.fsync(out.fileno())


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
        process_log.write('utc_epoch\towned_descendants\tscoped_group_pids\n')
        identity_log = (EVIDENCE / 'process-identities.tsv').open('a', buffering=1)
        while not sample_stop.wait(1):
            try:
                size = runtime_kib()
                process_count = owned_descendant_count()
                pgid = os.getpgid(0)
                ps = subprocess.check_output(['ps', '-e', '-o', 'pid=,pgid='], text=True)
                group_pids = ','.join(row.split()[0] for row in ps.splitlines()
                                      if len(row.split()) == 2 and int(row.split()[1]) == pgid)
                for pid in group_pids.split(',') if group_pids else ():
                    identity = process_identity(int(pid))
                    if identity is not None:
                        identity_log.write(f'scoped-live-sample@{time.time():.3f}\t{identity}\n')
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                custody_stop(f'resource sampler failed: {type(exc).__name__}: {exc}', 89)
            with sample_lock:
                sample_peak = max(sample_peak, size)
                process_peak = max(process_peak, process_count)
            out.write(f'{time.time():.3f}\t{size}\n')
            process_log.write(f'{time.time():.3f}\t{process_count}\t{group_pids}\n')
            if process_count > MAX_FIXTURE_PROCESSES:
                custody_stop(f'owned descendant process count {process_count} exceeded {MAX_FIXTURE_PROCESSES}', 87)
            if size >= PREEMPT_KIB:
                custody_stop(f'sampled private runtime size {size} KiB reached 1.5 GiB preemptive ceiling', 86)
            if size >= HARD_KIB:
                custody_stop(f'sampled private runtime size {size} KiB reached 2 GiB hard ceiling', 90)
            if time.time() >= DEADLINE_UTC:
                custody_stop('fixed 2026-09-30 18:05:14 UTC execution deadline reached', 88)


active_process = [None]
sampler_thread = threading.Thread(target=sampler, name='runtime-storage-sampler', daemon=True)


def run(label, command, env=None, expected=None, control=False):
    if time.monotonic() >= deadline or time.time() >= DEADLINE_UTC:
        raise TimeoutError('fixed 2026-09-30 18:05:14 UTC execution deadline reached')
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
        record_process(label, proc.pid)
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(line)
                stream.write(line)
                if time.monotonic() >= deadline or time.time() >= DEADLINE_UTC:
                    proc.terminate()
                    raise TimeoutError('fixed 2026-09-30 18:05:14 UTC execution deadline reached during command')
            status = proc.wait()
        finally:
            active_process[0] = None
    size = runtime_kib()
    with sample_lock:
        sampled_max = max(sample_peak, size)
    emit(f'STATUS {label}: {status}')
    status_file = EVIDENCE / f'{label}.status'
    status_file.write_text(f'{status}\n')
    with status_file.open('rb') as receipt:
        os.fsync(receipt.fileno())
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
        if f"thread '{CONTROL}' panicked" not in text:
            raise RuntimeError('wrong-expectation control did not panic in the exact file-read test')
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
    archive_path = STAGE / 'source.tar'
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise RuntimeError('staged complete git archive SHA256 mismatch')
    CARGO_HOME.mkdir()
    SOURCE.mkdir()
    if time.time() >= DEADLINE_UTC:
        raise TimeoutError('fixed 2026-09-30 18:05:14 UTC execution deadline reached before extraction')
    subprocess.run(['tar', '-xf', str(archive_path), '-C', str(SOURCE)], check=True,
                   timeout=max(1, DEADLINE_UTC-time.time()))
    workspace = (SOURCE / 'Cargo.toml').read_text()
    if '"codegen"' not in workspace or not (SOURCE / 'codegen' / 'Cargo.toml').is_file():
        raise RuntimeError('full workspace verification failed: codegen/Cargo.toml is absent')
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
    with (EVIDENCE / 'process-identities.tsv').open('w') as identities:
        identities.write('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n')
    record_process('driver', os.getpid())
    record_process('scoped-supervisor', os.getppid())
    sampler_thread.start()
    emit(f'SOURCE_REVISION {SOURCE_REV}')
    emit(f'PRIVATE_RUNTIME {RUNTIME}')
    emit(f'EXISTING_RUSTUP_HOME {RUSTUP_HOME} (read-only; no toolchain installation)')
    emit(f'PRIVATE_CARGO_HOME {CARGO_HOME}')
    emit(f'WORKSPACE_MEMBERS codegen_manifest_present=1 source_manifest={SOURCE / "Cargo.toml"}')
    emit(f'ARCHIVE_IDENTITY {archive_path} sha256={ARCHIVE_SHA256}')
    emit(f'NATIVE_TARGET {subprocess.check_output(["uname", "-sm"], text=True).strip()}')
    emit(f'HOST_KERNEL {subprocess.check_output(["uname", "-a"], text=True).strip()}')
    emit(f'PROOF_LIMITS absolute_deadline_utc=2026-09-30T18:05:14Z remaining_seconds={max(0, int(DEADLINE_UTC-time.time()))} two_cargo_jobs debug=0 incremental=0 storage_preempt_kib={PREEMPT_KIB} storage_hard_kib={HARD_KIB} owned_descendants<={MAX_FIXTURE_PROCESSES}')
    emit(f'INITIAL_PRIVATE_STORAGE {runtime_kib()} KiB')
    rustc = shutil.which('rustc')
    cargo = shutil.which('cargo')
    if not rustc or not cargo:
        raise RuntimeError('host rustc/cargo were not found without toolchain installation')
    run('rustc-version', [rustc, '--version', '--verbose'], expected=0)
    run('cargo-version', [cargo, '--version', '--verbose'], expected=0)

    run('generate-lockfile', [cargo, 'generate-lockfile'], expected=0)
    generated_lock = SOURCE / 'Cargo.lock'
    if not generated_lock.is_file():
        raise RuntimeError('cargo generate-lockfile completed without creating Cargo.lock')
    shutil.copy2(generated_lock, EVIDENCE / 'Cargo.lock.generated')
    with (EVIDENCE / 'Cargo.lock.generated').open('rb') as lock_receipt:
        os.fsync(lock_receipt.fileno())
    emit(f'GENERATED_LOCK_IDENTITY {EVIDENCE / "Cargo.lock.generated"} sha256={hashlib.sha256(generated_lock.read_bytes()).hexdigest()}')

    wrong_env = dict(BASE_ENV)
    wrong_env['RHAI_FILE_READ_WRONG_EXPECTATION'] = '1'
    baseline = ['--locked', '--jobs', '2', '--features', 'testing-environ,sys']
    wrong_status = run('wrong-expectation-control', [str(cargo), 'test'] + baseline + ['--test', 'sys_fs', CONTROL, '--', '--exact', '--nocapture', '--test-threads=1'], env=wrong_env, expected=101, control=True)
    with (EVIDENCE / 'outcome-status.tsv').open('a') as statuses:
        statuses.write(f'wrong-expectation-control\t{wrong_status}\ttesting-environ,sys\tsys_fs:{CONTROL}\n')
        statuses.flush()
        os.fsync(statuses.fileno())
    emit(f'WRONG_EXPECTATION_CONTROL_EXIT {wrong_status}; assertion verified left=abc right=wrong expectation')

    restored_status = run('restored-targeted-test', [str(cargo), 'test'] + baseline + ['--test', 'sys_fs', CONTROL, '--', '--exact', '--nocapture', '--test-threads=1'], expected=0)
    with (EVIDENCE / 'outcome-status.tsv').open('a') as statuses:
        statuses.write(f'restored-targeted-test\t{restored_status}\ttesting-environ,sys\tsys_fs:{CONTROL}\n')
        statuses.flush()
        os.fsync(statuses.fileno())
    for feature_index, features in enumerate(FEATURE_ROWS, 1):
        for target in TARGETS:
            label = f'fixture-{feature_index:02d}-{target}'
            case_status = run(label, [str(cargo), 'test', '--locked', '--jobs', '2', '--features', features,
                                      '--test', target, '--', '--test-threads=1', '--nocapture'])
            with (EVIDENCE / 'outcome-status.tsv').open('a') as statuses:
                statuses.write(f'{label}\t{case_status}\t{features}\t{target}\n')
                statuses.flush()
                os.fsync(statuses.fileno())
            if case_status != 0:
                raise RuntimeError(f'{label}: unexpected first matrix failure status={case_status}; stopping immediately')
    shutil.copy2(SOURCE / 'Cargo.lock', EVIDENCE / 'Cargo.lock')
    emit(f'EXPORTED_FINAL_LOCK {EVIDENCE / "Cargo.lock"} sha256={hashlib.sha256((EVIDENCE / "Cargo.lock").read_bytes()).hexdigest()}')
    emit('ACCEPTED: native Linux strict Engine/OS sys feature gates; negative control failed on actual fixture bytes and restored assertion passed.')
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
