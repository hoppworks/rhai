#!/usr/bin/env python3
"""Single-owner POSIX proof custodian. Source gate pending native macOS review."""
import argparse
import array
import hashlib
import json
import os
import select
import signal
import socket
import stat
import sys
import time
from pathlib import Path

POLL = 0.01
CLEANUP_DEADLINE = 5.0
MAX_FRAME = 65536


def waitid_nonreap(pid):
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT | os.WNOHANG)


def wait_until_exit(pid, deadline):
    while time.monotonic() < deadline:
        info = waitid_nonreap(pid)
        if info is not None and info.si_pid == pid:
            return info
        try:
            time.sleep(POLL)
        except InterruptedError:
            pass
    return None


def reap_exact(pid, deadline):
    while time.monotonic() < deadline:
        got, status = os.waitpid(pid, os.WNOHANG)
        if got == pid:
            return status
        time.sleep(POLL)
    raise TimeoutError('exact child reaping deadline exceeded for pid ' + str(pid))


def spawn(argv, env=None, actions=(), setpgroup=0):
    pid = os.posix_spawn(argv[0], argv, env or os.environ, file_actions=list(actions), setpgroup=setpgroup)
    # Caller stores this PID in its preallocated slot before any further fallible operation.
    return pid


def send_frame(sock, obj, fds=(), deadline=None):
    data = json.dumps(obj, separators=(',', ':')).encode()
    if not data or len(data) > MAX_FRAME:
        raise ValueError('frame size outside limit')
    ancillary = []
    if fds:
        packed = array.array('i', fds)
        ancillary = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, packed.tobytes())]
    deadline = deadline or (time.monotonic() + 5.0)
    while True:
        try:
            sent = sock.sendmsg([data], ancillary)
            if sent != len(data):
                raise OSError('short SOCK_DGRAM send')
            return
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('custodian datagram send deadline')
            select.select([], [sock], [], min(POLL, remaining))
        except InterruptedError:
            if time.monotonic() >= deadline:
                raise TimeoutError('custodian datagram send deadline')


def recv_frame(sock, deadline):
    while time.monotonic() < deadline:
        try:
            ready, _, _ = select.select([sock], [], [], min(POLL, deadline - time.monotonic()))
        except InterruptedError:
            continue
        if not ready:
            continue
        data, ancillary, flags, _ = sock.recvmsg(MAX_FRAME + 1, socket.CMSG_SPACE(16 * array.array('i').itemsize))
        fds = []
        try:
            for level, kind, payload in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    ints = array.array('i')
                    ints.frombytes(payload[:len(payload) - len(payload) % ints.itemsize])
                    fds.extend(ints.tolist())
                else:
                    raise ValueError('unexpected ancillary data')
            if not data or len(data) > MAX_FRAME or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
                raise ValueError('invalid/truncated protocol frame')
            return json.loads(data), fds
        except BaseException:
            for fd in fds:
                try: os.close(fd)
                except OSError: pass
            raise
    raise TimeoutError('custodian protocol deadline exceeded')


def checked_status(pid, status):
    return {'pid': pid, 'wait_status': status}


def kill_managed_group(children, leader, records, reason):
    anchor = children.get('anchor')
    if leader is None or anchor is None:
        raise RuntimeError('managed-group identity slots are incomplete')
    if waitid_nonreap(leader) is not None:
        raise RuntimeError('managed-group leader is no longer unreaped/live')
    if waitid_nonreap(anchor) is not None:
        raise RuntimeError('managed-group anchor is no longer live')
    os.killpg(leader, signal.SIGKILL)
    records['managed_group_signal'] = 'SIGKILL'
    records['managed_group_signal_reason'] = reason


def cleanup_owned(children, leader, records, exclude=(), group_signaled=False):
    deadline = time.monotonic() + CLEANUP_DEADLINE
    errors = []
    if leader is not None and not group_signaled:
        # Keep both direct children unreaped while the live anchor pins the group ID.
        anchor = children.get('anchor')
        try:
            # This process is the sole reaper; the live anchor pins the PGID.
            anchor_live = anchor is not None and waitid_nonreap(anchor) is None
        except BaseException as exc:
            anchor_live = False
            errors.append('managed-group liveness observation: ' + repr(exc))
        if anchor_live:
            try:
                # One KILL avoids TERM destroying the anchor before escalation.
                os.killpg(leader, signal.SIGKILL)
            except ProcessLookupError:
                errors.append('managed group absent before scope signal')
            except OSError as exc:
                errors.append('group SIGKILL: ' + repr(exc))
        else:
            errors.append('group signal withheld because live anchor identity was lost')
            try:
                if waitid_nonreap(leader) is None:
                    os.kill(leader, signal.SIGKILL)
            except OSError as exc:
                errors.append('exact unreaped leader SIGKILL: ' + repr(exc))
    for role, pid in list(children.items()):
        if pid is None or role == 'leader' or role in exclude:
            continue
        try:
            if waitid_nonreap(pid) is None:
                os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            errors.append(role + ' disappeared before exact signal')
        except OSError as exc:
            errors.append(role + ' SIGKILL: ' + repr(exc))
    for role, pid in list(children.items()):
        if pid is None or role == 'leader' or role in exclude:
            continue
        try:
            if wait_until_exit(pid, min(deadline, time.monotonic() + 1.0)) is None:
                os.kill(pid, signal.SIGKILL)
            records[role] = checked_status(pid, reap_exact(pid, deadline))
        except (OSError, TimeoutError, ChildProcessError) as exc:
            errors.append(role + ' cleanup/reap: ' + repr(exc))
    if leader is not None and 'leader' not in exclude:
        try:
            records['leader'] = checked_status(leader, reap_exact(leader, deadline))
        except (OSError, TimeoutError, ChildProcessError) as exc:
            errors.append('leader cleanup/reap: ' + repr(exc))
    for role in exclude:
        if role in children and children[role] is not None:
            records[role] = {'pid': children[role], 'wait_status': None, 'pending_owner': True}
    if errors:
        records['cleanup_errors'] = errors
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runtime', required=True)
    ap.add_argument('--runner', required=True)
    ap.add_argument('--binary', required=True)
    ap.add_argument('--control', choices=('normal', 'cancel', 'assert', 'timeout', 'kill'), default='normal')
    args = ap.parse_args()
    runtime = Path(args.runtime)
    st = runtime.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise RuntimeError('runtime must be an exact non-symlink directory')
    tmpdir = runtime / 'tmp'
    tmpdir.mkdir(exist_ok=True)
    tmp_st = tmpdir.lstat()
    if stat.S_ISLNK(tmp_st.st_mode) or not stat.S_ISDIR(tmp_st.st_mode):
        raise RuntimeError('runtime tmp must be an exact non-symlink directory')
    parent_sock, runner_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
    parent_sock.setblocking(False)
    fd = 198
    actions = [(os.POSIX_SPAWN_DUP2, runner_sock.fileno(), fd),
               (os.POSIX_SPAWN_CLOSE, parent_sock.fileno()),
               (os.POSIX_SPAWN_CLOSE, runner_sock.fileno())]
    env = dict(os.environ, PROCESS_PROTOTYPE_CUSTODIAN_FD=str(fd),
               PROCESS_PROTOTYPE_MAX_TIMEOUT='20', AGENT_RUNTIME_DIR=str(runtime),
               PROCESS_PROTOTYPE_CONTROL=args.control)
    runner_timeout = 8 if args.control == 'timeout' else 20
    fixture_mode = 'stall' if args.control == 'timeout' else 'stream'
    runner_argv = [sys.executable, args.runner, '--timeout', str(runner_timeout), '--', args.binary, '--fixture', fixture_mode]
    owned = {'runner': None, 'leader': None, 'anchor': None, 'holder': None, 'sentinel': None}
    records = {'custodian_pid': os.getpid(), 'runtime': str(runtime),
               'runtime_identity': [st.st_dev, st.st_ino],
               'tmp_identity': [tmp_st.st_dev, tmp_st.st_ino], 'children': {}}
    expected_payload = bytes(range(256)) * (2 * 1024 * 1024 // 256)
    expected_stderr = bytes(value ^ 0xA5 for value in expected_payload)
    expected_stream = {'input_bytes': len(expected_payload), 'stdout_bytes': len(expected_payload),
                       'stderr_bytes': len(expected_payload),
                       'input_sha256': hashlib.sha256(expected_payload).hexdigest(),
                       'stdout_sha256': hashlib.sha256(expected_payload).hexdigest(),
                       'stderr_sha256': hashlib.sha256(expected_stderr).hexdigest()}
    owned_fds = []
    runner_pid = None
    workload = None
    normal_completion = False
    expected_runner_status = None
    workload_exit = None
    session_deadline = time.monotonic() + 30.0
    req_fds = []
    try:
        runner_pid = spawn(runner_argv, env, actions)
        owned['runner'] = runner_pid
        runner_sock.close()
        req, req_fds = recv_frame(parent_sock, min(session_deadline, time.monotonic() + 5))
        if req_fds or req.get('op') != 'run' or req.get('argv') != [args.binary, '--fixture', fixture_mode]:
            raise ValueError('unexpected runner command; refusing spawn')
        timeout = req.get('timeout_seconds')
        if type(timeout) not in (int, float) or timeout <= 0 or timeout > 20:
            raise ValueError('invalid requested timeout')
        pipes = []
        for _ in range(3):
            pair = os.pipe()
            owned_fds.extend(pair)
            pipes.append(pair)
        (in_r, in_w), (out_r, out_w), (err_r, err_w) = pipes
        # Scope identity is assigned in the spawn attributes before fixture code can execute.
        actions = [(os.POSIX_SPAWN_DUP2, in_r, 0), (os.POSIX_SPAWN_DUP2, out_w, 1), (os.POSIX_SPAWN_DUP2, err_w, 2)]
        workload = spawn(req['argv'], dict(os.environ), actions, setpgroup=0)
        owned['leader'] = workload
        # The anchor must report its identity before any input is released.
        anchor_r, anchor_w = os.pipe()
        owned_fds.extend((anchor_r, anchor_w))
        anchor_actions = [(os.POSIX_SPAWN_DUP2, anchor_w, 1)]
        anchor = spawn([args.binary, '--fixture', 'anchor'], dict(os.environ), anchor_actions, setpgroup=workload)
        owned['anchor'] = anchor
        os.close(anchor_w); owned_fds.remove(anchor_w)
        os.set_blocking(anchor_r, False)
        anchor_line = bytearray()
        ready_deadline = time.monotonic() + 5
        while b'\n' not in anchor_line and time.monotonic() < ready_deadline:
            ready, _, _ = select.select([anchor_r], [], [], min(POLL, ready_deadline-time.monotonic()))
            if ready:
                block = os.read(anchor_r, 256-len(anchor_line))
                if not block or len(anchor_line)+len(block) > 256:
                    raise ValueError('anchor readiness record missing or over limit')
                anchor_line.extend(block)
        os.close(anchor_r); owned_fds.remove(anchor_r)
        text = bytes(anchor_line).decode('ascii', errors='strict').strip().split()
        if text != ['ANCHOR_READY', f'pid={anchor}', f'pgid={workload}']:
            raise ValueError('anchor PID/PGID readiness mismatch')
        sentinel = spawn(['/bin/sleep', '120'], dict(os.environ), (), setpgroup=0)
        owned['sentinel'] = sentinel
        # This control has a distinct process group and holds both output pipes when requested.
        if args.control != 'normal':
            holder_actions = [(os.POSIX_SPAWN_DUP2, out_w, 1), (os.POSIX_SPAWN_DUP2, err_w, 2)]
            holder = spawn(['/bin/sleep', '120'], dict(os.environ), holder_actions, setpgroup=0)
            owned['holder'] = holder
        for x in (in_r, out_w, err_w):
            os.close(x)
            owned_fds.remove(x)
        send_frame(parent_sock, {'op': 'pipes', 'workload_pid': workload, 'pgid': workload,
                                 'anchor_pid': anchor, 'anchor_pgid': workload},
                   (in_w, out_r, err_r), deadline=time.monotonic()+5)
        for x in (in_w, out_r, err_r):
            os.close(x)
            owned_fds.remove(x)
        deadline = session_deadline
        while True:
            event, extra = recv_frame(parent_sock, deadline)
            if extra:
                owned_fds.extend(extra)
                raise ValueError('runner sent unrequested descriptors')
            if event.get('op') == 'io_live' and args.control == 'assert':
                live = {role: (pid is not None and waitid_nonreap(pid) is None)
                        for role, pid in owned.items() if role != 'runner'}
                records['live_assertion_precondition'] = live
                if not all(live.get(role) for role in ('leader', 'anchor', 'holder', 'sentinel')):
                    raise AssertionError('live assertion control resources were not all live')
                send_frame(parent_sock, {'op': 'inject_assertion'}, deadline=min(session_deadline, time.monotonic()+2))
                continue
            if event.get('op') == 'assertion_failure' and args.control == 'assert':
                if (event.get('message') != 'intentional live-resource assertion'
                        or event.get('workers_started') != 3 or event.get('workers_joined') != 3):
                    raise ValueError('runner did not report expected live assertion and worker joins')
                records['live_assertion_failure'] = True
                records['worker_joins'] = event['workers_joined']
                expected_runner_status = 86
                break
            if event.get('op') == 'assertion_cleanup_required' and args.control == 'assert':
                live = {role: (pid is not None and waitid_nonreap(pid) is None)
                        for role, pid in owned.items() if role != 'runner'}
                records['live_assertion_precondition'] = live
                if not all(live.get(role) for role in ('leader', 'anchor', 'holder', 'sentinel')):
                    raise AssertionError('live assertion cleanup lost a required live resource')
                kill_managed_group(owned, workload, records, 'live assertion cleanup')
                send_frame(parent_sock, {'op': 'scope_terminated'}, deadline=min(session_deadline, time.monotonic()+2))
                continue
            if event.get('op') == 'timeout_cleanup_required' and args.control == 'timeout':
                live = {role: (pid is not None and waitid_nonreap(pid) is None)
                        for role, pid in owned.items() if role != 'runner'}
                records['runner_timeout_precondition'] = live
                if not all(live.get(role) for role in ('leader', 'anchor', 'holder', 'sentinel')):
                    raise AssertionError('runner timeout cleanup lost a required live resource')
                kill_managed_group(owned, workload, records, 'runner timeout cleanup')
                send_frame(parent_sock, {'op': 'scope_terminated'}, deadline=min(session_deadline, time.monotonic()+2))
                continue
            if event.get('op') == 'runner_timeout' and args.control == 'timeout':
                if (event.get('status') != 124 or event.get('workers_started') != 3
                        or event.get('workers_joined') != 3):
                    raise ValueError('runner timeout lacked the expected status or worker joins')
                records['runner_timeout_status'] = event['status']
                records['runner_timeout_workers_joined'] = event['workers_joined']
                expected_runner_status = 124
                break
            if event.get('op') == 'io_live' and args.control == 'kill':
                live = {role: (pid is not None and waitid_nonreap(pid) is None)
                        for role, pid in owned.items() if role != 'runner'}
                records['runner_kill_precondition'] = live
                if not all(live.get(role) for role in ('leader', 'anchor', 'holder', 'sentinel')):
                    raise AssertionError('runner SIGKILL control resources were not all live')
                os.kill(runner_pid, signal.SIGKILL)
                records['runner_interruption'] = 'SIGKILL'
                records['worker_outcome'] = 'process_terminated_by_runner_SIGKILL'
                expected_runner_status = -signal.SIGKILL
                break
            if event.get('op') == 'io_live' and args.control in ('normal', 'cancel', 'timeout'):
                if args.control == 'timeout':
                    live = {role: (pid is not None and waitid_nonreap(pid) is None)
                            for role, pid in owned.items() if role != 'runner'}
                    records['runner_timeout_precondition'] = live
                    if not all(live.get(role) for role in ('leader', 'anchor', 'holder', 'sentinel')):
                        raise AssertionError('runner timeout control resources were not all live')
                continue
            if event.get('op') == 'io_complete':
                stream = {key: event.get(key) for key in expected_stream}
                if stream != expected_stream or event.get('workers_started') != 3 or event.get('workers_joined') != 3:
                    raise ValueError('runner byte counts/checksums do not match fixture truth')
                records['stream_readback'] = stream
                records['worker_joins'] = event['workers_joined']
                observed = wait_until_exit(workload, deadline)
                if observed is None:
                    raise TimeoutError('workload exit observation timed out')
                workload_exit = (observed.si_code, observed.si_status)
                normal_completion = True
                break
            if event.get('op') == 'io_input_closed' and args.control == 'cancel':
                observed = wait_until_exit(workload, deadline)
                if observed is None:
                    raise TimeoutError('workload failed to exit while held pipe remained open')
                workload_exit = (observed.si_code, observed.si_status)
                records['held_pipe_open_at_exit'] = bool(waitid_nonreap(owned['holder']) is None)
                if not records['held_pipe_open_at_exit']:
                    raise AssertionError('independent holder exited before workload')
                send_frame(parent_sock, {'op': 'workload_exited'}, deadline=deadline)
                continue
            if event.get('op') == 'io_cancelled' and args.control == 'cancel':
                if event.get('workers_joined') != 3:
                    raise AssertionError('runner did not join all I/O workers')
                stream = {key: event.get(key) for key in expected_stream}
                if stream != expected_stream or event.get('workers_started') != 3:
                    raise ValueError('cancel stream byte counts/checksums do not match fixture truth')
                records['stream_readback'] = stream
                records['worker_joins'] = event['workers_joined']
                normal_completion = True
                records['cooperative_cancel'] = True
                break
            raise ValueError('unexpected runner progress event')
    except BaseException as exc:
        records['error'] = repr(exc)
    finally:
        try:
            if owned.get('sentinel') is not None:
                records['sentinel_alive_before_cleanup'] = waitid_nonreap(owned['sentinel']) is None
                if not records['sentinel_alive_before_cleanup']:
                    records.setdefault('error', 'unrelated sentinel exited before cleanup')
        except BaseException as exc:
            records.setdefault('error', 'sentinel liveness readback: ' + repr(exc))
        try:
            keep_runner = normal_completion or expected_runner_status is not None
            records['children'] = cleanup_owned(
                owned, workload, records['children'],
                exclude=('runner',) if keep_runner else (),
                group_signaled=records.get('managed_group_signal') == 'SIGKILL')
            if records['children'].get('cleanup_errors'):
                records.setdefault('cleanup_errors', []).extend(records['children']['cleanup_errors'])
        except BaseException as exc:
            records.setdefault('cleanup_errors', []).append('cleanup raised: ' + repr(exc))
        if normal_completion:
            try:
                code, value = workload_exit
                status = 1 if records.get('cooperative_cancel') else (value if code == os.CLD_EXITED else 128 + value)
                if not records.get('cooperative_cancel') and status != 0:
                    records.setdefault('error', 'normal stream workload returned nonzero status ' + str(status))
                expected_runner_status = status
                send_frame(parent_sock, {'op': 'result', 'status': status}, deadline=min(session_deadline, time.monotonic()+5))
            except BaseException as exc:
                records.setdefault('cleanup_errors', []).append('runner result send: ' + repr(exc))
            try:
                if wait_until_exit(runner_pid, min(session_deadline, time.monotonic() + 1.0)) is None:
                    os.kill(runner_pid, signal.SIGKILL)
                records['children']['runner'] = checked_status(runner_pid, reap_exact(runner_pid, min(session_deadline+CLEANUP_DEADLINE, time.monotonic()+CLEANUP_DEADLINE)))
            except BaseException as exc:
                records.setdefault('cleanup_errors', []).append('runner cleanup/reap: ' + repr(exc))
        elif expected_runner_status is not None:
            try:
                if wait_until_exit(runner_pid, min(session_deadline, time.monotonic()+1.0)) is None:
                    os.kill(runner_pid, signal.SIGKILL)
                records['children']['runner'] = checked_status(runner_pid, reap_exact(runner_pid, time.monotonic()+CLEANUP_DEADLINE))
            except BaseException as exc:
                records.setdefault('cleanup_errors', []).append('expected-control runner wait/reap: ' + repr(exc))
        else:
            if runner_pid is not None and owned['runner'] is not None and 'runner' not in records['children']:
                try: records['children']['runner'] = checked_status(runner_pid, reap_exact(runner_pid, time.monotonic() + CLEANUP_DEADLINE))
                except (OSError, TimeoutError, ChildProcessError) as exc: records.setdefault('cleanup_errors', []).append('runner reap: ' + repr(exc))
        if expected_runner_status is not None:
            runner_record = records['children'].get('runner', {})
            runner_wait = runner_record.get('wait_status')
            if runner_wait is None:
                records.setdefault('error', 'expected-control runner status was not reaped')
            elif expected_runner_status < 0:
                if not os.WIFSIGNALED(runner_wait) or os.WTERMSIG(runner_wait) != -expected_runner_status:
                    records.setdefault('error', 'runner did not terminate by expected signal')
            elif not os.WIFEXITED(runner_wait) or os.WEXITSTATUS(runner_wait) != expected_runner_status:
                records.setdefault('error', 'runner did not return expected control status')
        fd_errors = []
        for x in owned_fds + req_fds:
            try:
                os.close(x)
            except OSError as exc:
                fd_errors.append('fd ' + str(x) + ': ' + repr(exc))
        records['custodian_fds_closed'] = not fd_errors
        if fd_errors:
            records.setdefault('cleanup_errors', []).extend(fd_errors)
        for name, sock in (('custodian protocol socket', parent_sock), ('runner protocol socket', runner_sock)):
            try:
                sock.close()
            except OSError as exc:
                records['custodian_fds_closed'] = False
                records.setdefault('cleanup_errors', []).append(name + ' close: ' + repr(exc))
    required = ('runner', 'leader', 'anchor', 'sentinel')
    complete = all(records['children'].get(role, {}).get('wait_status') is not None for role in required)
    complete = complete and records.get('custodian_fds_closed') is True
    complete = complete and not records.get('cleanup_errors') and not records['children'].get('cleanup_errors') and 'error' not in records
    if owned.get('holder') is not None:
        complete = complete and records['children'].get('holder', {}).get('wait_status') is not None
    if complete:
        quiet = runtime / 'custody-quiescent.json'
        quiet_tmp = runtime / '.custody-quiescent.tmp'
        quiet_tmp.write_text(json.dumps(records, sort_keys=True) + '\n')
        os.replace(quiet_tmp, quiet)
        if json.loads(quiet.read_text()) != records:
            raise RuntimeError('quiescence record readback failed')
    receipt = runtime / 'receipt.json'
    tmp_receipt = runtime / '.receipt.tmp'
    tmp_receipt.write_text(json.dumps(records, sort_keys=True) + '\n')
    os.replace(tmp_receipt, receipt)
    reread = json.loads(receipt.read_text())
    if reread != records or (runtime.lstat().st_dev, runtime.lstat().st_ino) != (st.st_dev, st.st_ino):
        raise RuntimeError('custody receipt/runtime readback failed')
    return 0 if 'error' not in records and not records.get('cleanup_errors') and complete else 1


if __name__ == '__main__':
    sys.exit(main())
