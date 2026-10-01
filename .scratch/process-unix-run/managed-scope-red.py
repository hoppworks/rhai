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
EVIDENCE_DIR = REPO / '.scratch/process-unix-run/evidence'
LOG_PATH = Path(os.environ['RHAI_MANAGED_CARGO_LOG']).absolute()
SAMPLED_STOP_KIB = 1_572_864
BASE_LOCK_SHA = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
TOOLCHAIN = Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO = TOOLCHAIN / 'cargo'
RUSTC = TOOLCHAIN / 'rustc'
RUSTDOC = TOOLCHAIN / 'rustdoc'
TEST_NAME = 'managed_run_closes_worker_after_leader_exit_and_preserves_sentinel'
OVERLAYS = [
    'Cargo.toml',
    'src/packages/sys/config.rs',
    'src/packages/sys/mod.rs',
    'src/packages/sys/process.rs',
    'src/packages/sys/process/unix.rs',
    'tests/sys_process.rs',
]


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
            raise TimeoutError('private runtime storage sampling exceeded the cargo watchdog')
        timeout = min(5.0, remaining)
        try:
            result = subprocess.run(
                ['du', '-sk', str(RUNTIME)], capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode(errors='replace') if isinstance(error.stdout, bytes) else error.stdout
            stderr = error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else error.stderr
            print(f'storage_sample_attempt={attempt} status=timeout timeout_s={timeout:.3f} stdout={stdout!r} stderr={stderr!r}', flush=True)
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('private runtime storage sample timed out twice') from error
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            continue

        print(f'storage_sample_attempt={attempt} status={result.returncode} stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}', flush=True)
        if result.returncode != 0:
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('private runtime storage sample failed twice')
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            continue
        lines = result.stdout.strip().splitlines()
        fields = lines[0].split(maxsplit=1) if len(lines) == 1 else []
        if len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(RUNTIME):
            raise RuntimeError(f'private runtime sample had malformed output or path identity: {result.stdout!r}')
        kib = int(fields[0])
        print(f'storage_sample_kib={kib}', flush=True)
        if kib >= SAMPLED_STOP_KIB:
            raise RuntimeError(f'sampled private runtime reached existing stop threshold {SAMPLED_STOP_KIB} KiB')
        return kib
    raise RuntimeError('private runtime storage sample produced no successful bounded measurement')


def emit_log(complete):
    data = LOG_PATH.read_bytes() if LOG_PATH.exists() else b''
    print(f'cargo_output_begin complete={str(complete).lower()} bytes={len(data)}', flush=True)
    print(data.decode(errors='replace'), flush=True)
    print('cargo_output_end', flush=True)


def run_cargo(argv, cwd, env):
    print('cargo_argv=' + repr(argv), flush=True)
    print('cargo_cwd=' + str(cwd), flush=True)
    print('cargo_log=' + str(LOG_PATH), flush=True)
    deadline = time.monotonic() + 540
    with LOG_PATH.open('wb') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
        print(f'cargo_pid={proc.pid} cargo_pgid={os.getpgid(proc.pid)}', flush=True)
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('development managed-scope RED reached its 540s cargo watchdog')
                sample_storage(deadline)
                time.sleep(1)
            status = proc.returncode
            print(f'cargo_status={status}', flush=True)
            emit_log(True)
            sample_storage(deadline)
        except BaseException:
            terminal = proc.poll()
            if terminal is not None:
                print(f'cargo_status={terminal}', flush=True)
            emit_log(terminal is not None)
            raise
    return status, LOG_PATH.read_text(errors='replace')


if RUNTIME.is_symlink() or not RUNTIME.is_dir():
    raise RuntimeError('private runtime path is not an owned directory')
if LOG_PATH.parent != EVIDENCE_DIR or LOG_PATH.is_symlink():
    raise RuntimeError('external cargo log path is not the expected owned evidence location')
RUNTIME.joinpath('tmp').mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
print('phase=development_managed_scope_expected_denied_red', flush=True)
print('acceptance_scope=one_public_run_managed_scope_descendant_and_sentinel_contract', flush=True)
print('runtime_path=' + str(RUNTIME), flush=True)
print(f'python={sys.version.replace(chr(10), " ")}', flush=True)
print('platform=' + platform.platform(), flush=True)
print(f'harness_pid={os.getpid()} supervisor_pid={os.getppid()} inherited_pgid={os.getpgid(0)}', flush=True)
for name, path in [('cargo', CARGO), ('rustc', RUSTC), ('rustdoc', RUSTDOC)]:
    if not path.is_file():
        raise RuntimeError(f'expected existing development tool missing: {path}')
    argv = [str(path), '--version', '--verbose'] if name == 'rustc' else [str(path), '--version']
    version = subprocess.check_output(argv, text=True, timeout=10).strip().replace('\n', ' | ')
    print(f'{name}_path={path} {name}_version={version}', flush=True)

source_hashes = {name: sha(REPO / name) for name in OVERLAYS}
print('repo_head=' + subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('repo_dirty=' + repr(subprocess.check_output(['git', '-C', str(REPO), 'status', '--short', '--untracked-files=all'], text=True).splitlines()), flush=True)
print('original_overlay_hashes=' + repr(source_hashes), flush=True)
print('managed_test_hash=' + source_hashes['tests/sys_process.rs'], flush=True)
print('harness_hash=' + sha(Path(__file__)), flush=True)
runner_script = Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
wrapper_script = REPO / '.scratch/process-unix-run/run-managed-scope-red.sh'
print('run_scoped_hash=' + sha(runner_script), flush=True)
print('wrapper_hash=' + sha(wrapper_script), flush=True)

source = RUNTIME / 'source'
source.mkdir()
archive = RUNTIME / 'baseline.tar'
with archive.open('wb') as output:
    proc = subprocess.Popen(['git', '-C', str(REPO), 'archive', 'HEAD'], stdout=output, stderr=subprocess.PIPE, start_new_session=False)
    deadline = time.monotonic() + 90
    while proc.poll() is None:
        if time.monotonic() >= deadline:
            raise TimeoutError('baseline git archive exceeded 90s')
        sample_storage(deadline)
        time.sleep(0.5)
    stderr = proc.stderr.read().decode(errors='replace')
    if proc.returncode != 0:
        raise RuntimeError(f'baseline git archive status={proc.returncode} stderr={stderr}')
extract = subprocess.run(['tar', '-xf', str(archive), '-C', str(source)], timeout=90, check=False)
if extract.returncode != 0:
    raise RuntimeError(f'baseline tar extraction status={extract.returncode}')
archive.unlink()
for name in OVERLAYS:
    destination = source / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / name, destination)
private_hashes = {name: sha(source / name) for name in OVERLAYS}
if private_hashes != source_hashes:
    raise RuntimeError('private source overlays do not match the frozen original hashes')
print('private_source_hashes=' + repr(private_hashes), flush=True)
print('private_source=' + str(source), flush=True)

accepted_lock = REPO / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
lock_hash = sha(accepted_lock)
if lock_hash != BASE_LOCK_SHA:
    raise RuntimeError(f'accepted compatible lock hash mismatch: {lock_hash}')
private_lock = source / 'Cargo.lock'
shutil.copy2(accepted_lock, private_lock)
lock_text = private_lock.read_text()
marker = 'name = "rhai"\nversion = "1.26.1"\ndependencies = [\n'
if lock_text.count(marker) != 1:
    raise RuntimeError('accepted lock has an unexpected rhai package entry')
start = lock_text.index(marker)
end = lock_text.index('\n]', start)
section = lock_text[start:end]
if ' "libc",\n' not in section:
    insert_at = section.index(' "libm",\n')
    section = section[:insert_at] + ' "libc",\n' + section[insert_at:]
    lock_text = lock_text[:start] + section + lock_text[end:]
    private_lock.write_text(lock_text)
print(f'accepted_lock_sha256={lock_hash} private_lock_sha256={sha(private_lock)} private_direct_libc_edge=true', flush=True)

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
    'RUSTC': str(RUSTC),
    'RUSTDOC': str(RUSTDOC),
    'TMPDIR': str(RUNTIME / 'tmp'),
    'TMP': str(RUNTIME / 'tmp'),
    'TEMP': str(RUNTIME / 'tmp'),
})
(RUNTIME / 'cargo-home').mkdir()
(RUNTIME / 'rustup-home').mkdir()

command = [
    str(CARGO), 'test', '--locked', '--test', 'sys_process',
    '--features', 'testing-environ,sys', '--', TEST_NAME,
    '--exact', '--nocapture', '--test-threads=1',
]
status, output = run_cargo(command, source, env)
denial_message = 'Managed process scope is not supported by this target'
denial_prefix = 'managed run returned SysError::Denied: '

def has_typed_managed_denial(text):
    return denial_prefix + denial_message in text

typed_sample = denial_prefix + denial_message
generic_sample = 'managed run returned a non-Denied error: Runtime error: SysError'
other_denial_sample = denial_prefix + 'program is not allowed'
classifier_probes = (
    has_typed_managed_denial(typed_sample)
    and not has_typed_managed_denial(generic_sample)
    and not has_typed_managed_denial(other_denial_sample)
)
specific_denial = has_typed_managed_denial(output)
error_path = denial_prefix in output
one_test = re.search(r'(?m)^running 1 test$', output) is not None
named_failed = re.search(r'(?m)^    ' + re.escape(TEST_NAME) + r'$', output) is not None
one_failure = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output) is not None
receipt = re.search(r'managed_fixture_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+)', output)
sentinel_cleanup = re.search(r'managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true', output)
pid_receipt = bool(receipt and sentinel_cleanup and receipt.group(3) == sentinel_cleanup.group(1))
fixture_absent = False
test_pid_absent = False
sentinel_absent = False
if receipt:
    fixture_root = Path(receipt.group(1))
    expected_parent = RUNTIME / 'tmp'
    fixture_absent = (
        fixture_root.is_absolute()
        and fixture_root.parent == expected_parent
        and not fixture_root.is_symlink()
        and re.fullmatch(r'rhai-sys-test-[0-9]+-.+', fixture_root.name) is not None
        and not fixture_root.exists()
    )
    test_pid_absent = pid_is_esrch(int(receipt.group(2)))
    sentinel_absent = pid_is_esrch(int(receipt.group(3)))
print(
    f'expected_denied_red status={status} one_test={one_test} named_failed={named_failed} '
    f'specific_managed_denial={specific_denial} error_path={error_path} one_failure={one_failure} '
    f'fixture_receipt={bool(receipt)} sentinel_exact_cleanup_receipt={pid_receipt} '
    f'fixture_root_owned_absent={fixture_absent} test_process_esrch={test_pid_absent} sentinel_esrch={sentinel_absent}',
    flush=True,
)
print(f'typed_denial_classifier_offline_probes={classifier_probes}', flush=True)
final_private_hashes = {name: sha(source / name) for name in OVERLAYS}
final_original_hashes = {name: sha(REPO / name) for name in OVERLAYS}
print('final_private_source_hashes=' + repr(final_private_hashes), flush=True)
print('final_original_overlay_hashes=' + repr(final_original_hashes), flush=True)
unchanged = final_private_hashes == private_hashes and final_original_hashes == source_hashes
print(f'source_manifests_unchanged={unchanged}', flush=True)
accepted = (
    status == 101 and one_test and named_failed and specific_denial and error_path and one_failure
    and classifier_probes and pid_receipt and fixture_absent and test_pid_absent and sentinel_absent and unchanged
)
print(f'classification=expected_public_managed_scope_denial_RED accepted={accepted}', flush=True)
print('scope=development_toolchain_only; managed_behavior_not_implemented_or_accepted; no_release_or_msrv_claim', flush=True)
if not accepted:
    raise RuntimeError('managed-scope baseline did not fail specifically at the existing Managed denial or failed custody readback')
