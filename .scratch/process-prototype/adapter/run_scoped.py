#!/usr/bin/env python3
"""Project-local scoped runner client; an external custodian owns all children."""
import argparse
import array
import errno
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


def _drive_io(fds, deadline, sock, cancel_mode=False, expected_pid=None, expected_pgid=None):
    in_fd, out_fd, err_fd = fds
    for fd in fds:
        os.set_blocking(fd, False)
    payload = bytes(range(256)) * (MAX_PAYLOAD // 256)
    first_end = len(payload) // 2
    stop = threading.Event()
    checkpoints = [threading.Event(), threading.Event()]
    errors = queue.Queue()
    outputs = [bytearray(), bytearray()]

    def reader(fd, index):
        try:
            while not stop.is_set():
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
        except BaseException as exc:
            errors.put(exc)
            stop.set()

    def writer():
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
            while not stop.is_set() and not all(ev.is_set() for ev in checkpoints):
                if time.monotonic() >= deadline:
                    raise TimeoutError('output checkpoint deadline')
                time.sleep(0.005)
            if stop.is_set():
                return
            # Parent sends readiness only after both output streams have yielded the
            # workload's first-code PID/PGID line; no cancellation control can race it.
            while not stop.is_set() and not all(ev.is_set() for ev in checkpoints):
                if time.monotonic() >= deadline:
                    raise TimeoutError('readiness checkpoint deadline')
                time.sleep(0.005)
            ready, sep, _ = bytes(outputs[1]).partition(b'\n')
            fields = ready.decode('ascii', errors='strict').split()
            if (not sep or fields != ['WORKLOAD_READY', f'pid={expected_pid}', f'pgid={expected_pgid}']
                    or expected_pid != expected_pgid):
                raise AssertionError('workload first-code PID/PGID readiness mismatch')
            _send(sock, json.dumps({'op': 'io_live'}).encode(), deadline)
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
            stop.set()
        finally:
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

    threads = [threading.Thread(target=reader, args=(out_fd, 0), daemon=True),
               threading.Thread(target=reader, args=(err_fd, 1), daemon=True),
               threading.Thread(target=writer, daemon=True)]
    started = []
    try:
        for thread in threads:
            thread.start()
            started.append(thread)
        while threads[2].is_alive():
            if time.monotonic() >= deadline:
                raise TimeoutError('I/O worker deadline')
            if not errors.empty():
                raise errors.get()
            threads[2].join(0.01)
        if cancel_mode:
            event, extra = _recv(sock, deadline)
            if extra or event.get('op') != 'workload_exited':
                raise ValueError('custodian did not confirm non-reaped workload exit')
            stop.set()
        while any(thread.is_alive() for thread in started):
            if time.monotonic() >= deadline:
                raise TimeoutError('I/O worker deadline')
            if not errors.empty():
                raise errors.get()
            for thread in started:
                thread.join(0.01)
        if not errors.empty():
            raise errors.get()
        if not all(ev.is_set() for ev in checkpoints):
            raise AssertionError('overlap checkpoints missing')
    finally:
        stop.set()
        remaining = max(0, min(0.5, deadline-time.monotonic()))
        join_deadline = time.monotonic() + remaining
        for thread in started:
            thread.join(max(0, join_deadline-time.monotonic()))
        if any(thread.is_alive() for thread in started):
            raise TimeoutError('I/O worker did not join within cleanup bound')
    ready, sep, stderr_payload = bytes(outputs[1]).partition(b'\n')
    expected_stderr = bytes(value ^ 0xA5 for value in payload)
    if outputs[0] != payload or stderr_payload != expected_stderr:
        raise AssertionError('overlap/round-trip output contract failed')
    if cancel_mode:
        _send(sock, json.dumps({'op': 'io_cancelled', 'workers_joined': len(started)}).encode(), deadline)
    return {'input_bytes': len(payload), 'stdout_bytes': len(outputs[0]), 'stderr_bytes': len(stderr_payload)}


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
        cancel_mode = os.environ.get('PROCESS_PROTOTYPE_CONTROL') == 'cancel'
        stats = _drive_io(opened, deadline, sock, cancel_mode,
                          response['workload_pid'], response['pgid'])
        if not cancel_mode:
            _send(sock, json.dumps({'op': 'io_complete', **stats}, separators=(',', ':')).encode(), deadline)
        result, extra = _recv(sock, deadline)
        if extra or result.get('op') != 'result' or type(result.get('status')) is not int or not -255 <= result['status'] <= 255:
            raise ValueError('invalid custodian result')
        return result['status']
    except TimeoutError:
        print('run_scoped: command timed out', file=sys.stderr)
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
