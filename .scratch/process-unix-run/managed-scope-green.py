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
TEST_NAME = 'managed_timeout_kills_leader_after_it_changes_process_group'
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


def control_identity_matches(started, leader, sentinel, escape, sentinel_live):
    return bool(
        started and leader and sentinel and escape and sentinel_live
        and started.group(3) == sentinel.group(1)
        and escape.group(1) == leader.group(1)
        and escape.group(1) == escape.group(2)
        and escape.group(3) == started.group(4)
        and escape.group(2) != escape.group(3)
        and escape.group(4) == 'false'
        and sentinel_live.group(1) == started.group(3)
    )


def normal_identity_matches(started, cleanup, leader, worker_leaf, sentinel_live, sentinel):
    return bool(
        started and cleanup and leader and worker_leaf and sentinel_live and sentinel
        and leader.group(1) == leader.group(2)
        and worker_leaf.group(1) == cleanup.group(1)
        and worker_leaf.group(2) == cleanup.group(2)
        and sentinel_live.group(1) == started.group(3)
        and sentinel == started.group(3)
    )


def preflight_classifier_logic():
    started_pattern = r'managed_escape_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+)'
    leader_pattern = r'managed_escape_fixture_cleanup pid=Some\((\d+)\) esrch=true'
    sentinel_pattern = r'managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true'
    escape_pattern = r'managed_escape_leader pid=(\d+) original_pgid=(\d+) escaped_pgid=(\d+) esrch=(true|false)'
    live_pattern = r'managed_escape_sentinel_live pid=(\d+) live=true'
    valid = (
        'managed_escape_started root=/tmp/rhai-sys-test-11-t test_pid=10 sentinel_pid=23 sentinel_pgid=23\n'
        'managed_escape_fixture_cleanup pid=Some(20) esrch=true\n'
        'managed-scope sentinel_cleanup pid=23 status=Some(0) esrch=true\n'
        'managed_escape_leader pid=20 original_pgid=20 escaped_pgid=23 esrch=false\n'
        'managed_escape_sentinel_live pid=23 live=true\n'
    )
    def parsed(pattern, text):
        return re.search(pattern, text)
    baseline = control_identity_matches(
        parsed(started_pattern, valid), parsed(leader_pattern, valid),
        parsed(sentinel_pattern, valid), parsed(escape_pattern, valid),
        parsed(live_pattern, valid),
    )
    wrong_group = valid.replace('escaped_pgid=23', 'escaped_pgid=24')
    missing_cleanup = valid.replace('managed-scope sentinel_cleanup', 'unmatched sentinel_cleanup')
    assert baseline, 'offline control classifier rejected its complete valid receipt'
    assert not control_identity_matches(
        parsed(started_pattern, wrong_group), parsed(leader_pattern, wrong_group),
        parsed(sentinel_pattern, wrong_group), parsed(escape_pattern, wrong_group),
        parsed(live_pattern, wrong_group),
    ), 'offline control classifier accepted a mismatched escaped group'
    assert not control_identity_matches(
        parsed(started_pattern, missing_cleanup), parsed(leader_pattern, missing_cleanup),
        parsed(sentinel_pattern, missing_cleanup), parsed(escape_pattern, missing_cleanup),
        parsed(live_pattern, missing_cleanup),
    ), 'offline control classifier accepted a missing sentinel cleanup receipt'
    normal_valid = (
        'managed_fixture_started root=/tmp/rhai-sys-test-12-u test_pid=11 sentinel_pid=23\n'
        'managed_fixture_cleanup worker_pid=Some(31) worker_esrch=true leaf_pid=Some(32) leaf_esrch=true\n'
        'managed_normal_leader pid=30 pgid=30 esrch=true\n'
        'managed_normal_worker_leaf worker_pid=31 worker_esrch=true leaf_pid=32 leaf_esrch=true\n'
        'managed_normal_sentinel pid=23 live=true\n'
        'managed-scope sentinel_cleanup pid=23 status=Some(0) esrch=true\n'
    )
    normal_started = re.search(r'managed_fixture_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+)', normal_valid)
    normal_cleanup = re.search(r'managed_fixture_cleanup worker_pid=Some\((\d+)\) worker_esrch=true leaf_pid=Some\((\d+)\) leaf_esrch=true', normal_valid)
    normal_leader = re.search(r'managed_normal_leader pid=(\d+) pgid=(\d+) esrch=true', normal_valid)
    normal_worker_leaf = re.search(r'managed_normal_worker_leaf worker_pid=(\d+) worker_esrch=true leaf_pid=(\d+) leaf_esrch=true', normal_valid)
    normal_live = re.search(r'managed_normal_sentinel pid=(\d+) live=true', normal_valid)
    normal_sentinel_records = re.findall(r'managed-scope sentinel_cleanup pid=(\d+) status=[^\\n]* esrch=true', normal_valid)
    normal_sentinel = next((pid for pid in normal_sentinel_records if pid == normal_started.group(3)), None)
    normal = normal_identity_matches(normal_started, normal_cleanup, normal_leader, normal_worker_leaf, normal_live, normal_sentinel)
    assert normal, 'offline normal-fixture classifier rejected its complete valid receipt'
    assert not normal_identity_matches(normal_started, normal_cleanup, normal_leader, normal_worker_leaf, normal_live, '24'), 'offline normal-fixture classifier accepted a sentinel mismatch'
    assert not normal_identity_matches(normal_started, None, normal_leader, normal_worker_leaf, normal_live, '23'), 'offline normal-fixture classifier accepted a missing worker/leaf receipt'
    print('offline_receipt_classifier_checks=6 baseline_and_identity_or_missing_receipt_mutations_passed', flush=True)


preflight_classifier_logic()


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


def emit_log(log_path, complete):
    data = log_path.read_bytes() if log_path.exists() else b''
    print(f'cargo_output_begin path={log_path} complete={str(complete).lower()} bytes={len(data)}', flush=True)
    print(data.decode(errors='replace'), flush=True)
    print('cargo_output_end', flush=True)


def run_cargo(argv, cwd, env, log_path):
    print('cargo_argv=' + repr(argv), flush=True)
    print('cargo_cwd=' + str(cwd), flush=True)
    print('cargo_log=' + str(log_path), flush=True)
    deadline = time.monotonic() + 540
    with log_path.open('wb') as log:
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
            emit_log(log_path, True)
            sample_storage(deadline)
        except BaseException:
            terminal = proc.poll()
            if terminal is not None:
                print(f'cargo_status={terminal}', flush=True)
            emit_log(log_path, terminal is not None)
            raise
    return status, log_path.read_text(errors='replace')


if RUNTIME.is_symlink() or not RUNTIME.is_dir():
    raise RuntimeError('private runtime path is not an owned directory')
if LOG_PATH.parent != EVIDENCE_DIR or LOG_PATH.is_symlink():
    raise RuntimeError('external cargo log path is not the expected owned evidence location')
RUNTIME.joinpath('tmp').mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
print('phase=development_managed_scope_escape_control_and_green', flush=True)
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
wrapper_script = REPO / '.scratch/process-unix-run/run-managed-scope-green.sh'
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

control_source = source / 'src/packages/sys/process/unix.rs'
control_original = control_source.read_bytes()
control_needle = b'let child_error = child.kill().err();'
if control_original.count(control_needle) != 1:
    raise RuntimeError('direct-child signal control needle must match exactly once')
control_mutation = b'let child_error = None;'
control_source.write_bytes(control_original.replace(control_needle, control_mutation, 1))
print(f'control_mutated_unix_sha256={sha(control_source)} control_kind=omit_exact_direct_child_kill', flush=True)

control_command = [
    str(CARGO), 'test', '--locked', '--test', 'sys_process',
    '--features', 'testing-environ,sys', '--', TEST_NAME,
    '--exact', '--nocapture', '--test-threads=1',
]
control_log_path = LOG_PATH.with_name(LOG_PATH.name + '.direct-child-control.log')
control_status, control_output = run_cargo(control_command, source, env, control_log_path)
control_one_test = re.search(r'(?m)^running 1 test$', control_output) is not None
control_named_failure = re.search(r'(?m)^    ' + re.escape(TEST_NAME) + r'$', control_output) is not None
control_failed_summary = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', control_output) is not None
control_assertion = 'managed direct leader must be gone before return' in control_output
control_started = re.search(
    r'managed_escape_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+)',
    control_output,
)
control_leader = re.search(
    r'managed_escape_fixture_cleanup pid=Some\((\d+)\) esrch=true', control_output
)
control_sentinel = re.search(
    r'managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true', control_output
)
control_escape = re.search(
    r'managed_escape_leader pid=(\d+) original_pgid=(\d+) escaped_pgid=(\d+) esrch=(true|false)',
    control_output,
)
control_sentinel_live = re.search(
    r'managed_escape_sentinel_live pid=(\d+) live=true', control_output
)
control_ids_match = bool(
    control_started and control_leader and control_sentinel and control_escape and control_sentinel_live
    and control_started.group(3) == control_sentinel.group(1)
    and control_escape.group(1) == control_leader.group(1)
    and control_escape.group(1) == control_escape.group(2)
    and control_escape.group(3) == control_started.group(4)
    and control_escape.group(2) != control_escape.group(3)
    and control_escape.group(4) == 'false'
    and control_sentinel_live.group(1) == control_started.group(3)
)
control_fixture_root_absent = False
control_test_esrch = control_sentinel_esrch = control_leader_esrch = False
if control_started:
    fixture_root = Path(control_started.group(1))
    expected_parent = RUNTIME / 'tmp'
    control_fixture_root_absent = (
        fixture_root.is_absolute()
        and fixture_root.parent == expected_parent
        and not fixture_root.is_symlink()
        and re.fullmatch(r'rhai-sys-test-[0-9]+-.+', fixture_root.name) is not None
        and not fixture_root.exists()
    )
    control_test_esrch = pid_is_esrch(int(control_started.group(2)))
    control_sentinel_esrch = pid_is_esrch(int(control_started.group(3)))
if control_leader:
    control_leader_esrch = pid_is_esrch(int(control_leader.group(1)))
control_accepted = (
    control_status == 101 and control_one_test and control_named_failure
    and control_failed_summary and control_assertion and control_ids_match
    and control_fixture_root_absent and control_test_esrch
    and control_sentinel_esrch and control_leader_esrch
)
print(
    f'direct_child_kill_wrong_control status={control_status} one_test={control_one_test} '
    f'named_failure={control_named_failure} intended_assertion={control_assertion} '
    f'pid_receipts={control_ids_match} leader_esrch={control_leader_esrch} '
    f'test_esrch={control_test_esrch} sentinel_esrch={control_sentinel_esrch} '
    f'fixture_root_absent={control_fixture_root_absent} accepted={control_accepted}',
    flush=True,
)
if not control_accepted:
    raise RuntimeError('omitting exact direct-child kill did not fail at the intended managed-leader assertion or cleanup proof')

control_source.write_bytes(control_original)
if sha(control_source) != source_hashes['src/packages/sys/process/unix.rs']:
    raise RuntimeError('private production source was not restored byte-for-byte before GREEN')
print(f'control_source_restored_sha256={sha(control_source)}', flush=True)

restored_command = [
    str(CARGO), 'test', '--locked', '--test', 'sys_process',
    '--features', 'testing-environ,sys', '--', 'managed_',
    '--nocapture', '--test-threads=1',
]
restored_log_path = LOG_PATH.with_name(LOG_PATH.name + '.restored-managed-suite.log')
restored_status, restored_output = run_cargo(restored_command, source, env, restored_log_path)
restored_summary = re.search(r'(?m)^test result: ok\. 6 passed; 0 failed;', restored_output) is not None
restored_escape = re.search(
    r'managed_escape_leader pid=(\d+) original_pgid=(\d+) escaped_pgid=(\d+) esrch=true',
    restored_output,
)
restored_sentinel_live = re.search(
    r'managed_escape_sentinel_live pid=(\d+) live=true', restored_output
)
restored_sentinel_records = re.findall(
    r'managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true', restored_output
)
restored_child_esrch = restored_sentinel_esrch = False
restored_sentinel = None
if restored_escape:
    restored_child_esrch = pid_is_esrch(int(restored_escape.group(1)))
    restored_sentinel = next(
        (pid for pid in restored_sentinel_records if pid == restored_escape.group(3)), None
    )
if restored_sentinel:
    restored_sentinel_esrch = pid_is_esrch(int(restored_sentinel))
restored_escape_identity = bool(
    restored_escape and restored_sentinel and restored_sentinel_live
    and restored_escape.group(1) == restored_escape.group(2)
    and restored_escape.group(3) == restored_sentinel
    and restored_escape.group(2) != restored_escape.group(3)
    and restored_sentinel_live.group(1) == restored_escape.group(3)
)
restored_started = re.search(
    r'managed_escape_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+)',
    restored_output,
)
restored_root_absent = False
restored_test_esrch = False
if restored_started:
    fixture_root = Path(restored_started.group(1))
    restored_root_absent = (
        fixture_root.is_absolute()
        and fixture_root.parent == RUNTIME / 'tmp'
        and not fixture_root.is_symlink()
        and re.fullmatch(r'rhai-sys-test-[0-9]+-.+', fixture_root.name) is not None
        and not fixture_root.exists()
    )
    restored_test_esrch = pid_is_esrch(int(restored_started.group(2)))
restored_ok = (
    restored_status == 0 and restored_summary and restored_escape_identity
    and restored_child_esrch and restored_sentinel_esrch
    and restored_root_absent and restored_test_esrch
)
normal_started = re.search(
    r'managed_fixture_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+)', restored_output
)
normal_cleanup = re.search(
    r'managed_fixture_cleanup worker_pid=Some\((\d+)\) worker_esrch=true '
    r'leaf_pid=Some\((\d+)\) leaf_esrch=true',
    restored_output,
)
normal_leader = re.search(
    r'managed_normal_leader pid=(\d+) pgid=(\d+) esrch=true', restored_output
)
normal_worker_leaf = re.search(
    r'managed_normal_worker_leaf worker_pid=(\d+) worker_esrch=true '
    r'leaf_pid=(\d+) leaf_esrch=true',
    restored_output,
)
normal_sentinel_live = re.search(
    r'managed_normal_sentinel pid=(\d+) live=true', restored_output
)
normal_sentinel_records = re.findall(
    r'managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true', restored_output
)
normal_sentinel = None
if normal_started:
    normal_sentinel = next(
        (pid for pid in normal_sentinel_records if pid == normal_started.group(3)), None
    )
normal_root_absent = False
normal_pids_esrch = False
if normal_started:
    fixture_root = Path(normal_started.group(1))
    normal_root_absent = (
        fixture_root.is_absolute()
        and fixture_root.parent == RUNTIME / 'tmp'
        and not fixture_root.is_symlink()
        and re.fullmatch(r'rhai-sys-test-[0-9]+-.+', fixture_root.name) is not None
        and not fixture_root.exists()
    )
if normal_started and normal_cleanup and normal_leader and normal_worker_leaf and normal_sentinel_live and normal_sentinel:
    normal_pids_esrch = all(
        pid_is_esrch(int(pid))
        for pid in (
            normal_started.group(2),
            normal_started.group(3),
            normal_leader.group(1),
            normal_worker_leaf.group(1),
            normal_worker_leaf.group(2),
            normal_cleanup.group(1),
            normal_cleanup.group(2),
            normal_sentinel,
        )
    )
normal_fixture_receipt = bool(
    normal_started and normal_cleanup and normal_leader and normal_worker_leaf
    and normal_sentinel_live and normal_sentinel
    and normal_leader.group(1) == normal_leader.group(2)
    and normal_worker_leaf.group(1) == normal_cleanup.group(1)
    and normal_worker_leaf.group(2) == normal_cleanup.group(2)
    and normal_sentinel_live.group(1) == normal_started.group(3)
    and normal_sentinel == normal_started.group(3)
    and normal_root_absent and normal_pids_esrch
)
print(
    f'restored_managed_suite status={restored_status} six_tests={restored_summary} '
    f'escape_identity={restored_escape_identity} child_esrch={restored_child_esrch} '
    f'sentinel_esrch={restored_sentinel_esrch} test_esrch={restored_test_esrch} '
    f'fixture_root_absent={restored_root_absent} accepted={restored_ok}',
    flush=True,
)
print(
    f'normal_leader_worker_leaf_sentinel_receipt={normal_fixture_receipt} '
    f'normal_root_absent={normal_root_absent} normal_pids_esrch={normal_pids_esrch}',
    flush=True,
)
final_private_hashes = {name: sha(source / name) for name in OVERLAYS}
final_original_hashes = {name: sha(REPO / name) for name in OVERLAYS}
print('final_private_source_hashes=' + repr(final_private_hashes), flush=True)
print('final_original_overlay_hashes=' + repr(final_original_hashes), flush=True)
unchanged = final_private_hashes == private_hashes and final_original_hashes == source_hashes
print(f'source_manifests_unchanged={unchanged}', flush=True)
for log_path in (control_log_path, restored_log_path):
    if log_path.parent != EVIDENCE_DIR or log_path.is_symlink() or not log_path.is_file():
        raise RuntimeError(f'complete Cargo log was not retained at an owned evidence path: {log_path}')
    print(f'retained_cargo_log path={log_path} bytes={log_path.stat().st_size} sha256={sha(log_path)}', flush=True)
accepted = control_accepted and restored_ok and normal_fixture_receipt and unchanged
print(f'classification=managed_group_escape_and_direct_child_cancellation accepted={accepted}', flush=True)
print('scope=development_toolchain_only; unix_managed_scope_contract_slice; no_release_or_msrv_claim', flush=True)
if not accepted:
    raise RuntimeError('managed-scope wrong-control, restored suite, manifests, or exact custody proof failed')
