import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path('/Users/hoppworks/projects/rhai-process-unix-run')
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
EVIDENCE_DIR = REPO / '.scratch/process-unix-run/evidence'
LOG_BASE = Path(os.environ['RHAI_DIRECT_DROP_CARGO_LOG']).absolute()
SAMPLED_STOP_KIB = 1_572_864
BASE_LOCK_SHA = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
TOOLCHAIN = Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO, RUSTC, RUSTDOC = (TOOLCHAIN / name for name in ('cargo', 'rustc', 'rustdoc'))
TEST = 'direct_spawn_kill_on_drop_false_preserves_child_and_capture'
owner_name = 'packages::sys::process::unix::tests::public_kill_on_drop_false_final_lease_retires_owner_and_worker'
OVERLAYS = [
    'Cargo.toml', 'src/packages/sys/config.rs', 'src/packages/sys/mod.rs',
    'src/packages/sys/process.rs', 'src/packages/sys/process/unix.rs', 'tests/sys_process.rs',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_storage(deadline):
    for attempt in range(1, 3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('private runtime storage sampling exceeded the cargo watchdog')
        timeout = min(5.0, remaining)
        try:
            result = subprocess.run(['du', '-sk', str(RUNTIME)], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            print(f'storage_sample_attempt={attempt} status=timeout stdout={error.stdout!r} stderr={error.stderr!r}', flush=True)
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('private runtime storage sample timed out twice') from error
            time.sleep(min(.05, max(0.0, deadline - time.monotonic())))
            continue
        print(f'storage_sample_attempt={attempt} status={result.returncode} stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}', flush=True)
        if result.returncode:
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('private runtime storage sample failed twice')
            time.sleep(min(.05, max(0.0, deadline - time.monotonic())))
            continue
        fields = result.stdout.strip().split(maxsplit=1)
        if len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(RUNTIME):
            raise RuntimeError(f'malformed private storage sample: {result.stdout!r}')
        kib = int(fields[0])
        print(f'storage_sample_kib={kib}', flush=True)
        if kib >= SAMPLED_STOP_KIB:
            raise RuntimeError(f'sampled storage reached stop threshold {SAMPLED_STOP_KIB} KiB')
        return kib
    raise RuntimeError('no successful storage measurement')


def emit_log(path, complete):
    data = path.read_bytes() if path.exists() else b''
    print(f'cargo_output_begin path={path} complete={str(complete).lower()} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()}', flush=True)
    print(data.decode(errors='replace'), flush=True)
    print('cargo_output_end', flush=True)


def run_cargo(argv, cwd, env, path, deadline):
    print('cargo_argv=' + repr(argv), flush=True)
    print('cargo_cwd=' + str(cwd), flush=True)
    print('cargo_log=' + str(path), flush=True)
    with path.open('wb') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
        print(f'cargo_pid={proc.pid} cargo_pgid={os.getpgid(proc.pid)}', flush=True)
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Cargo exceeded its 540s aggregate watchdog')
                sample_storage(deadline)
                time.sleep(1)
            status = proc.returncode
            print(f'cargo_status={status}', flush=True)
            emit_log(path, True)
            sample_storage(deadline)
        except BaseException:
            terminal = proc.poll()
            if terminal is not None:
                print(f'cargo_status={terminal}', flush=True)
            emit_log(path, terminal is not None)
            raise
    return status, path.read_text(errors='replace')


def control_valid(output):
    named = re.search(rf'(?m)^test {TEST} \.\.\. ', output)
    summary = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output)
    started = fixture_started(output)
    observed = re.search(r'(?m)^direct_drop_after_final_client_drop pid=(\d+) alive=false challenge_ack=false completion_exists=false$', output)
    panic = 'kill_on_drop(false) must preserve the child after final handle drop' in output
    cleanup = re.search(r'(?m)^direct_drop_fixture_cleanup root=(\S+) pid=(\d+) esrch=true$', output)
    if not all((named, summary, started, observed, panic, cleanup)):
        return False
    root, test_pid, child_pid = started
    return bool(
        observed.group(1) == child_pid and cleanup.group(1) == root and cleanup.group(2) == child_pid
        and int(test_pid) != int(child_pid)
        and valid_fixture_root(root, test_pid) and not Path(root).exists()
    )


def green_valid(output):
    named = re.search(rf'(?m)^test {TEST} \.\.\. ', output)
    summary = re.search(r'(?m)^test result: ok\. 1 passed; 0 failed;', output)
    started = fixture_started(output)
    observed = re.search(r'(?m)^direct_drop_after_final_client_drop pid=(\d+) alive=true challenge_ack=true completion_exists=false$', output)
    complete = re.search(r'(?m)^direct_drop_completion pid=(\d+) record="pid=(\d+) stdout_bytes=524288 stderr_bytes=524288 complete=true\\n"$', output)
    terminal = re.search(r'(?m)^direct_drop_terminal pid=(\d+) esrch=true$', output)
    cleanup = re.search(r'(?m)^direct_drop_fixture_cleanup root=(\S+) pid=(\d+) esrch=true$', output)
    if not all((named, summary, started, observed, complete, terminal, cleanup)):
        return False
    root, test_pid, child_pid = started
    return bool(
        observed.group(1) == child_pid and complete.group(1) == child_pid and complete.group(2) == child_pid
        and terminal.group(1) == child_pid and cleanup.group(1) == root and cleanup.group(2) == child_pid
        and int(test_pid) != int(child_pid)
        and valid_fixture_root(root, test_pid) and not Path(root).exists()
    )


def fixture_started(output):
    # With --nocapture, libtest prefixes the first eprintln on the test-start line.
    inline = re.search(rf'(?m)^test {TEST} \.\.\. direct_drop_fixture_started root=(\S+) test_pid=(\d+) child_pid=(\d+)$', output)
    if inline:
        return inline.groups()
    separate = re.search(r'(?m)^direct_drop_fixture_started root=(\S+) test_pid=(\d+) child_pid=(\d+)$', output)
    return separate.groups() if separate else None


def valid_fixture_root(root, test_pid):
    path = Path(root)
    return (
        not path.is_symlink()
        and path.parent == RUNTIME / 'tmp'
        and re.fullmatch(rf'rhai-sys-test-{test_pid}-{TEST}-\d+', path.name) is not None
    )


MANAGED_TEST = 'managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit'


def managed_started(output):
    match = re.search(
        rf'(?m)^test {MANAGED_TEST} \.\.\. managed_false_drop_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)$',
        output,
    )
    if not match:
        match = re.search(
            r'(?m)^managed_false_drop_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)$',
            output,
        )
    if not match:
        return None
    root, *ids = match.groups()
    return root, *(int(value) for value in ids)


def managed_cleanup(output, started):
    if not started:
        return False
    root, test_pid, sentinel, sentinel_group, leader, worker, leaf, group = started
    fixture = re.search(
        rf'(?m)^managed_fixture_cleanup worker_pid=Some\({worker}\) worker_esrch=true leaf_pid=Some\({leaf}\) leaf_esrch=true$',
        output,
    )
    leader_cleanup = re.search(
        rf'(?m)^managed_spawn_fixture_leader_cleanup leader_pid=Some\({leader}\) leader_esrch=true$', output
    )
    sentinel_cleanup = re.search(
        rf'(?m)^managed-scope sentinel_cleanup pid={sentinel} status=.* esrch=true$', output
    )
    distinct = len({test_pid, sentinel, leader, worker, leaf}) == 5
    absent = all(pid_is_absent(pid) for pid in (sentinel, leader, worker, leaf))
    return bool(
        fixture and leader_cleanup and sentinel_cleanup and distinct
        and sentinel == sentinel_group and leader == group
        and valid_managed_root(root, test_pid) and not Path(root).exists() and absent
    )


def valid_managed_root(root, test_pid):
    path = Path(root)
    return (
        not path.is_symlink()
        and path.parent == RUNTIME / 'tmp'
        and re.fullmatch(rf'rhai-sys-test-{test_pid}-{MANAGED_TEST}-\d+', path.name) is not None
    )


def pid_is_absent(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def managed_control_valid(output):
    started = managed_started(output)
    if not started:
        return False
    root, test_pid, sentinel, sentinel_group, leader, worker, leaf, group = started
    named = re.search(rf'(?m)^test {MANAGED_TEST} \.\.\. ', output)
    summary = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output)
    observed = re.search(
        rf'(?m)^managed_false_drop_after_final_client_drop leader={leader} leader_live=false worker={worker} worker_live=false leaf={leaf} leaf_live=false sentinel={sentinel} sentinel_live=true$',
        output,
    )
    panic = 'kill_on_drop(false) must preserve managed members after final handle drop' in output
    return bool(named and summary and observed and panic and managed_cleanup(output, started))


def managed_green_valid(output):
    started = managed_started(output)
    if not started:
        return False
    root, test_pid, sentinel, sentinel_group, leader, worker, leaf, group = started
    named = re.search(rf'(?m)^test {MANAGED_TEST} \.\.\. ', output)
    summary = re.search(r'(?m)^test result: ok\. 1 passed; 0 failed;', output)
    observed = re.search(
        rf'(?m)^managed_false_drop_after_final_client_drop leader={leader} leader_live=true worker={worker} worker_live=true leaf={leaf} leaf_live=true sentinel={sentinel} sentinel_live=true$',
        output,
    )
    challenge = re.search(
        rf'(?m)^managed_false_drop_live_challenge leader={leader} worker={worker} leaf={leaf} group={group} ack_count=3 ack_pids=\[Some\({leader}\), Some\({worker}\), Some\({leaf}\)\] ack_groups=\[Some\({group}\), Some\({group}\), Some\({group}\)\]$',
        output,
    )
    closed = re.search(
        rf'(?m)^managed_false_drop_after_leader_exit leader={leader} leader_esrch=true worker={worker} worker_esrch=true leaf={leaf} leaf_esrch=true sentinel={sentinel} sentinel_live=true$',
        output,
    )
    return bool(named and summary and observed and challenge and closed and managed_cleanup(output, started))



def owner_suite_valid(output, status):
    owner_named = re.search(r'(?m)^test ' + re.escape(owner_name) + r' \.\.\. ', output)
    owner_summary = re.search(r'(?m)^test result: ok\. (\d+) passed; 0 failed;', output)
    owner_receipt = re.search(
        r'(?m)^(?:test ' + re.escape(owner_name) + r' \.\.\. )?false-policy-owner-retired pid=(\d+) slot_retired=true worker_done=true reap=ESRCH stdout=retained-output stdout_complete=true stderr_complete=true exit=Code\(0\)$',
        output,
    )
    return status == 0 and bool(owner_named and owner_summary and int(owner_summary.group(1)) > 0 and owner_receipt)

def preflight():
    root = str(RUNTIME / 'tmp' / f'rhai-sys-test-301-{TEST}-9988776655')
    control = (
        f'test {TEST} ... direct_drop_fixture_started root={root} test_pid=301 child_pid=302\n'
        'direct_drop_after_final_client_drop pid=302 alive=false challenge_ack=false completion_exists=false\n'
        'direct_drop_fixture_cleanup root=' + root + ' pid=302 esrch=true\n'
        f'    {TEST}\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 40 filtered out\n'
        'kill_on_drop(false) must preserve the child after final handle drop\n'
    )
    green_root = str(RUNTIME / 'tmp' / f'rhai-sys-test-401-{TEST}-9988776656')
    green = (
        f'test {TEST} ... direct_drop_fixture_started root={green_root} test_pid=401 child_pid=402\n'
        'direct_drop_after_final_client_drop pid=402 alive=true challenge_ack=true completion_exists=false\n'
        'direct_drop_completion pid=402 record="pid=402 stdout_bytes=524288 stderr_bytes=524288 complete=true\\n"\n'
        'direct_drop_terminal pid=402 esrch=true\n'
        f'direct_drop_fixture_cleanup root={green_root} pid=402 esrch=true\nok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 40 filtered out\n'
    )
    assert not Path(root).exists(), 'preflight temp root must be absent'
    assert control_valid(control), 'valid intentional-failure receipt rejected'
    assert green_valid(green), 'valid restored receipt rejected'
    direct_mutations = [
        (control.replace('alive=false', 'alive=true'), control, control_valid, 'wrong liveness receipt accepted'),
        (control.replace('test_pid=301', 'test_pid=999'), control, control_valid, 'root owner PID mismatch accepted'),
        (control.replace('pid=302 esrch=true', 'pid=999 esrch=true'), control, control_valid, 'wrong child cleanup identity accepted'),
        (green.replace('stderr_bytes=524288', 'stderr_bytes=524287'), green, green_valid, 'incomplete output receipt accepted'),
        (green.replace('direct_drop_terminal pid=402 esrch=true', 'direct_drop_terminal pid=999 esrch=true'), green, green_valid, 'wrong terminal identity accepted'),
    ]
    for mutated, baseline, checker, message in direct_mutations:
        assert mutated != baseline, f'preflight mutation was a no-op: {message}'
        assert checker(baseline), f'preflight positive baseline failed: {message}'
        assert not checker(mutated), message
    managed_root = str(RUNTIME / 'tmp' / f'rhai-sys-test-987654321-{MANAGED_TEST}-9988776657')
    managed_control = (
        f'test {MANAGED_TEST} ... managed_false_drop_started root={managed_root} test_pid=987654321 sentinel_pid=987654322 sentinel_pgid=987654322 leader=987654323 worker=987654324 leaf=987654325 group=987654323\n'
        'managed_false_drop_after_final_client_drop leader=987654323 leader_live=false worker=987654324 worker_live=false leaf=987654325 leaf_live=false sentinel=987654322 sentinel_live=true\n'
        'managed_fixture_cleanup worker_pid=Some(987654324) worker_esrch=true leaf_pid=Some(987654325) leaf_esrch=true\n'
        'managed_spawn_fixture_leader_cleanup leader_pid=Some(987654323) leader_esrch=true\n'
        'managed-scope sentinel_cleanup pid=987654322 status=Some(ExitStatus) esrch=true\n'
        f'    {MANAGED_TEST}\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 40 filtered out\n'
        'kill_on_drop(false) must preserve managed members after final handle drop\n'
    )
    managed_green = (
        f'test {MANAGED_TEST} ... managed_false_drop_started root={managed_root} test_pid=987654321 sentinel_pid=987654322 sentinel_pgid=987654322 leader=987654323 worker=987654324 leaf=987654325 group=987654323\n'
        'managed_false_drop_after_final_client_drop leader=987654323 leader_live=true worker=987654324 worker_live=true leaf=987654325 leaf_live=true sentinel=987654322 sentinel_live=true\n'
        'managed_false_drop_live_challenge leader=987654323 worker=987654324 leaf=987654325 group=987654323 ack_count=3 ack_pids=[Some(987654323), Some(987654324), Some(987654325)] ack_groups=[Some(987654323), Some(987654323), Some(987654323)]\n'
        'managed_false_drop_after_leader_exit leader=987654323 leader_esrch=true worker=987654324 worker_esrch=true leaf=987654325 leaf_esrch=true sentinel=987654322 sentinel_live=true\n'
        'managed_fixture_cleanup worker_pid=Some(987654324) worker_esrch=true leaf_pid=Some(987654325) leaf_esrch=true\n'
        'managed_spawn_fixture_leader_cleanup leader_pid=Some(987654323) leader_esrch=true\n'
        'managed-scope sentinel_cleanup pid=987654322 status=Some(ExitStatus) esrch=true\n'
        f'ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 40 filtered out\n'
    )
    assert managed_control_valid(managed_control), 'valid managed control rejected'
    assert managed_green_valid(managed_green), 'valid managed green rejected'
    managed_mutations = [
        (managed_green.replace('leader=987654323 worker=987654324 leaf=987654325 group=987654323', 'leader=987654399 worker=987654324 leaf=987654325 group=987654399', 1), managed_green, managed_green_valid, 'wrong member identity accepted'),
        (managed_green.replace('ack_count=3', 'ack_count=2'), managed_green, managed_green_valid, 'missing challenge receipt accepted'),
        (managed_green.replace('sentinel_live=true', 'sentinel_live=false', 1), managed_green, managed_green_valid, 'dead sentinel accepted'),
        (managed_control.replace('worker_esrch=true', 'worker_esrch=false'), managed_control, managed_control_valid, 'uncleaned worker accepted'),
    ]
    for mutated, baseline, checker, message in managed_mutations:
        assert mutated != baseline, f'preflight mutation was a no-op: {message}'
        assert checker(baseline), f'preflight positive baseline failed: {message}'
        assert not checker(mutated), message
    owner_inline = (
        f'test {owner_name} ... false-policy-owner-retired pid=987654321 slot_retired=true worker_done=true reap=ESRCH stdout=retained-output stdout_complete=true stderr_complete=true exit=Code(0)\n'
        f'test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 27 filtered out\n'
    )
    owner_separate = (
        f'test {owner_name} ... \n'
        'false-policy-owner-retired pid=987654321 slot_retired=true worker_done=true reap=ESRCH stdout=retained-output stdout_complete=true stderr_complete=true exit=Code(0)\n'
        f'test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 27 filtered out\n'
    )
    assert owner_suite_valid(owner_inline, 0), 'valid inline owner receipt rejected'
    assert owner_suite_valid(owner_separate, 0), 'valid owner receipt rejected'
    owner_mutations = [
        (owner_inline.replace('slot_retired=true', 'slot_retired=false'), 'slot retirement mutation accepted'),
        (owner_inline.replace('worker_done=true', 'worker_done=false'), 'worker completion mutation accepted'),
        (owner_inline.replace('stdout=retained-output', 'stdout=missing'), 'retained output mutation accepted'),
        (owner_inline.replace('13 passed; 0 failed', '12 passed; 1 failed'), 'failed suite summary accepted'),
    ]
    for mutated, message in owner_mutations:
        assert mutated != owner_inline, f'owner preflight mutation was a no-op: {message}'
        assert not owner_suite_valid(mutated, 0), message
    assert not owner_suite_valid(owner_inline, 101), 'nonzero owner suite status accepted'
    print('false_policy_classifier_preflight=direct_managed_owner_positive_cases_and_mutations_passed', flush=True)


if RUNTIME.is_symlink() or not RUNTIME.is_dir():
    raise RuntimeError('private runtime is not an owned directory')
if LOG_BASE.parent != EVIDENCE_DIR or LOG_BASE.is_symlink():
    raise RuntimeError('external Cargo log path is outside the owned evidence directory')
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
print('phase=public_direct_spawn_kill_on_drop_false_final_lease', flush=True)
print('acceptance_scope=direct_child_survives_final_client_drop_then_retained_owner_drains_and_reaps_after_natural_exit', flush=True)
print('runtime_path=' + str(RUNTIME), flush=True)
print(f'python={sys.version.replace(chr(10), " ")}', flush=True)
print('platform=' + platform.platform(), flush=True)
print(f'harness_pid={os.getpid()} supervisor_pid={os.getppid()} inherited_pgid={os.getpgid(0)}', flush=True)
for name, path in [('cargo', CARGO), ('rustc', RUSTC), ('rustdoc', RUSTDOC)]:
    if not path.is_file():
        raise RuntimeError(f'existing development tool missing: {path}')
    argv = [str(path), '--version', '--verbose'] if name == 'rustc' else [str(path), '--version']
    version = subprocess.check_output(argv, text=True, timeout=10).strip().replace('\n', ' | ')
    print(f'{name}_path={path} {name}_version={version}', flush=True)

preflight()
if os.environ.get('RHAI_HARNESS_PREFLIGHT_ONLY') == '1':
    raise SystemExit(0)
source_hashes = {name: sha(REPO / name) for name in OVERLAYS}
print('repo_head=' + subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('original_overlay_hashes=' + repr(source_hashes), flush=True)
print('test_hash=' + source_hashes['tests/sys_process.rs'], flush=True)
print('harness_hash=' + sha(Path(__file__)), flush=True)
runner_script = Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
wrapper_script = REPO / '.scratch/process-unix-run/run-direct-drop-false.sh'
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
            raise TimeoutError('baseline source archive exceeded 90s')
        sample_storage(deadline)
        time.sleep(.5)
    stderr = proc.stderr.read().decode(errors='replace')
    if proc.returncode:
        raise RuntimeError(f'baseline git archive status={proc.returncode} stderr={stderr}')
if subprocess.run(['tar', '-xf', str(archive), '-C', str(source)], timeout=90).returncode:
    raise RuntimeError('private baseline extraction failed')
archive.unlink()
for name in OVERLAYS:
    destination = source / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / name, destination)
private_hashes = {name: sha(source / name) for name in OVERLAYS}
if private_hashes != source_hashes:
    raise RuntimeError('private source overlays differ from frozen original files')
print('private_source_hashes=' + repr(private_hashes), flush=True)

accepted_lock = REPO / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
lock_hash = sha(accepted_lock)
if lock_hash != BASE_LOCK_SHA:
    raise RuntimeError(f'accepted compatible lock hash mismatch: {lock_hash}')
private_lock = source / 'Cargo.lock'
shutil.copy2(accepted_lock, private_lock)
lock_text = private_lock.read_text()
marker = 'name = "rhai"\nversion = "1.26.1"\ndependencies = [\n'
if lock_text.count(marker) != 1:
    raise RuntimeError('accepted lock has unexpected rhai entry')
start = lock_text.index(marker)
end = lock_text.index('\n]', start)
section = lock_text[start:end]
if ' "libc",\n' not in section:
    insert = section.index(' "libm",\n')
    section = section[:insert] + ' "libc",\n' + section[insert:]
    private_lock.write_text(lock_text[:start] + section + lock_text[end:])
print(f'accepted_lock_sha256={lock_hash} private_lock_sha256={sha(private_lock)}', flush=True)

env = dict(os.environ)
for key in ('RUSTUP_TOOLCHAIN', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_BUILD_RUSTC_WRAPPER'):
    env.pop(key, None)
env.update({
    'PATH': f'{TOOLCHAIN}:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',
    'CARGO_HOME': str(RUNTIME / 'cargo-home'),
    'RUSTUP_HOME': str(RUNTIME / 'rustup-home'),
    'CARGO_TARGET_DIR': str(RUNTIME / 'target'),
    'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
    'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0',
    'RUSTC': str(RUSTC), 'RUSTDOC': str(RUSTDOC),
    'TMPDIR': str(RUNTIME / 'tmp'), 'TMP': str(RUNTIME / 'tmp'), 'TEMP': str(RUNTIME / 'tmp'),
})
(RUNTIME / 'cargo-home').mkdir()
(RUNTIME / 'rustup-home').mkdir()
private_unix = source / 'src/packages/sys/process/unix.rs'
original_unix = private_unix.read_bytes()
needle = b'if !state.terminal && state.kill_on_drop {'
if original_unix.count(needle) != 1:
    raise RuntimeError('kill_on_drop policy mutation must identify exactly one ClientLease branch')
private_unix.write_bytes(original_unix.replace(needle, b'if !state.terminal {', 1))
print(f'wrong_control_unix_sha256={sha(private_unix)} control_mutation=force_final_client_drop_kill_even_when_policy_false', flush=True)

integration_base = [str(CARGO), 'test', '--locked', '--test', 'sys_process', '--features', 'testing-environ,sys']
def integration_command(name):
    return integration_base + ['--', name, '--exact', '--nocapture', '--test-threads=1']

owner_command = [str(CARGO), 'test', '--locked', '--lib', '--features', 'testing-environ,sys', 'packages::sys::process::unix::tests::', '--', '--nocapture', '--test-threads=1']
full_integration_command = integration_base + ['--', '--nocapture', '--test-threads=1']
cargo_deadline = time.monotonic() + 540

def run_control(name, suffix, checker, label):
    path = LOG_BASE.with_name(LOG_BASE.name + suffix)
    status, output = run_cargo(integration_command(name), source, env, path, cargo_deadline)
    accepted = status == 101 and checker(output)
    print(f'{label} status={status} intended_failure={accepted}', flush=True)
    if not accepted:
        raise RuntimeError(f'{label} missed its exact child/group survival assertion or cleanup receipt')
    return path

control_direct_log = run_control(TEST, '.wrong-kill-on-drop-direct.log', control_valid, 'wrong_kill_on_drop_direct')
control_managed_log = run_control(MANAGED_TEST, '.wrong-kill-on-drop-managed.log', managed_control_valid, 'wrong_kill_on_drop_managed')

private_unix.write_bytes(original_unix)
if sha(private_unix) != private_hashes['src/packages/sys/process/unix.rs']:
    raise RuntimeError('production source was not restored byte-for-byte')
print('control_source_restored_sha256=' + sha(private_unix), flush=True)

restored_direct_log = LOG_BASE.with_name(LOG_BASE.name + '.restored-kill-on-drop-direct.log')
direct_status, direct_output = run_cargo(integration_command(TEST), source, env, restored_direct_log, cargo_deadline)
direct_green = direct_status == 0 and green_valid(direct_output)
print(f'restored_direct_drop_test status={direct_status} green_receipt={direct_green}', flush=True)
if not direct_green:
    raise RuntimeError('restored direct false-policy contract lacked exact capture/reap receipts')

restored_managed_log = LOG_BASE.with_name(LOG_BASE.name + '.restored-kill-on-drop-managed.log')
managed_status, managed_output = run_cargo(integration_command(MANAGED_TEST), source, env, restored_managed_log, cargo_deadline)
managed_green = managed_status == 0 and managed_green_valid(managed_output)
print(f'restored_managed_drop_test status={managed_status} green_receipt={managed_green}', flush=True)
if not managed_green:
    raise RuntimeError('restored managed false-policy contract lacked exact member/cleanup receipts')

owner_log = LOG_BASE.with_name(LOG_BASE.name + '.restored-kill-on-drop-owner.log')
owner_status, owner_output = run_cargo(owner_command, source, env, owner_log, cargo_deadline)
owner_summary = re.search(r'(?m)^test result: ok\. (\d+) passed; 0 failed;', owner_output)
owner_green = owner_suite_valid(owner_output, owner_status)
print(f'restored_owner_retirement_suite status={owner_status} receipt={bool(owner_green)} tests={owner_summary.group(1) if owner_summary else "missing"}', flush=True)
if not owner_green:
    raise RuntimeError('false-policy owner slot/worker/capture retirement test suite failed')

full_log = LOG_BASE.with_name(LOG_BASE.name + '.restored-sys-process-suite.log')
full_status, full_output = run_cargo(full_integration_command, source, env, full_log, cargo_deadline)
full_summary = re.search(r'(?m)^test result: ok\. (\d+) passed; 0 failed;', full_output)
full_green = full_status == 0 and bool(full_summary and int(full_summary.group(1)) > 0)
print(f'restored_full_sys_process_suite status={full_status} green={bool(full_green)} tests={full_summary.group(1) if full_summary else "missing"}', flush=True)
if not full_green:
    raise RuntimeError('full sys_process integration suite failed after fixture Drop changes')

final_hashes = {name: sha(source / name) for name in OVERLAYS}
if final_hashes != source_hashes:
    raise RuntimeError('final private source manifest differs from original frozen overlays')
print('final_private_source_hashes=' + repr(final_hashes), flush=True)
for label, path in [('wrong_direct_control', control_direct_log), ('wrong_managed_control', control_managed_log), ('restored_direct', restored_direct_log), ('restored_managed', restored_managed_log), ('restored_owner_suite', owner_log), ('restored_full_sys_process', full_log)]:
    print(f'{label}_cargo_log_path={path} sha256={sha(path)} bytes={path.stat().st_size}', flush=True)
print('narrow_contract_status=accepted_development_macos_only', flush=True)
