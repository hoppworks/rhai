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
EVIDENCE_CAP = 256 * 1024
SAMPLED_STOP_KIB = 1_572_864
BASE_LOCK_SHA = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
TOOLCHAIN = Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO = TOOLCHAIN / 'cargo'
RUSTC = TOOLCHAIN / 'rustc'
RUSTDOC = TOOLCHAIN / 'rustdoc'
DROP_TRUE_TEST = 'shared_child_contract::nonfinal_child_clone_drop_keeps_the_real_child_available'
DROP_FALSE_TEST = 'shared_child_contract::final_drop_honors_both_kill_on_drop_policies'
GREEN_FILTER = 'shared_child_contract::'
GREEN_TESTS = [
    'shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable',
    'shared_child_contract::nonfinal_child_clone_drop_keeps_the_real_child_available',
    'shared_child_contract::final_drop_honors_both_kill_on_drop_policies',
    'shared_child_contract::sync_waiter_can_be_cancelled_through_another_shared_child_handle',
]
OVERLAYS = [
    'Cargo.toml',
    'src/packages/sys/mod.rs',
    'src/packages/sys/process.rs',
    'src/packages/sys/process/unix.rs',
    'src/types/token.rs',
    'tests/tokens.rs',
    'tests/sys_process.rs',
    'tests/fixtures/sys_process_shared_child_contract.rs',
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


def sample_storage(deadline=None):
    for attempt in range(1, 3):
        remaining = 5.0 if deadline is None else deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('private runtime storage sampling exceeded its enclosing deadline')
        timeout = min(5.0, remaining)
        try:
            result = subprocess.run(
                ['du', '-sk', str(RUNTIME)], capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode(errors='replace') if isinstance(error.stdout, bytes) else error.stdout
            stderr = error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else error.stderr
            print(f'storage_sample_attempt={attempt} status=timeout timeout_s={timeout:.3f} stdout={stdout!r} stderr={stderr!r}', flush=True)
            if attempt == 2 or (deadline is not None and time.monotonic() >= deadline):
                raise RuntimeError('private runtime storage sampling timed out twice') from error
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic()) if deadline is not None else 0.05))
            continue

        print(f'storage_sample_attempt={attempt} status={result.returncode} stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}', flush=True)
        if result.returncode != 0:
            if attempt == 2 or (deadline is not None and time.monotonic() >= deadline):
                raise RuntimeError('private runtime storage sample failed twice')
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic()) if deadline is not None else 0.05))
            continue

        lines = result.stdout.strip().splitlines()
        fields = lines[0].split(maxsplit=1) if len(lines) == 1 else []
        if len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(RUNTIME):
            raise RuntimeError(f'private runtime storage sample had malformed output or path identity: {result.stdout!r}')
        kib = int(fields[0])
        if kib >= SAMPLED_STOP_KIB:
            raise RuntimeError(f'sampled private runtime reached existing stop threshold {SAMPLED_STOP_KIB} KiB')
        return kib
    raise RuntimeError('private runtime storage sample produced no successful bounded measurement')


def emit_log(path, complete):
    data = path.read_bytes() if path.exists() else b''
    clipped = len(data) > EVIDENCE_CAP
    print(f'cargo_output_begin complete={str(complete).lower()} bytes={len(data)} clipped={str(clipped).lower()}', flush=True)
    if clipped:
        print('[earlier output truncated; retained final 256 KiB]', flush=True)
    print((data[-EVIDENCE_CAP:] if clipped else data).decode(errors='replace'), flush=True)
    print('cargo_output_end', flush=True)


def run_cargo(argv, cwd, env, log_path):
    print('cargo_argv=' + repr(argv), flush=True)
    print('cargo_cwd=' + str(cwd), flush=True)
    print('cargo_log=' + str(log_path), flush=True)
    with log_path.open('wb') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
        print(f'cargo_pid={proc.pid} cargo_pgid={os.getpgid(proc.pid)}', flush=True)
        deadline = time.monotonic() + 540
        log_emitted = False
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('development RED cargo command reached 540s watchdog')
                sample_storage(deadline)
                time.sleep(1)
            status = proc.returncode
            print(f'cargo_status={status}', flush=True)
            emit_log(log_path, True)
            log_emitted = True
            sample_storage(deadline)
        except BaseException:
            terminal_status = proc.poll()
            if not log_emitted:
                if terminal_status is not None:
                    print(f'cargo_status={terminal_status}', flush=True)
                emit_log(log_path, terminal_status is not None)
            raise
    return status, log_path.read_text(errors='replace')


RUNTIME.mkdir(parents=True, exist_ok=True)
(RUNTIME / 'tmp').mkdir(exist_ok=True)
print('phase=development_shared_child_contract', flush=True)
print('runtime_path=' + str(RUNTIME), flush=True)
print(f'python={sys.version.replace(chr(10), " ")}', flush=True)
print('platform=' + platform.platform(), flush=True)
print(f'runner_pid={os.getpid()} supervisor_pid={os.getppid()} owned_pgid={os.getpgid(0)}', flush=True)
for name, path in [('cargo', CARGO), ('rustc', RUSTC), ('rustdoc', RUSTDOC)]:
    if not path.is_file():
        raise RuntimeError(f'expected existing development tool missing: {path}')
    version = subprocess.check_output([str(path), '--version', '--verbose'] if name == 'rustc' else [str(path), '--version'], text=True, timeout=10).strip().replace('\n', ' | ')
    print(f'{name}_path={path} {name}_version={version}', flush=True)

source_hashes = {name: sha(REPO / name) for name in OVERLAYS}
print('repo_head=' + subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('repo_dirty=' + repr(subprocess.check_output(['git', '-C', str(REPO), 'status', '--short', '--untracked-files=all'], text=True).splitlines()), flush=True)
print('original_overlay_hashes=' + repr(source_hashes), flush=True)
print('test_fixture_hash=' + sha(REPO / 'tests/fixtures/sys_process_shared_child_contract.rs'), flush=True)
print('harness_hash=' + sha(Path(__file__)), flush=True)
runner_script = Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
wrapper_script = REPO / '.scratch/process-unix-run/run-shared-child-first-green.sh'
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
        raise RuntimeError(f'git archive status={proc.returncode} stderr={stderr}')
sample_storage(deadline)
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
    raise RuntimeError('private source overlays do not match frozen source hashes')

test_file = source / 'tests/sys_process.rs'
test_text = test_file.read_text()
registration = '\n#[cfg(all(feature = "sys", unix, not(feature = "no_index")))]\n#[path = "fixtures/sys_process_shared_child_contract.rs"]\nmod shared_child_contract;\n'
if 'mod shared_child_contract;' in test_text:
    raise RuntimeError('shared fixture unexpectedly already registered in baseline')
test_file.write_text(test_text + registration)
injected_test_hash = sha(test_file)
print('private_source_hashes=' + repr(private_hashes), flush=True)
print('private_injected_test_hash=' + injected_test_hash, flush=True)
print('private_source=' + str(source), flush=True)

def export_exit_manifests():
    try:
        available_private = {name: sha(source / name) for name in OVERLAYS if (source / name).is_file()}
        available_original = {name: sha(REPO / name) for name in OVERLAYS if (REPO / name).is_file()}
        private_test = source / 'tests/sys_process.rs'
        print('exit_available_private_overlay_hashes=' + repr(available_private), flush=True)
        print('exit_available_original_overlay_hashes=' + repr(available_original), flush=True)
        if private_test.is_file():
            print('exit_available_private_injected_test_hash=' + sha(private_test), flush=True)
    except BaseException as error:
        print(f'exit_manifest_export_error={type(error).__name__}: {error}', flush=True)

atexit.register(export_exit_manifests)

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
print(f'accepted_lock_sha256={lock_hash} private_lock_sha256={sha(private_lock)} private_lock_direct_libc_edge=true', flush=True)

env = dict(os.environ)
for key in ('RHAI_SHARED_CHILD_SCENARIO', 'RHAI_SHARED_CHILD_ROOT', 'RHAI_SHARED_CHILD_FIXTURE'):
    env.pop(key, None)
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
print('parser_compatibility_evidence=run45 commit=a22f053beade6d39f661cdc049ec9fd89dafa648; no parser variants rerun', flush=True)

def controller_roots_are_owned_and_absent(output, scenario):
    matches = re.findall(r'shared-child controller_started scenario=' + re.escape(scenario) + r' pid=(\d+) root=(\S+)', output)
    if len(matches) != 1:
        return False
    root = Path(matches[0][1])
    lexical = Path(os.path.abspath(root))
    runtime_lexical = Path(os.path.abspath(os.environ['AGENT_RUNTIME_DIR']))
    valid = (
        lexical == root
        and not root.is_symlink()
        and root.parent == runtime_lexical
        and runtime_lexical.resolve() == RUNTIME
        and re.fullmatch(r'shared-child-fixture-[0-9]+-[0-9]+', root.name) is not None
    )
    return valid and not root.exists()
private_unix = source / 'src/packages/sys/process/unix.rs'
restored_unix = private_unix.read_bytes()
kill_policy = b'if !state.terminal && state.kill_on_drop {'

def run_drop_control(label, scenario, test_name, replacement, expected_diagnostic):
    if restored_unix.count(kill_policy) != 1:
        raise RuntimeError('ClientLease kill-on-drop branch was not unique')
    private_unix.write_bytes(restored_unix.replace(kill_policy, replacement, 1))
    print(f'{label}_unix_sha256={sha(private_unix)}', flush=True)
    selected = [str(CARGO), 'test', '--locked', '--test', 'sys_process', '--features',
                'testing-environ,sys,sync', '--', test_name, '--exact', '--nocapture', '--test-threads=1']
    status, output = run_cargo(selected, source, env, RUNTIME / f'{label}.log')
    exact_test = bool(re.search(r'(?m)^    ' + re.escape(test_name) + r'$', output))
    one_failure = bool(re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output))
    intended = expected_diagnostic in output
    controller = f'shared-child controller_reaped scenario={scenario}' in output
    controller_reap = bool(re.search(r'shared-child controller_esrch pid=\d+ verified=true', output))
    roots_absent = controller_roots_are_owned_and_absent(output, scenario)
    fixture_cleanup = re.findall(r'shared-child fixture_cleanup pid=(\d+) absent=true', output)
    fixture_absent = len(fixture_cleanup) == 1 and pid_is_esrch(int(fixture_cleanup[0]))
    print(f'{label} status={status} exact_failed_test={exact_test} one_failure={one_failure} intended_drop_assertion={intended} controller_reaped={controller} controller_esrch={controller_reap} fixture_child_esrch={fixture_absent} fixture_root_owned_absent={roots_absent}', flush=True)
    private_unix.write_bytes(restored_unix)
    restored = sha(private_unix) == private_hashes['src/packages/sys/process/unix.rs']
    print(f'{label}_source_restored={restored}', flush=True)
    if not (status == 101 and exact_test and one_failure and intended and controller and controller_reap and fixture_absent and roots_absent and restored):
        raise RuntimeError(f'{label} did not fail at its intended drop-policy contract and clean the exact fixture')

run_drop_control(
    'drop_true_wrong_control', 'drop_true', DROP_TRUE_TEST,
    b'if !state.terminal && false {',
    'did not become absent before watchdog',
)
run_drop_control(
    'drop_false_wrong_control', 'drop_false', DROP_FALSE_TEST,
    b'if !state.terminal {',
    'kill_on_drop=false must leave the child operational after final-client drop',
)

green_command = [
    str(CARGO), 'test', '--locked', '--test', 'sys_process',
    '--features', 'testing-environ,sys,sync', '--', GREEN_FILTER,
    '--nocapture', '--test-threads=1',
]
status, output = run_cargo(green_command, source, env, RUNTIME / 'cargo-green.log')
started_tests = [name for name in GREEN_TESTS if f'test {name} ...' in output]
test_count = 6  # fixture_entry and scenario_entry also run once without child env.
all_tests_passed = re.search(rf'(?m)^test result: ok\. {test_count} passed; 0 failed;', output) is not None
controllers = re.findall(r'shared-child controller_started scenario=(\S+) pid=(\d+) root=(\S+)', output)
controller_reaps = set(re.findall(r'shared-child controller_esrch pid=(\d+) verified=true', output))
controller_child_pids = {pid for _, pid, _ in controllers}
controller_roots_owned_absent = len(controllers) == 4 and len({scenario for scenario, _, _ in controllers}) == 4
if controller_roots_owned_absent:
    for _, _, root_text in controllers:
        root = Path(root_text)
        lexical = Path(os.path.abspath(root))
        if not (
            lexical == root
            and not root.is_symlink()
            and root.parent == Path(os.path.abspath(os.environ['AGENT_RUNTIME_DIR']))
            and RUNTIME.resolve() == Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
            and re.fullmatch(r'shared-child-fixture-[0-9]+-[0-9]+', root.name)
            and not root.exists()
        ):
            controller_roots_owned_absent = False
            break
controller_esrch = controller_child_pids == controller_reaps
fixture_records = sorted(set(re.findall(r'fixture_record=Some\(\"pid=(\d+)', output)))
fixture_pids_absent = len(fixture_records) == 4
for child_pid in fixture_records:
    child_absent = pid_is_esrch(int(child_pid))
    if not child_absent:
        fixture_pids_absent = False
    print(f'fixture_child_pid={child_pid} fixture_child_esrch={child_absent}', flush=True)
controller_reaped = len(controller_child_pids) == 4 and controller_esrch
passed = (
    status == 0
    and re.search(r'(?m)^running 6 tests$', output) is not None
    and len(started_tests) == len(GREEN_TESTS)
    and all_tests_passed
    and controller_reaped
    and controller_roots_owned_absent
    and fixture_pids_absent
)

final_private_hashes = {name: sha(source / name) for name in OVERLAYS}
final_private_test_hash = sha(source / 'tests/sys_process.rs')
expected_private_hashes = dict(private_hashes)
expected_private_hashes['tests/sys_process.rs'] = injected_test_hash
source_unchanged = final_private_hashes == expected_private_hashes and final_private_test_hash == injected_test_hash
final_original_hashes = {name: sha(REPO / name) for name in OVERLAYS}
original_unchanged = final_original_hashes == source_hashes
print('final_private_source_hashes=' + repr(final_private_hashes), flush=True)
print('final_private_injected_test_hash=' + final_private_test_hash, flush=True)
print('final_original_overlay_hashes=' + repr(final_original_hashes), flush=True)
print(f'green status={status} passed={passed} started_tests={started_tests!r} all_tests_passed={all_tests_passed} controller_count={len(controllers)} controller_reaped={controller_reaped} controller_esrch={controller_esrch} fixture_roots_owned_absent={controller_roots_owned_absent} fixture_child_count={len(fixture_records)} fixture_children_esrch={fixture_pids_absent} private_source_unchanged={source_unchanged} original_sources_unchanged={original_unchanged}', flush=True)
if not (passed and source_unchanged and original_unchanged):
    raise RuntimeError('shared Child restored Engine proof did not meet its narrow contract')
print('classification=development_only_shared_child_contract; not_msrv_or_release_acceptance; lifecycle_and_platform_requirements_remain_open', flush=True)
