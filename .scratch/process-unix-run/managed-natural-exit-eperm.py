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
LOG_BASE = Path(os.environ['RHAI_PIPE_CARGO_LOG']).absolute()
SAMPLED_STOP_KIB = 1_572_864
BASE_LOCK_SHA = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
TOOLCHAIN = Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO, RUSTC, RUSTDOC = (TOOLCHAIN / name for name in ('cargo', 'rustc', 'rustdoc'))
TEST_OLD = 'managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes'
TEST_REAP = 'managed_spawn_post_reap_cancel_bounds_escaped_capture'
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
            raise TimeoutError('storage sample exceeded aggregate watchdog')
        try:
            result = subprocess.run(['du', '-sk', str(RUNTIME)], capture_output=True, text=True, timeout=min(5.0, remaining))
        except subprocess.TimeoutExpired as error:
            print(f'storage_sample_attempt={attempt} status=timeout stdout={error.stdout!r} stderr={error.stderr!r}', flush=True)
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('storage sampling failed twice') from error
            time.sleep(min(.05, max(0, deadline - time.monotonic())))
            continue
        print(f'storage_sample_attempt={attempt} status={result.returncode} stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}', flush=True)
        if result.returncode:
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('storage sampling failed twice')
            time.sleep(min(.05, max(0, deadline - time.monotonic())))
            continue
        fields = result.stdout.strip().split(maxsplit=1)
        if len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(RUNTIME):
            raise RuntimeError(f'malformed storage sample: {result.stdout!r}')
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


def has_cleanup(output, prefix):
    cleanups = re.findall(rf'(?m)^{prefix} root=(\S+) leader=Some\((\d+)\) leader_esrch=true holder=Some\((\d+)\) holder_esrch=true$', output)
    terminals = re.findall(r'(?m)^managed_escaped_pipe_terminal leader=Some\((\d+)\) leader_esrch=true holder=Some\((\d+)\) holder_esrch=true sentinel=(\d+) sentinel_esrch=true$', output)
    sentinels = re.findall(r'(?m)^managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true$', output)
    if not cleanups or not terminals or not sentinels:
        return False
    for leader_text, holder_text, sentinel_text in terminals:
        leader, holder, sentinel = map(int, (leader_text, holder_text, sentinel_text))
        if not any(int(row[1]) == leader and int(row[2]) == holder for row in cleanups):
            return False
        if sentinel not in {int(pid) for pid in sentinels}:
            return False
    return True


def cleanup_matches(output, root, leader, holder, sentinel):
    cleanups = re.findall(r'(?m)^managed_escaped_pipe_cleanup root=(\S+) leader=Some\((\d+)\) leader_esrch=true holder=Some\((\d+)\) holder_esrch=true$', output)
    terminals = re.findall(r'(?m)^managed_escaped_pipe_terminal leader=Some\((\d+)\) leader_esrch=true holder=Some\((\d+)\) holder_esrch=true sentinel=(\d+) sentinel_esrch=true$', output)
    sentinels = re.findall(r'(?m)^managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true$', output)
    return (
        (root, str(leader), str(holder)) in cleanups
        and (str(leader), str(holder), str(sentinel)) in terminals
        and str(sentinel) in sentinels
    )


def test_section(output, name):
    starts = list(re.finditer(r'(?m)^test ([A-Za-z0-9_:]+) \.\.\. ', output))
    for index, match in enumerate(starts):
        if match.group(1) == name:
            end = starts[index + 1].start() if index + 1 < len(starts) else output.find('test result:', match.end())
            if end < 0:
                end = len(output)
            return output[match.start():end]
    return None


def parse_natural_control(output):
    section = test_section(output, TEST_REAP)
    ordinary = re.search(r'managed_post_reap_ordinary_wait root=(\S+) test_pid=(\d+) leader=(\d+) holder=(\d+) sentinel=(\d+) wait_unit=true holder_live=true', section or '')
    typed = re.search(r'managed_post_reap_typed_error cause=Io \{ op: "terminate process group", target: "([^"]+)", kind: PermissionDenied, message: "Operation not permitted \(os error 1\)" \}', section or '')
    leader = re.search(r'managed_post_reap_leader leader=(\d+) exit_record_matches=true exit_record="pid=(\d+) release_seen=true exit_intent=true.*try_wait_unit=false .*ps_status=Ok\("Z"\) leader_esrch=false holder=(\d+) holder_live=true', section or '')
    cleanup = re.search(r'managed_escaped_pipe_cleanup root=(\S+) leader=Some\((\d+)\) leader_esrch=false holder=Some\((\d+)\) holder_esrch=true', section or '')
    sentinel = re.search(r'managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true', section or '')
    named = bool(re.search(rf'(?m)^    {re.escape(TEST_REAP)}$', output))
    summary = bool(re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output))
    failure = 'natural leader exit with only its zombie remaining must not fail group closure' in output
    identities = bool(ordinary and typed and leader and cleanup and sentinel and named and summary and failure)
    if identities:
        root, test_pid, leader_pid, holder_pid, sentinel_pid = ordinary.groups()
        target = Path(typed.group(1))
        identities = (
            target.is_absolute() and target.parent.resolve() == (RUNTIME / 'target/debug/deps').resolve()
            and target.name.startswith('sys_process-')
            and leader.group(1) == leader_pid and leader.group(2) == leader_pid and leader.group(3) == holder_pid
            and cleanup.group(1) == root and cleanup.group(2) == leader_pid and cleanup.group(3) == holder_pid
            and sentinel.group(1) == sentinel_pid
            and len({int(test_pid), int(leader_pid), int(holder_pid), int(sentinel_pid)}) == 4
        )
        root_path = Path(root)
        identities = identities and root_path.is_absolute() and root_path.parent == RUNTIME / 'tmp' and root_path.name.startswith('rhai-sys-test-') and not root_path.is_symlink() and not root_path.exists()
    else:
        root = test_pid = leader_pid = holder_pid = sentinel_pid = None
    return {'valid': bool(identities), 'root': root, 'pids': [int(x) for x in (test_pid, leader_pid, holder_pid, sentinel_pid)] if identities else [], 'typed': bool(typed), 'specific_failure': failure, 'cleanup': bool(cleanup and sentinel)}


def preflight_natural_control():
    root = RUNTIME / 'tmp' / 'rhai-sys-test-natural-exit-control'
    valid = (
        f'test {TEST_REAP} ... managed_post_reap_ordinary_wait root={root} test_pid=301 leader=311 holder=312 sentinel=313 wait_unit=true holder_live=true\n'
        f'managed_post_reap_typed_error cause=Io {{ op: "terminate process group", target: "{RUNTIME}/target/debug/deps/sys_process-test", kind: PermissionDenied, message: "Operation not permitted (os error 1)" }} exit_code=None\n'
        'managed_post_reap_leader leader=311 exit_record_matches=true exit_record="pid=311 release_seen=true exit_intent=true\\n" try_wait_unit=false try_wait_error=Some("Process error") ps_status=Ok("Z") leader_esrch=false holder=312 holder_live=true\n'
        f'managed_escaped_pipe_cleanup root={root} leader=Some(311) leader_esrch=false holder=Some(312) holder_esrch=true\n'
        'managed-scope sentinel_cleanup pid=313 status=Some(0) esrch=true\n'
        f'    {TEST_REAP}\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 11 filtered out\n'
        'natural leader exit with only its zombie remaining must not fail group closure\n'
    )
    parsed = parse_natural_control(valid)
    assert parsed['valid'], f'valid typed-EPERM control rejected: {parsed!r}'
    assert not parse_natural_control(valid.replace('holder_live=true', 'holder_live=false', 1))['valid']
    assert not parse_natural_control(valid.replace('Operation not permitted (os error 1)', 'Input/output error (os error 5)', 1))['valid']
    assert not parse_natural_control(valid.replace('leader_esrch=false', 'leader_esrch=true', 1))['valid']
    assert not parse_natural_control(valid.replace('exit_record_matches=true', 'exit_record_matches=false', 1))['valid']
    assert not parse_natural_control(valid.replace('ps_status=Ok("Z")', 'ps_status=Err(Os { code: 3 })', 1))['valid']
    assert not parse_natural_control(valid.replace('exit_record_matches=true ', '', 1))['valid']
    assert not parse_natural_control(valid.replace('pid=311 release_seen=true', 'pid=999 release_seen=true', 1))['valid']
    assert not parse_natural_control(valid.replace('target: "', 'target: "/tmp/foreign-', 1))['valid']
    assert not parse_natural_control(valid.replace('leader_esrch=false holder=Some(312)', 'leader_esrch=true holder=Some(312)', 1))['valid']
    assert not parse_natural_control(valid.replace('natural leader exit with only its zombie remaining must not fail group closure', 'unrelated panic', 1))['valid']
    assert not parse_natural_control(valid.replace('holder=312', 'holder=999', 1))['valid']
    print('natural_exit_control_classifier_preflight=valid_and_11_mutations_passed', flush=True)

def parse_green(output):
    old_section = test_section(output, TEST_OLD)
    reap_section = test_section(output, TEST_REAP)
    old_wait = re.search(r'(?m)managed_escaped_pipe_wait root=(\S+) test_pid=(\d+) leader=(\d+) leader_pgid=(\d+) leader_esrch=true holder=(\d+) holder_pgid=(\d+) holder_live_after_wait=true sentinel=(\d+) sentinel_pgid=(\d+) sentinel_live_after_wait=true wait_unit=false probe="pid=(\d+) stdout_result=-1 stdout_error=(\d+) stderr_result=-1 stderr_error=(\d+)\\n" identity_ok=true', old_section or '')
    old_cleanup = bool(old_section and has_cleanup(old_section, 'managed_escaped_pipe_cleanup'))
    reap_ordinary = re.search(r'(?m)managed_post_reap_ordinary_wait root=(\S+) test_pid=(\d+) leader=(\d+) holder=(\d+) sentinel=(\d+) wait_unit=true holder_live=true', reap_section or '')
    reap_leader = re.search(r'(?m)managed_post_reap_leader leader=(\d+) exit_record_matches=true exit_record=.*release_seen=true exit_intent=true.*try_wait_unit=true .*leader_esrch=true holder=(\d+) holder_live=true', reap_section or '')
    reap_uncancelled = re.search(r'(?m)managed_post_reap_uncancelled_wait leader=(\d+) wait_unit=true holder=(\d+) holder_live=true sentinel=(\d+) sentinel_live=true', reap_section or '')
    reap_cancel = re.search(r'(?m)managed_post_reap_cancel root=(\S+) test_pid=(\d+) leader=(\d+) leader_esrch_before_kill=true leader_esrch=true holder=(\d+) holder_live_after_cancel=true holder_esrch=true sentinel=(\d+) sentinel_esrch=true probe="pid=(\d+) stdout_result=-1 stdout_error=(\d+) stderr_result=-1 stderr_error=(\d+)\\n" wait_unit=false', reap_section or '')
    green_tests = re.findall(r'(?m)^test (managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes|managed_spawn_post_reap_cancel_bounds_escaped_capture) \.\.\. ', output)
    summary = re.search(r'(?m)^test result: ok\. \d+ passed; 0 failed;', output)
    valid = bool(old_wait and old_cleanup and reap_ordinary and reap_leader and reap_uncancelled and reap_cancel and summary and sorted(green_tests) == sorted((TEST_OLD, TEST_REAP)))
    identities = False
    roots_absent = False
    if valid:
        old = tuple(map(int, old_wait.groups()[1:]))
        old_test, old_leader, old_pgid, old_holder, old_holder_pgid, old_sentinel, old_sentinel_pgid, old_probe, old_out_err, old_err_err = old
        r = reap_cancel.groups()
        reap_test, reap_leader_pid, reap_holder, reap_sentinel, reap_probe, reap_out_err, reap_err_err = map(int, r[1:])
        uncancelled_leader, uncancelled_holder, uncancelled_sentinel = map(int, reap_uncancelled.groups())
        old_root, reap_root = old_wait.group(1), reap_cancel.group(1)
        identities = (
            old_leader == old_pgid and old_holder != old_leader and old_holder_pgid == old_sentinel_pgid
            and old_sentinel == old_sentinel_pgid and old_probe == old_holder and old_out_err == 32 and old_err_err == 32
            and reap_ordinary.group(3) == reap_leader.group(1) == r[2]
            and reap_ordinary.group(4) == reap_leader.group(2) == r[3] == r[5]
            and (uncancelled_leader, uncancelled_holder, uncancelled_sentinel) == (reap_leader_pid, reap_holder, reap_sentinel)
            and reap_out_err == 32 and reap_err_err == 32
            and old_test == reap_test
            and len({old_test, old_leader, old_holder, old_sentinel, reap_leader_pid, reap_holder, reap_sentinel}) == 7
        )
        cleanup_lines = []
        terminal_lines = []
        sentinel_lines = []
        for section in (old_section, reap_section):
            cleanup_lines.extend(re.findall(r'(?m)^managed_escaped_pipe_cleanup root=(\S+) leader=Some\((\d+)\) leader_esrch=true holder=Some\((\d+)\) holder_esrch=true$', section or ''))
            terminal_lines.extend(re.findall(r'(?m)^managed_escaped_pipe_terminal leader=Some\((\d+)\) leader_esrch=true holder=Some\((\d+)\) holder_esrch=true sentinel=(\d+) sentinel_esrch=true$', section or ''))
            sentinel_lines.extend(re.findall(r'(?m)^managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true$', section or ''))
        roots = [Path(line[0]) for line in cleanup_lines]
        roots_absent = all(root.is_absolute() and root.parent == RUNTIME / 'tmp' and root.name.startswith('rhai-sys-test-') and not root.is_symlink() and not root.exists() for root in roots)
        cleanup_ids = {(row[0], int(row[1]), int(row[2])) for row in cleanup_lines}
        terminal_ids = [(int(row[0]), int(row[1]), int(row[2])) for row in terminal_lines]
        sentinel_ids = {int(row) for row in sentinel_lines}
        old_cleanup_matches = (old_root, old_leader, old_holder) in cleanup_ids
        reap_cleanup_matches = (reap_root, reap_leader_pid, reap_holder) in cleanup_ids
        identities = identities and len(terminal_ids) == 2 and terminal_ids == [
            (old_leader, old_holder, old_sentinel),
            (reap_leader_pid, reap_holder, reap_sentinel),
        ] and old_cleanup_matches and reap_cleanup_matches and old_sentinel in sentinel_ids and reap_sentinel in sentinel_ids
    return {'valid': bool(valid and identities and roots_absent), 'test_count': len(green_tests), 'identity': identities, 'fixture_roots_absent': roots_absent, 'old_cleanup': old_cleanup}


def run_cargo(argv, cwd, env, log_path, total_deadline):
    print('cargo_argv=' + repr(argv), flush=True)
    print('cargo_cwd=' + str(cwd), flush=True)
    print('cargo_log=' + str(log_path), flush=True)
    with log_path.open('wb') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
        print(f'cargo_pid={proc.pid} cargo_pgid={os.getpgid(proc.pid)}', flush=True)
        try:
            while proc.poll() is None:
                if time.monotonic() >= total_deadline:
                    raise TimeoutError('Cargo reached aggregate 540s watchdog')
                sample_storage(total_deadline)
                time.sleep(.5)
            status = proc.returncode
            emit_log(log_path, True)
            sample_storage(total_deadline)
        except BaseException:
            emit_log(log_path, proc.poll() is not None)
            raise
    return status, log_path.read_text(errors='replace')


if RUNTIME.is_symlink() or not RUNTIME.is_dir():
    raise RuntimeError('private runtime is not an owned directory')
if LOG_BASE.parent != EVIDENCE_DIR or LOG_BASE.is_symlink():
    raise RuntimeError('Cargo log is not in the owned evidence directory')
RUNTIME.joinpath('tmp').mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
print('phase=darwin_natural_exit_eperm_candidate', flush=True)
print('acceptance_scope=natural-exit EPERM fallback only after exact WNOWAIT leader identity and complete sole-leader process-group listing; cancellation remains fail-closed', flush=True)
print('runtime_path=' + str(RUNTIME), flush=True)
preflight_natural_control()
print(f'python={sys.version.replace(chr(10), " ")}', flush=True)
print('platform=' + platform.platform(), flush=True)
print(f'harness_pid={os.getpid()} supervisor_pid={os.getppid()} inherited_pgid={os.getpgid(0)}', flush=True)
for name, path in [('cargo', CARGO), ('rustc', RUSTC), ('rustdoc', RUSTDOC)]:
    if not path.is_file():
        raise RuntimeError(f'expected existing development tool missing: {path}')
    argv = [str(path), '--version', '--verbose'] if name == 'rustc' else [str(path), '--version']
    version = subprocess.check_output(argv, text=True, timeout=10).strip().replace('\n', ' | ')
    print(f'{name}_path={path} {name}_version={version}', flush=True)

original = {name: sha(REPO / name) for name in OVERLAYS}
print('repo_head=' + subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('original_overlay_hashes=' + repr(original), flush=True)
print('harness_hash=' + sha(Path(__file__)), flush=True)
print('wrapper_hash=' + sha(REPO / '.scratch/process-unix-run/run-managed-natural-exit-eperm.sh'), flush=True)

source = RUNTIME / 'source'
source.mkdir()
archive = RUNTIME / 'baseline.tar'
with archive.open('wb') as output:
    proc = subprocess.Popen(['git', '-C', str(REPO), 'archive', 'HEAD'], stdout=output, stderr=subprocess.PIPE, start_new_session=False)
    deadline = time.monotonic() + 90
    while proc.poll() is None:
        if time.monotonic() >= deadline:
            raise TimeoutError('baseline archive exceeded 90s')
        sample_storage(deadline)
        time.sleep(.5)
    stderr = proc.stderr.read().decode(errors='replace')
    if proc.returncode:
        raise RuntimeError(f'git archive failed: {stderr}')
extract = subprocess.run(['tar', '-xf', str(archive), '-C', str(source)], timeout=90)
if extract.returncode:
    raise RuntimeError('baseline extraction failed')
archive.unlink()
for name in OVERLAYS:
    (source / name).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / name, source / name)
candidate_hashes = {name: sha(source / name) for name in OVERLAYS}
if candidate_hashes != original:
    raise RuntimeError('private candidate overlays differ from frozen source')
print('private_candidate_hashes=' + repr(candidate_hashes), flush=True)

accepted_lock = REPO / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
lock_hash = sha(accepted_lock)
if lock_hash != BASE_LOCK_SHA:
    raise RuntimeError(f'accepted lock hash mismatch: {lock_hash}')
private_lock = source / 'Cargo.lock'
shutil.copy2(accepted_lock, private_lock)
lock_text = private_lock.read_text()
marker = 'name = "rhai"\nversion = "1.26.1"\ndependencies = [\n'
if lock_text.count(marker) != 1:
    raise RuntimeError('unexpected accepted-lock rhai entry')
start = lock_text.index(marker)
end = lock_text.index('\n]', start)
section = lock_text[start:end]
if ' "libc",\n' not in section:
    at = section.index(' "libm",\n')
    section = section[:at] + ' "libc",\n' + section[at:]
    lock_text = lock_text[:start] + section + lock_text[end:]
    private_lock.write_text(lock_text)
print(f'accepted_lock_sha256={lock_hash} private_lock_sha256={sha(private_lock)} private_direct_libc_edge=true', flush=True)

env = dict(os.environ)
for key in ('RUSTUP_TOOLCHAIN', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_BUILD_RUSTC_WRAPPER'):
    env.pop(key, None)
env.update({
    'PATH': f'{TOOLCHAIN}:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',
    'CARGO_HOME': str(RUNTIME / 'cargo-home'), 'RUSTUP_HOME': str(RUNTIME / 'rustup-home'),
    'CARGO_TARGET_DIR': str(RUNTIME / 'target'), 'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
    'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0', 'RUSTC': str(RUSTC),
    'RUSTDOC': str(RUSTDOC), 'TMPDIR': str(RUNTIME / 'tmp'), 'TMP': str(RUNTIME / 'tmp'), 'TEMP': str(RUNTIME / 'tmp'),
})
(RUNTIME / 'cargo-home').mkdir()
(RUNTIME / 'rustup-home').mkdir()
deadline = time.monotonic() + 540
control_logs = [LOG_BASE.with_name(LOG_BASE.name + f'.control-{TEST_REAP}.log')]
integration_log = LOG_BASE.with_name(LOG_BASE.name + '.restored-sys-process.log')
unit_log = LOG_BASE.with_name(LOG_BASE.name + '.restored-unix-owner-tests.log')
# Publish the log index before any Cargo command so early control failures retain discoverable logs.
LOG_BASE.write_text('\n'.join([f'control={path}' for path in control_logs] + [f'integration={integration_log}', f'unix_owner_tests={unit_log}']) + '\n')
print(f'cargo_log_index={LOG_BASE} control_logs={control_logs!r} integration_log={integration_log} unit_log={unit_log}', flush=True)

def exact_test(name, path):
    return [str(CARGO), 'test', '--locked', '--test', 'sys_process', '--features', 'testing-environ,sys', '--', name, '--exact', '--nocapture', '--test-threads=1']

private_unix = source / 'src/packages/sys/process/unix.rs'
unix_original = private_unix.read_bytes()
needle = b'if error.raw_os_error() == Some(libc::EPERM) && context == GroupCloseContext::LeaderExited {'
if unix_original.count(needle) != 1:
    raise RuntimeError('expected one narrow Darwin natural-exit EPERM fallback branch')
private_unix.write_bytes(unix_original.replace(needle, b'if false {'))
print('broken_control_mutation=reject sole-zombie natural-exit EPERM fallback', flush=True)

# The one intended control proves the otherwise accepted natural-exit path fails specifically
# when the fallback is omitted. The fixture's typed cause/identity and Drop cleanup are required.
status, output = run_cargo(exact_test(TEST_REAP, control_logs[0]), source, env, control_logs[0], deadline)
parsed_control = parse_natural_control(output)
control_valid = status == 101 and parsed_control['valid']
control_pids = parsed_control['pids']
print(f'natural_exit_eperm_omission_control status={status} valid={control_valid} identities={parsed_control!r}', flush=True)
if not control_valid:
    raise RuntimeError('fallback-omission control did not reach the exact typed-EPERM assertion and cleanup')
for pid in control_pids:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        absent = True
    except PermissionError:
        absent = False
    else:
        absent = False
    print(f'control_pid_esrch pid={pid} absent={str(absent).lower()}', flush=True)
    if not absent:
        raise RuntimeError(f'control-owned PID was not independently ESRCH after Cargo: {pid}')
private_unix.write_bytes(unix_original)
if sha(private_unix) != candidate_hashes['src/packages/sys/process/unix.rs']:
    raise RuntimeError('restored production source does not match frozen candidate')
print('broken_control_source_restored=true', flush=True)

integration_argv = [str(CARGO), 'test', '--locked', '--test', 'sys_process', '--features', 'testing-environ,sys', '--', '--nocapture', '--test-threads=1']
integration_status, integration_output = run_cargo(integration_argv, source, env, integration_log, deadline)
green_receipt = parse_green(integration_output)
print(f'restored_sys_process_status={integration_status} receipt={green_receipt!r}', flush=True)
if integration_status != 0 or not green_receipt['valid']:
    raise RuntimeError('restored sys_process suite did not pass with complete retained-pipe receipts')

unit_argv = [str(CARGO), 'test', '--locked', '--lib', '--features', 'testing-environ,sys', 'packages::sys::process::unix::tests::', '--', '--test-threads=1', '--nocapture']
unit_status, unit_output = run_cargo(unit_argv, source, env, unit_log, deadline)
unit_match = re.search(r'(?m)^test result: ok\. (\d+) passed; 0 failed;', unit_output)
print(f'restored_unix_owner_tests_status={unit_status} passed={unit_match.group(1) if unit_match else "missing"}', flush=True)
if unit_status != 0 or not unit_match or int(unit_match.group(1)) == 0:
    raise RuntimeError('restored Unix owner unit suite did not pass')

final = {name: sha(source / name) for name in OVERLAYS}
print('final_private_overlay_hashes=' + repr(final), flush=True)
if final != candidate_hashes:
    raise RuntimeError('private candidate overlays changed during verification')
exit_manifest = {name: sha(source / name) for name in OVERLAYS}
print('exit_private_overlay_hashes=' + repr(exit_manifest), flush=True)
if exit_manifest != candidate_hashes:
    raise RuntimeError('exit private overlay manifest differs from frozen candidate')
LOG_BASE.write_text('\n'.join([
    f'control={LOG_BASE.name + ".control-" + TEST_REAP + ".log"}',
    f'integration={integration_log}', f'unix_owner_tests={unit_log}',
]) + '\n')
print('retained_pipe_cancellation_green=accepted_development_only', flush=True)
