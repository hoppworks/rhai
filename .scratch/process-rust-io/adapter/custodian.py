#!/usr/bin/env python3
"""Single-owner POSIX proof custodian. Source gate pending native macOS review."""
import argparse
import array
import ctypes
import errno
import hashlib
import json
import os
import select
import signal
import socket
import stat
import sys
import time
from process_identity import process_start_identity, _linux_process_snapshot
from pathlib import Path

POLL = 0.01
CLEANUP_DEADLINE = 5.0
MAX_FRAME = 65536
_WAITID = None


class _DarwinSigVal(ctypes.Union):
    _fields_ = [('sival_int', ctypes.c_int), ('sival_ptr', ctypes.c_void_p)]


class _DarwinSigInfo(ctypes.Structure):
    # Field order and widths match this host's sys/signal.h siginfo_t.
    _fields_ = [('si_signo', ctypes.c_int), ('si_errno', ctypes.c_int),
                ('si_code', ctypes.c_int), ('si_pid', ctypes.c_int32),
                ('si_uid', ctypes.c_uint32), ('si_status', ctypes.c_int),
                ('si_addr', ctypes.c_void_p), ('si_value', _DarwinSigVal),
                ('si_band', ctypes.c_long), ('__pad', ctypes.c_ulong * 7)]


class _WaitInfo:
    def __init__(self, pid, code, status):
        self.si_pid = pid
        self.si_code = code
        self.si_status = status


def require_waitid_support():
    """Resolve WNOWAIT and required POSIX primitives before spawning owned children."""
    global _WAITID
    for name in ('posix_spawn', 'waitpid', 'killpg', 'set_blocking'):
        if not callable(getattr(os, name, None)):
            raise RuntimeError('required POSIX primitive is unavailable: os.' + name)
    if not callable(getattr(os, 'kill', None)):
        raise RuntimeError('required POSIX primitive is unavailable: os.kill')
    for name in ('POSIX_SPAWN_DUP2', 'POSIX_SPAWN_CLOSE', 'WNOHANG'):
        if not hasattr(os, name):
            raise RuntimeError('required POSIX constant is unavailable: os.' + name)
    if not hasattr(signal, 'SIGKILL') or not hasattr(signal, 'SIGTERM'):
        raise RuntimeError('required POSIX termination signals are unavailable')
    for name in ('socketpair', 'CMSG_SPACE'):
        if not hasattr(socket, name):
            raise RuntimeError('required socket primitive is unavailable: socket.' + name)
    for name in ('AF_UNIX', 'SOCK_DGRAM', 'SOL_SOCKET', 'SCM_RIGHTS'):
        if not hasattr(socket, name):
            raise RuntimeError('required socket constant is unavailable: socket.' + name)
    if hasattr(os, 'waitid'):
        if not callable(os.waitid):
            raise RuntimeError('os.waitid is present but not callable')
        for name in ('P_PID', 'WEXITED', 'WNOHANG', 'WNOWAIT', 'CLD_EXITED'):
            if not hasattr(os, name):
                raise RuntimeError('Python waitid support lacks os.' + name)
        _WAITID = os.waitid
        return
    if sys.platform != 'darwin' or ctypes.sizeof(_DarwinSigInfo) != 104:
        raise RuntimeError('no reviewed waitid/WNOWAIT ABI for this Python/platform')
    expected_constants = {'P_PID': 1, 'WEXITED': 0x00000004,
                          'WNOHANG': 0x00000001, 'WNOWAIT': 0x00000020,
                          'CLD_EXITED': 1}
    if any(getattr(os, name, None) != value for name, value in expected_constants.items()):
        raise RuntimeError('Python wait flags do not match the reviewed Darwin waitid ABI')
    libc = ctypes.CDLL(None, use_errno=True)
    # Darwin SDK sys/wait.h and sys/signal.h: P_PID=1, WEXITED=4,
    # WNOHANG=1, WNOWAIT=0x20; siginfo_t is 104 bytes on arm64/x86_64.
    native = getattr(libc, 'waitid', None)
    if native is None:
        raise RuntimeError('native waitid symbol is unavailable')
    native.argtypes = (ctypes.c_int, ctypes.c_uint32,
                       ctypes.POINTER(_DarwinSigInfo), ctypes.c_int)
    native.restype = ctypes.c_int

    def waitid(pid):
        info = _DarwinSigInfo()
        while True:
            ctypes.set_errno(0)
            result = native(1, pid, ctypes.byref(info), 0x00000004 | 0x00000001 | 0x00000020)
            if result == 0:
                if info.si_pid == 0:
                    return None
                return _WaitInfo(info.si_pid, info.si_code, info.si_status)
            error = ctypes.get_errno()
            if error == errno.EINTR:
                continue
            raise OSError(error, os.strerror(error))

    _WAITID = waitid


def enable_linux_child_subreaper():
    if not sys.platform.startswith('linux') or not hasattr(os, 'waitid'):
        raise RuntimeError('workload topology case requires Linux waitid and subreaper support')
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                      ctypes.c_ulong, ctypes.c_ulong)
    prctl.restype = ctypes.c_int
    ctypes.set_errno(0)
    if prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), 'PR_SET_CHILD_SUBREAPER')


def waitid_nonreap(pid):
    if _WAITID is None:
        raise RuntimeError('waitid support was not checked before use')
    if hasattr(os, 'waitid'):
        return _WAITID(os.P_PID, pid, os.WEXITED | os.WNOWAIT | os.WNOHANG)
    return _WAITID(pid)


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


PROCESS_STARTS = {}


def spawn(argv, env=None, actions=(), setpgroup=0):
    pid = os.posix_spawn(argv[0], argv, env or os.environ, file_actions=list(actions), setpgroup=setpgroup)
    try:
        PROCESS_STARTS[pid] = process_start_identity(pid)
    except BaseException:
        # Do not leave a successfully spawned child unowned if identity capture fails.
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        reap_exact(pid, time.monotonic() + CLEANUP_DEADLINE)
        raise
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
            invalid_ancillary = False
            for level, kind, payload in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    ints = array.array('i')
                    ints.frombytes(payload[:len(payload) - len(payload) % ints.itemsize])
                    fds.extend(ints.tolist())
                    if len(payload) % ints.itemsize:
                        invalid_ancillary = True
                else:
                    invalid_ancillary = True
            if invalid_ancillary or not data or len(data) > MAX_FRAME or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
                raise ValueError('invalid/truncated protocol frame')
            return json.loads(data), fds
        except BaseException:
            for fd in fds:
                try: os.close(fd)
                except OSError: pass
            raise
    raise TimeoutError('custodian protocol deadline exceeded')


def checked_status(pid, status):
    return {'pid': pid, 'start_identity': PROCESS_STARTS.get(pid), 'wait_status': status}


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


def cleanup_workload_topology(owned, leader, records):
    """Signal the pinned workload group, then prove and reap adopted descendants."""
    anchor = owned.get('anchor')
    holder = owned.get('holder')
    if leader is None or anchor is None or holder is None:
        raise RuntimeError('workload topology custody slots are incomplete')
    deadline = time.monotonic() + CLEANUP_DEADLINE
    leader_info = waitid_nonreap(leader)
    if anchor not in PROCESS_STARTS or holder not in PROCESS_STARTS:
        # This path is only reachable before the custodian's durable pre-escape
        # handoff. The fixture cannot escape until the custodian ACKs that file.
        PROCESS_STARTS[anchor] = _linux_process_snapshot(anchor)['start_identity']
        PROCESS_STARTS[holder] = _linux_process_snapshot(holder)['start_identity']
        records.setdefault('workload_topology', {})['incomplete_handoff_cleanup'] = True
    anchor_snapshot = _linux_process_snapshot(anchor)
    holder_snapshot = _linux_process_snapshot(holder)
    if (anchor_snapshot['start_identity'] != PROCESS_STARTS.get(anchor)
            or holder_snapshot['start_identity'] != PROCESS_STARTS.get(holder)
            or anchor_snapshot['pgid'] != leader
            or holder_snapshot['sid'] != anchor_snapshot['sid']):
        raise RuntimeError('workload topology exact identity/group pin changed before cleanup')
    holder_in_managed_group = holder_snapshot['pgid'] == anchor_snapshot['pgid']
    anchor_live = anchor_snapshot['state'] not in ('Z', 'X')
    if leader_info is None or anchor_live:
        # Never wait on the managed child before the leader exits and the
        # subreaper has adopted it. The unreaped leader/anchor keeps this PGID
        # pinned while the single cleanup signal is sent.
        os.killpg(anchor_snapshot['pgid'], signal.SIGKILL)
        records['managed_group_signal'] = 'SIGKILL'
        records['managed_group_signal_reason'] = (
            'workload topology after native worker joins' if 'error' not in records
            else 'workload topology failure cleanup')
    if leader_info is None:
        leader_info = wait_until_exit(leader, deadline)
        if leader_info is None:
            raise TimeoutError('topology leader did not exit after managed-group signal')
    if ('error' not in records and (leader_info.si_code != os.CLD_EXITED
                                    or leader_info.si_status != 0)):
        raise RuntimeError('topology leader did not exit naturally with status zero')
    records['topology_leader_exit'] = {'si_code': leader_info.si_code,
                                       'si_status': leader_info.si_status}
    records['children']['leader'] = checked_status(leader, reap_exact(leader, deadline))
    owned['leader'] = None
    # Reparenting to this explicitly enabled subreaper is observable through
    # both the exact direct-child wait API and the per-PID parent field.
    anchor_snapshot = _linux_process_snapshot(anchor)
    if anchor_snapshot['ppid'] != os.getpid():
        raise RuntimeError('managed child was not adopted by the custodian subreaper')
    if wait_until_exit(anchor, deadline) is None:
        raise TimeoutError('SIGKILLed managed child did not exit')
    records['children']['anchor'] = checked_status(anchor, reap_exact(anchor, deadline))
    owned['anchor'] = None
    holder_snapshot = _linux_process_snapshot(holder)
    if (holder_snapshot['start_identity'] != PROCESS_STARTS.get(holder)
            or holder_snapshot['ppid'] != os.getpid()):
        raise RuntimeError('workload grandchild was not adopted as the same exact child')
    holder_terminal = waitid_nonreap(holder)
    if holder_terminal is None:
        # If the grandchild escaped before failure cleanup, signal only after
        # its durable PID/start identity and subreaper parent are revalidated.
        current = _linux_process_snapshot(holder)
        if current['start_identity'] != PROCESS_STARTS[holder] or current['ppid'] != os.getpid():
            raise RuntimeError('escaped grandchild exact identity changed before cleanup signal')
        os.kill(holder, signal.SIGKILL)
        if wait_until_exit(holder, deadline) is None:
            raise TimeoutError('exact escaped grandchild SIGKILL did not terminate it')
    records['children']['holder'] = checked_status(holder, reap_exact(holder, deadline))
    owned['holder'] = None
    records['workload_topology_cleanup'] = {
        'managed_child_adopted_and_reaped': anchor,
        'escaped_grandchild_adopted_and_exactly_signaled_and_reaped': holder,
        'escaped_grandchild_signal': 'SIGKILL' if not holder_in_managed_group else 'managed group SIGKILL'}
    if 'workload_topology' in records:
        if 'managed_group_signal' in records:
            records['workload_topology']['managed_group_signal'] = records['managed_group_signal']
        records['workload_topology']['cleanup'] = dict(records['workload_topology_cleanup'])


def cleanup_unreported_workload_topology(owned, leader, records):
    """Kill the still-pinned pre-ACK group and reap only kernel-owned group children."""
    if leader is None or PROCESS_STARTS.get(leader) is None:
        raise RuntimeError('unreported topology has no exact leader identity')
    pinned = _linux_process_snapshot(leader)
    if pinned['start_identity'] != PROCESS_STARTS[leader] or pinned['pgid'] != leader:
        raise RuntimeError('unreported topology leader identity/group pin changed')
    # The fixture cannot escape this group before the custodian ACK, which is
    # sent only after both descendant identities have been durably recorded.
    # Keep the exact leader unreaped until the one group signal is delivered.
    os.killpg(leader, signal.SIGKILL)
    records['managed_group_signal'] = 'SIGKILL'
    records['managed_group_signal_reason'] = 'unreported pre-ACK topology failure'
    deadline = time.monotonic() + CLEANUP_DEADLINE
    leader_info = wait_until_exit(leader, deadline)
    if leader_info is None:
        raise TimeoutError('unreported topology leader did not exit after group SIGKILL')
    records['children']['leader'] = checked_status(leader, reap_exact(leader, deadline))
    owned['leader'] = None

    adopted = []
    while time.monotonic() < deadline:
        try:
            info = os.waitid(os.P_PGID, leader,
                             os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError:
            info = None
        if info is not None and info.si_pid:
            pid = info.si_pid
            snapshot = _linux_process_snapshot(pid)
            if snapshot['ppid'] != os.getpid() or snapshot['pgid'] != leader:
                raise RuntimeError('kernel-reported topology child has unexpected owner/group')
            status = reap_exact(pid, deadline)
            PROCESS_STARTS[pid] = snapshot['start_identity']
            role = ('anchor' if pid == owned.get('anchor') else
                    'holder' if pid == owned.get('holder') else None)
            if role is not None:
                records['children'][role] = checked_status(pid, status)
                owned[role] = None
            adopted.append({'pid': pid, 'start_identity': snapshot['start_identity'],
                            'wait_status': status})
            continue
        try:
            os.killpg(leader, 0)
        except ProcessLookupError:
            break
        time.sleep(POLL)
    else:
        raise TimeoutError('unreported topology process group did not become empty')
    records['unreported_topology_children_reaped'] = adopted
    records['workload_topology_cleanup'] = {
        'pre_ack_group_killed_while_leader_pinned': leader,
        'kernel_wait_owned_children_reaped': len(adopted)}


def cleanup_owned(children, leader, records, exclude=(), group_signaled=False):
    deadline = time.monotonic() + CLEANUP_DEADLINE
    errors = []
    confirmed_group_signal = group_signaled
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
                confirmed_group_signal = True
                records['managed_group_signal'] = 'SIGKILL'
                records['managed_group_signal_reason'] = 'owned cleanup'
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
            if waitid_nonreap(pid) is None and not (role == 'anchor' and confirmed_group_signal):
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
            records[role] = {'pid': children[role], 'start_identity': PROCESS_STARTS.get(children[role]),
                             'wait_status': None, 'pending_owner': True}
    if errors:
        records['cleanup_errors'] = errors
    return records


def main():
    require_waitid_support()
    ap = argparse.ArgumentParser()
    ap.add_argument('--runtime', required=True)
    ap.add_argument('--native-runner', required=True)
    ap.add_argument('--binary', required=True)
    ap.add_argument('--control', choices=('normal', 'cancel', 'missing-wake', 'term', 'kill', 'topology-cancel',
        'stdout-4096-4096', 'stdout-4096-4097', 'stdout-0-0', 'stdout-0-1',
        'stderr-4096-4096', 'stderr-4096-4097', 'stderr-0-0', 'stderr-0-1'), default='normal')
    args = ap.parse_args()
    topology_case = args.control == 'topology-cancel'
    if topology_case:
        enable_linux_child_subreaper()
    runtime = Path(args.runtime)
    st = runtime.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise RuntimeError('runtime must be an exact non-symlink directory')
    tmpdir = runtime / 'tmp'
    tmpdir.mkdir(exist_ok=True)
    tmp_st = tmpdir.lstat()
    if stat.S_ISLNK(tmp_st.st_mode) or not stat.S_ISDIR(tmp_st.st_mode):
        raise RuntimeError('runtime tmp must be an exact non-symlink directory')
    cap_case = args.control.startswith(('stdout-', 'stderr-'))
    parent_sock, runner_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
    socket_capacity = None
    if cap_case:
        socket_capacity = {'requested_bytes': MAX_FRAME, 'endpoints': {}}
        for name, endpoint in (('custodian', parent_sock), ('runner', runner_sock)):
            endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, MAX_FRAME)
            endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, MAX_FRAME)
            send_bytes = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
            receive_bytes = endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
            socket_capacity['endpoints'][name] = {
                'send_bytes': send_bytes, 'receive_bytes': receive_bytes}
            if send_bytes < MAX_FRAME or receive_bytes < MAX_FRAME:
                parent_sock.close()
                runner_sock.close()
                raise RuntimeError('cap protocol socket buffers are below MAX_FRAME')
    parent_sock.setblocking(False)
    fd = 198
    actions = [(os.POSIX_SPAWN_DUP2, runner_sock.fileno(), fd),
               (os.POSIX_SPAWN_CLOSE, parent_sock.fileno()),
               (os.POSIX_SPAWN_CLOSE, runner_sock.fileno())]
    env = dict(os.environ, PROCESS_PROTOTYPE_CUSTODIAN_FD=str(fd),
               PROCESS_PROTOTYPE_MAX_TIMEOUT='20', AGENT_RUNTIME_DIR=str(runtime),
               PROCESS_PROTOTYPE_CONTROL=args.control,
               PROCESS_PROTOTYPE_WORKLOAD_BINARY=args.binary,
               PROCESS_PROTOTYPE_NATIVE_RUNNER_BINARY=args.native_runner)
    runner_timeout = 20
    fixture_mode = 'stream' if args.control == 'normal' else ('topology' if topology_case else 'stall')
    runner_argv = [args.native_runner, '--acceptance', '--binary', args.binary, '--case', args.control]
    owned = {'runner': None, 'leader': None, 'anchor': None, 'holder': None, 'sentinel': None}
    topology_acknowledged = False
    records = {'custodian_pid': os.getpid(), 'runtime': str(runtime),
               'runtime_identity': [st.st_dev, st.st_ino],
               'tmp_identity': [tmp_st.st_dev, tmp_st.st_ino], 'children': {},
               'custodian': {'pid': os.getpid(), 'start_identity': process_start_identity(os.getpid())},
               'controller': {'pid': int(os.environ['PROCESS_NATIVE_CONTROLLER_PID']),
                              'start_identity': json.loads(os.environ['PROCESS_NATIVE_CONTROLLER_START'])}}
    if socket_capacity is not None:
        records['cap_protocol_socket_buffers'] = socket_capacity
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
        if cap_case:
            channel, cap_text, count_text = args.control.split('-')
            cap, count = int(cap_text), int(count_text)
            fixture_argv = [args.native_runner, '--fixture', 'cap', channel, str(count)]
        else:
            fixture_argv = [args.binary, '--fixture', fixture_mode]
        req, req_fds = recv_frame(parent_sock, min(session_deadline, time.monotonic() + 5))
        if req_fds or req.get('op') != 'run' or req.get('argv') != fixture_argv:
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
        readiness_r = readiness_w = None
        topology_ack_r = topology_ack_w = None
        if cap_case or topology_case:
            readiness_r, readiness_w = os.pipe()
            owned_fds.extend((readiness_r, readiness_w))
            actions.append((os.POSIX_SPAWN_DUP2, readiness_w, 3))
        if topology_case:
            topology_ack_r, topology_ack_w = os.pipe()
            owned_fds.extend((topology_ack_r, topology_ack_w))
            actions.append((os.POSIX_SPAWN_DUP2, topology_ack_r, 4))
        fixture_env = dict(os.environ)
        if cap_case:
            fixture_env.update(PROCESS_PROTOTYPE_CUSTODIAN_FD='native-fixture',
                               PROCESS_PROTOTYPE_FIXTURE_AUTHORIZATION='raw-cap-v1')
        if topology_case:
            fixture_env.update(PROCESS_PROTOTYPE_CUSTODIAN_FD='native-fixture',
                               PROCESS_PROTOTYPE_FIXTURE_AUTHORIZATION='workload-topology-v1')
        workload = spawn(req['argv'], fixture_env, actions, setpgroup=0)
        owned['leader'] = workload
        topology_ready = None
        if topology_case:
            os.close(readiness_w); owned_fds.remove(readiness_w)
            os.close(topology_ack_r); owned_fds.remove(topology_ack_r)
            os.set_blocking(readiness_r, False)
            ready_deadline = min(session_deadline, time.monotonic() + 5)
            data = bytearray()
            while b'\n' not in data and time.monotonic() < ready_deadline:
                ready, _, _ = select.select([readiness_r], [], [], min(POLL, ready_deadline-time.monotonic()))
                if ready:
                    block = os.read(readiness_r, 257-len(data))
                    if not block or len(data)+len(block) > 256:
                        raise ValueError('workload topology ownership record missing or over limit')
                    data.extend(block)
            first = bytes(data).decode('ascii', errors='strict').strip().split()
            if len(first) != 4 or first[0] != 'TOPOLOGY_TREE':
                raise ValueError('workload topology ownership record schema mismatch')
            def ready_fields(tokens):
                values = {}
                for token in tokens[1:]:
                    key, sep, value = token.partition('=')
                    if not sep or key in values or not value.isdigit():
                        raise ValueError('workload topology readiness field is malformed')
                    values[key] = int(value)
                return values
            handoff = ready_fields(first)
            if (set(handoff) != {'leader_pid', 'managed_pid', 'grandchild_pid'}
                    or handoff['leader_pid'] != workload):
                raise ValueError('workload topology lineage PID handoff mismatch')
            managed_pid = handoff['managed_pid']
            grandchild_pid = handoff['grandchild_pid']
            # These PIDs came directly from the workload's bounded readiness
            # record. Keep them in owned slots before any further fallible read.
            owned['anchor'] = managed_pid
            owned['holder'] = grandchild_pid
            leader_snapshot = _linux_process_snapshot(workload)
            managed_snapshot = _linux_process_snapshot(managed_pid)
            grandchild_snapshot = _linux_process_snapshot(grandchild_pid)
            if (managed_snapshot['ppid'] != workload
                    or managed_snapshot['pgid'] != workload
                    or managed_snapshot['sid'] != leader_snapshot['sid']
                    or grandchild_snapshot['ppid'] != managed_pid
                    or grandchild_snapshot['pgid'] != workload
                    or grandchild_snapshot['sid'] != leader_snapshot['sid']):
                raise ValueError('pre-escape topology identity/group readback mismatch')
            PROCESS_STARTS[managed_pid] = managed_snapshot['start_identity']
            PROCESS_STARTS[grandchild_pid] = grandchild_snapshot['start_identity']
            topology_ready = {'leader': leader_snapshot, 'managed_child': managed_snapshot,
                              'escaped_grandchild_pre_escape': grandchild_snapshot,
                              'custodian_subreaper': os.getpid(),
                              'pre_escape_group_shared': True}
            records['workload_topology'] = topology_ready
            handoff_path = runtime / 'topology-handoff.json'
            handoff_tmp = runtime / '.topology-handoff.tmp'
            handoff_tmp.write_text(json.dumps(topology_ready, sort_keys=True) + '\n')
            os.replace(handoff_tmp, handoff_path)
            if json.loads(handoff_path.read_text()) != topology_ready:
                raise RuntimeError('pre-escape topology ownership readback mismatch')
            if os.write(topology_ack_w, b'1') != 1:
                raise OSError('topology ownership acknowledgement was short')
            topology_acknowledged = True
            os.close(topology_ack_w); owned_fds.remove(topology_ack_w)
            escaped = bytearray()
            ready_deadline = min(session_deadline, time.monotonic() + 5)
            while b'\n' not in escaped and time.monotonic() < ready_deadline:
                ready, _, _ = select.select([readiness_r], [], [], min(POLL, ready_deadline-time.monotonic()))
                if ready:
                    block = os.read(readiness_r, 257-len(escaped))
                    if not block or len(escaped)+len(block) > 256:
                        raise ValueError('escaped topology confirmation missing or over limit')
                    escaped.extend(block)
            second = bytes(escaped).decode('ascii', errors='strict').strip().split()
            if len(second) != 4 or second[0] != 'TOPOLOGY_ESCAPED':
                raise ValueError('escaped topology confirmation schema mismatch')
            escaped_values = ready_fields(second)
            after_escape = _linux_process_snapshot(grandchild_pid)
            if (escaped_values != {'pid': grandchild_pid, 'pgid': after_escape['pgid'], 'sid': after_escape['sid']}
                    or after_escape['ppid'] != managed_pid
                    or after_escape['start_identity'] != grandchild_snapshot['start_identity']
                    or after_escape['pgid'] == workload
                    or after_escape['sid'] != leader_snapshot['sid']):
                raise ValueError('escaped grandchild identity/lineage confirmation mismatch')
            topology_ready['escaped_grandchild'] = after_escape
            handoff_tmp.write_text(json.dumps(topology_ready, sort_keys=True) + '\n')
            os.replace(handoff_tmp, handoff_path)
            if json.loads(handoff_path.read_text()) != topology_ready:
                raise RuntimeError('escaped topology confirmation readback mismatch')
            os.close(readiness_r); owned_fds.remove(readiness_r)
        if not topology_case:
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
        # Cancellation controls hold both output pipes. Overflow cap controls
        # hold only the capped pipe; boundary caps need real EOF on both.
        cap_overflow = cap_case and count > cap
        if args.control != 'normal' and not topology_case and (not cap_case or cap_overflow):
            if cap_case and channel == 'stdout':
                holder_actions = [(os.POSIX_SPAWN_DUP2, out_w, 1)]
            elif cap_case:
                holder_actions = [(os.POSIX_SPAWN_DUP2, err_w, 2)]
            else:
                holder_actions = [(os.POSIX_SPAWN_DUP2, out_w, 1), (os.POSIX_SPAWN_DUP2, err_w, 2)]
            holder = spawn(['/bin/sleep', '120'], dict(os.environ), holder_actions, setpgroup=0)
            owned['holder'] = holder
        for x in (in_r, out_w, err_w):
            os.close(x)
            owned_fds.remove(x)
        send_frame(parent_sock, {'op': 'pipes', 'workload_pid': workload, 'pgid': workload,
                                 'anchor_pid': owned['anchor'], 'anchor_pgid': workload},
                   (in_w, out_r, err_r), deadline=time.monotonic()+5)
        for x in (in_w, out_r, err_r):
            os.close(x)
            owned_fds.remove(x)
        if cap_case:
            os.close(readiness_w); owned_fds.remove(readiness_w)
            os.set_blocking(readiness_r, False)
            line = bytearray()
            ready_deadline = min(session_deadline, time.monotonic() + 5)
            while b'\n' not in line and time.monotonic() < ready_deadline:
                ready, _, _ = select.select([readiness_r], [], [], min(POLL, ready_deadline-time.monotonic()))
                if ready:
                    block = os.read(readiness_r, 257-len(line))
                    if not block or len(line)+len(block) > 256:
                        raise ValueError('raw cap readiness record missing or over limit')
                    line.extend(block)
            os.close(readiness_r); owned_fds.remove(readiness_r)
            ready_fields = bytes(line).decode('ascii', errors='strict').strip().split()
            expected_prefix = bytes(i % 256 for i in range(4096))
            expected_hash = hashlib.sha256(expected_prefix).hexdigest()
            if ready_fields != ['CAP_READY', f'pid={workload}', f'pgid={workload}',
                                f'channel={channel}', f'bytes={count}', 'stdin_bytes=4096',
                                'stdin_sha256=' + expected_hash]:
                raise ValueError('raw cap readiness identity/contract mismatch')
            records['raw_cap_readiness'] = {'pid': workload, 'pgid': workload,
                                            'channel': channel, 'requested_bytes': count,
                                            'stdin_bytes': 4096, 'stdin_sha256': expected_hash}
            send_frame(parent_sock, {'op': 'fixture_ready_ack', 'status': 0},
                       deadline=min(session_deadline, time.monotonic()+2))
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
            if event.get('op') == 'assertion_worker_snapshot' and args.control == 'assert':
                snapshot = {key: event.get(key) for key in
                            ('workers_started', 'workers_alive', 'active_workers', 'assertion_held_workers',
                             'assertion_worker_acknowledgements')}
                expected_workers = sorted(['stdin-writer', 'stderr-reader', 'stdout-reader'])
                records['assertion_worker_snapshot'] = snapshot
                if (snapshot['workers_started'] != 3 or snapshot['workers_alive'] != 3
                        or snapshot['active_workers'] != expected_workers
                        or snapshot['assertion_held_workers'] != expected_workers
                        or snapshot['assertion_worker_acknowledgements'] != expected_workers):
                    raise AssertionError('runner assertion injection did not have all three workers active')
                send_frame(parent_sock, {'op': 'release_assertion'}, deadline=min(session_deadline, time.monotonic()+2))
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
            if event.get('op') == 'io_live':
                names = ('stdin-writer', 'stderr-reader', 'stdout-reader')
                active, pending = event.get('active_workers'), event.get('pending_workers')
                alive = event.get('workers_alive')
                if (event.get('workers_started') != 3 or type(alive) is not int or not 0 <= alive <= 3
                        or not isinstance(active, list) or active != sorted(set(active))
                        or any(name not in names for name in active) or len(active) != alive
                        or not isinstance(pending, list) or pending != sorted(set(pending))
                        or any(name not in names for name in pending)):
                    raise ValueError('native runner live snapshot schema or worker states are invalid')
                if args.control in ('cancel', 'missing-wake', 'term', 'kill', 'topology-cancel') and (
                        active != sorted(names) or pending != sorted(names)):
                    raise ValueError('native cancellation/interruption snapshot lacks fresh EAGAIN acknowledgements')
                if topology_case:
                    records['workload_topology']['pre_cancel_workers'] = {
                        'workers_started': event['workers_started'],
                        'active_workers': active, 'pending_workers': pending}
                live = {role: (pid is not None and waitid_nonreap(pid) is None)
                        for role, pid in owned.items()
                        if role != 'runner' and pid is not None
                        and not (topology_case and role == 'holder')}
                if topology_case:
                    leader_info = wait_until_exit(owned['leader'], deadline)
                    if (leader_info is None or leader_info.si_code != os.CLD_EXITED
                            or leader_info.si_status != 0):
                        raise AssertionError('topology workload leader did not naturally exit before live snapshot')
                    anchor_snapshot = _linux_process_snapshot(owned['anchor'])
                    holder_snapshot = _linux_process_snapshot(owned['holder'])
                    if (anchor_snapshot['ppid'] != os.getpid()
                            or waitid_nonreap(owned['anchor']) is not None
                            or holder_snapshot['ppid'] != owned['anchor']
                            or holder_snapshot['start_identity'] != PROCESS_STARTS[owned['holder']]
                            or holder_snapshot['state'] in ('Z', 'X')):
                        raise AssertionError('workload descendants were not live with exact lineage before cancellation')
                    records['workload_topology']['adoption_before_cancel'] = {
                        'managed_child_ppid': anchor_snapshot['ppid'],
                        'grandchild_ppid': holder_snapshot['ppid'],
                        'custodian_pid': os.getpid(),
                        'grandchild_live': True}
                    records['workload_topology']['pre_cancel_live'] = {
                        'managed_child': True, 'escaped_grandchild': True,
                        'sentinel': live.get('sentinel') is True}
                    if not records['workload_topology']['pre_cancel_live']['sentinel']:
                        raise AssertionError('unrelated sentinel was not live at topology cancellation')
                    live.update({'leader': False, 'anchor': True, 'holder': True})
                records['native_live_snapshot'] = live
                if not all(live.get(role) for role in ('anchor', 'sentinel')):
                    raise AssertionError('native runner anchor or sentinel was not live')
                if not live.get('leader'):
                    if args.control != 'normal' and not args.control.startswith(('stdout-', 'stderr-')) and not topology_case:
                        raise AssertionError('native control leader was not live')
                    exited = waitid_nonreap(owned['leader'])
                    if exited is None or exited.si_code != os.CLD_EXITED or exited.si_status != 0:
                        raise AssertionError('normal/raw-cap leader did not naturally exit with status zero')
                    records['leader_natural_exit_before_live_snapshot'] = {
                        'si_code': exited.si_code, 'si_status': exited.si_status}
                if args.control in ('cancel', 'missing-wake', 'term', 'kill') and not live.get('holder'):
                    raise AssertionError('native cancellation/interruption holder was not live')
                if topology_case and not live.get('holder'):
                    raise AssertionError('escaped grandchild was not live through the runner checkpoint')
                if args.control in ('term', 'kill'):
                    records['runner_interruption_precondition'] = live
                    send_frame(parent_sock, {'op': 'io_live_ack', 'status': 0}, deadline=min(session_deadline, time.monotonic()+2))
                    interruption_signal = signal.SIGTERM if args.control == 'term' else signal.SIGKILL
                    os.kill(runner_pid, interruption_signal)
                    records['runner_interruption'] = signal.Signals(interruption_signal).name
                    records['worker_outcome'] = 'process_terminated_by_runner_' + signal.Signals(interruption_signal).name
                    expected_runner_status = -interruption_signal
                    break
                send_frame(parent_sock, {'op': 'io_live_ack', 'status': 0}, deadline=min(session_deadline, time.monotonic()+2))
                continue
            if event.get('op') == 'native_done':
                if event.get('workers_started') != 3 or event.get('workers_joined') != 3:
                    raise ValueError('native runner did not join all three workers')
                records['native_io'] = {key: event.get(key) for key in
                    ('case', 'workers_started', 'workers_joined', 'stdin_bytes', 'stdout_bytes',
                     'stderr_bytes', 'stdin_end', 'stdout_end', 'stderr_end', 'stdout_prefix_hex',
                     'stderr_prefix_hex', 'stdin_sha256', 'stdout_sha256', 'stderr_sha256',
                     'wake_to_join_ms', 'missing_wake_observation_ms', 'first_cause')}
                if event.get('case') != args.control:
                    raise ValueError('native runner case does not match custodian request')
                if args.control == 'normal':
                    if (event.get('stdin_bytes') != len(expected_payload)
                            or event.get('stdout_bytes') != len(expected_payload)
                            or event.get('stderr_bytes') != len(expected_payload)
                            or event.get('stdin_sha256') != expected_stream['input_sha256']
                            or event.get('stdout_sha256') != expected_stream['stdout_sha256']
                            or event.get('stderr_sha256') != expected_stream['stderr_sha256']
                            or event.get('stdin_end') != 'complete'
                            or event.get('stdout_end') != 'eof'
                            or event.get('stderr_end') != 'eof'):
                        raise ValueError('native normal stream byte counts or end states differ')
                    observed = wait_until_exit(workload, deadline)
                    if observed is None:
                        raise TimeoutError('workload exit observation timed out')
                    workload_exit = (observed.si_code, observed.si_status)
                    normal_completion = True
                elif args.control.startswith(('stdout-', 'stderr-')):
                    channel, cap_text, count_text = args.control.split('-')
                    cap, count = int(cap_text), int(count_text)
                    expected_capture = min(cap, count)
                    stream_name = 'stdout' if channel == 'stdout' else 'stderr'
                    target_bytes = stream_name + '_bytes'
                    target_prefix = stream_name + '_prefix_hex'
                    target_end = stream_name + '_end'
                    other_stream = 'stderr' if channel == 'stdout' else 'stdout'
                    other_bytes = other_stream + '_bytes'
                    expected_end = 'output_limit' if count > cap else 'eof'
                    if (event.get(target_bytes) != expected_capture
                            or event.get(target_prefix) != bytes(i % 256 for i in range(expected_capture)).hex()
                            or event.get(target_end) != expected_end or event.get(other_bytes) != 0
                            or event.get(other_stream + '_end') not in (('eof', 'cancelled') if count > cap else ('eof',))
                            or (event.get('stdin_end') not in ('broken_pipe', 'cancelled') if count > cap
                                else event.get('stdin_end') != 'broken_pipe')
                            or type(event.get('stdin_bytes')) is not int
                            or not 4096 <= event.get('stdin_bytes', -1) < len(expected_payload)
                            or event.get('stdin_sha256') != hashlib.sha256(expected_payload[:event.get('stdin_bytes', 0)]).hexdigest()
                            or event.get('first_cause') != (stream_name + '-output-limit' if count > cap else None)):
                        raise ValueError('native raw-byte cap receipt differs from independent fixture truth')
                    if count > cap:
                        if owned.get('holder') is None or waitid_nonreap(owned['holder']) is not None:
                            raise AssertionError('overflow cap target-pipe holder was not live through joins')
                        records['raw_cap_holder_live_after_joins'] = True
                    elif owned.get('holder') is not None:
                        raise AssertionError('boundary cap unexpectedly retained an output pipe holder')
                    else:
                        records['raw_cap_boundary_natural_eof'] = True
                    records['raw_cap_readback'] = records['native_io']
                    observed = wait_until_exit(workload, deadline)
                    if observed is None:
                        raise TimeoutError('raw cap workload exit observation timed out')
                    workload_exit = (observed.si_code, observed.si_status)
                    normal_completion = True
                else:
                    if (event.get('stdout_end') != 'cancelled' or event.get('stderr_end') != 'cancelled'
                            or event.get('stdin_end') != 'cancelled'
                            or event.get('checkpoint_bytes') != {'stdin': 1048576, 'stdout': 1048576, 'stderr': 1048576}
                            or not 0 < event.get('stdin_bytes', 0) < len(expected_payload)
                            or event.get('wake_to_join_ms', 999999) > 1000):
                        raise ValueError('native cancellation did not prove bounded cancellation joins')
                    if args.control == 'missing-wake' and event.get('missing_wake_observation_ms') != 250:
                        raise ValueError('missing-wake negative control did not observe the full fixed interval')
                    try:
                        stdout_prefix = bytes.fromhex(event.get('stdout_prefix_hex', ''))
                        stderr_prefix = bytes.fromhex(event.get('stderr_prefix_hex', ''))
                    except (TypeError, ValueError) as exc:
                        raise ValueError('native cancellation prefixes are malformed') from exc
                    expected_stderr_prefix = bytes(value ^ 0xA5 for value in expected_payload[:len(stderr_prefix)])
                    if (stdout_prefix != expected_payload[:len(stdout_prefix)]
                            or stderr_prefix != expected_stderr_prefix
                            or event.get('stdout_sha256') != hashlib.sha256(expected_payload[:event.get('stdout_bytes', 0)]).hexdigest()
                            or event.get('stderr_sha256') != hashlib.sha256(bytes(value ^ 0xA5 for value in expected_payload[:event.get('stderr_bytes', 0)])).hexdigest()):
                        raise ValueError('native cancellation prefixes differ from the explicit fixture')
                    if topology_case:
                        holder_snapshot = _linux_process_snapshot(owned['holder'])
                        if (holder_snapshot['state'] in ('Z', 'X')
                                or holder_snapshot['start_identity'] != PROCESS_STARTS[owned['holder']]
                                or holder_snapshot['ppid'] != owned['anchor']):
                            raise AssertionError('workload escaped grandchild did not remain live through worker joins')
                        records['workload_topology']['grandchild_live_after_worker_joins'] = True
                    elif waitid_nonreap(owned['holder']) is not None:
                        raise AssertionError('pipe holder did not remain live through worker joins')
                    records['cooperative_cancel'] = True
                    normal_completion = True
                    workload_exit = None
                break
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
            if event.get('op') == 'io_cancelled' and args.control in ('cancel', 'topology-cancel'):
                if event.get('workers_joined') != 3:
                    raise AssertionError('runner did not join all I/O workers')
                stream = {key: event.get(key) for key in expected_stream}
                if stream != expected_stream or event.get('workers_started') != 3:
                    raise ValueError('cancel stream byte counts/checksums do not match fixture truth')
                records['stream_readback'] = stream
                records['worker_joins'] = event['workers_joined']
                if topology_case:
                    records['workload_topology']['worker_joins'] = event['workers_joined']
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
            if topology_case and workload is not None:
                try:
                    if (topology_acknowledged
                            and owned.get('anchor') is not None and owned.get('holder') is not None):
                        cleanup_workload_topology(owned, workload, records)
                    else:
                        cleanup_unreported_workload_topology(owned, workload, records)
                except BaseException as exc:
                    records.setdefault('cleanup_errors', []).append('workload topology cleanup: ' + repr(exc))
            keep_runner = normal_completion or expected_runner_status is not None
            records['children'] = cleanup_owned(
                owned, owned.get('leader'), records['children'],
                exclude=('runner',) if keep_runner else (),
                group_signaled=records.get('managed_group_signal') == 'SIGKILL')
            if records['children'].get('cleanup_errors'):
                records.setdefault('cleanup_errors', []).extend(records['children']['cleanup_errors'])
        except BaseException as exc:
            records.setdefault('cleanup_errors', []).append('cleanup raised: ' + repr(exc))
        if normal_completion:
            try:
                if records.get('cooperative_cancel'):
                    status = 0
                else:
                    code, value = workload_exit
                    status = value if code == os.CLD_EXITED else 128 + value
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
    if topology_case:
        required += ('holder',)
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
