#!/usr/bin/env python3
"""Single-owner POSIX proof custodian. Source gate pending native macOS review."""
import argparse
import array
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
TERM_GRACE = 1.0
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


def cleanup_owned(children, leader, records, exclude=()):
    deadline = time.monotonic() + CLEANUP_DEADLINE
    errors = []
    if leader is not None:
        # WNOWAIT keeps this identity unreaped through its final group signal.
        anchor = children.get('anchor')
        try:
            anchor_live = anchor is not None and waitid_nonreap(anchor) is None
        except BaseException as exc:
            anchor_live = False
            errors.append('anchor liveness observation: ' + repr(exc))
        if anchor_live:
            try:
                os.killpg(leader, signal.SIGTERM)
            except ProcessLookupError:
                errors.append('managed group absent before final signal')
            except OSError as exc:
                errors.append('group SIGTERM: ' + repr(exc))
            try:
                wait_until_exit(leader, min(deadline, time.monotonic() + TERM_GRACE))
                # The independently live anchor, not leader state, retains PGID identity.
                if waitid_nonreap(anchor) is None:
                    os.killpg(leader, signal.SIGKILL)
                else:
                    errors.append('anchor exited before final managed-group signal')
            except OSError as exc:
                errors.append('group escalation: ' + repr(exc))
        else:
            errors.append('group signal withheld because anchor readiness/liveness was lost')
            try: os.kill(leader, signal.SIGTERM)
            except OSError as exc: errors.append('leader exact SIGTERM: ' + repr(exc))
    for role, pid in list(children.items()):
        if pid is None or role == 'leader' or role in exclude:
            continue
        try:
            if waitid_nonreap(pid) is None:
                os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            errors.append(role + ' disappeared before exact signal')
        except OSError as exc:
            errors.append(role + ' SIGTERM: ' + repr(exc))
    for role, pid in list(children.items()):
        if pid is None or role == 'leader' or role in exclude:
            continue
        try:
            if wait_until_exit(pid, min(deadline, time.monotonic() + TERM_GRACE)) is None:
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
    ap.add_argument('--control', choices=('normal', 'cancel', 'term', 'kill'), default='normal')
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
    runner_argv = [sys.executable, args.runner, '--timeout', '20', '--', args.binary, '--fixture', 'stream']
    owned = {'runner': None, 'leader': None, 'anchor': None, 'holder': None, 'sentinel': None}
    records = {'custodian_pid': os.getpid(), 'runtime': str(runtime),
               'runtime_identity': [st.st_dev, st.st_ino],
               'tmp_identity': [tmp_st.st_dev, tmp_st.st_ino], 'children': {}}
    owned_fds = []
    runner_pid = None
    workload = None
    normal_completion = False
    workload_exit = None
    session_deadline = time.monotonic() + 30.0
    req_fds = []
    try:
        runner_pid = spawn(runner_argv, env, actions)
        owned['runner'] = runner_pid
        runner_sock.close()
        req, req_fds = recv_frame(parent_sock, min(session_deadline, time.monotonic() + 5))
        if req_fds or req.get('op') != 'run' or req.get('argv') != [args.binary, '--fixture', 'stream']:
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
        deadline = min(session_deadline, time.monotonic() + min(float(timeout), 20.0))
        while True:
            event, extra = recv_frame(parent_sock, deadline)
            if extra:
                for x in extra: os.close(x)
                raise ValueError('runner sent unrequested descriptors')
            if event.get('op') == 'io_live' and args.control in ('term', 'kill'):
                sig = signal.SIGTERM if args.control == 'term' else signal.SIGKILL
                os.kill(runner_pid, sig)
                records['runner_interruption'] = args.control
                break
            if event.get('op') == 'io_live' and args.control == 'normal':
                continue
            if event.get('op') == 'io_complete':
                if event.get('input_bytes') != 2 * 1024 * 1024 or event.get('stdout_bytes') != 2 * 1024 * 1024 or event.get('stderr_bytes') != 2 * 1024 * 1024:
                    raise ValueError('runner completion counts do not match contract')
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
            records['children'] = cleanup_owned(owned, workload, records['children'], exclude=('runner',) if normal_completion else ())
            if records['children'].get('cleanup_errors'):
                records.setdefault('cleanup_errors', []).extend(records['children']['cleanup_errors'])
        except BaseException as exc:
            records.setdefault('cleanup_errors', []).append('cleanup raised: ' + repr(exc))
        if normal_completion:
            try:
                code, value = workload_exit
                status = 1 if records.get('cooperative_cancel') else (value if code == os.CLD_EXITED else 128 + value)
                send_frame(parent_sock, {'op': 'result', 'status': status}, deadline=min(session_deadline, time.monotonic()+5))
            except BaseException as exc:
                records.setdefault('cleanup_errors', []).append('runner result send: ' + repr(exc))
            try:
                if wait_until_exit(runner_pid, min(session_deadline, time.monotonic() + TERM_GRACE)) is None:
                    os.kill(runner_pid, signal.SIGKILL)
                records['children']['runner'] = checked_status(runner_pid, reap_exact(runner_pid, min(session_deadline+CLEANUP_DEADLINE, time.monotonic()+CLEANUP_DEADLINE)))
            except BaseException as exc:
                records.setdefault('cleanup_errors', []).append('runner cleanup/reap: ' + repr(exc))
        else:
            if runner_pid is not None and owned['runner'] is not None and 'runner' not in records['children']:
                try: records['children']['runner'] = checked_status(runner_pid, reap_exact(runner_pid, time.monotonic() + CLEANUP_DEADLINE))
                except (OSError, TimeoutError, ChildProcessError) as exc: records.setdefault('cleanup_errors', []).append('runner reap: ' + repr(exc))
        for x in owned_fds + req_fds:
            try: os.close(x)
            except OSError: pass
        try: parent_sock.close()
        except OSError: pass
        try: runner_sock.close()
        except OSError: pass
    required = ('runner', 'leader', 'anchor', 'sentinel')
    complete = all(records['children'].get(role, {}).get('wait_status') is not None for role in required)
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
