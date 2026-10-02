import atexit
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path('/Users/hoppworks/projects/rhai-process-unix-run')
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
TOOLCHAIN = Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO = TOOLCHAIN / 'cargo'
OVERLAYS = ['Cargo.toml', 'src/packages/sys/process/unix.rs']
THRESHOLD_KIB = 1_572_864
SAMPLE_CAP = 256 * 1024
EVIDENCE = Path(os.environ['PROCESS_EVIDENCE']).resolve()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pid_is_esrch(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def sample_storage(deadline):
    for attempt in range(1, 3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('storage sample deadline expired')
        timeout = min(5.0, remaining)
        try:
            sample = subprocess.run(['du', '-sk', str(RUNTIME)], capture_output=True, text=True,
                                    timeout=timeout)
        except subprocess.TimeoutExpired as error:
            out = error.stdout.decode(errors='replace') if isinstance(error.stdout, bytes) else error.stdout
            err = error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else error.stderr
            print(f'storage_attempt={attempt} status=timeout timeout_s={timeout:.3f} stdout={out!r} stderr={err!r}', flush=True)
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('two storage samples timed out') from error
            time.sleep(min(.05, max(0.0, deadline - time.monotonic())))
            continue
        print(f'storage_attempt={attempt} status={sample.returncode} stdout={sample.stdout.strip()!r} stderr={sample.stderr.strip()!r}', flush=True)
        if sample.returncode:
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('two storage samples failed')
            time.sleep(min(.05, max(0.0, deadline - time.monotonic())))
            continue
        lines = sample.stdout.strip().splitlines()
        fields = lines[0].split(maxsplit=1) if len(lines) == 1 else []
        if len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(RUNTIME):
            raise RuntimeError(f'storage sample path or value malformed: {sample.stdout!r}')
        kib = int(fields[0])
        if kib >= THRESHOLD_KIB:
            raise RuntimeError(f'sampled storage crossed {THRESHOLD_KIB} KiB')
        return kib
    raise RuntimeError('no successful storage sample')


def run(argv, cwd, env, log):
    print('cargo_argv=' + repr(argv), flush=True)
    with log.open('wb') as output:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output,
                                stderr=subprocess.STDOUT, start_new_session=False)
        print(f'cargo_pid={proc.pid} cargo_pgid={os.getpgid(proc.pid)}', flush=True)
        deadline = time.monotonic() + 540
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Cargo exceeded 540s command bound')
                sample_storage(deadline)
                time.sleep(1)
            status = proc.returncode
            print(f'cargo_status={status}', flush=True)
            data = log.read_bytes()
            clipped = len(data) > SAMPLE_CAP
            exported = EVIDENCE.with_name(EVIDENCE.name + '.' + log.stem + '.log')
            shutil.copy2(log, exported)
            print(f'cargo_log_bytes={len(data)} clipped={clipped} full_log_path={exported} full_log_sha256={hashlib.sha256(data).hexdigest()}', flush=True)
            print((data[-SAMPLE_CAP:] if clipped else data).decode(errors='replace'), flush=True)
            sample_storage(deadline)
            return status, data.decode(errors='replace')
        except BaseException:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            data = log.read_bytes()
            exported = EVIDENCE.with_name(EVIDENCE.name + '.' + log.stem + '.log')
            shutil.copy2(log, exported)
            print(f'cargo_terminal_status={proc.returncode} cargo_partial_bytes={len(data)} full_log_path={exported} full_log_sha256={hashlib.sha256(data).hexdigest()}', flush=True)
            print(data[-SAMPLE_CAP:].decode(errors='replace'), flush=True)
            raise


RUNTIME.mkdir(parents=True, exist_ok=True)
(RUNTIME / 'tmp').mkdir(exist_ok=True)
EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
print('phase=development_entered_wait_contract', flush=True)
print(f'python={sys.version.replace(chr(10), " ")}', flush=True)
print('platform=' + platform.platform(), flush=True)
print(f'runtime={RUNTIME}', flush=True)
print(f'runner_pid={os.getpid()} supervisor_pid={os.getppid()} pgid={os.getpgid(0)}', flush=True)
for name in ('cargo', 'rustc', 'rustdoc'):
    path = TOOLCHAIN / name
    if not path.is_file():
        raise RuntimeError(f'missing direct development tool: {path}')
    args = [str(path), '--version', '--verbose'] if name == 'rustc' else [str(path), '--version']
    version = subprocess.check_output(args, text=True, timeout=10).strip().replace('\n', ' | ')
    print(f'{name}_path={path} version={version}', flush=True)

source_hashes = {name: sha(REPO / name) for name in OVERLAYS}
print('source_hashes=' + repr(source_hashes), flush=True)
print('repo_head=' + subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('repo_dirty=' + repr(subprocess.check_output(['git', '-C', str(REPO), 'status', '--short', '--untracked-files=all'], text=True).splitlines()), flush=True)
source = RUNTIME / 'source'
source.mkdir()
archive = RUNTIME / 'baseline.tar'
with archive.open('wb') as output:
    proc = subprocess.Popen(['git', '-C', str(REPO), 'archive', 'HEAD'], stdout=output, stderr=subprocess.PIPE,
                            start_new_session=False)
    deadline = time.monotonic() + 90
    while proc.poll() is None:
        if time.monotonic() >= deadline:
            raise TimeoutError('baseline archive exceeded 90 seconds')
        sample_storage(deadline)
        time.sleep(.5)
    error = proc.stderr.read().decode(errors='replace')
    if proc.returncode:
        raise RuntimeError(f'git archive failed: {error}')
subprocess.run(['tar', '-xf', str(archive), '-C', str(source)], check=True, timeout=90)
archive.unlink()
for name in OVERLAYS:
    destination = source / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / name, destination)
private_hashes = {name: sha(source / name) for name in OVERLAYS}
if private_hashes != source_hashes:
    raise RuntimeError('private overlay source differs from frozen source')


def export_exit_manifests():
    try:
        current_original = {name: sha(REPO / name) for name in OVERLAYS if (REPO / name).is_file()}
        current_private = {name: sha(source / name) for name in OVERLAYS if (source / name).is_file()}
        print('exit_original_hashes=' + repr(current_original), flush=True)
        print('exit_private_hashes=' + repr(current_private), flush=True)
        lock_path = source / 'Cargo.lock'
        if lock_path.is_file():
            print(f'exit_private_lock_sha256={sha(lock_path)}', flush=True)
    except BaseException as error:
        print(f'exit_manifest_error={type(error).__name__}: {error}', flush=True)


atexit.register(export_exit_manifests)
test_file = source / 'src/packages/sys/process/unix.rs'
original_test_source = test_file.read_bytes()
print('private_source_hashes=' + repr(private_hashes), flush=True)

accepted_lock = REPO / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
lock = source / 'Cargo.lock'
shutil.copy2(accepted_lock, lock)
lock_text = lock.read_text()
marker = 'name = "rhai"\nversion = "1.26.1"\ndependencies = [\n'
if lock_text.count(marker) != 1:
    raise RuntimeError('accepted Cargo.lock root package entry changed')
start = lock_text.index(marker)
end = lock_text.index('\n]', start)
section = lock_text[start:end]
if ' "libc",\n' not in section:
    pos = section.index(' "libm",\n')
    section = section[:pos] + ' "libc",\n' + section[pos:]
    lock.write_text(lock_text[:start] + section + lock_text[end:])
print(f'accepted_lock_sha256={sha(accepted_lock)} private_lock_sha256={sha(lock)}', flush=True)

env = dict(os.environ)
for key in ('RUSTUP_TOOLCHAIN', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_BUILD_RUSTC_WRAPPER'):
    env.pop(key, None)
env.update({
    'PATH': f'{TOOLCHAIN}:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',
    'CARGO_HOME': str(RUNTIME / 'cargo-home'),
    'RUSTUP_HOME': str(RUNTIME / 'rustup-home'),
    'CARGO_TARGET_DIR': str(RUNTIME / 'target'),
    'CARGO_BUILD_JOBS': '2',
    'CARGO_INCREMENTAL': '0',
    'CARGO_PROFILE_DEV_DEBUG': '0',
    'CARGO_PROFILE_TEST_DEBUG': '0',
    'RUSTC': str(TOOLCHAIN / 'rustc'),
    'RUSTDOC': str(TOOLCHAIN / 'rustdoc'),
    'TMPDIR': str(RUNTIME / 'tmp'), 'TMP': str(RUNTIME / 'tmp'), 'TEMP': str(RUNTIME / 'tmp'),
})
for directory in ('cargo-home', 'rustup-home'):
    (RUNTIME / directory).mkdir()

test_name = 'packages::sys::process::unix::tests::public_wait_is_cancelled_after_entering_condvar'


def failed_exact_test(output, name):
    started = re.findall(r'(?m)^test ' + re.escape(name) + r' \.\.\.', output)
    section = re.search(r'(?ms)^failures:\n\n(.*?)\n\ntest result:', output)
    failures = re.findall(r'(?m)^    ([^\n]+)$', section.group(1)) if section else []
    summary = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output)
    return 'running 1 test' in output and len(started) == 1 and failures == [name] and summary is not None


def passed_exact_test(output, name):
    started = re.findall(r'(?m)^test ' + re.escape(name) + r' \.\.\.', output)
    summary = re.search(r'(?m)^test result: ok\. 1 passed; 0 failed;', output)
    return 'running 1 test' in output and len(started) == 1 and summary is not None


bad = b'entered_waits > 0,\n            "observer acquired snapshot mutex after Condvar wait entry"'
wrong = b'entered_waits == 0,\n            "observer acquired snapshot mutex after Condvar wait entry"'
if original_test_source.count(bad) != 1:
    raise RuntimeError('wait-entry assertion mutation anchor was not unique')
test_file.write_bytes(original_test_source.replace(bad, wrong, 1))
print(f'wrong_control_source_sha256={sha(test_file)}', flush=True)
command = [str(CARGO), 'test', '--locked', '--lib', '--features', 'testing-environ,sys,sync', test_name, '--', '--exact', '--nocapture', '--test-threads=1']
status, output = run(command, source, env, RUNTIME / 'wrong-control.log')
failed_test = failed_exact_test(output, test_name)
one_failure = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output) is not None
specific = 'observer acquired snapshot mutex after Condvar wait entry' in output
checkpoint = re.search(r'wait-entry checkpoint pid=(\d+) count=(\d+) nonterminal=true', output)
cleanup = re.search(r'wait-entry fixture cleanup pid=(\d+) reap=ESRCH', output)
pid_clean = bool(checkpoint and cleanup and checkpoint.group(1) == cleanup.group(1)
                 and int(checkpoint.group(2)) > 0 and pid_is_esrch(int(checkpoint.group(1))))
print(f'wrong_control status={status} exact_failed_test={failed_test} one_failure={one_failure} intended_assertion={specific} wait_checkpoint={checkpoint.group(0) if checkpoint else None!r} fixture_reap={cleanup.group(0) if cleanup else None!r} pid_receipt_consistent={pid_clean}', flush=True)
test_file.write_bytes(original_test_source)
restored = sha(test_file) == source_hashes['src/packages/sys/process/unix.rs']
print(f'candidate_restored={restored}', flush=True)
if not (status == 101 and failed_test and one_failure and specific and checkpoint and cleanup and pid_clean and restored):
    raise RuntimeError('entered-wait wrong control missed its specific failure or exact cleanup')

status, output = run(command, source, env, RUNTIME / 'green.log')
passed = (status == 0 and passed_exact_test(output, test_name)
          and 'shared-child entered-wait pid=' in output
          and 'waiter_woke=true reap=ESRCH' in output)
final_hashes = {name: sha(source / name) for name in OVERLAYS}
original_final = {name: sha(REPO / name) for name in OVERLAYS}
unchanged = final_hashes == private_hashes and original_final == source_hashes
print('final_private_hashes=' + repr(final_hashes), flush=True)
print('final_original_hashes=' + repr(original_final), flush=True)
print(f'entered_wait_green status={status} passed={passed} source_unchanged={unchanged}', flush=True)
if not (passed and unchanged):
    raise RuntimeError('entered-wait restored test or source manifests failed')
print('classification=development_only_entered_wait; not_msrv_or_release_acceptance; broader_lifecycle_remains_open', flush=True)
