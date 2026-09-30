#!/usr/bin/env python3
"""Project-local scoped runner client; an external custodian owns all children."""
import argparse
import array
import hashlib
import json
import math
import os
import select
import socket
import sys
import time
import threading
import queue
from pathlib import Path

MAX_WIRE = 65536
MAX_PAYLOAD = 2 * 1024 * 1024


class ProofTimeout(TimeoutError):
    def __init__(self, message, workers_started, workers_joined):
        super().__init__(message)
        self.workers_started = workers_started
        self.workers_joined = workers_joined


class WorkerJoinError(RuntimeError):
    pass


def _wait(fd, read, deadline):
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        try:
            ready = select.select([fd] if read else [], [] if read else [fd], [], min(0.05, remaining))
        except InterruptedError:
            continue
        if ready[0] or ready[1]:
            return


def _send(sock, data, deadline):
    if len(data) > MAX_WIRE:
        raise ValueError('custodian frame exceeds limit')
    while True:
        try:
            sent = sock.send(data)
            if sent != len(data):
                raise OSError('SOCK_DGRAM short send')
            return
        except BlockingIOError:
            _wait(sock.fileno(), False, deadline)
        except InterruptedError:
            continue


def _recv(sock, deadline, want_fds=0):
    while True:
        try:
            data, ancillary, flags, _addr = sock.recvmsg(MAX_WIRE + 1, socket.CMSG_SPACE(16 * array.array('i').itemsize))
            break
        except BlockingIOError:
            _wait(sock.fileno(), True, deadline)
        except InterruptedError:
            continue
    fds = []
    try:
        for level, kind, payload in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                ints = array.array('i')
                ints.frombytes(payload[:len(payload) - (len(payload) % ints.itemsize)])
                fds.extend(ints.tolist())
            else:
                raise ValueError('unexpected ancillary data')
        if not data or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) or len(data) > MAX_WIRE:
            raise ValueError('invalid or truncated custodian frame')
        if len(fds) != want_fds:
            raise ValueError('unexpected custodian descriptor count')
        obj = json.loads(data)
        if type(obj) is not dict:
            raise ValueError('custodian frame must be an object')
        return obj, fds
    except BaseException:
        for fd in fds:
            try: os.close(fd)
            except OSError: pass
        raise


def _drive_io(fds, deadline, sock, cancel_mode=False, assertion_mode=False, timeout_mode=False,
              expected_pid=None, expected_pgid=None):
    in_fd, out_fd, err_fd = fds
    for fd in fds:
        os.set_blocking(fd, False)
    payload = bytes(range(256)) * (MAX_PAYLOAD // 256)
    first_end = len(payload) // 2
    stop = threading.Event()
    checkpoints = [threading.Event(), threading.Event()]
    readiness_line = threading.Event()
    live_event = threading.Event()
    scope_cleanup_done = threading.Event()
    assertion_prepare = threading.Event()
    assertion_gate = threading.Event()
    assertion_worker_ready = queue.Queue()
    errors = queue.Queue()
    outputs = [bytearray(), bytearray()]
    worker_names = ('stdout-reader', 'stderr-reader', 'stdin-writer')
    active_workers = set()
    held_workers = set()
    prepared_workers = set()
    active_lock = threading.Lock()

    def set_worker_active(name, active):
        with active_lock:
            if active:
                active_workers.add(name)
            else:
                active_workers.discard(name)

    def worker_snapshot():
        with active_lock:
            active = sorted(active_workers)
            held = sorted(held_workers)
        return {'workers_started': len(started), 'workers_alive': sum(thread.is_alive() for thread in threads),
                'active_workers': active, 'assertion_held_workers': held}

    def hold_for_assertion(name, wait_for_prepare=False):
        if not assertion_mode:
            return
        if not wait_for_prepare and not assertion_prepare.is_set():
            return
        with active_lock:
            if name in prepared_workers:
                return
        if wait_for_prepare:
            while not assertion_prepare.wait(0.01):
                if time.monotonic() >= deadline:
                    raise TimeoutError('assertion preparation deadline')
        with active_lock:
            prepared_workers.add(name)
            held_workers.add(name)
        assertion_worker_ready.put(name)
        while not assertion_gate.wait(0.01):
            if time.monotonic() >= deadline:
                raise TimeoutError('assertion injection deadline')
        with active_lock:
            held_workers.discard(name)

    def reader(fd, index):
        name = worker_names[index]
        set_worker_active(name, True)
        try:
            while not stop.is_set():
                hold_for_assertion(worker_names[index])
                if time.monotonic() >= deadline:
                    raise TimeoutError('reader deadline')
                ready, _, _ = select.select([fd], [], [], min(0.05, max(0, deadline-time.monotonic())))
                if not ready:
                    continue
                try:
                    block = os.read(fd, 16384)
                except BlockingIOError:
                    continue
                if not block:
                    return
                if len(outputs[index]) + len(block) > MAX_PAYLOAD + 256:
                    raise ValueError('output exceeds bounded proof payload')
                outputs[index].extend(block)
                checkpoints[index].set()
                if index == 1:
                    first_line, sep, _ = bytes(outputs[index]).partition(b'\n')
                    if (sep and len(first_line) > 256) or (not sep and len(outputs[index]) > 256):
                        raise ValueError('workload readiness line exceeds 256-byte prefix cap')
                    if sep:
                        readiness_line.set()
        except BaseException as exc:
            errors.put(exc)
            stop.set()
        finally:
            set_worker_active(name, False)

    def writer():
        set_worker_active('stdin-writer', True)
        offset = 0
        try:
            while offset < first_end and not stop.is_set():
                if time.monotonic() >= deadline:
                    raise TimeoutError('writer first-segment deadline')
                _, ready, _ = select.select([], [in_fd], [], min(0.05, max(0, deadline-time.monotonic())))
                if ready:
                    try:
                        offset += os.write(in_fd, payload[offset:min(first_end, offset+16384)])
                    except BlockingIOError:
                        pass
                    except BrokenPipeError:
                        raise OSError('workload closed stdin before checkpoint')
            if not checkpoints[0].wait(max(0, deadline-time.monotonic())):
                raise TimeoutError('stdout checkpoint deadline')
            if not checkpoints[1].wait(max(0, deadline-time.monotonic())):
                raise TimeoutError('stderr checkpoint deadline')
            if not readiness_line.wait(max(0, deadline-time.monotonic())):
                raise TimeoutError('complete workload readiness line deadline')
            if stop.is_set():
                return
            # Parent sends readiness only after both stream checkpoints and the
            # complete bounded stderr identity line; split pipe reads cannot pass.
            ready, sep, _ = bytes(outputs[1]).partition(b'\n')
            fields = ready.decode('ascii', errors='strict').split()
            if (not sep or fields != ['WORKLOAD_READY', f'pid={expected_pid}', f'pgid={expected_pgid}']
                    or expected_pid != expected_pgid):
                raise AssertionError('workload first-code PID/PGID readiness mismatch')
            _send(sock, json.dumps({'op': 'io_live'}).encode(), deadline)
            live_event.set()
            if assertion_mode:
                hold_for_assertion('stdin-writer', wait_for_prepare=True)
                raise AssertionError('intentional live-resource assertion')
            while offset < len(payload) and not stop.is_set():
                if time.monotonic() >= deadline:
                    raise TimeoutError('writer final-segment deadline')
                _, ready, _ = select.select([], [in_fd], [], min(0.05, max(0, deadline-time.monotonic())))
                if ready:
                    try:
                        offset += os.write(in_fd, payload[offset:min(len(payload), offset+16384)])
                    except BlockingIOError:
                        pass
                    except BrokenPipeError:
                        raise OSError('workload closed stdin early')
            if offset != len(payload):
                raise OSError('stdin transfer interrupted')
        except BaseException as exc:
            errors.put(exc)
            held_failure = ((assertion_mode and isinstance(exc, AssertionError)
                             and str(exc) == 'intentional live-resource assertion')
                            or (timeout_mode and isinstance(exc, TimeoutError)))
            if held_failure:
                if not scope_cleanup_done.wait(7.0):
                    stop.set()
            else:
                stop.set()
        finally:
            if not assertion_mode:
                fds[0] = None
                try:
                    os.close(in_fd)
                except OSError:
                    pass
            if cancel_mode:
                try:
                    _send(sock, json.dumps({'op': 'io_input_closed'}).encode(), deadline)
                except BaseException as exc:
                    errors.put(exc)
                    stop.set()
            set_worker_active('stdin-writer', False)

    threads = [threading.Thread(target=reader, args=(out_fd, 0), daemon=True),
               threading.Thread(target=reader, args=(err_fd, 1), daemon=True),
               threading.Thread(target=writer, daemon=True)]
    started = []
    timed_out = None
    live_assertion = None

    def request_scope_cleanup(op):
        _send(sock, json.dumps({'op': op}, separators=(',', ':')).encode(), time.monotonic()+2)
        event, extra = _recv(sock, time.monotonic()+7)
        if extra or event.get('op') != 'scope_terminated':
            raise RuntimeError('custodian did not confirm managed-scope termination')

    try:
        for thread in threads:
            thread.start()
            started.append(thread)
        while threads[2].is_alive():
            if time.monotonic() >= deadline:
                raise TimeoutError('I/O worker deadline')
            if assertion_mode and live_event.is_set() and not assertion_gate.is_set():
                event, extra = _recv(sock, deadline)
                if extra or event.get('op') != 'inject_assertion':
                    raise ValueError('custodian did not authorize the live assertion control')
                assertion_prepare.set()
                acknowledgements = [assertion_worker_ready.get(timeout=max(0, deadline-time.monotonic()))
                                    for _ in worker_names]
                snapshot = worker_snapshot()
                snapshot['assertion_worker_acknowledgements'] = sorted(acknowledgements)
                _send(sock, json.dumps({'op': 'assertion_worker_snapshot', **snapshot},
                                       separators=(',', ':')).encode(), deadline)
                event, extra = _recv(sock, deadline)
                if extra or event.get('op') != 'release_assertion':
                    raise ValueError('custodian rejected the live worker snapshot')
                assertion_gate.set()
                continue
            if not errors.empty():
                error = errors.get()
                if assertion_mode and isinstance(error, AssertionError) and str(error) == 'intentional live-resource assertion':
                    request_scope_cleanup('assertion_cleanup_required')
                    live_assertion = error
                    scope_cleanup_done.set()
                    break
                raise error
            threads[2].join(0.01)
        if cancel_mode and live_assertion is None:
            event, extra = _recv(sock, deadline)
            if extra or event.get('op') != 'workload_exited':
                raise ValueError('custodian did not confirm non-reaped workload exit')
            stop.set()
        while live_assertion is None and any(thread.is_alive() for thread in started):
            if time.monotonic() >= deadline:
                raise TimeoutError('I/O worker deadline')
            if not errors.empty():
                error = errors.get()
                if assertion_mode and isinstance(error, AssertionError) and str(error) == 'intentional live-resource assertion':
                    request_scope_cleanup('assertion_cleanup_required')
                    live_assertion = error
                    scope_cleanup_done.set()
                    break
                raise error
            for thread in started:
                thread.join(0.01)
        if live_assertion is None and not errors.empty():
            raise errors.get()
        if live_assertion is None and not all(ev.is_set() for ev in checkpoints):
            raise AssertionError('overlap checkpoints missing')
    except TimeoutError as exc:
        if timeout_mode:
            request_scope_cleanup('timeout_cleanup_required')
            scope_cleanup_done.set()
        timed_out = exc
    finally:
        stop.set()
        if live_assertion is not None or (timed_out is not None and timeout_mode):
            if fds[0] is not None:
                fds[0] = None
                try:
                    os.close(in_fd)
                except OSError:
                    pass
        join_deadline = time.monotonic() + 5.0
        for thread in started:
            thread.join(max(0, join_deadline-time.monotonic()))
        if any(thread.is_alive() for thread in started):
            joined = sum(not thread.is_alive() for thread in started)
            raise WorkerJoinError('I/O worker join failed; joined ' + str(joined) + '/' + str(len(started)))
    if timed_out is not None:
        raise ProofTimeout(str(timed_out), len(started), sum(not thread.is_alive() for thread in started))
    if live_assertion is not None:
        raise AssertionError('intentional live-resource assertion; workers_started=' + str(len(started)) +
                             '; workers_joined=' + str(sum(not thread.is_alive() for thread in started)))
    ready, sep, stderr_payload = bytes(outputs[1]).partition(b'\n')
    expected_stderr = bytes(value ^ 0xA5 for value in payload)
    if outputs[0] != payload or stderr_payload != expected_stderr:
        raise AssertionError('overlap/round-trip output contract failed')
    stats = {'input_bytes': len(payload), 'stdout_bytes': len(outputs[0]),
             'stderr_bytes': len(stderr_payload),
             'workers_started': len(started),
             'workers_joined': sum(not thread.is_alive() for thread in started),
             'input_sha256': hashlib.sha256(payload).hexdigest(),
             'stdout_sha256': hashlib.sha256(outputs[0]).hexdigest(),
             'stderr_sha256': hashlib.sha256(stderr_payload).hexdigest()}
    if cancel_mode:
        _send(sock, json.dumps({'op': 'io_cancelled', 'workers_joined': len(started),
                                **stats}, separators=(',', ':')).encode(), deadline)
    return stats


def run_command(command, timeout):
    if timeout is None or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('custodian command timeout must be finite and positive')
    cap = float(os.environ.get('PROCESS_PROTOTYPE_MAX_TIMEOUT', '30'))
    if not math.isfinite(cap) or cap <= 0 or timeout > cap:
        raise ValueError('command timeout exceeds custodian cap')
    fd_text = os.environ.get('PROCESS_PROTOTYPE_CUSTODIAN_FD')
    if fd_text is None:
        raise RuntimeError('custodian protocol is required; refusing local subprocess fallback')
    sock = socket.socket(fileno=int(fd_text))
    sock.setblocking(False)
    deadline = time.monotonic() + timeout
    _send(sock, json.dumps({'op': 'run', 'argv': command, 'timeout_seconds': timeout}, separators=(',', ':')).encode(), deadline)
    opened = []
    try:
        response, opened = _recv(sock, deadline, 3)
        if (response.get('op') != 'pipes' or type(response.get('workload_pid')) is not int
                or response.get('pgid') != response.get('workload_pid')
                or type(response.get('anchor_pid')) is not int
                or response.get('anchor_pgid') != response.get('workload_pid')):
            raise ValueError('unexpected custodian pipe response')
        control = os.environ.get('PROCESS_PROTOTYPE_CONTROL')
        cancel_mode = control == 'cancel'
        assertion_mode = control == 'assert'
        timeout_mode = control == 'timeout'
        try:
            stats = _drive_io(opened, deadline, sock, cancel_mode, assertion_mode, timeout_mode,
                              response['workload_pid'], response['pgid'])
        except AssertionError as exc:
            if assertion_mode and str(exc).startswith('intentional live-resource assertion;'):
                fields = dict(item.split('=', 1) for item in str(exc).split('; ')[1:])
                _send(sock, json.dumps({'op': 'assertion_failure',
                                        'message': 'intentional live-resource assertion',
                                        'workers_started': int(fields['workers_started']),
                                        'workers_joined': int(fields['workers_joined'])}).encode(), time.monotonic()+2)
                return 86
            raise
        if not cancel_mode:
            _send(sock, json.dumps({'op': 'io_complete', **stats}, separators=(',', ':')).encode(), deadline)
        result, extra = _recv(sock, deadline)
        if extra or result.get('op') != 'result' or type(result.get('status')) is not int or not -255 <= result['status'] <= 255:
            raise ValueError('invalid custodian result')
        return result['status']
    except ProofTimeout as exc:
        print('run_scoped: command timed out', file=sys.stderr)
        if os.environ.get('PROCESS_PROTOTYPE_CONTROL') == 'timeout':
            try:
                _send(sock, json.dumps({'op': 'runner_timeout', 'status': 124,
                                        'workers_started': exc.workers_started,
                                        'workers_joined': exc.workers_joined}).encode(), time.monotonic()+2)
            except BaseException as exc:
                print('run_scoped: could not report timeout to custodian: ' + str(exc), file=sys.stderr)
        return 124
    except TimeoutError:
        print('run_scoped: command timed out', file=sys.stderr)
        if os.environ.get('PROCESS_PROTOTYPE_CONTROL') == 'timeout':
            try:
                _send(sock, json.dumps({'op': 'runner_timeout', 'status': 124,
                                        'workers_started': 0, 'workers_joined': 0}).encode(), time.monotonic()+2)
            except BaseException as exc:
                print('run_scoped: could not report timeout to custodian: ' + str(exc), file=sys.stderr)
        return 124
    finally:
        for fd in opened:
            if fd is None:
                continue
            try:
                os.close(fd)
            except OSError:
                pass
        sock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('provide a command after --')
    root = Path(os.environ.get('AGENT_RUNTIME_DIR', ''))
    if not root.is_dir() or root.is_symlink() or not (root / 'tmp').is_dir():
        parser.error('custodian must provide an existing private runtime and tmp directory')
    try:
        return run_command(command, args.timeout)
    except Exception as exc:
        print('run_scoped: ' + str(exc), file=sys.stderr)
        return 125


if __name__ == '__main__':
    sys.exit(main())
