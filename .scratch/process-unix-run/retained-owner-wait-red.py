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
wrapper = repo / '.scratch/process-unix-run/run-retained-owner-wait-red.sh'
print('wrapper_sha256=' + hashlib.sha256(wrapper.read_bytes()).hexdigest(), flush=True)

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
test_name = 'packages::sys::process::unix::tests::non_consuming_cleanup_wait_failure_publishes_frozen_snapshot'
output = run_case(
    ['rustup', 'run', '1.77.2', 'cargo', 'test', '--locked', '--features', features, '--lib', test_name, '--', '--exact', '--nocapture'],
    source, env, 101, 'retained-owner-wait-failure-red')
if 'running 1 test' not in output or 'test ' + test_name + ' ... FAILED' not in output or '1 failed' not in output:
    raise RuntimeError('RED did not execute and fail the exact retained-owner test')
if 'non-consuming wait failure must publish an unavailable exit snapshot' not in output:
    raise RuntimeError('RED did not reach the intended frozen-incomplete-snapshot assertion')
if 'external watchdog had to release the child' in output or 'error[E' in output or 'could not compile' in output:
    raise RuntimeError('RED was masked by watchdog release or compile/setup failure')
if 'retained-owner-wait child_pid=' not in output or 'reap=ESRCH' not in output:
    raise RuntimeError('RED omitted exact child PID and independent ESRCH cleanup receipt')
print('red_classification=foreground_retried_nonconsuming_wait_instead_of_publishing_snapshot', flush=True)
final_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in inputs}
if final_hashes != hashes:
    raise RuntimeError('tested private sources changed after initial overlay')
print('final_tested_source_manifest=' + repr(final_hashes), flush=True)
sample_storage()
print('sampled_storage_max_kib=' + str(max(samples)), flush=True)
