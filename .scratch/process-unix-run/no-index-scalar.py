import hashlib, os, platform, shutil, subprocess, sys, time
from pathlib import Path

repo = Path('/Users/hoppworks/projects/rhai-process-unix-run')
runtime = Path(os.path.abspath(os.environ['AGENT_RUNTIME_DIR']))
MAX_SAMPLED_KIB = 1_572_864
samples = []
inputs = ['Cargo.toml', 'src/packages/sys/mod.rs', 'src/packages/sys/process.rs', 'src/packages/sys/process/unix.rs', 'tests/sys_process.rs']
test_name = 'scalar_run_with_cwd_works_without_collections'
features = 'testing-environ,sys,metadata,no_index'
command_index = 0

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

def read_child_pid(output, label):
    import re
    match = re.search(r'no-index scalar child_pid=(\d+) reap=ESRCH', output)
    if not match:
        raise RuntimeError(f'{label} omitted child reap receipt')
    pid = int(match.group(1))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        print(f'external_pid_readback pid={pid} result=ESRCH label={label}', flush=True)
    else:
        raise RuntimeError(f'{label} exact child {pid} still exists after test')
    return pid

runtime.mkdir(parents=True, exist_ok=True)
print('runtime_path=' + str(runtime), flush=True)
print('os=' + platform.platform(), flush=True)
print('python=' + sys.version.replace('\n', ' '), flush=True)
print('source_head=' + subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
hashes = {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in inputs}
print('source_manifest=' + repr(hashes), flush=True)
print('harness_sha256=' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), flush=True)
runner = Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
print('runner_sha256=' + hashlib.sha256(runner.read_bytes()).hexdigest(), flush=True)
wrapper = repo / '.scratch/process-unix-run/run-no-index-scalar.sh'
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

env = dict(os.environ, CARGO_HOME=str(runtime / 'cargo-home'), RUSTUP_HOME=str(runtime / 'rustup-home'), CARGO_TARGET_DIR=str(runtime / 'target'), CARGO_BUILD_JOBS='2', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0', CARGO_PROFILE_TEST_DEBUG='0')
run_bounded(['rustup', 'toolchain', 'install', '1.77.2', '--profile', 'minimal', '--no-self-update'], source, env, 0, 'install-rust-1.77.2', 120)
rustc = run_bounded(['rustup', 'run', '1.77.2', 'rustc', '--version'], source, env, 0, 'rustc-version')
cargo = run_bounded(['rustup', 'run', '1.77.2', 'cargo', '--version'], source, env, 0, 'cargo-version')
print('rustc_version=' + rustc.strip(), flush=True)
print('cargo_version=' + cargo.strip(), flush=True)

cargo_prefix = ['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--test', 'sys_process', test_name, '--', '--exact', '--nocapture']
private_test = source / 'tests/sys_process.rs'
original = private_test.read_bytes()
expected = b'assert_eq!(result["stdout"].as_immutable_string_ref().unwrap().as_str(), format!("{}\\n", expected.display()));'
wrong = b'assert_eq!(result["stdout"].as_immutable_string_ref().unwrap().as_str(), format!("{}\\nwrong-control", expected.display()));'
if original.count(expected) != 1:
    raise RuntimeError('no_index expected-output assertion is not unique')
try:
    private_test.write_bytes(original.replace(expected, wrong, 1))
    control = run_bounded(cargo_prefix, source, env, 101, 'wrong-no-index-output-expectation')
    if 'running 1 test' not in control or f'test {test_name} ... FAILED' not in control:
        raise RuntimeError('wrong control did not execute the exact no_index test')
    if 'wrong-control' not in control:
        raise RuntimeError('wrong control did not fail at the deliberately wrong output')
    control_pid = read_child_pid(control, 'wrong-control')
finally:
    private_test.write_bytes(original)
if hashlib.sha256(private_test.read_bytes()).hexdigest() != hashes['tests/sys_process.rs']:
    raise RuntimeError('private test source was not restored before GREEN')
restored = run_bounded(cargo_prefix, source, env, 0, 'no-index-scalar-green')
if 'running 1 test' not in restored or f'test {test_name} ... ok' not in restored or '1 passed' not in restored:
    raise RuntimeError('restored no_index scalar test did not run and pass exactly once')
green_pid = read_child_pid(restored, 'restored-green')
final_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in inputs}
if final_hashes != hashes:
    raise RuntimeError('final private tested source differs from restored source manifest')
print('final_tested_source_manifest=' + repr(final_hashes), flush=True)
sample_storage()
print('sampled_storage_max_kib=' + str(max(samples)), flush=True)
print(f'no_index_classification=scalar_text_cwd_child_reaped_control_pid={control_pid}_green_pid={green_pid}', flush=True)
