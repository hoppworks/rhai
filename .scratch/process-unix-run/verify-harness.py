import difflib
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

repo = Path('/Users/hoppworks/projects/rhai-process-unix-run')
runtime = Path(os.path.abspath(os.environ['AGENT_RUNTIME_DIR']))
print('runtime_path=' + str(runtime), flush=True)
print('private_working_directory=' + str(runtime), flush=True)
print('os=' + platform.platform(), flush=True)
print('python=' + sys.version.replace('\n', ' '), flush=True)
for tool in ('python3', 'git', 'tar', 'rustup', 'shasum'):
    print(f'tool_path_{tool}=' + str(shutil.which(tool)), flush=True)

MAX_SAMPLED_KIB = 1_572_864
storage_samples = []
command_index = 0


def sample_storage():
    try:
        sampled = subprocess.run(
            ['du', '-sk', str(runtime)], capture_output=True, text=True, timeout=5, check=True
        )
        kib = int(sampled.stdout.split()[0])
    except Exception as exc:
        raise RuntimeError(f'bounded storage sampler failed: {exc}') from exc
    storage_samples.append(kib)
    print(f'storage_sample_kib={kib}', flush=True)
    if kib >= MAX_SAMPLED_KIB:
        raise RuntimeError(f'sampled private runtime reached conservative stop threshold {MAX_SAMPLED_KIB} KiB')
    return kib


def print_case_log(log_path, complete):
    content = log_path.read_bytes()
    cap = 256 * 1024
    clipped = len(content) > cap
    tail = content[-cap:] if clipped else content
    print(f'case_log_output_begin label={log_path.name} complete={str(complete).lower()} bytes={len(content)} clipped={str(clipped).lower()}', flush=True)
    if clipped:
        print('[earlier case output truncated; retained final 256 KiB]', flush=True)
    print(tail.decode(errors='replace'), flush=True)
    print('case_log_output_end', flush=True)


def run_bounded(argv, cwd, env=None, expected=None, timeout=120, label='command'):
    global command_index
    command_index += 1
    log_path = runtime / f'{command_index:02d}-{label}.log'
    command_env = dict(os.environ if env is None else env)
    print('case_argv=' + repr(argv), flush=True)
    print('case_cwd=' + str(cwd), flush=True)
    print('case_log=' + str(log_path), flush=True)
    with log_path.open('wb') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=command_env, stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
        deadline = time.monotonic() + timeout
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'{label} exceeded external watchdog {timeout}s')
                sample_storage()
                time.sleep(1)
            status = proc.returncode
        except BaseException:
            log.flush()
            print_case_log(log_path, complete=False)
            # The enclosing run_scoped owner will terminate this inherited process group.
            raise
    sample_storage()
    print(f'case_status={status} label={label}', flush=True)
    print_case_log(log_path, complete=True)
    if expected is not None and status != expected:
        raise RuntimeError(f'{label} returned {status}, expected {expected}')
    return status, log_path


try:
    runtime.mkdir(parents=True, exist_ok=True)
    changed_inputs = [
        'Cargo.toml',
        'src/packages/sys/fs.rs',
        'src/packages/sys/mod.rs',
        'src/packages/sys/process.rs',
        'src/packages/sys/process/unix.rs',
        'tests/sys_process.rs',
    ]
    test_inputs = ['tests/sys_process_report.rs', 'tests/sys_support/mod.rs']
    source_inputs = changed_inputs + test_inputs
    baseline_hashes = {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in source_inputs}
    print('source_head=' + subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
    print('dirty_input_status=' + repr(subprocess.check_output(['git', '-C', str(repo), 'status', '--short', '--untracked-files=all'], text=True).splitlines()), flush=True)
    print('source_manifest=' + repr(baseline_hashes), flush=True)
    print('harness_sha256=' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), flush=True)
    runner = Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
    print('runner_sha256=' + hashlib.sha256(runner.read_bytes()).hexdigest(), flush=True)
    wrapper = repo / '.scratch/process-unix-run/run-verification.sh'
    print('wrapper_sha256=' + hashlib.sha256(wrapper.read_bytes()).hexdigest(), flush=True)

    source = runtime / 'source'
    source.mkdir()
    archive_path = runtime / 'baseline.tar'
    with archive_path.open('wb') as archive:
        p = subprocess.Popen(['git', '-C', str(repo), 'archive', 'HEAD'], stdout=archive, stderr=subprocess.PIPE, start_new_session=False)
        try:
            deadline = time.monotonic() + 120
            while p.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('git archive exceeded external watchdog 120s')
                sample_storage()
                time.sleep(1)
            if p.returncode != 0:
                raise RuntimeError('git archive failed: ' + p.stderr.read().decode(errors='replace'))
        except BaseException:
            raise
    sample_storage()
    run_bounded(['tar', '-xf', str(archive_path), '-C', str(source)], repo, timeout=120, expected=0, label='extract-baseline')
    archive_path.unlink()
    for name in changed_inputs:
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / name, destination)
        sample_storage()
    copied_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in source_inputs}
    if copied_hashes != baseline_hashes:
        raise RuntimeError(f'private copied source differs from frozen manifest: {copied_hashes!r}')
    print('private_source_manifest=' + repr(copied_hashes), flush=True)
    print('private_source_cwd=' + str(source), flush=True)

    accepted = repo / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
    accepted_hash = hashlib.sha256(accepted.read_bytes()).hexdigest()
    expected_lock_hash = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
    if accepted_hash != expected_lock_hash:
        raise RuntimeError(f'accepted lock hash changed: {accepted_hash}')
    private_lock = source / 'Cargo.lock'
    shutil.copy2(accepted, private_lock)
    original_lock = private_lock.read_text()
    start = original_lock.index('name = "rhai"\nversion = "1.26.1"')
    end = original_lock.index('\n]\n', start)
    package = original_lock[start:end]
    if ' "libc",' in package:
        raise RuntimeError('accepted lock already has direct libc edge; review changed')
    needle = ' "libm",\n'
    if package.count(needle) != 1:
        raise RuntimeError('cannot locate unique direct dependency insertion point')
    expected_lock = original_lock[:start] + package.replace(needle, needle + ' "libc",\n', 1) + original_lock[end:]
    private_lock.write_text(expected_lock)
    if private_lock.read_text() != expected_lock:
        raise RuntimeError('private lock does not equal exact direct-edge update')
    print('accepted_lock_sha256=' + accepted_hash, flush=True)
    print('private_lock_diff_begin', flush=True)
    print(''.join(difflib.unified_diff(original_lock.splitlines(True), expected_lock.splitlines(True), fromfile='accepted', tofile='private')), flush=True)
    print('private_lock_diff_end', flush=True)
    print('private_lock_sha256=' + hashlib.sha256(private_lock.read_bytes()).hexdigest(), flush=True)

    env = dict(os.environ, CARGO_HOME=str(runtime / 'cargo-home'), RUSTUP_HOME=str(runtime / 'rustup-home'), CARGO_TARGET_DIR=str(runtime / 'target'), CARGO_BUILD_JOBS='2')
    run_bounded(['rustup', 'toolchain', 'install', '1.77.2', '--profile', 'minimal', '--no-self-update'], source, env, expected=0, timeout=120, label='install-rust-1.77.2')
    _, rustc_log = run_bounded(['rustup', 'run', '1.77.2', 'rustc', '--version'], source, env, expected=0, label='rustc-version')
    _, cargo_log = run_bounded(['rustup', 'run', '1.77.2', 'cargo', '--version'], source, env, expected=0, label='cargo-version')
    print('rustc_version=' + rustc_log.read_text().strip(), flush=True)
    print('cargo_version=' + cargo_log.read_text().strip(), flush=True)

    features = 'testing-environ,sys,metadata'
    run_bounded(['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--test', 'sys_process', '--', '--nocapture'], source, env, expected=0, timeout=180, label='sys-process')
    run_bounded(['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--test', 'sys_process_report', '--', '--nocapture'], source, env, expected=0, timeout=120, label='sys-process-report')

    fixture = source / 'tests/sys_process.rs'
    restored = fixture.read_bytes()
    expected_line = b'expected_stdout.extend_from_slice(&[0x00, 0x41, 0xff]);'
    wrong_line = b'expected_stdout.extend_from_slice(&[0x00, 0x42, 0xff]);'
    if restored.count(expected_line) != 1:
        raise RuntimeError('wrong-expectation control target must occur exactly once')
    try:
        fixture.write_bytes(restored.replace(expected_line, wrong_line, 1))
        status, control_log = run_bounded(
            ['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--test', 'sys_process', 'run_raw_captures_exact_stream_bytes_and_nonzero_exit_as_data', '--', '--exact', '--nocapture'],
            source, env, timeout=120, label='wrong-expectation-control')
        output = control_log.read_text(errors='replace')
        print('wrong_control_output_begin', flush=True)
        print(output[-10000:], flush=True)
        print('wrong_control_output_end', flush=True)
        if status != 101 or 'run_raw_captures_exact_stream_bytes_and_nonzero_exit_as_data' not in output or 'assertion `left == right` failed' not in output or '65, 255]' not in output or '66, 255]' not in output:
            raise RuntimeError('wrong expectation control did not fail specifically on the intended stdout byte assertion')
    finally:
        fixture.write_bytes(restored)
    restored_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
    if restored_hash != copied_hashes['tests/sys_process.rs']:
        raise RuntimeError('private fixture was not byte-for-byte restored')
    print('restored_fixture_sha256=' + restored_hash, flush=True)
    run_bounded(['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--test', 'sys_process', '--', '--nocapture'], source, env, expected=0, timeout=180, label='sys-process-restored')
    run_bounded(
        ['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', 'testing-environ,sys,metadata,no_index', '--test', 'sys_process', 'scalar_run_with_cwd_works_without_collections', '--', '--exact', '--nocapture'],
        source, env, expected=0, timeout=180, label='no-index-scalar-os-proof')
    final_private_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in source_inputs}
    if final_private_hashes != copied_hashes:
        raise RuntimeError('private tested source changed after restored verification')
    print('final_tested_source_manifest=' + repr(final_private_hashes), flush=True)
finally:
    try:
        sample_storage()
    except Exception as exc:
        print('final_storage_sample_error=' + repr(exc), flush=True)
        raise
    print('sampled_storage_max_kib=' + str(max(storage_samples) if storage_samples else 'unavailable'), flush=True)
    print('sampled_storage_readings=' + repr(storage_samples), flush=True)
