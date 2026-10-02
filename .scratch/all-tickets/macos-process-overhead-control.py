#!/usr/bin/env python3
"""Run one finite controller exchange with the scoped overhead custodian."""
import argparse
import importlib.util
import json
import select
import socket
import sys
import time
from pathlib import Path

ADAPTER_PATH = Path(__file__).with_name('run-macos-process-overhead-scoped.py')
ADAPTER_SPEC = importlib.util.spec_from_file_location('overhead_control_adapter', ADAPTER_PATH)
adapter = importlib.util.module_from_spec(ADAPTER_SPEC)
ADAPTER_SPEC.loader.exec_module(adapter)


def send_frame(conn, value):
    conn.sendall(json.dumps(value, sort_keys=True).encode('utf-8') + b'\n')


def receive_frame(conn, deadline, buffered):
    while b'\n' not in buffered:
        if len(buffered) >= 65535:
            raise RuntimeError('controller event exceeds 64 KiB')
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('controller event deadline expired')
        readable, _, _ = select.select([conn], [], [], min(0.1, left))
        if not readable:
            continue
        block = conn.recv(65536 - len(buffered))
        if not block:
            if buffered:
                raise RuntimeError('truncated controller event')
            return None
        buffered.extend(block)
        if len(buffered) > 65535:
            raise RuntimeError('controller event exceeds 64 KiB')
    line, remainder = bytes(buffered).split(b'\n', 1)
    buffered.clear()
    buffered.extend(remainder)
    value = json.loads(line)
    if type(value) is not dict:
        raise RuntimeError('controller event must be an object')
    return value


def run_control_protocol(conn, case, deadline):
    adapter.validate_control_case(case)
    buffered = bytearray()
    send_frame(conn, {'op': 'select', 'case': case})
    selected = receive_frame(conn, deadline, buffered)
    if selected != {'event': 'selected', 'case': case}:
        raise RuntimeError('custodian did not acknowledge the exact selected case')
    event = receive_frame(conn, deadline, buffered)
    if event is None:
        raise RuntimeError('custodian closed before publishing readiness')
    required = adapter.make_case_ready_event(
        case, event.get('event_id'), event.get('identities'), event.get('evidence'))
    if required != event:
        raise RuntimeError('custodian readiness event has unexpected or mismatched fields')
    expected_signal = adapter.CONTROL_CASES[case]['signal']
    if expected_signal is None:
        completion = receive_frame(conn, deadline, buffered)
        expected = {'event': 'deadline-expired', 'case': case,
                    'event_id': event['event_id'],
                    'reason': 'work-deadline-expired',
                    'command_status': -adapter.signal.SIGKILL}
        if completion != expected:
            raise RuntimeError('custodian closed before the actual deadline cleanup')
        return {'case': case, 'event_id': event['event_id'],
                'action': 'deadline-stop-observed', 'status': completion['command_status']}
    target = 'managed_host' if case == 'managed' else 'client'
    send_frame(conn, {'op': 'interrupt', 'case': case, 'event_id': event['event_id'],
                      'target': target, 'signal': expected_signal})
    result = receive_frame(conn, deadline, buffered)
    if (type(result) is not dict
            or set(result) != {'event', 'case', 'event_id', 'status'}
            or result.get('event') != ('managed-host-reaped' if case == 'managed' else 'client-reaped')
            or result.get('case') != case
            or result.get('event_id') != event['event_id']):
        raise RuntimeError('custodian did not confirm the selected client reap')
    accepted_statuses = {-getattr(adapter.signal, 'SIG' + expected_signal)}
    if expected_signal == 'TERM':
        accepted_statuses.add(-adapter.signal.SIGKILL)
    if type(result.get('status')) is not int or result['status'] not in accepted_statuses:
        raise RuntimeError('custodian client status does not match the requested interruption')
    return {'case': case, 'event_id': event['event_id'],
            'action': 'managed-host-interrupted' if case == 'managed' else 'client-interrupted',
            'status': result['status']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', required=True)
    parser.add_argument('--case', choices=('setup', 'build', 'managed', 'deadline'), required=True)
    parser.add_argument('--timeout', type=float, default=585.0)
    args = parser.parse_args()
    if args.timeout <= 0 or args.timeout > 585:
        parser.error('timeout must be positive and at most 585 seconds')
    deadline = time.monotonic() + args.timeout
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(min(2.0, args.timeout))
        conn.connect(args.socket)
        conn.settimeout(None)
        result = run_control_protocol(conn, args.case, deadline)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
