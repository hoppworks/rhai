#!/usr/bin/env python3
"""Run the frozen Linux process contract in run_scoped's private runtime."""
import hashlib
import os
import pathlib
import re
import shutil
import signal
import subprocess
import threading
import time

STAGE = pathlib.Path(os.environ['PROOF_STAGE']).resolve(strict=True)
EVIDENCE = STAGE / 'evidence'
RUNTIME = pathlib.Path(os.environ['AGENT_RUNTIME_DIR']).resolve(strict=True)
SOURCE = RUNTIME / 'source'
TARGET = RUNTIME / 'target'
LOCK_BASE = STAGE / 'Cargo.lock.baseline'
LOCK_SHA = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
LOCK_EDGE = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
ARCHIVE_SHA = '44b60f1d1260d90b4bb546aad92ff44f673c3257fc0cd9b1e35faf01c33240d5'
RUST = pathlib.Path('/root/.rustup/toolchains/1.93.0-x86_64-unknown-linux-gnu/bin')
CARGO = RUST / 'cargo'
RUSTC = RUST / 'rustc'
RUSTDOC = RUST / 'rustdoc'
BASE_ENV = {}
OUTER_DEADLINE = time.monotonic() + 580  # leave 20 seconds of the 600-second package for scoped cleanup/readback
CARGO_DEADLINE = time.monotonic() + 540
SAMPLED_STOP_KIB = 1_572_864
HARD_KIB = 2 * 1024 * 1024
MAX_OWNED_PROCESSES = 16
SOURCE_PATHS = (
    'Cargo.toml', 'src/packages/sys/config.rs', 'src/packages/sys/mod.rs',
    'src/packages/sys/process.rs', 'src/packages/sys/process/unix.rs', 'tests/sys_process.rs',
)

EVIDENCE.mkdir(parents=True, exist_ok=True)
stop_sampler = threading.Event()
custody_failure = []
identities = {}  # pid -> (start_ticks, ppid, pgid, cmdline); exact observed identity only
storage_samples = []
identities_lock = threading.Lock()
active = [None]
sampler_thread = None
proof_completed = False
initial_source_hashes = {}


def emit(message):
    print(message, flush=True)


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def proc_stat(pid):
    raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
    fields = raw[raw.rfind(')') + 2:].split()  # fields begin at stat field 3
    return int(fields[1]), int(fields[2]), fields[19]  # ppid, pgrp, starttime (field 22)


def proc_identity(pid):
    ppid, pgid, start = proc_stat(pid)
    cmdline = pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
    return (start, ppid, pgid, cmdline)


def signal_exact_identity(pid, start_ticks, signum):
    """Pin the Linux task with pidfd, then revalidate its start tick before signaling."""
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('pidfd_open/pidfd_send_signal unavailable; refusing stale-PID cleanup')
    try:
        fd = os.pidfd_open(pid, 0)
    except ProcessLookupError:
        return False
    try:
        try:
            current = proc_identity(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
            return False
        if current[0] != start_ticks:
            return False
        try:
            signal.pidfd_send_signal(fd, signum)
            return True
        except ProcessLookupError:
            return False
    finally:
        os.close(fd)


def live_processes():
    found = {}
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            found[pid] = proc_identity(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
            continue
    return found


def descendants(snapshot, root):
    children = {}
    for pid, identity in snapshot.items():
        children.setdefault(identity[1], []).append(pid)
    result = set()
    todo = [root]
    while todo:
        parent = todo.pop()
        for pid in children.get(parent, ()):
            if pid not in result:
                result.add(pid)
                todo.append(pid)
    return result


def bounded_storage():
    result = subprocess.run(['du', '-sk', str(RUNTIME)], capture_output=True, text=True, timeout=4, check=True)
    fields = result.stdout.strip().split(maxsplit=1)
    if len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(RUNTIME):
        raise RuntimeError('malformed private runtime storage sample: ' + repr(result.stdout))
    return int(fields[0])


def sampler():
    try:
        with (EVIDENCE / 'resource-samples.tsv').open('w', buffering=1) as storage, \
             (EVIDENCE / 'process-samples.tsv').open('w', buffering=1) as processes, \
             (EVIDENCE / 'process-identities.tsv').open('w', buffering=1) as identity_log:
            storage.write('utc_epoch\tsampled_runtime_kib\n')
            processes.write('utc_epoch\towned_descendants\tscoped_group_pids\n')
            identity_log.write('pid\tstart_ticks\tppid\tpgid\tcmdline\n')
            while not stop_sampler.wait(1):
                size = bounded_storage()
                snapshot = live_processes()
                owned = descendants(snapshot, os.getpid())
                group = os.getpgid(0)
                scoped = sorted(pid for pid, ident in snapshot.items() if ident[2] == group)
                with identities_lock:
                    for pid in owned:
                        ident = snapshot.get(pid)
                        if ident is None:
                            continue
                        old = identities.get(pid)
                        if old is not None and old[0] != ident[0]:
                            raise RuntimeError(f'PID {pid} was reused during custody sampling')
                        identities[pid] = ident
                        if old != ident:
                            identity_log.write(f'{pid}\t{ident[0]}\t{ident[1]}\t{ident[2]}\t{ident[3]}\n')
                    storage_samples.append(size)
                storage.write(f'{time.time():.3f}\t{size}\n')
                processes.write(f'{time.time():.3f}\t{len(owned)}\t{",".join(map(str, scoped))}\n')
                if len(owned) > MAX_OWNED_PROCESSES:
                    raise RuntimeError(f'owned descendant count {len(owned)} exceeded {MAX_OWNED_PROCESSES}')
                if size >= SAMPLED_STOP_KIB or size >= HARD_KIB:
                    raise RuntimeError(f'sampled private storage reached {size} KiB (stop {SAMPLED_STOP_KIB}; hard {HARD_KIB})')
                if time.monotonic() >= min(OUTER_DEADLINE, CARGO_DEADLINE):
                    raise TimeoutError('600-second outer or 540-second aggregate Cargo deadline reached')
    except BaseException as exc:
        custody_failure.append(exc)
        emit(f'CUSTODY_SAMPLER_FAILURE {type(exc).__name__}: {exc}')
        proc = active[0]
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass


def stop_handler(signum, _frame):
    raise InterruptedError(f'received signal {signum}; cleaning sampled exact child identities')


for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, stop_handler)


def record_process(label, pid, log):
    # A very short Cargo wrapper can exit before its first /proc sample.
    try:
        ident = proc_identity(pid)
    except (FileNotFoundError, ProcessLookupError):
        log.write(f'{label}\t{pid}\t<exited-before-identity-sample>\n')
        return
    with identities_lock:
        identities[pid] = ident
    log.write(f'{label}\t{pid}\t{ident[0]}\t{ident[1]}\t{ident[2]}\t{ident[3]}\n')
    log.flush()
    os.fsync(log.fileno())


def monitor_health():
    heartbeat = pathlib.Path(os.environ['PROOF_CUSTODY_HEARTBEAT'])
    ready = pathlib.Path(os.environ['PROOF_CUSTODY_READY'])
    if ready.is_symlink() or not ready.is_file() or heartbeat.is_symlink() or not heartbeat.is_file():
        return False, 'ready/heartbeat missing or symlinked'
    try:
        ready_text = ready.read_text()
        heartbeat_text = heartbeat.read_text().strip()
    except OSError as exc:
        return False, f'ready/heartbeat unreadable: {type(exc).__name__}'
    match = re.fullmatch(r'pid=(\d+) start_ticks=(\d+)\n?', ready_text)
    if not match:
        return False, 'ready identity malformed'
    expected_pid, expected_start = int(match.group(1)), match.group(2)
    try:
        age = time.time() - float(heartbeat_text)
    except ValueError:
        return False, 'heartbeat timestamp malformed or observed during a partial update'
    if age > 1.0:
        return False, f'heartbeat stale by {age:.3f}s'
    try:
        current = os.getpid()
        for _ in range(8):
            identity = proc_identity(current)
            if current == expected_pid:
                if identity[0] != expected_start:
                    return False, 'monitor root PID start tick changed'
                return True, 'ready'
            current = identity[1]
            if current <= 1:
                return False, 'monitor root is not in the owned ancestor chain'
    except (OSError, ValueError, IndexError) as exc:
        return False, f'monitor ancestry unreadable: {type(exc).__name__}'
    return False, 'monitor root not found in the owned ancestor chain'

def monitor_ready():
    return monitor_health()[0]

def source_manifest(phase):
    path = EVIDENCE / 'source-restoration-manifests.tsv'
    with path.open('a') as stream:
        for relative in SOURCE_PATHS:
            stream.write(f'{phase}\t{relative}\t{sha(SOURCE / relative)}\n')
        stream.flush()
        os.fsync(stream.fileno())

def sources_match_initial():
    for relative, expected in initial_source_hashes.items():
        if sha(SOURCE / relative) != expected:
            return False
    return True

def run(label, args, expect=0):
    monitor_ok, monitor_reason = monitor_health()
    if not monitor_ok:
        raise RuntimeError(f'external process custody monitor is not ready: {monitor_reason}')
    deadline = min(OUTER_DEADLINE, CARGO_DEADLINE)
    if time.monotonic() >= deadline:
        raise TimeoutError(f'{label} started after the package deadline')
    log_path = EVIDENCE / f'{label}.log'
    status_path = EVIDENCE / f'{label}.status'
    argv = [str(CARGO), *args]
    emit(f'COMMAND {label}: {argv!r}')
    start = time.monotonic()
    with log_path.open('w', buffering=1) as stream, (EVIDENCE / 'command-identities.tsv').open('a', buffering=1) as ids:
        if ids.tell() == 0:
            ids.write('label\tpid\tstart_ticks\tppid\tpgid\tcmdline\n')
            ids.flush()
        proc = subprocess.Popen(argv, cwd=SOURCE, env=BASE_ENV, stdout=stream, stderr=subprocess.STDOUT, start_new_session=False)
        active[0] = proc
        record_process(label, proc.pid, ids)
        try:
            while proc.poll() is None:
                if custody_failure:
                    raise RuntimeError('resource/process sampler failed') from custody_failure[0]
                monitor_ok, monitor_reason = monitor_health()
                if not monitor_ok:
                    raise RuntimeError(f'external process custody monitor failed: {monitor_reason}')
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'{label} exceeded active command deadline; Cargo emits to a file')
                time.sleep(.2)
            status = proc.returncode
        finally:
            # Cargo is our direct child, so its unreaped PID cannot be reused.
            # Reap it before exact descendant cleanup and runtime exit.
            if proc.poll() is None:
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1)
            else:
                proc.wait()
            active[0] = None
    status_path.write_text(f'{status}\n')
    with status_path.open('rb') as receipt:
        os.fsync(receipt.fileno())
    text = log_path.read_text(errors='replace')
    emit(f'STATUS {label}={status} elapsed={time.monotonic()-start:.2f}s')
    if status != expect:
        raise RuntimeError(f'{label}: expected exit {expect}, observed {status}')
    if re.search(r'(?m)^error:|^test result: FAILED\.', text) and expect == 0:
        raise RuntimeError(f'{label}: output contains a compile or test failure despite zero exit')
    return text


def exact_receipt(label, log, expected_status, test_name):
    if expected_status == 101:
        summary = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', log)
        named = re.search(rf'(?m)^test {re.escape(test_name)} \.\.\. ', log)
        survivor = re.search(r'managed member pid=(\d+) start=(\d+) remained live at API return', log)
        worker = re.search(r'managed_fixture_cleanup worker_pid=Some\((\d+)\) worker_esrch=true', log)
        acquired = [tuple(match.groups()) for match in re.finditer(
            r'managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)', log)]
        worker_identity = next((row for row in acquired if survivor and row[:2] == survivor.groups()), None)
        cleanup = re.search(r'managed_fixture_cleanup worker_pid=Some\((\d+)\) worker_esrch=true leaf_pid=Some\((\d+)\) leaf_esrch=true', log)
        topology = (len(acquired) == 3 and worker_identity == acquired[1] and
                    acquired[1][2] == acquired[0][0] and acquired[1][3] == acquired[0][3] and
                    acquired[2][2] == acquired[1][0] and acquired[2][3] == acquired[1][3])
        if not (summary and named and survivor and worker and worker_identity and cleanup and topology and
                survivor.group(1) == worker.group(1) == cleanup.group(1) == acquired[1][0] and
                cleanup.groups() == (acquired[1][0], acquired[2][0])):
            raise RuntimeError('known-broken control did not fail on the exact acquired worker PID/start identity and then clean both fixture members')


def owner_suite_valid(log, expected_count=20):
    summaries = re.findall(r'(?m)^test result: ok\. (\d+) passed; 0 failed;', log)
    name = 'packages::sys::process::unix::tests::public_kill_on_drop_false_final_lease_retires_owner_and_worker'
    named = re.search(rf'(?m)^test {re.escape(name)} \.\.\. ', log)
    receipt = re.search(
        rf'(?m)^(?:test {re.escape(name)} \.\.\. )?false-policy-owner-retired '
        r'pid=(\d+) slot_retired=true worker_done=true reap=ESRCH '
        r'stdout=retained-output stdout_complete=true stderr_complete=true exit=Code\(0\)$',
        log,
    )
    return bool(summaries and int(summaries[-1]) == expected_count and named and receipt)


def fixture_root_valid(root, test_pid, test_name):
    path = pathlib.Path(root)
    return (not path.is_symlink() and path.parent.resolve() == (RUNTIME / 'tmp').resolve() and not path.exists() and
            re.fullmatch(rf'rhai-sys-test-{test_pid}-{re.escape(test_name)}-\d+', path.name) is not None)

def successful_test_section(log, name):
    lines = log.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(rf'test {re.escape(name)} \.\.\. ', line)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if re.match(r'^test [\w:]+ \.\.\. ', lines[i])), len(lines))
    section = lines[start:end]
    terminal = any(line.strip() == 'ok' or line == f'test {name} ... ok' for line in section)
    return section if terminal else None


def restored_direct_valid(log, expected_summary=1):
    name = 'direct_spawn_kill_on_drop_false_preserves_child_and_capture'
    started = re.search(rf'(?m)^test {name} \.\.\. direct_drop_fixture_started root=(\S+) test_pid=(\d+) child_pid=(\d+)$', log)
    if not started:
        started = re.search(rf'(?m)^direct_drop_fixture_started root=(\S+) test_pid=(\d+) child_pid=(\d+)$', log)
    if not started:
        return False
    root, owner, child = started.groups()
    observed = re.search(rf'(?m)^direct_drop_after_final_client_drop pid={child} alive=true challenge_ack=true completion_exists=false$', log)
    complete = re.search(rf'(?m)^direct_drop_completion pid={child} record="pid={child} stdout_bytes=524288 stderr_bytes=524288 complete=true\\n"$', log)
    terminal = re.search(rf'(?m)^direct_drop_terminal pid={child} esrch=true$', log)
    cleanup = re.search(rf'(?m)^direct_drop_fixture_cleanup root={re.escape(root)} pid={child} esrch=true$', log)
    summary = re.search(rf'(?m)^test result: ok\. {expected_summary} passed; 0 failed;', log)
    named = re.search(rf'(?m)^test {name} \.\.\. ', log)
    return bool(summary and named and observed and complete and terminal and cleanup and owner != child and fixture_root_valid(root, owner, name))


def restored_managed_valid(log, expected_summary=1):
    name = 'managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit'
    started = re.search(rf'(?m)^test {name} \.\.\. managed_false_drop_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)$', log)
    if not started:
        started = re.search(r'(?m)^managed_false_drop_started root=(\S+) test_pid=(\d+) sentinel_pid=(\d+) sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)$', log)
    if not started:
        return False
    root, test_pid, sentinel, sentinel_group, leader, worker, leaf, group = started.groups()
    live = re.search(rf'(?m)^managed_false_drop_after_final_client_drop leader={leader} leader_live=true worker={worker} worker_live=true leaf={leaf} leaf_live=true sentinel={sentinel} sentinel_live=true$', log)
    challenge = re.search(rf'(?m)^managed_false_drop_live_challenge leader={leader} worker={worker} leaf={leaf} group={group} ack_count=3 ack_pids=\[Some\({leader}\), Some\({worker}\), Some\({leaf}\)\] ack_groups=\[Some\({group}\), Some\({group}\), Some\({group}\)\]$', log)
    closed = re.search(rf'(?m)^managed_false_drop_after_leader_exit leader={leader} leader_esrch=true worker={worker} worker_esrch=true leaf={leaf} leaf_esrch=true sentinel={sentinel} sentinel_live=true$', log)
    cleanup = re.search(rf'(?m)^managed_fixture_cleanup worker_pid=Some\({worker}\) worker_esrch=true leaf_pid=Some\({leaf}\) leaf_esrch=true$', log)
    leader_cleanup = re.search(rf'(?m)^managed_spawn_fixture_leader_cleanup leader_pid=Some\({leader}\) leader_esrch=true$', log)
    sentinel_cleanup = re.search(rf'(?m)^managed-scope sentinel_cleanup pid={sentinel} status=.* esrch=true$', log)
    summary = re.search(rf'(?m)^test result: ok\. {expected_summary} passed; 0 failed;', log)
    named = re.search(rf'(?m)^test {name} \.\.\. ', log)
    distinct = len({test_pid, sentinel, leader, worker, leaf}) == 5 and sentinel == sentinel_group and leader == group
    root_ok = fixture_root_valid(root, test_pid, name)
    return bool(named and summary and live and challenge and closed and cleanup and leader_cleanup and sentinel_cleanup and distinct and root_ok)


def held_zombie_boundary_valid(log, expected_summary=32):
    name = 'managed_run_reports_while_fixture_reaper_holds_stopped_zombies'
    section = successful_test_section(log, name)
    boundary = re.search(
        r'managed_held_zombie_boundary host_live_at_return=true leader=(\d+) leader_start=(\d+) leader_reaped=true '
        r'worker=(\d+) worker_start=(\d+) worker_state=Z worker_pgid=(\d+) '
        r'leaf=(\d+) leaf_start=(\d+) leaf_state=Z leaf_pgid=(\d+) '
        r'group=(\d+) kill_zero_result=(-?\d+) kill_zero_errno=(\d+) capture_complete=true '
        r'host=\d+ host_start=\d+ (?:api_success=true api_outcome=success_report|'
        r'api_success=false api_outcome=typed_process_io cause_op=observe_process_group_closure '
        r'cause_op_matches=true kind=\S+ exit=\S+ stdout_complete=true stderr_complete=true diagnostic=true)',
        log,
    )
    cleanup = re.search(r'managed_held_zombie_cleanup worker=(\d+) reaped=true leaf=(\d+) reaped=true', log)
    summaries = re.findall(r'(?m)^test result: ok\. (\d+) passed; 0 failed;', log)
    if not (section and boundary and cleanup and summaries and int(summaries[-1]) == expected_summary):
        return False
    leader, leader_start, worker, worker_start, worker_group, leaf, leaf_start, leaf_group, group, kill_result, kill_errno = boundary.groups()
    return (cleanup.groups() == (worker, leaf) and worker != leaf and worker_start != '0' and leaf_start != '0'
            and leader != worker and leader_start != '0' and worker_group == leaf_group == group == leader
            and kill_result in ('0', '-1')
            and (kill_result == '0' or kill_errno in ('1', '3')))


def kill_sampled_exact_children():
    # pidfd pins the process; recheck start ticks after opening it, before signaling.
    with identities_lock:
        observed = list(identities.items())
    for pid, identity in observed:
        if pid in (os.getpid(), os.getppid()):
            continue
        signal_exact_identity(pid, identity[0], signal.SIGTERM)
    until = time.monotonic() + 1.0
    while time.monotonic() < until:
        alive = []
        for pid, identity in observed:
            try:
                current = proc_identity(pid)
            except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
                continue
            if current[0] == identity[0]:
                alive.append(pid)
        if not alive:
            break
        time.sleep(.05)
    for pid, identity in observed:
        try:
            current = proc_identity(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
            continue
        if current[0] == identity[0]:
            signal_exact_identity(pid, identity[0], signal.SIGKILL)
    still_live = []
    for pid, identity in observed:
        try:
            current = proc_identity(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
            continue
        if current[0] == identity[0]:
            still_live.append(pid)
    return still_live


def main():
    global BASE_ENV, sampler_thread, proof_completed, initial_source_hashes
    if RUNTIME.is_symlink() or not RUNTIME.is_dir() or STAGE.is_symlink():
        raise RuntimeError('runtime/stage ownership path is not a real directory')
    if sha(LOCK_BASE) != LOCK_SHA or sha(STAGE / 'source.tar') != ARCHIVE_SHA:
        raise RuntimeError('staged archive or accepted baseline lock hash mismatch')
    for name in ('cargo', 'rustc', 'rustdoc'):
        path = RUST / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f'required direct toolchain binary is unavailable: {path}')
    for label, binary in (('rustc-version', RUSTC), ('cargo-version', CARGO)):
        out = subprocess.run([str(binary), '--version', '--verbose'], capture_output=True, text=True, timeout=10, check=True).stdout
        if '1.93.0' not in out:
            raise RuntimeError(f'{binary} is not the preexisting direct 1.93.0 tool: {out!r}')
        (EVIDENCE / f'{label}.txt').write_text(out)

    SOURCE.mkdir()
    RUNTIME.joinpath('cargo-home').mkdir()
    RUNTIME.joinpath('rustup-home').mkdir()
    runtime_tmp = RUNTIME / 'tmp'
    if runtime_tmp.is_symlink() or not runtime_tmp.is_dir():
        raise RuntimeError('scoped runner did not create its private runtime/tmp directory')
    with __import__('tarfile').open(STAGE / 'source.tar') as archive:
        archive.extractall(SOURCE, filter='data')
    shutil.copy2(LOCK_BASE, SOURCE / 'Cargo.lock')
    initial_source_hashes = {relative: sha(SOURCE / relative) for relative in SOURCE_PATHS}
    source_manifest('before-control')
    manifest = SOURCE / 'Cargo.toml'
    if 'libc = { version = "=0.2.189", optional = true }' not in manifest.read_text():
        raise RuntimeError('frozen production manifest lacks the expected exact optional libc dependency')
    lock_path = SOURCE / 'Cargo.lock'
    lock = lock_path.read_text()
    start = lock.index('name = "rhai"\n')
    end = lock.index('[[package]]', start)
    package = lock[start:end]
    if ' "libc",\n' not in package:
        if ' "libm",\n' not in package:
            raise RuntimeError('baseline lock lacks the exact package edge insertion anchor')
        lock_path.write_text(lock[:start] + package.replace(' "libm",\n', ' "libc",\n "libm",\n', 1) + lock[end:])
    if sha(lock_path) != LOCK_EDGE:
        raise RuntimeError('private edge-only lock hash differs from independently accepted SHA')

    global BASE_ENV
    BASE_ENV = dict(os.environ)
    BASE_ENV.update({
        'CARGO_HOME': str(RUNTIME / 'cargo-home'),
        'RUSTUP_HOME': str(RUNTIME / 'rustup-home'),
        'CARGO_TARGET_DIR': str(TARGET),
        'TMPDIR': str(RUNTIME / 'tmp'), 'TMP': str(RUNTIME / 'tmp'), 'TEMP': str(RUNTIME / 'tmp'),
        'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0', 'CARGO_PROFILE_DEV_DEBUG': '0',
        'CARGO_PROFILE_TEST_DEBUG': '0', 'RUSTFLAGS': '-C debuginfo=0',
        'RUSTC': str(RUSTC), 'RUSTDOC': str(RUSTDOC), 'PATH': str(RUST) + os.pathsep + os.environ.get('PATH', ''),
    })
    for key in ('RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTUP_TOOLCHAIN', 'CARGO_HOME_CONFIG'):
        BASE_ENV.pop(key, None)
    emit(f'PRIVATE_RUNTIME {RUNTIME}')
    emit(f'SOURCE_ARCHIVE sha256={ARCHIVE_SHA} revision=911fe6fc047cfc5240347ccc4cd11fa56a282ff8')
    emit(f'LOCK edge_only_sha256={LOCK_EDGE} baseline_sha256={LOCK_SHA}')
    emit(f'PLATFORM {subprocess.check_output(["uname", "-a"], text=True).strip()}')
    emit('LIMITS package_outer_seconds=600 active_driver_seconds=580 aggregate_cargo_seconds=540 cargo_jobs=2 storage_sample_stop_kib=1572864 hard_policy_kib=2097152 sampler_interval_seconds=1')
    sampler_thread = threading.Thread(target=sampler, name='linux-process-custody-sampler', daemon=True)
    sampler_thread.start()
    common = ['test', '--locked', '--no-fail-fast', '--features', 'testing-environ,sys']
    test = 'managed_run_closes_pipe_closed_worker_before_return'
    implementation = SOURCE / 'src/packages/sys/process/unix.rs'
    original = implementation.read_bytes()
    original_sha = hashlib.sha256(original).hexdigest()
    old = b'if status.is_some() && out_eof && err_eof && scope_closed {'
    new = b'if status.is_some() && out_eof && err_eof {'
    group_signal = b'libc::kill(-(pid as libc::pid_t), libc::SIGKILL)'
    group_probe = b'libc::kill(-(pid as libc::pid_t), 0)'
    if original.count(old) != 1 or original.count(group_signal) != 1:
        raise RuntimeError('known-broken control could not locate exactly one managed scope-completion gate and group-close signal')
    try:
        controlled = original.replace(old, new, 1).replace(group_signal, group_probe, 1)
        implementation.write_bytes(controlled)
        control = run('known-broken-managed-gate-control', common + ['--test', 'sys_process', test, '--', '--exact', '--nocapture', '--test-threads=1'], expect=101)
        exact_receipt('known-broken-managed-gate-control', control, 101, test)
    finally:
        implementation.write_bytes(original)
    if sha(implementation) != original_sha:
        raise RuntimeError('production implementation bytes did not restore exactly after control')
    emit(f'CONTROL_SOURCE_RESTORED sha256={original_sha}')
    if not sources_match_initial():
        raise RuntimeError('one or more frozen production/test inputs did not restore after control')
    source_manifest('after-control-restoration')

    if sha(implementation) != original_sha:
        raise RuntimeError('production source drifted before restored suites')
    owner = run('unix-owner', common + ['--lib', 'packages::sys::process::unix::tests::', '--', '--nocapture', '--test-threads=1'])
    if not owner_suite_valid(owner):
        raise RuntimeError('Unix process owner suite lacks 20 passing tests or exact owner/worker/reap/output receipt')
    source_manifest('after-owner-suite')
    if not sources_match_initial():
        raise RuntimeError('frozen production/test inputs drifted during owner suite')
    full = run('full-sys-process', common + ['--test', 'sys_process', '--', '--nocapture', '--test-threads=1'])
    if not restored_direct_valid(full, expected_summary=32) or not restored_managed_valid(full, expected_summary=32) or not held_zombie_boundary_valid(full, expected_summary=32):
        raise RuntimeError('full sys_process suite did not emit direct and managed challenge/cleanup receipts')
    full_summaries = re.findall(r'(?m)^test result: ok\. (\d+) passed; 0 failed;', full)
    if not full_summaries or int(full_summaries[-1]) != 32:
        raise RuntimeError('public sys_process suite lacks the expected 32-test passing outer summary')
    for name in ('managed_run_closes_pipe_closed_worker_before_return', 'direct_run_returns_with_pipe_closed_worker_live_control', 'managed_run_reports_while_fixture_reaper_holds_stopped_zombies'):
        if successful_test_section(full, name) is None:
            raise RuntimeError(f'full public suite did not emit a successful terminal receipt for boundary test {name}')
    source_manifest('after-full-suite')
    if not sources_match_initial():
        raise RuntimeError('frozen production/test inputs differ from original after restored suites')
    owner_summaries = re.findall(r'(?m)^test result: ok\. (\d+) passed; 0 failed;', owner)
    emit(f'OUTER_SUMMARY full_sys_process_passed={full_summaries[-1]} owner_passed={owner_summaries[-1]} raw_sys_process_test_attributes=33')
    shutil.copy2(lock_path, EVIDENCE / 'Cargo.lock.final')
    emit(f'EXPORTED_FINAL_LOCK sha256={sha(lock_path)}')
    emit(f'SAMPLED_PRIVATE_STORAGE_MAX_KIB={max(storage_samples, default=0)}; interval=1s du -sk; sampled maximum, not continuous peak')
    emit('LINUX_PROCESS_PUBLIC_BEHAVIOR_PROOF_COMPLETE')
    proof_completed = True


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        emit(f'PROOF_STOP {type(exc).__name__}: {exc}')
        raise
    finally:
        stop_sampler.set()
        if sampler_thread is not None and sampler_thread.is_alive():
            sampler_thread.join(timeout=3)
        before_cleanup = []
        with identities_lock:
            exact_seen = list(identities.items())
        for pid, ident in exact_seen:
            try:
                current = proc_identity(pid)
            except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
                continue
            if current[0] == ident[0]:
                before_cleanup.append((pid, ident[0]))
        cleanup_failure = kill_sampled_exact_children()
        (EVIDENCE / 'exact-cleanup-readback.txt').write_text(
            'sampled_exact_children_alive_before_cleanup=' + repr(before_cleanup) + '\n' +
            'sampled_exact_children_remaining=' + repr(cleanup_failure) + '\n')
        emit(f'EXACT_SAMPLED_CHILD_CLEANUP alive_before={before_cleanup!r} remaining={cleanup_failure!r}')
        emit(f'SAMPLED_PRIVATE_STORAGE_MAX_KIB={max(storage_samples, default=0)}; interval=1s du -sk; sampled maximum, not continuous peak')
        if cleanup_failure or (proof_completed and before_cleanup):
            raise RuntimeError('sampled exact child identities remain alive after cleanup')
