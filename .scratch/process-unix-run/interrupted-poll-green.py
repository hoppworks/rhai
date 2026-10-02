import hashlib
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

repo = Path('/Users/hoppworks/projects/rhai-process-unix-run')
runtime = Path(os.path.abspath(os.environ['AGENT_RUNTIME_DIR']))
MAX_SAMPLED_KIB = 1_572_864
samples = []
command_index = 0
inputs = [
    'Cargo.toml',
    'src/packages/sys/mod.rs',
    'src/packages/sys/process.rs',
    'src/packages/sys/process/unix.rs',
]
test_name = 'packages::sys::process::unix::tests::interrupted_poll_does_not_skip_public_deadline'


def sample_storage():
    for attempt in range(2):
        result = subprocess.run(['du', '-sk', str(runtime)], capture_output=True, text=True, timeout=5, check=False)
        if result.returncode == 0:
            fields = result.stdout.split()
            if not fields:
                raise RuntimeError('du returned success without a storage measurement')
            kib = int(fields[0])
            samples.append(kib)
            print(f'storage_sample_kib={kib}', flush=True)
            if kib >= MAX_SAMPLED_KIB:
                raise RuntimeError(f'sampled private runtime reached stop threshold {MAX_SAMPLED_KIB} KiB')
            return
        print(f'storage_sample_error attempt={attempt + 1} status={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}', flush=True)
        if attempt == 0:
            time.sleep(0.05)
    raise RuntimeError('du storage sample failed after one bounded retry')


def print_log(path, complete):
    data = path.read_bytes()
    cap = 256 * 1024
    clipped = len(data) > cap
    print(f'command_output_begin name={path.name} complete={str(complete).lower()} bytes={len(data)} clipped={str(clipped).lower()}', flush=True)
    if clipped:
        print('[earlier output truncated; retained final 256 KiB]', flush=True)
    print((data[-cap:] if clipped else data).decode(errors='replace'), flush=True)
    print('command_output_end', flush=True)


def run_bounded(argv, cwd, env, expected, name, timeout=180):
    global command_index
    command_index += 1
    log = runtime / f'{command_index:02d}-{name}.log'
    print(f'command_name={name}', flush=True)
    print('command_argv=' + repr(argv), flush=True)
    print('command_cwd=' + str(cwd), flush=True)
    print('command_log=' + str(log), flush=True)
    with log.open('wb') as output:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=False)
        deadline = time.monotonic() + timeout
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'{name} exceeded external watchdog {timeout}s')
                sample_storage()
                time.sleep(1)
            status = proc.returncode
        except BaseException:
            print_log(log, False)
            raise
    sample_storage()
    print(f'command_status={status} name={name}', flush=True)
    print_log(log, True)
    if status != expected:
        raise RuntimeError(f'{name} returned {status}, expected {expected}')
    return log.read_text(errors='replace')


def verify_reaped(output, label):
    import re
    match = re.search(r'interrupted-poll child_pid=(\d+) reap=ESRCH elapsed_ms=(\d+) injected=(\d+)', output)
    if not match:
        raise RuntimeError(f'{label} omitted child PID/reap/elapsed/injection receipt')
    pid, elapsed, injected = map(int, match.groups())
    if not 0 < injected <= 3000:
        raise RuntimeError(f'{label} observed invalid injected-interruption count {injected}')
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        print(f'external_pid_readback pid={pid} result=ESRCH label={label}', flush=True)
    else:
        raise RuntimeError(f'{label} exact fixture child {pid} still exists after test')
    return elapsed


runtime.mkdir(parents=True, exist_ok=True)
print('runtime_path=' + str(runtime), flush=True)
print('os=' + platform.platform(), flush=True)
print('python=' + sys.version.replace('\n', ' '), flush=True)
for tool in ('python3', 'git', 'tar', 'rustup', 'shasum'):
    print(f'tool_path_{tool}=' + str(shutil.which(tool)), flush=True)
hashes = {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in inputs}
print('source_head=' + subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('dirty_input_status=' + repr(subprocess.check_output(['git', '-C', str(repo), 'status', '--short', '--untracked-files=all'], text=True).splitlines()), flush=True)
print('source_manifest=' + repr(hashes), flush=True)
print('harness_sha256=' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), flush=True)
runner = Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
print('runner_sha256=' + hashlib.sha256(runner.read_bytes()).hexdigest(), flush=True)
wrapper = repo / '.scratch/process-unix-run/run-interrupted-poll-green.sh'
print('wrapper_sha256=' + hashlib.sha256(wrapper.read_bytes()).hexdigest(), flush=True)

source = runtime / 'source'
source.mkdir()
archive = runtime / 'baseline.tar'
with archive.open('wb') as output:
    proc = subprocess.Popen(['git', '-C', str(repo), 'archive', 'HEAD'], stdout=output, stderr=subprocess.PIPE, start_new_session=False)
    deadline = time.monotonic() + 120
    while proc.poll() is None:
        if time.monotonic() >= deadline:
            raise TimeoutError('git archive exceeded watchdog')
        sample_storage()
        time.sleep(1)
    if proc.returncode:
        raise RuntimeError('git archive failed: ' + proc.stderr.read().decode(errors='replace'))
sample_storage()
run_bounded(['tar', '-xf', str(archive), '-C', str(source)], repo, dict(os.environ), 0, 'extract-baseline', 120)
archive.unlink()
for name in inputs:
    (source / name).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / name, source / name)
private_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in inputs}
if private_hashes != hashes:
    raise RuntimeError('private source overlay does not match frozen manifest')
print('private_source_manifest=' + repr(private_hashes), flush=True)
print('private_source=' + str(source), flush=True)

accepted_lock = repo / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
accepted_hash = hashlib.sha256(accepted_lock.read_bytes()).hexdigest()
if accepted_hash != '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa':
    raise RuntimeError('accepted lock hash mismatch: ' + accepted_hash)
private_lock = source / 'Cargo.lock'
shutil.copy2(accepted_lock, private_lock)
lock_text = private_lock.read_text()
start = lock_text.index('name = "rhai"\nversion = "1.26.1"')
end = lock_text.index('\n]\n', start)
package = lock_text[start:end]
needle = ' "libm",\n'
if package.count(needle) != 1 or ' "libc",' in package:
    raise RuntimeError('accepted lock direct-edge insertion point changed')
private_lock.write_text(lock_text[:start] + package.replace(needle, needle + ' "libc",\n', 1) + lock_text[end:])
print('accepted_lock_sha256=' + accepted_hash, flush=True)
print('private_lock_sha256=' + hashlib.sha256(private_lock.read_bytes()).hexdigest(), flush=True)

env = dict(os.environ, CARGO_HOME=str(runtime / 'cargo-home'), RUSTUP_HOME=str(runtime / 'rustup-home'), CARGO_TARGET_DIR=str(runtime / 'target'), CARGO_BUILD_JOBS='2')
run_bounded(['rustup', 'toolchain', 'install', '1.77.2', '--profile', 'minimal', '--no-self-update'], source, env, 0, 'install-rust-1.77.2', 120)
rustc = run_bounded(['rustup', 'run', '1.77.2', 'rustc', '--version'], source, env, 0, 'rustc-version')
cargo = run_bounded(['rustup', 'run', '1.77.2', 'cargo', '--version'], source, env, 0, 'cargo-version')
print('rustc_version=' + rustc.strip(), flush=True)
print('cargo_version=' + cargo.strip(), flush=True)

cargo_prefix = ['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', 'testing-environ,sys,metadata', '--lib', test_name, '--', '--exact', '--nocapture']
private_test = source / 'src/packages/sys/process/unix.rs'
original = private_test.read_bytes()
original_line = b'            elapsed < Duration::from_millis(1500),'
wrong_line = b'            elapsed < Duration::from_millis(1),'
wrong_message = b'            "wrong-control: deliberately impossible 1ms bound elapsed_ms={} injected={}",'
original_message = b'            "poll EINTR handling delayed a 100ms public deadline: elapsed_ms={} injected={}",'
if original.count(original_line) != 1 or original.count(original_message) != 1:
    raise RuntimeError('wrong-control assertion target is not unique')
try:
    private_test.write_bytes(original.replace(original_line, wrong_line, 1).replace(original_message, wrong_message, 1))
    control = run_bounded(cargo_prefix, source, env, 101, 'wrong-deadline-expectation')
    if 'running 1 test' not in control or f'test {test_name} ... FAILED' not in control:
        raise RuntimeError('wrong control did not execute the exact test')
    if 'wrong-control: deliberately impossible 1ms bound' not in control:
        raise RuntimeError('wrong control did not fail at the deliberately wrong expectation')
    elapsed = verify_reaped(control, 'wrong-control')
    if elapsed >= 1500:
        raise RuntimeError(f'wrong-control call exceeded deadline bound: {elapsed}ms')
finally:
    private_test.write_bytes(original)
if hashlib.sha256(private_test.read_bytes()).hexdigest() != hashes['src/packages/sys/process/unix.rs']:
    raise RuntimeError('private source was not byte-restored before the GREEN run')
if 'wrong-control: deliberately impossible 1ms bound' not in control:
    raise RuntimeError('wrong control did not fail at the deliberately wrong expectation')
restored = run_bounded(cargo_prefix, source, env, 0, 'interrupted-poll-deadline-green')
if 'running 1 test' not in restored or f'test {test_name} ... ok' not in restored or '1 passed' not in restored:
    raise RuntimeError('restored interrupted-poll test did not run and pass exactly once')
if 'poll EINTR handling delayed a 100ms public deadline' in restored or 'external watchdog' in restored or 'error[E' in restored or 'could not compile' in restored:
    raise RuntimeError('GREEN was masked by a failed assertion, watchdog or compile/setup failure')
elapsed = verify_reaped(restored, 'restored-green')
if elapsed >= 1500:
    raise RuntimeError(f'GREEN public deadline remained late after interrupted-poll handling: {elapsed}ms')
features = 'testing-environ,sys,metadata'
run_bounded(['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--lib', 'packages::sys::process::unix::tests::', '--', '--test-threads=1', '--nocapture'], source, env, 0, 'unix-process-unit-regressions')
run_bounded(['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--test', 'sys_process', '--', '--nocapture'], source, env, 0, 'sys-process-regression')
run_bounded(['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--test', 'sys_process_report', '--', '--nocapture'], source, env, 0, 'sys-process-report-regression')
run_bounded(['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', 'testing-environ,sys,metadata,no_index', '--test', 'sys_process', 'scalar_run_with_cwd_works_without_collections', '--', '--exact', '--nocapture'], source, env, 0, 'no-index-scalar-process-regression')
final_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in inputs}
if final_hashes != hashes:
    raise RuntimeError('final private tested source differs from restored source manifest')
print('final_tested_source_manifest=' + repr(final_hashes), flush=True)
sample_storage()
print('sampled_storage_max_kib=' + str(max(samples)), flush=True)
print('green_classification=interrupted_poll_rechecks_deadline_then_returns_timed_out_map_after_exact_child_reap', flush=True)
