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
    normal_sentinel_records = re.findall(r'managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true', normal_valid)
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
print('phase=development_managed_spawn_explicit_kill_and_final_clone_drop', flush=True)
print('acceptance_scope=public_managed_spawn_kill_and_final_shared_child_drop', flush=True)
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
wrapper_script = REPO / '.scratch/process-unix-run/run-managed-spawn-group-controls.sh'
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
control_needle = b'let group_error = close_managed_group(child.id()).err();'
if control_original.count(control_needle) != 1:
    raise RuntimeError('managed group-close control needle must match exactly once')
control_mutation = b'let group_error = None;'
control_source.write_bytes(control_original.replace(control_needle, control_mutation, 1))
print(f'control_mutated_unix_sha256={sha(control_source)} control_kind=omit_managed_group_close_keep_direct_child_kill', flush=True)


def command_for(test_name):
    return [
        str(CARGO), 'test', '--locked', '--test', 'sys_process',
        '--features', 'testing-environ,sys', '--', test_name,
        '--exact', '--nocapture', '--test-threads=1',
    ]


def managed_receipts(output, prefix, expected_mode, pid_probe=pid_is_esrch):
    sections = managed_case_sections(output)
    matching = [part for start, part in sections if start.group(2) == prefix]
    section = matching[0] if len(matching) == 1 else None
    if section is None:
        return {'valid': False, 'reason': 'missing exact test start receipt'}
    started = re.search(
        rf'(?m)^(?:test \S+ \.\.\. )?{prefix}_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)$',
        section,
    )
    cleanup = re.search(r'(?m)^managed_fixture_cleanup worker_pid=Some\((\d+)\) worker_esrch=(true|false) leaf_pid=Some\((\d+)\) leaf_esrch=(true|false)$', section)
    leader_cleanup = re.search(r'(?m)^managed_spawn_fixture_leader_cleanup leader_pid=Some\((\d+)\) leader_esrch=(true|false)$', section)
    sentinel_cleanup = re.search(r'(?m)^managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=(true|false)$', section)
    if not all((started, cleanup, leader_cleanup, sentinel_cleanup)):
        return {'valid': False, 'reason': 'missing start or exact cleanup receipt'}
    root = Path(started.group(1))
    values = {
        'test': int(started.group(2)), 'sentinel': int(started.group(3)), 'sentinel_pgid': int(started.group(4)),
        'leader': int(started.group(5)), 'worker': int(started.group(6)), 'leaf': int(started.group(7)), 'group': int(started.group(8)),
    }
    ids_consistent = (
        values['sentinel'] == values['sentinel_pgid']
        and values['leader'] == values['group']
        and values['leader'] != values['sentinel']
        and values['worker'] == int(cleanup.group(1))
        and values['leaf'] == int(cleanup.group(3))
        and values['leader'] == int(leader_cleanup.group(1))
        and values['sentinel'] == int(sentinel_cleanup.group(1))
        and len({values['test'], values['sentinel'], values['leader'], values['worker'], values['leaf']}) == 5
    )
    root_owned_absent = (
        root.is_absolute() and root.parent == RUNTIME / 'tmp'
        and not root.is_symlink()
        and re.fullmatch(r'rhai-sys-test-[0-9]+-.+', root.name) is not None
        and not root.exists()
    )
    pid_states = {name: pid_probe(pid) for name, pid in values.items() if name != 'group'}
    cleanup_states = {
        'leader': leader_cleanup.group(2) == 'true',
        'worker': cleanup.group(2) == 'true',
        'leaf': cleanup.group(4) == 'true',
        'sentinel': sentinel_cleanup.group(2) == 'true',
    }
    if expected_mode == 'kill':
        live_line = re.search(r'(?m)^managed_spawn_kill leader=(\d+) leader_esrch=(true|false) worker=(\d+) worker_esrch=(true|false) leaf=(\d+) leaf_esrch=(true|false) all_esrch=(true|false) sentinel=(\d+) live=(true|false) wait_returned=(true|false)$', section)
        mode_ok = bool(live_line and tuple(map(int, (live_line.group(1), live_line.group(3), live_line.group(5), live_line.group(8)))) == (values['leader'], values['worker'], values['leaf'], values['sentinel']) and live_line.group(2) == 'true' and live_line.group(4) == 'false' and live_line.group(6) == 'false' and live_line.group(7) == 'false' and live_line.group(9) == 'true')
        assertion = 'managed spawned members must be gone after public kill' in section
        test_name = 'managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel'
    else:
        nonfinal = re.search(r'(?m)^managed_spawn_nonfinal_drop leader=(\d+) leader_live=(true|false) worker=(\d+) worker_live=(true|false) leaf=(\d+) leaf_live=(true|false) all_live=(true|false)$', section)
        final = re.search(r'(?m)^managed_spawn_final_drop leader=(\d+) leader_esrch=(true|false) worker=(\d+) worker_esrch=(true|false) leaf=(\d+) leaf_esrch=(true|false) all_esrch=(true|false) sentinel=(\d+) live=(true|false)$', section)
        mode_ok = bool(nonfinal and final and tuple(map(int, (nonfinal.group(1), nonfinal.group(3), nonfinal.group(5)))) == (values['leader'], values['worker'], values['leaf']) and nonfinal.group(2) == 'true' and nonfinal.group(4) == 'true' and nonfinal.group(6) == 'true' and nonfinal.group(7) == 'true' and tuple(map(int, (final.group(1), final.group(3), final.group(5), final.group(8)))) == (values['leader'], values['worker'], values['leaf'], values['sentinel']) and final.group(2) == 'true' and final.group(4) == 'false' and final.group(6) == 'false' and final.group(7) == 'false' and final.group(9) == 'true')
        assertion = 'dropping final Child clone did not terminate the managed group' in section
        test_name = 'managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not'
    test_summary = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', section) is not None
    named_failure = re.search(r'(?m)^    ' + re.escape(test_name) + r'$', section) is not None
    operation_states = mode_ok
    terminal_states = all(pid_states.values()) and all(cleanup_states.values())
    return {
        'valid': bool(ids_consistent and root_owned_absent and terminal_states and operation_states and assertion and named_failure and test_summary),
        'ids_consistent': ids_consistent, 'root_absent': root_owned_absent,
        'cleanup_states': cleanup_states, 'pid_states': pid_states,
        'mode_receipt': bool(mode_ok), 'expected_assertion': assertion,
        'named_failure': named_failure, 'one_failure_summary': test_summary,
    }


def managed_case_sections(output):
    starts = list(re.finditer(r'(?m)^((?:test \S+ \.\.\. )?)(managed_spawn_(?:kill|drop))_started ', output))
    return [(start, output[start.start():starts[index + 1].start() if index + 1 < len(starts) else len(output)]) for index, start in enumerate(starts)]


def managed_started_identities_unique(output):
    all_members = []
    for start, section in managed_case_sections(output):
        match = re.search(rf'(?m)^(?:test \S+ \.\.\. )?{re.escape(start.group(2))}_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)$', section)
        if not match:
            return False
        sentinel, leader, worker, leaf = map(int, (match.group(3), match.group(5), match.group(6), match.group(7)))
        if sentinel == leader or leader != int(match.group(8)) or len({sentinel, leader, worker, leaf}) != 4:
            return False
        all_members.extend((sentinel, leader, worker, leaf))
    return len(all_members) == len(set(all_members))


def restored_spawn_receipt(output, prefix, pid_probe=pid_is_esrch):
    case_prefix = 'managed_spawn_kill' if prefix == 'managed_spawn_kill' else 'managed_spawn_drop'
    matching = [part for start, part in managed_case_sections(output) if start.group(2) == case_prefix]
    section = matching[0] if len(matching) == 1 else None
    if section is None:
        return False
    started = re.search(rf'(?m)^(?:test \S+ \.\.\. )?{prefix}_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)$', section)
    cleanup = re.search(r'(?m)^managed_fixture_cleanup worker_pid=Some\((\d+)\) worker_esrch=true leaf_pid=Some\((\d+)\) leaf_esrch=true$', section)
    leader_cleanup = re.search(r'(?m)^managed_spawn_fixture_leader_cleanup leader_pid=Some\((\d+)\) leader_esrch=true$', section)
    sentinel_cleanup = re.search(r'(?m)^managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true$', section)
    line_name = 'managed_spawn_kill' if prefix.endswith('kill') else 'managed_spawn_final_drop'
    result = re.search(rf'(?m)^{line_name} leader=(\d+) leader_esrch=true worker=(\d+) worker_esrch=true leaf=(\d+) leaf_esrch=true all_esrch=true sentinel=(\d+) live=true(?: wait_returned=true)?$', section)
    nonfinal = re.search(r'(?m)^managed_spawn_nonfinal_drop leader=(\d+) leader_live=true worker=(\d+) worker_live=true leaf=(\d+) leaf_live=true all_live=true$', section) if prefix == 'managed_spawn_drop' else None
    if not all((started, cleanup, leader_cleanup, sentinel_cleanup, result)):
        return False
    ids = list(map(int, started.groups()[1:]))
    test_pid, sentinel, sentinel_pgid, leader, worker, leaf, group = ids
    root = Path(started.group(1))
    pids = (test_pid, sentinel, leader, worker, leaf)
    return bool(
        sentinel == sentinel_pgid and leader == group and leader != sentinel
        and worker == int(cleanup.group(1)) and leaf == int(cleanup.group(2))
        and leader == int(leader_cleanup.group(1)) and sentinel == int(sentinel_cleanup.group(1))
        and tuple(map(int, result.groups())) == (leader, worker, leaf, sentinel)
        and (prefix != 'managed_spawn_drop' or (nonfinal and tuple(map(int, nonfinal.groups()[:3])) == (leader, worker, leaf)))
        and root.is_absolute() and root.parent == RUNTIME / 'tmp' and not root.is_symlink()
        and re.fullmatch(r'rhai-sys-test-[0-9]+-.+', root.name) is not None and not root.exists()
        and all(pid_probe(pid) for pid in pids)
    )


def preflight_managed_receipt_logic():
    root = str(RUNTIME / 'tmp' / 'rhai-sys-test-9876-valid')

    def section(prefix, test_pid, sentinel, leader, worker, leaf, *, mode, restored):
        test_name = 'managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel' if mode == 'kill' else 'managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not'
        part = [f'test {test_name} ... {prefix}_started root={root} test_pid={test_pid} sentinel_pid={sentinel} sentinel_pgid={sentinel} leader={leader} worker={worker} leaf={leaf} group={leader}']
        part.append(f'managed_fixture_cleanup worker_pid=Some({worker}) worker_esrch=true leaf_pid=Some({leaf}) leaf_esrch=true')
        part.append(f'managed_spawn_fixture_leader_cleanup leader_pid=Some({leader}) leader_esrch=true')
        if mode == 'kill':
            fields = (f'managed_spawn_kill leader={leader} leader_esrch=true worker={worker} worker_esrch={"true" if restored else "false"} leaf={leaf} leaf_esrch={"true" if restored else "false"} all_esrch={"true" if restored else "false"} sentinel={sentinel} live=true wait_returned=true')
            part.append(fields)
            part.append('managed spawned members must be gone after public kill')
            if not restored:
                part.extend(['    managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel', 'test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out'])
        else:
            part.append(f'managed_spawn_nonfinal_drop leader={leader} leader_live=true worker={worker} worker_live=true leaf={leaf} leaf_live=true all_live=true')
            part.append(f'managed_spawn_final_drop leader={leader} leader_esrch=true worker={worker} worker_esrch={"true" if restored else "false"} leaf={leaf} leaf_esrch={"true" if restored else "false"} all_esrch={"true" if restored else "false"} sentinel={sentinel} live=true')
            part.append('dropping final Child clone did not terminate the managed group')
            if not restored:
                part.extend(['    managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not', 'test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out'])
        part.append(f'managed-scope sentinel_cleanup pid={sentinel} status=Some(0) esrch=true')
        if restored:
            part.extend(['ok', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 8 filtered out'])
        return '\n'.join(part) + '\n'

    gone = lambda _pid: True
    kill_control = section('managed_spawn_kill', 7001, 7002, 7003, 7004, 7005, mode='kill', restored=False)
    drop_control = section('managed_spawn_drop', 7011, 7012, 7013, 7014, 7015, mode='drop', restored=False)
    assert managed_receipts(kill_control, 'managed_spawn_kill', 'kill', gone)['valid']
    assert managed_receipts(drop_control, 'managed_spawn_drop', 'drop', gone)['valid']
    assert not managed_receipts(kill_control.replace('worker=7004', 'worker=7999'), 'managed_spawn_kill', 'kill', gone)['valid']
    assert not managed_receipts(drop_control.replace('worker_live=true', 'worker_live=false'), 'managed_spawn_drop', 'drop', gone)['valid']
    assert not managed_receipts(drop_control.replace('managed_fixture_cleanup ', 'missing_cleanup '), 'managed_spawn_drop', 'drop', gone)['valid']

    restored = section('managed_spawn_kill', 7021, 7022, 7023, 7024, 7025, mode='kill', restored=True)
    restored += section('managed_spawn_drop', 7031, 7032, 7033, 7034, 7035, mode='drop', restored=True)
    assert restored_spawn_receipt(restored, 'managed_spawn_kill', gone)
    assert restored_spawn_receipt(restored, 'managed_spawn_drop', gone)
    assert not restored_spawn_receipt(restored.replace('worker_pid=Some(7034)', 'worker_pid=Some(7999)'), 'managed_spawn_drop', gone)
    assert not restored_spawn_receipt(restored.replace('managed_spawn_nonfinal_drop ', 'missing_nonfinal_drop '), 'managed_spawn_drop', gone)
    print('offline_managed_receipt_checks=9 valid controls/restored plus identity, missing, and contradictory mutations rejected', flush=True)


preflight_managed_receipt_logic()

control_results = []
control_logs = []
for test_name, mode in [
    ('managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel', 'kill'),
    ('managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not', 'drop'),
]:
    log_path = LOG_PATH.with_name(LOG_PATH.name + f'.{mode}-group-control.log')
    status, output = run_cargo(command_for(test_name), source, env, log_path)
    receipts = managed_receipts(output, 'managed_spawn_' + ('kill' if mode == 'kill' else 'drop'), mode)
    accepted = status == 101 and receipts['valid']
    print(f'{mode}_group_close_wrong_control status={status} receipts={receipts!r} accepted={accepted}', flush=True)
    control_results.append(accepted)
    control_logs.append(log_path)
    if not accepted:
        raise RuntimeError(f'{mode} group-close omission did not fail at its intended live-member assertion or cleanup proof')

control_source.write_bytes(control_original)
if sha(control_source) != private_hashes['src/packages/sys/process/unix.rs']:
    raise RuntimeError('production source was not restored byte-for-byte before GREEN')
print(f'control_source_restored_sha256={sha(control_source)}', flush=True)

restored_log_path = LOG_PATH.with_name(LOG_PATH.name + '.restored-managed-spawn-suite.log')
restored_status, restored_output = run_cargo(
    [str(CARGO), 'test', '--locked', '--test', 'sys_process', '--features', 'testing-environ,sys', '--', 'managed_', '--nocapture', '--test-threads=1'],
    source, env, restored_log_path,
)
restored_summary = re.search(r'(?m)^test result: ok\. 9 passed; 0 failed;', restored_output) is not None
restored_named = all(any(
    re.search(r'(?m)^test ' + re.escape(name) + r' \.\.\. ', section)
    and re.search(r'(?m)^ok$', section)
    for start, section in managed_case_sections(restored_output)
    if start.group(2) == ('managed_spawn_kill' if name.endswith('preserves_sentinel') else 'managed_spawn_drop')
) for name in (
    'managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel',
    'managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not',
))
# The restored path is successful: validate its explicit post-operation records and the cleanup
# receipts separately because managed_receipts' wrong-control predicate expects live descendants.

restored_kill_ok = restored_spawn_receipt(restored_output, 'managed_spawn_kill')
restored_drop_ok = restored_spawn_receipt(restored_output, 'managed_spawn_drop')
restored_unique = managed_started_identities_unique(restored_output)
restored_ok = restored_status == 0 and restored_summary and restored_named and restored_kill_ok and restored_drop_ok and restored_unique
print(f'restored_managed_spawn_suite status={restored_status} nine_tests={restored_summary} named_tests={restored_named} kill_receipt={restored_kill_ok} final_drop_receipt={restored_drop_ok} unique_fixture_ids={restored_unique} accepted={restored_ok}', flush=True)

final_private_hashes = {name: sha(source / name) for name in OVERLAYS}
final_original_hashes = {name: sha(REPO / name) for name in OVERLAYS}
print('final_private_source_hashes=' + repr(final_private_hashes), flush=True)
print('final_original_overlay_hashes=' + repr(final_original_hashes), flush=True)
unchanged = final_private_hashes == private_hashes and final_original_hashes == source_hashes
print(f'source_manifests_unchanged={unchanged}', flush=True)
for log_path in (*control_logs, restored_log_path):
    if log_path.parent != EVIDENCE_DIR or log_path.is_symlink() or not log_path.is_file():
        raise RuntimeError(f'complete Cargo log was not retained at an owned evidence path: {log_path}')
    print(f'complete_log_receipt path={log_path} bytes={log_path.stat().st_size} sha256={sha(log_path)}', flush=True)
if not all(control_results) or not restored_ok or not unchanged:
    raise RuntimeError('managed public kill/final-drop proof did not pass all wrong-control, restored, and manifest checks')
print('managed_spawn_group_cancel_acceptance=pass', flush=True)
