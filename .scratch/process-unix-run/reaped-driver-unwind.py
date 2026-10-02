import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

repo = Path('/Users/hoppworks/projects/rhai-process-unix-run')
runtime = Path(os.path.abspath(os.environ['AGENT_RUNTIME_DIR']))
runtime.mkdir(parents=True, exist_ok=True)
proof_dir = repo / '.scratch/process-unix-run/evidence'
proof_dir.mkdir(parents=True, exist_ok=True)
print(f'runtime_path={runtime}', flush=True)
print(f'os={platform.platform()}', flush=True)
print(f'python={sys.version.replace(chr(10), " ")}', flush=True)

MAX_SAMPLED_KIB = 1_572_864
storage_samples = []
command_index = 0


def sample_storage():
    sampled = subprocess.run(
        ['du', '-sk', str(runtime)], capture_output=True, text=True, timeout=5
    )
    print(f'sampler_status={sampled.returncode} stdout={sampled.stdout!r} stderr={sampled.stderr!r}', flush=True)
    if sampled.returncode != 0:
        raise RuntimeError('bounded private-storage sampler failed')
    kib = int(sampled.stdout.split()[0])
    storage_samples.append(kib)
    print(f'storage_sample_kib={kib}', flush=True)
    if kib >= MAX_SAMPLED_KIB:
        raise RuntimeError(f'sampled private runtime reached stop threshold {MAX_SAMPLED_KIB} KiB')
    return kib


def print_case_log(path, complete):
    content = path.read_bytes()
    cap = 256 * 1024
    clipped = len(content) > cap
    print(f'case_log_output_begin label={path.name} complete={str(complete).lower()} bytes={len(content)} clipped={str(clipped).lower()}', flush=True)
    if clipped:
        print('[earlier output truncated; retained final 256 KiB]', flush=True)
    print((content[-cap:] if clipped else content).decode(errors='replace'), flush=True)
    print('case_log_output_end', flush=True)


def run_bounded(argv, cwd, env, expected, label, timeout=180):
    global command_index
    command_index += 1
    log = runtime / f'{command_index:02d}-{label}.log'
    print(f'case_argv={argv!r}', flush=True)
    print(f'case_log={log}', flush=True)
    with log.open('wb') as output:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=False)
        deadline = time.monotonic() + timeout
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'{label} exceeded external watchdog {timeout}s')
                sample_storage()
                time.sleep(1)
            status = proc.returncode
        except BaseException:
            output.flush()
            print_case_log(log, False)
            raise
    sample_storage()
    print(f'case_status={status} label={label}', flush=True)
    print_case_log(log, True)
    if status != expected:
        raise RuntimeError(f'{label} returned {status}, expected {expected}')
    return log


def insert_test(baseline, current):
    start = current.index('    #[test]\n    fn reaped_driver_unwind_retires_completed_owner_once() {')
    end = current.index('\n    fn assert_pid_present(', start)
    test = current[start:end]
    if test.count('fn reaped_driver_unwind_retires_completed_owner_once') != 1:
        raise RuntimeError('unwind test extraction was not unique')
    if baseline.count('    fn assert_pid_present(') != 1:
        raise RuntimeError('baseline test insertion point was not unique')
    baseline = baseline.replace(
        'use std::process::{Child, Command, Stdio};',
        'use std::process::{Child, Command, Stdio};\n    use std::panic::{catch_unwind, AssertUnwindSafe};',
        1,
    )
    baseline = baseline.replace(
        'use std::sync::atomic::{AtomicBool, Ordering};',
        'use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};',
        1,
    )
    return baseline.replace('    fn assert_pid_present(', test + '\n\n    fn assert_pid_present(', 1)


try:
    source_paths = [
        'Cargo.toml',
        'src/packages/sys/fs.rs',
        'src/packages/sys/mod.rs',
        'src/packages/sys/process.rs',
        'src/packages/sys/process/unix.rs',
    ]
    hashes = {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in source_paths}
    current_hash = hashes['src/packages/sys/process/unix.rs']
    expected_current_hash = '678ff28a121f84f6d6a57ab10dd86f6a6bedb15f32c80bbc9074acc80a32b558'
    if current_hash != expected_current_hash:
        raise RuntimeError(f'frozen production/test source hash mismatch: {current_hash}')
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if head != 'fd86c9bb7e3770deadf0276decd28a7d73ea1f01':
        raise RuntimeError(f'unexpected baseline HEAD: {head}')
    baseline_unix = subprocess.check_output(
        ['git', '-C', str(repo), 'show', 'fd86c9bb7e3770deadf0276decd28a7d73ea1f01:src/packages/sys/process/unix.rs']
    ).decode()
    current_unix = (repo / 'src/packages/sys/process/unix.rs').read_text()
    baseline_with_test = insert_test(baseline_unix, current_unix)
    baseline_path = runtime / 'baseline-unix.rs'
    baseline_path.write_text(baseline_with_test)
    baseline_hash = hashlib.sha256(baseline_with_test.encode()).hexdigest()
    exported_baseline = proof_dir / 'reaped-driver-unwind.baseline-unix.rs'
    exported_baseline.write_bytes(baseline_with_test.encode())
    print(f'head={head}', flush=True)
    print(f'current_source_manifest={hashes!r}', flush=True)
    print(f'baseline_unix_original_sha256={hashlib.sha256(baseline_unix.encode()).hexdigest()}', flush=True)
    print(f'baseline_unix_with_only_test_sha256={baseline_hash}', flush=True)
    print(f'candidate_harness_sha256={hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}', flush=True)

    source = runtime / 'source'
    source.mkdir()
    archive = runtime / 'head.tar'
    with archive.open('wb') as output:
        proc = subprocess.Popen(['git', '-C', str(repo), 'archive', head], stdout=output, stderr=subprocess.PIPE)
        if proc.wait(timeout=120) != 0:
            raise RuntimeError('git archive failed: ' + proc.stderr.read().decode(errors='replace'))
    run_bounded(['tar', '-xf', str(archive), '-C', str(source)], repo, dict(os.environ), 0, 'extract-head')
    archive.unlink()
    for name in source_paths[:-1]:
        shutil.copy2(repo / name, source / name)
    unix_path = source / 'src/packages/sys/process/unix.rs'
    unix_path.write_bytes(baseline_with_test.encode())
    baseline_manifest = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in source_paths}
    if baseline_manifest['src/packages/sys/process/unix.rs'] != baseline_hash:
        raise RuntimeError('baseline source write/readback mismatch')
    print(f'baseline_private_manifest={baseline_manifest!r}', flush=True)

    lock_source = repo / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
    accepted_lock_hash = hashlib.sha256(lock_source.read_bytes()).hexdigest()
    if accepted_lock_hash != '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa':
        raise RuntimeError(f'accepted dependency lock changed: {accepted_lock_hash}')
    private_lock = source / 'Cargo.lock'
    lock = lock_source.read_text()
    start = lock.index('name = "rhai"\nversion = "1.26.1"')
    end = lock.index('\n]\n', start)
    package = lock[start:end]
    if ' "libc",' in package or package.count(' "libm",\n') != 1:
        raise RuntimeError('accepted lock direct-edge location changed')
    lock = lock[:start] + package.replace(' "libm",\n', ' "libm",\n "libc",\n', 1) + lock[end:]
    private_lock.write_text(lock)
    print(f'accepted_lock_sha256={accepted_lock_hash}', flush=True)
    print(f'private_lock_sha256={hashlib.sha256(private_lock.read_bytes()).hexdigest()}', flush=True)

    env = dict(os.environ)
    env.update({
        'CARGO_HOME': str(runtime / 'cargo-home'),
        'RUSTUP_HOME': str(runtime / 'rustup-home'),
        'CARGO_TARGET_DIR': str(runtime / 'target'),
        'CARGO_BUILD_JOBS': '2',
        'CARGO_INCREMENTAL': '0',
        'CARGO_PROFILE_DEV_DEBUG': '0',
        'CARGO_PROFILE_TEST_DEBUG': '0',
    })
    install_log = run_bounded(
        ['rustup', 'toolchain', 'install', '1.77.2', '--profile', 'minimal', '--no-self-update'],
        source, env, 0, 'install-rust-1.77.2', timeout=180,
    )
    print(f'toolchain_install_output={install_log.read_text(errors="replace")[-4096:]}', flush=True)
    for tool, args in [('rustc', ['rustc', '--version']), ('cargo', ['cargo', '--version'])]:
        tool_log = run_bounded(['rustup', 'run', '1.77.2', *args], source, env, 0, f'{tool}-version')
        print(f'{tool}_version={tool_log.read_text().strip()}', flush=True)

    command = ['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', 'testing-environ,sys,metadata', '--lib', 'reaped_driver_unwind_retires_completed_owner_once', '--', '--nocapture']
    baseline_log = run_bounded(command, source, env, 101, 'known-broken-baseline-red')
    baseline_output = baseline_log.read_text(errors='replace')
    if 'reaped-driver-unwind child_pid=' not in baseline_output or 'reap=ESRCH' not in baseline_output or 'reaped owner slot was not retired' not in baseline_output:
        raise RuntimeError('baseline did not fail at the intended retired-slot assertion after actual child reap')
    print('baseline_red_contract=slot retirement fails after real child wait and ESRCH receipt', flush=True)

    candidate_source = (repo / 'src/packages/sys/process/unix.rs').read_bytes()
    exported_candidate = proof_dir / 'reaped-driver-unwind.candidate-unix.rs'
    exported_candidate.write_bytes(candidate_source)
    unix_path.write_bytes(candidate_source)
    candidate_hash = hashlib.sha256(unix_path.read_bytes()).hexdigest()
    if candidate_hash != expected_current_hash:
        raise RuntimeError('candidate source was not copied byte-for-byte')
    print(f'candidate_unix_sha256={candidate_hash}', flush=True)

    restored = unix_path.read_bytes()
    line = b'            retired.load(Ordering::Acquire),\n'
    wrong = b'            !retired.load(Ordering::Acquire),\n'
    message = b'            "reaped owner slot was not retired"\n'
    wrong_message = b'            "wrong-control expected owner slot to remain unretired"\n'
    test_start = restored.index(b'fn reaped_driver_unwind_retires_completed_owner_once')
    test_end = restored.index(b'fn assert_pid_present', test_start)
    test_source = restored[test_start:test_end]
    if test_source.count(line) != 1:
        raise RuntimeError('wrong-retirement control target is not unique')
    if test_source.count(message) != 1:
        raise RuntimeError('wrong-retirement diagnostic target is not unique')
    try:
        wrong_test = test_source.replace(line, wrong, 1).replace(message, wrong_message, 1)
        unix_path.write_bytes(restored[:test_start] + wrong_test + restored[test_end:])
        wrong_log = run_bounded(command, source, env, 101, 'wrong-retirement-control')
        wrong_output = wrong_log.read_text(errors='replace')
        if 'reaped-driver-unwind child_pid=' not in wrong_output or 'reap=ESRCH' not in wrong_output or 'wrong-control expected owner slot to remain unretired' not in wrong_output:
            raise RuntimeError('wrong control did not fail specifically at the slot retirement assertion')
    finally:
        unix_path.write_bytes(restored)
    if hashlib.sha256(unix_path.read_bytes()).hexdigest() != candidate_hash:
        raise RuntimeError('candidate source was not byte-for-byte restored after wrong control')
    restored_log = run_bounded(command, source, env, 0, 'candidate-restored-green')
    restored_output = restored_log.read_text(errors='replace')
    if 'running 1 test' not in restored_output or 'reaped_driver_unwind_retires_completed_owner_once ... ok' not in restored_output:
        raise RuntimeError('restored candidate check did not pass the exact owner-unwind test')
    owner_suite = ['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', 'testing-environ,sys,metadata', '--lib', 'packages::sys::process::unix::tests::', '--', '--test-threads=1', '--nocapture']
    owner_suite_log = run_bounded(owner_suite, source, env, 0, 'restored-unix-owner-regressions', timeout=300)
    owner_suite_output = owner_suite_log.read_text(errors='replace')
    suite_result = re.search(r'test result: ok\. (\d+) passed;', owner_suite_output)
    if suite_result is None or int(suite_result.group(1)) == 0:
        raise RuntimeError('restored Unix owner regression filter ran no tests or failed')
    final_manifest = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in source_paths}
    print(f'final_private_manifest={final_manifest!r}', flush=True)
    print(f'exported_baseline_path={exported_baseline}', flush=True)
    print(f'exported_baseline_sha256={hashlib.sha256(exported_baseline.read_bytes()).hexdigest()}', flush=True)
    print(f'exported_candidate_path={exported_candidate}', flush=True)
    print(f'exported_candidate_sha256={hashlib.sha256(exported_candidate.read_bytes()).hexdigest()}', flush=True)
finally:
    sample_storage()
    print(f'sampled_storage_max_kib={max(storage_samples) if storage_samples else "unavailable"}', flush=True)
    print(f'sampled_storage_readings={storage_samples!r}', flush=True)
