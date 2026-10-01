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
print('os=' + platform.platform(), flush=True)
print('python=' + sys.version.replace('\n', ' '), flush=True)
for tool in ('python3', 'git', 'tar', 'rustup', 'shasum'):
    print(f'tool_path_{tool}=' + str(shutil.which(tool)), flush=True)

MAX_SAMPLED_KIB = 1_572_864
samples = []


def sample_storage():
    result = subprocess.run(['du', '-sk', str(runtime)], capture_output=True, text=True, timeout=5, check=True)
    kib = int(result.stdout.split()[0])
    samples.append(kib)
    print(f'storage_sample_kib={kib}', flush=True)
    if kib >= MAX_SAMPLED_KIB:
        raise RuntimeError(f'sampled private runtime reached stop threshold {MAX_SAMPLED_KIB} KiB')


def run_case(argv, cwd, env, expected, label, timeout=120):
    print('case_label=' + label, flush=True)
    print('case_argv=' + repr(argv), flush=True)
    print('case_cwd=' + str(cwd), flush=True)
    log_path = runtime / (label + '.log')
    print('case_log=' + str(log_path), flush=True)
    with log_path.open('wb') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            if time.monotonic() >= deadline:
                raise TimeoutError(f'{label} exceeded watchdog {timeout}s')
            sample_storage()
            time.sleep(1)
        status = proc.returncode
    output = log_path.read_text(errors='replace')
    print(f'case_status={status} label={label}', flush=True)
    print(f'case_output_begin label={label}', flush=True)
    print(output[-262144:], flush=True)
    print(f'case_output_end label={label}', flush=True)
    if status != expected:
        raise RuntimeError(f'{label} returned {status}, expected {expected}')
    return output


runtime.mkdir(parents=True, exist_ok=True)
inputs = [
    'Cargo.toml',
    'src/packages/sys/mod.rs',
    'src/packages/sys/process.rs',
    'src/packages/sys/process/unix.rs',
    'tests/sys_process.rs',
]
hashes = {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in inputs}
print('source_head=' + subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('dirty_input_status=' + repr(subprocess.check_output(['git', '-C', str(repo), 'status', '--short', '--untracked-files=all'], text=True).splitlines()), flush=True)
print('source_manifest=' + repr(hashes), flush=True)
print('harness_sha256=' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), flush=True)
runner = Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
print('runner_sha256=' + hashlib.sha256(runner.read_bytes()).hexdigest(), flush=True)
wrapper = repo / '.scratch/process-unix-run/run-inherited-pipe-holder-green.sh'
print('wrapper_sha256=' + hashlib.sha256(wrapper.read_bytes()).hexdigest(), flush=True)
if not Path('/usr/bin/python3').is_file() or not os.access('/usr/bin/python3', os.X_OK):
    raise RuntimeError('fixture requires executable /usr/bin/python3 for raw os.write pipe probes')
probe_version = subprocess.run(['/usr/bin/python3', '--version'], capture_output=True, text=True, timeout=5, check=True)
print('endpoint_probe_executable=/usr/bin/python3', flush=True)
print('endpoint_probe_version=' + (probe_version.stdout or probe_version.stderr).strip(), flush=True)

source = runtime / 'source'
source.mkdir()
archive = runtime / 'baseline.tar'
with archive.open('wb') as target:
    proc = subprocess.Popen(['git', '-C', str(repo), 'archive', 'HEAD'], stdout=target, stderr=subprocess.PIPE, start_new_session=False)
    deadline = time.monotonic() + 120
    while proc.poll() is None:
        if time.monotonic() >= deadline:
            raise TimeoutError('baseline archive exceeded watchdog 120s')
        sample_storage()
        time.sleep(1)
    if proc.returncode != 0:
        raise RuntimeError('git archive failed: ' + proc.stderr.read().decode(errors='replace'))
sample_storage()
run_case(['tar', '-xf', str(archive), '-C', str(source)], repo, dict(os.environ), 0, 'extract-baseline', 120)
archive.unlink()
for name in inputs:
    shutil.copy2(repo / name, source / name)
    sample_storage()
private_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in inputs}
if private_hashes != hashes:
    raise RuntimeError('private source does not match frozen manifest')
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
run_case(['rustup', 'toolchain', 'install', '1.77.2', '--profile', 'minimal', '--no-self-update'], source, env, 0, 'install-rust-1.77.2', 120)
rustc = run_case(['rustup', 'run', '1.77.2', 'rustc', '--version'], source, env, 0, 'rustc-version')
cargo = run_case(['rustup', 'run', '1.77.2', 'cargo', '--version'], source, env, 0, 'cargo-version')
print('rustc_version=' + rustc.strip(), flush=True)
print('cargo_version=' + cargo.strip(), flush=True)

features = 'testing-environ,sys,metadata'
test_name = 'packages::sys::process::unix::tests::inherited_pipe_holder_is_alive_at_timeout_and_fixture_releases_it'
cargo_prefix = ['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--lib', test_name, '--', '--exact', '--nocapture']
private_test = source / 'src/packages/sys/process/unix.rs'
original_tested_bytes = private_test.read_bytes()
# Change only the final expected endpoint-probe result; the holder is reaped before this assertion.
text = private_test.read_text()
needle = '            pipe_probe, "stdout=errno=32 stderr=errno=32\\n",'
assert text.count(needle) == 1
mutated = text.replace(needle, '            pipe_probe, "stdout=errno=13 stderr=errno=13\\n",', 1)
assert mutated.count('            pipe_probe, "stdout=errno=13 stderr=errno=13\\n",') == 1
assert 'public run must cancel both local pipe read endpoints before returning' in mutated
private_test.write_text(mutated)
try:
    control = run_case(cargo_prefix, source, env, 101, 'inherited-pipe-holder-wrong-endpoint-control')
finally:
    private_test.write_bytes(original_tested_bytes)
if hashlib.sha256(private_test.read_bytes()).hexdigest() != hashes['src/packages/sys/process/unix.rs']:
    raise RuntimeError('wrong-endpoint control source was not byte-restored')
if 'running 1 test' not in control or 'test ' + test_name + ' ... FAILED' not in control:
    raise RuntimeError('wrong-endpoint control did not execute the exact test')
if 'public run must cancel both local pipe read endpoints before returning' not in control or 'test ' + test_name + ' ... FAILED' not in control or 'inherited-pipe timeout child_pid=' not in control or 'holder_pid=' not in control or 'probe="stdout=errno=32 stderr=errno=32' not in control or 'reap=ESRCH' not in control:
    raise RuntimeError('wrong-endpoint control missed assertion or cleanup receipt')
output = run_case(cargo_prefix, source, env, 0, 'inherited-pipe-holder-green')
if 'running 1 test' not in output or 'test ' + test_name + ' ... ok' not in output or '1 passed' not in output:
    raise RuntimeError('GREEN did not run and pass the exact retained-owner test')
if 'external watchdog' in output or 'error[E' in output or 'could not compile' in output:
    raise RuntimeError('GREEN was masked by watchdog or compile/setup failure')
if 'inherited-pipe timeout child_pid=' not in output or 'inherited-pipe holder_pid=' not in output or 'inherited-pipe outer child_pid=' not in output or 'both=ESRCH' not in output:
    raise RuntimeError('GREEN omitted direct-child and holder liveness/cleanup receipts')
if 'before:nonce-before-timeout' not in output or 'after:nonce-after-return' not in output or 'api_returned_after_pre_ack=true' not in output:
    raise RuntimeError('GREEN omitted ordered pre-timeout and post-return challenge receipts')
if 'captured_stdout_ready=true captured_stderr_ready=true' not in output:
    raise RuntimeError('GREEN omitted successful initial output capture on both inherited pipes')
test_source = private_test.read_text()
for assertion in ('public run must cancel both local pipe read endpoints before returning', 'stdout_complete=false stderr_complete=false'):
    if assertion not in test_source:
        raise RuntimeError('GREEN source omits acceptance assertion: ' + assertion)
print('green_classification=inherited_pipe_holder_alive_incomplete_capture_and_fixture_reaped', flush=True)
final_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in inputs}
if final_hashes != hashes:
    raise RuntimeError('tested private sources changed after initial overlay')
print('final_tested_source_manifest=' + repr(final_hashes), flush=True)
sample_storage()
print('sampled_storage_max_kib=' + str(max(samples)), flush=True)
