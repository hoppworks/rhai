#!/usr/bin/env python3
"""Narrow runtime custodian for the macOS overhead source harness."""
import json
import math
import os
import select
import shutil
import socket
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

XCODE_TOOLS = Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin')
REPO = Path(__file__).resolve().parents[2]
EXACT_XCODE_PREFLIGHT = {
    ('/usr/bin/xcrun', '--version'),
    ('/usr/bin/xcrun', '--show-sdk-path'),
    ('/usr/bin/xcrun', '--find', 'cc'),
    ('/usr/bin/xcrun', '--find', 'clang'),
    ('/usr/bin/xcrun', '--find', 'ld'),
    ('/usr/bin/xcrun', '--find', 'dsymutil'),
    (str(XCODE_TOOLS/'cc'), '--version'),
    (str(XCODE_TOOLS/'clang'), '--version'),
    (str(XCODE_TOOLS/'ld'), '-v'),
    (str(XCODE_TOOLS/'dsymutil'), '--version'),
}

def is_exact_xcode_preflight(argv):
    return tuple(argv) in EXACT_XCODE_PREFLIGHT


CONTROL_CASES = {
    'setup': {'signal': 'TERM', 'evidence': ('setup_command_live',)},
    'build': {'signal': 'KILL', 'evidence': ('cargo_live', 'compiler_descendant_live')},
    'managed': {'signal': 'KILL', 'evidence': ('managed_host_live', 'fixture_live',
        'fixture_topology_live', 'fixture_thread_count', 'stdout_bytes_read', 'stderr_bytes_read')},
    'deadline': {'signal': None, 'evidence': ('command_live',)},
}
DEADLINE_CONTROL_ARGV = [sys.executable, '-c', 'import time; time.sleep(600)']


def validate_control_case(case):
    if type(case) is not str or case not in CONTROL_CASES:
        raise ValueError('one finite control case is required')
    return case


def validate_control_selection(request, expected_case):
    validate_control_case(expected_case)
    if (not isinstance(request, dict) or set(request) != {'op', 'case'}
            or request.get('op') != 'select' or request.get('case') != expected_case):
        raise ValueError('controller selection does not match the one selected control case')
    return expected_case


def validate_case_evidence(case, evidence):
    validate_control_case(case)
    required = CONTROL_CASES[case]['evidence']
    if case == 'managed':
        if (type(evidence) is not dict or set(evidence) != set(required)
                or any(evidence.get(key) is not True for key in
                       ('managed_host_live', 'fixture_live', 'fixture_topology_live'))
                or type(evidence.get('fixture_thread_count')) is not int
                or evidence['fixture_thread_count'] != 4
                or any(type(evidence.get(key)) is not int or evidence[key] <= 0
                       for key in ('stdout_bytes_read', 'stderr_bytes_read'))):
            raise ValueError(f'{case} case readiness evidence is incomplete')
        return dict(evidence)
    if type(evidence) is not dict or any(evidence.get(key) is not True for key in required):
        raise ValueError(f'{case} case readiness evidence is incomplete')
    return {key: True for key in required}


def validate_managed_task_sample(sample, expected_identity):
    keys = ('pid', 'start_seconds', 'start_microseconds')
    if (type(sample) is not dict or type(expected_identity) is not dict
            or sample.get('foreign') is True
            or any(type(sample.get(key)) is not int or sample.get(key) != expected_identity.get(key)
                   for key in keys)
            or type(sample.get('thread_count')) is not int or sample['thread_count'] != 4):
        raise ValueError('Managed task sample identity/count is not the exact expected live fixture')
    return True


def validate_managed_capture_progress(progress, host_identity, fixture_identity):
    """Require independently observed live byte progress from both captured streams."""
    keys = ('pid', 'start_seconds', 'start_microseconds')
    if (type(progress) is not dict
            or set(progress) != {'schema', 'stage', 'host', 'fixture',
                                 'stdout_bytes_read', 'stderr_bytes_read'}
            or type(progress.get('schema')) is not int or progress['schema'] != 1
            or progress.get('stage') != 'capturing'):
        raise ValueError('Managed capture progress receipt is malformed')
    for slot, expected in (('host', host_identity), ('fixture', fixture_identity)):
        got = progress.get(slot)
        if (type(got) is not dict
                or any(type(got.get(key)) is not int or got.get(key) != expected.get(key)
                       for key in keys)):
            raise ValueError('Managed capture progress receipt identity changed')
    if any(type(progress.get(key)) is not int or progress[key] <= 0
           for key in ('stdout_bytes_read', 'stderr_bytes_read')):
        raise ValueError('Managed capture progress receipt has no positive per-stream read')
    return {key: progress[key] for key in ('stdout_bytes_read', 'stderr_bytes_read')}


def bind_managed_capture_receipt(receipt, host_identity, fixture_identity):
    """Bind private read-path counters to full identities from one native census."""
    expected = {'schema', 'stage', 'host_pid', 'fixture_pid',
                'stdout_bytes_read', 'stderr_bytes_read'}
    if (type(receipt) is not dict or set(receipt) != expected
            or type(receipt.get('schema')) is not int or receipt['schema'] != 1
            or receipt.get('stage') != 'capturing'
            or type(receipt.get('host_pid')) is not int
            or type(receipt.get('fixture_pid')) is not int
            or type(host_identity) is not dict or type(fixture_identity) is not dict
            or receipt['host_pid'] != host_identity.get('pid')
            or receipt['fixture_pid'] != fixture_identity.get('pid')):
        raise ValueError('Managed capture receipt does not match the observed host/fixture PIDs')
    bound = {'schema': 1, 'stage': 'capturing', 'host': dict(host_identity),
        'fixture': dict(fixture_identity),
        'stdout_bytes_read': receipt['stdout_bytes_read'],
        'stderr_bytes_read': receipt['stderr_bytes_read']}
    validate_managed_capture_progress(bound, host_identity, fixture_identity)
    return bound


def validate_managed_snapshot(rows, gate_pid, anchor_pid, host_pid, fixture_pid,
                              host_path, fixture_path, capture_progress, custody,
                              client_pid=None):
    """Validate one full-tuple native snapshot; task count is conditional fixture evidence."""
    by_pid = {row.get('pid'): row for row in rows if not row.get('foreign')}
    gate, anchor = by_pid.get(gate_pid), by_pid.get(anchor_pid)
    host, fixture = by_pid.get(host_pid), by_pid.get(fixture_pid)
    client = by_pid.get(client_pid) if client_pid is not None else None
    if any(row is None for row in (gate, anchor, host, fixture)) or (
            client_pid is not None and (client is None or client.get('path') != sys.executable)):
        raise ValueError('Managed snapshot omitted an exact live slot')
    if gate.get('pid') != host_pid or gate.get('path') != host_path:
        raise ValueError('Managed host is not the exact anchored direct command')
    if host.get('pgid') != gate_pid or anchor.get('pgid') != gate_pid:
        raise ValueError('Managed host/anchor escaped the pinned command group')
    if fixture.get('pgid') != fixture_pid:
        raise ValueError('Managed fixture is not in its exact new process group')
    if fixture.get('path') != fixture_path:
        raise ValueError('Managed fixture image differs from the private artifact')
    if fixture_pid not in {row.get('pid') for row in custody.descendants(by_pid, host_pid)}:
        raise ValueError('Managed fixture is not a native-census descendant of the exact host')
    host_identity = {key: host[key] for key in ('pid', 'start_seconds', 'start_microseconds')}
    fixture_identity = {key: fixture[key] for key in ('pid', 'start_seconds', 'start_microseconds')}
    validate_managed_task_sample(fixture, fixture_identity)
    bound_capture_progress = bind_managed_capture_receipt(
        capture_progress, host_identity, fixture_identity)
    stream_progress = validate_managed_capture_progress(
        bound_capture_progress, host_identity, fixture_identity)
    result = {'gate': host_identity, 'anchor': {key: anchor[key] for key in
            ('pid', 'start_seconds', 'start_microseconds')},
            'managed_host': host_identity, 'fixture': fixture_identity,
            'evidence': {'managed_host_live': True, 'fixture_live': True,
                # The frozen fixture writes child-ready before starting exactly
                # two blocking writers. Four tasks are necessary but do not
                # identify those threads; this topology claim is source-bound.
                'fixture_topology_live': True, 'fixture_thread_count': 4,
                **stream_progress}}
    if client is not None:
        result['client'] = {key: client[key] for key in
                            ('pid', 'start_seconds', 'start_microseconds')}
    return result


def validate_control_request(request, selected_case, ready_event, consumed):
    validate_control_case(selected_case)
    if consumed:
        raise ValueError('control request already consumed')
    if not isinstance(ready_event, dict) or ready_event.get('event') != 'case-ready':
        raise ValueError('control request requires a published readiness event')
    if ready_event.get('case') != selected_case or not ready_event.get('event_id'):
        raise ValueError('control request readiness event does not match selected case')
    expected_signal = CONTROL_CASES[selected_case]['signal']
    if expected_signal is None:
        raise ValueError('deadline case has no controller signal action')
    if (not isinstance(request, dict)
            or set(request) != {'op', 'case', 'event_id', 'target', 'signal'}
            or request.get('op') != 'interrupt'
            or request.get('case') != selected_case
            or request.get('event_id') != ready_event['event_id']
            or request.get('target') != ('managed_host' if selected_case == 'managed' else 'client')
            or request.get('signal') != expected_signal):
        raise ValueError('control request is invalid or does not match readiness')
    identities = ready_event.get('identities')
    target = 'managed_host' if selected_case == 'managed' else 'client'
    if (type(identities) is not dict or type(identities.get(target)) is not dict
            or any(type(identities[target].get(key)) is not int
                   for key in ('pid', 'start_seconds', 'start_microseconds'))):
        raise ValueError('control request readiness lacks exact owned target identity')
    return (target, getattr(signal, 'SIG' + expected_signal))


def make_case_ready_event(case, event_id, identities, evidence):
    validate_control_case(case)
    validate_case_evidence(case, evidence)
    if case == 'managed':
        required_slots = ('client', 'gate', 'anchor', 'managed_host', 'fixture')
    else:
        required_slots = ('gate', 'anchor') if case == 'deadline' else ('client', 'gate', 'anchor')
    if type(identities) is not dict or any(
            type(identities.get(slot)) is not dict
            or any(type(identities[slot].get(key)) is not int
                   for key in ('pid', 'start_seconds', 'start_microseconds'))
            for slot in required_slots):
        raise ValueError('readiness event lacks exact owned process identities')
    if type(event_id) is not str or not event_id:
        raise ValueError('readiness event id is required')
    return {'event': 'case-ready', 'case': case, 'event_id': event_id,
            'identities': identities, 'evidence': validate_case_evidence(case, evidence)}


def accept_controller(server, expected_case, deadline):
    conn, _ = server.accept()
    conn.setblocking(True)
    try:
        selection = read_line(conn, deadline)
        validate_control_selection(selection, expected_case)
        conn.sendall(json.dumps({'event': 'selected', 'case': expected_case}).encode() + b'\n')
        return conn
    except BaseException:
        conn.close()
        raise


def signal_and_reap_owned_client(proc, signum, deadline):
    if proc.poll() is None:
        if signum == signal.SIGTERM:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
            try:
                return proc.wait(timeout=max(0, min(deadline, time.monotonic() + 2) - time.monotonic()))
            except subprocess.TimeoutExpired:
                if proc.poll() is None:
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
        elif signum == signal.SIGKILL:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        else:
            raise ValueError('unsupported direct-child signal')
    status = proc.wait(timeout=max(0, deadline - time.monotonic()))
    if status != -signum and not (signum == signal.SIGTERM and status == -signal.SIGKILL):
        raise RuntimeError('selected workload ended before the requested client interruption')
    return status


def signal_unreaped_managed_host(proc, signum):
    """Signal the exact unreaped direct child without Popen.poll/wait side effects."""
    if signum != signal.SIGKILL or proc.returncode is not None:
        raise RuntimeError('Managed host must be an unreaped direct child for exact KILL')
    try:
        # The unreaped direct child retains its PID, so this exact-child signal
        # cannot be redirected to a reused PID. Do not call Popen.kill(): its
        # send_signal implementation polls and may reap before group cleanup.
        os.kill(proc.pid, signum)
    except ProcessLookupError as exc:
        raise RuntimeError('Managed host exited before the exact-child signal') from exc


def service_controller(controller, selected_case, ready_event, consumed, client_proc, command_proc, deadline):
    readable, _, _ = select.select([controller], [], [], 0)
    if not readable:
        return None
    request = read_line(controller, deadline)
    target, signum = validate_control_request(request, selected_case, ready_event, consumed)
    proc = command_proc if target == 'managed_host' else client_proc
    if proc is None or ready_event['identities'][target]['pid'] != proc.pid:
        raise ValueError('readiness target identity does not match its exact direct-child handle')
    if target == 'managed_host':
        signal_unreaped_managed_host(proc, signum)
        # Confirmation is deferred until stop_anchored issues the one pinned
        # group signal and then reaps the exact gate and anchor children.
        return {'action': 'managed-host-interrupted', 'case': selected_case,
                'event_id': ready_event['event_id'], 'status': None}
    status = signal_and_reap_owned_client(proc, signum, deadline)
    controller.sendall(json.dumps({'event': 'client-reaped', 'case': selected_case,
        'event_id': ready_event['event_id'], 'status': status}).encode() + b'\n')
    return {'action': 'client-interrupted', 'case': selected_case,
            'event_id': ready_event['event_id'], 'status': status}


def case_evidence(case, argv, gate_row, anchor_row, client_row, native_rows, custody):
    """Derive only source-supported case evidence from one complete census."""
    rows_to_check = (gate_row, anchor_row) if case == 'deadline' else (gate_row, anchor_row, client_row)
    if any(row is None or row.get('foreign') for row in rows_to_check):
        raise ValueError('case readiness contains an inaccessible owned process row')
    if anchor_row.get('pgid') != gate_row.get('pid'):
        raise ValueError('case readiness anchor is outside the registered gate group')
    if case == 'setup':
        if argv[0] not in ('/usr/bin/git', '/usr/bin/tar') or gate_row.get('path') != argv[0]:
            raise ValueError('setup readiness requires the exact live Git/tar command')
        evidence = {'setup_command_live': True}
    elif case == 'build':
        cargo = str(custody.CARGO)
        rustc = str(custody.RUSTC)
        if argv[0] != cargo or gate_row.get('path') != cargo:
            raise ValueError('build readiness requires the pinned Cargo image')
        by_pid = {row.get('pid'): row for row in native_rows if not row.get('foreign')}
        child_rows = custody.descendants(by_pid, gate_row['pid'])
        if not any(row.get('path') == rustc for row in child_rows):
            raise ValueError('build readiness requires an observed pinned rustc descendant')
        evidence = {'cargo_live': True, 'compiler_descendant_live': True}
    elif case == 'managed':
        raise ValueError('Managed readiness requires the paired native snapshot path')
    else:
        if argv != DEADLINE_CONTROL_ARGV or gate_row.get('path') != sys.executable:
            raise ValueError('deadline readiness requires the fixed adapter-owned sleeper')
        evidence = {'command_live': True}
    return evidence


def validate_managed_command_argv(argv, runtime):
    runtime = Path(runtime)
    host = runtime/'target/debug/examples/macos-managed-capture-companion'
    if len(argv) != 6 or argv[0] != str(host):
        raise ValueError('Managed host command vector is not the single reviewed companion')
    fixture = Path(argv[1])
    fixture_root = runtime/'target/debug/deps'
    if (not fixture.is_absolute() or fixture.is_symlink()
            or fixture_root not in fixture.resolve(strict=True).parents
            or argv[2:] != [str(runtime/'managed-host-ready.json'),
                str(runtime/'managed-fixture.record'), str(runtime/'managed-host-complete'),
                str(runtime/'managed-capture-progress.json')]):
        raise ValueError('Managed host command vector escapes its exact private artifacts')
    return host, fixture


def observe_managed_case_ready(custody, argv, gate, anchor, client_proc, deadline, runtime):
    expected_host = runtime/'target/debug/examples/macos-managed-capture-companion'
    if not argv or argv[0] != str(expected_host):
        return None
    _host, fixture_path = validate_managed_command_argv(argv, runtime)
    ready_path, fixture_record, complete_path, progress_path = map(Path, argv[2:])
    if complete_path.exists():
        return None
    try:
        ready = json.loads(ready_path.read_text(encoding='utf-8'))
        fields = fixture_record.read_text(encoding='ascii').split()
        progress = json.loads(progress_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        # The frozen public run_raw API returns captured bytes only at
        # completion. No pre-completion per-stream progress source is currently
        # wired, so absent progress must keep this Managed control unavailable.
        return None
    if (type(ready) is not dict or set(ready) != {'schema', 'host_pid', 'stage'}
            or ready.get('schema') != 1 or ready.get('stage') != 'managed-run-entering'
            or type(ready.get('host_pid')) is not int or len(fields) != 2
            or not fields[0].startswith('child-pid=') or fields[1] != 'child-ready=1'):
        return None
    try:
        fixture_pid = int(fields[0].split('=', 1)[1])
    except ValueError:
        return None
    if (type(progress) is not dict or progress.get('host_pid') != ready['host_pid']
            or progress.get('fixture_pid') != fixture_pid):
        return None
    reader = custody._adapter_process_reader
    snapshots = []
    for _ in range(2):
        rows = reader.complete_listing(deadline)
        by_pid = {row.get('pid'): row for row in rows}
        observed = [row for row in rows if row.get('pid') == os.getpid()]
        observed.extend(custody.descendants(by_pid, gate.pid))
        merge_observed_identities(observed)
        snapshot = validate_managed_snapshot(rows, gate.pid, anchor.pid,
            ready['host_pid'], fixture_pid, str(expected_host), str(fixture_path),
            progress, custody,
            client_proc.pid if client_proc else None)
        snapshots.append(snapshot)
    if snapshots[0] != snapshots[1]:
        raise ValueError('Managed host/fixture full identity or task sample changed between censuses')
    slots = snapshots[1]
    return make_case_ready_event('managed', str(uuid.uuid4()),
        {key: slots[key] for key in ('client', 'gate', 'anchor', 'managed_host', 'fixture')},
        slots['evidence'])


def observe_case_ready(custody, case, argv, gate, anchor, client_proc, deadline, runtime=None):
    if case == 'managed':
        if runtime is None:
            raise ValueError('Managed readiness requires the exact private runtime path')
        return observe_managed_case_ready(custody, argv, gate, anchor, client_proc,
                                          deadline, Path(runtime))
    reader = custody._adapter_process_reader
    rows = reader.complete_listing(deadline)
    by_pid = {row['pid']: row for row in rows if not row.get('foreign')}
    if LEDGER_PATH is not None:
        observed = [by_pid[pid] for pid in (gate.pid, anchor.pid, client_proc.pid if client_proc else None)
                    if pid is not None and pid in by_pid]
        observed.extend(custody.descendants(by_pid, gate.pid))
        merge_observed_identities(observed)
    slots = {'gate': by_pid.get(gate.pid), 'anchor': by_pid.get(anchor.pid)}
    if client_proc is not None:
        slots['client'] = by_pid.get(client_proc.pid)
    if any(row is None for row in slots.values()):
        raise ValueError('case readiness lacks a complete native census of every exact owned slot')
    if slots['gate'].get('pgid') != gate.pid or slots['anchor'].get('pgid') != gate.pid:
        raise ValueError('case readiness gate/anchor identity is outside the exact pinned group')
    if client_proc is not None and slots['client'].get('path') != sys.executable:
        raise ValueError('case readiness client image differs from the exact Python interpreter')
    evidence = case_evidence(case, argv, slots['gate'], slots['anchor'], slots.get('client'), rows, custody)
    identities = {name: {key: row[key] for key in ('pid', 'start_seconds', 'start_microseconds')}
                  for name, row in slots.items()}
    return make_case_ready_event(case, str(uuid.uuid4()), identities, evidence)


def _identity_triplet(reader, pid, deadline):
    rows = reader.complete_listing(deadline)
    matches = [row for row in rows if row.get('pid') == pid and not row.get('foreign')]
    if len(matches) != 1:
        raise ValueError('exact client identity is absent from complete native census')
    merge_observed_identities(matches)
    return {key: matches[0][key] for key in ('pid', 'start_seconds', 'start_microseconds')}

GATE_CODE = ('import os,signal,sys; fd=int(sys.argv[1]); mask=sys.argv[2]; '
             'token=os.read(fd,1); os.close(fd); '
             'sys.exit(125) if token != b"1" else None; '
             'signal.pthread_sigmask(signal.SIG_SETMASK,{signal.Signals(int(v)) for v in mask.split(",") if v}); '
             'os.execve(sys.argv[3],sys.argv[3:],os.environ)')
ANCHOR_CODE = ('import os,signal,sys,time; fd=int(sys.argv[1]); mask=sys.argv[2]; '
               'signal.pthread_sigmask(signal.SIG_SETMASK,{signal.Signals(int(v)) for v in mask.split(",") if v}); '
               'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
               'os.write(fd, ("ANCHOR_READY pid=%d pgid=%d\\n" '
               '% (os.getpid(),os.getpgrp())).encode("ascii")); os.close(fd); '
               'exec("while True: time.sleep(3600)")')
CLIENT_CODE = ('import os,signal,sys; mask=sys.argv[1]; '
               'signal.pthread_sigmask(signal.SIG_SETMASK,{signal.Signals(int(v)) for v in mask.split(",") if v}); '
               'os.execv(sys.argv[2],sys.argv[2:])')


def client_argv(driver, mask_arg):
    """Run the non-executable driver path through this Python interpreter."""
    return [sys.executable, '-c', CLIENT_CODE, mask_arg, sys.executable, str(driver)]


REQUESTED_SIGNAL = None
CUSTODY_RECORDS = []
CUSTODY_IDENTITIES = {}
LEDGER_PATH = None
CUSTODIAN_IDENTITY = None


def note_signal(signum, _frame):
    global REQUESTED_SIGNAL
    if REQUESTED_SIGNAL is None:
        REQUESTED_SIGNAL = signum


def interruption_pending():
    if REQUESTED_SIGNAL is not None:
        return True
    pending = getattr(signal, 'sigpending', None)
    return callable(pending) and bool(set(pending()) & {signal.SIGINT, signal.SIGTERM})


def require_active(deadline, operation):
    if interruption_pending():
        raise InterruptedError(f'custodian cancellation before {operation}')
    if time.monotonic() >= deadline:
        raise TimeoutError(f'deadline expired before {operation}')


def _mask_argument(mask):
    return ','.join(str(int(sig)) for sig in sorted(mask, key=int))


def terminate_and_reap_client(proc, deadline):
    """Stop only the exact direct RPC child, escalating once and reaping it."""
    if proc.returncode is not None:
        return proc.returncode
    try:
        proc.terminate()
    except ProcessLookupError:
        # The unreaped child may have exited between the returncode check and
        # the exact-child signal. wait() below still reaps that child handle.
        pass
    term_deadline = min(deadline, time.monotonic() + 2)
    try:
        return proc.wait(timeout=max(0, term_deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return proc.wait(timeout=max(0, deadline - time.monotonic()))


def kill_and_reap_direct_children(children, deadline, issued):
    statuses = []
    failures = []
    for label, child in children:
        try:
            if child.returncode is None and not issued.get(label, False):
                issued[label] = True
                child.kill()  # Popen is the exact direct child handle.
            statuses.append(child.wait(timeout=max(0, deadline - time.monotonic())))
        except (OSError, subprocess.TimeoutExpired, ChildProcessError) as exc:
            failures.append(f'{label} pid={child.pid}: {type(exc).__name__}: {exc}')
            statuses.append(None)
    if failures:
        raise RuntimeError('exact direct-child kill/reap incomplete: ' + '; '.join(failures))
    return statuses


def read_line(conn, deadline):
    data = bytearray()
    while b'\n' not in data:
        if len(data) >= 65535:
            raise RuntimeError('custody RPC frame exceeds 64 KiB')
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('custody RPC deadline expired')
        ready, _, _ = select.select([conn], [], [], min(0.1, left))
        if not ready:
            if REQUESTED_SIGNAL is not None:
                raise InterruptedError(f'custodian received signal {REQUESTED_SIGNAL}')
            continue
        block = conn.recv(65536 - len(data))
        if not block:
            if data:
                raise RuntimeError('truncated custody RPC frame')
            return None
        data.extend(block)
        if len(data) > 65535:
            raise RuntimeError('custody RPC frame exceeds 64 KiB')
    line, extra = bytes(data).split(b'\n', 1)
    if extra:
        raise RuntimeError('custody RPC pipelining is forbidden')
    return json.loads(line)


def client_gone(conn):
    ready, _, _ = select.select([conn], [], [], 0)
    if not ready:
        return False
    data = conn.recv(1, socket.MSG_PEEK)
    return not data


def popen_group_options(group_pgid=None):
    if 'process_group' in __import__('inspect').signature(subprocess.Popen).parameters:
        return {'process_group': 0 if group_pgid is None else group_pgid}
    if os.name != 'posix' or not callable(getattr(os, 'setpgid', None)):
        raise RuntimeError('no reviewed process-group child setup API')
    import threading
    if threading.active_count() != 1:
        raise RuntimeError('preexec setpgid fallback requires a single-threaded custodian')
    return {'preexec_fn': os.setpgrp if group_pgid is None else lambda: os.setpgid(0, group_pgid)}


def read_anchor_ready(fd, pid, pgid, deadline):
    os.set_blocking(fd, False)
    data = bytearray()
    while b'\n' not in data:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('anchor readiness deadline expired')
        ready, _, _ = select.select([fd], [], [], min(0.05, left))
        if not ready:
            continue
        block = os.read(fd, 256 - len(data))
        if not block or len(data) + len(block) > 256:
            raise RuntimeError('invalid anchor readiness record')
        data.extend(block)
    if data.count(b'\n') != 1 or not data.endswith(b'\n'):
        raise RuntimeError('anchor readiness must be exactly one line')
    value = bytes(data).decode('ascii').strip()
    if value.split() != ['ANCHOR_READY', f'pid={pid}', f'pgid={pgid}']:
        raise RuntimeError('anchor PID/PGID identity mismatch')
    return value


def waitid_nonreap(custody, pid):
    return custody.waitid_nonreap(pid)


def spawn_anchored(custody, argv, cwd, env, output_path, deadline, closure_deadline,
                   stderr_path=None):
    require_active(deadline, 'owned command setup')
    release_r, release_w = os.pipe()
    ready_r, ready_w = os.pipe()
    gate = anchor = None
    signal_state = {'issued': False}
    released = False
    record = {'command_pid': None, 'anchor_pid': None, 'pgid': None,
              'released': False, 'group_signal_issued': False,
              'gate_status': None, 'anchor_status': None,
              'output': str(output_path), 'setup_complete': False}
    CUSTODY_RECORDS.append(record)
    old = {sig: signal.signal(sig, note_signal) for sig in (signal.SIGINT, signal.SIGTERM)}
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    mask_arg = _mask_argument(blocked)
    try:
        require_active(deadline, 'gate spawn')
        with Path(output_path).open('wb') as output:
            error_output = Path(stderr_path).open('wb') if stderr_path else None
            try:
                gate = subprocess.Popen([sys.executable, '-c', GATE_CODE, str(release_r), mask_arg, *argv],
                    cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=output,
                    stderr=error_output if error_output else subprocess.STDOUT,
                    close_fds=True, pass_fds=(release_r,), **popen_group_options())
                record.update({'command_pid': gate.pid, 'pgid': gate.pid})
            finally:
                if error_output:
                    error_output.close()
        os.close(release_r); release_r = -1
        require_active(deadline, 'anchor spawn')
        anchor = subprocess.Popen([sys.executable, '-c', ANCHOR_CODE, str(ready_w), mask_arg],
            cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True, pass_fds=(ready_w,),
            **popen_group_options(gate.pid))
        record['anchor_pid'] = anchor.pid
        os.close(ready_w); ready_w = -1
        ready = read_anchor_ready(ready_r, anchor.pid, gate.pid, min(deadline, time.monotonic() + 5))
        if os.getpgid(anchor.pid) != gate.pid:
            raise RuntimeError('anchor is not in gate process group')
        if LEDGER_PATH is not None:
            record_registered_processes(custody, (gate.pid, anchor.pid),
                                        min(deadline, time.monotonic() + 2))
        if waitid_nonreap(custody, gate.pid) is not None or waitid_nonreap(custody, anchor.pid) is not None:
            raise RuntimeError('gate or anchor exited before release')
        require_active(deadline, 'gate release')
        released = True
        record['released'] = True
        if os.write(release_w, b'1') != 1:
            raise RuntimeError('custody gate release write was incomplete')
        os.close(release_w); release_w = -1
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        record['setup_complete'] = True
        return gate, anchor, ready, old, blocked, signal_state, record
    except BaseException as setup_error:
        cleanup_failure = None
        try:
            if gate is not None and anchor is not None:
                try:
                    statuses = stop_anchored(custody, gate, anchor, gate.pid,
                                             min(closure_deadline, time.monotonic() + 5), signal_state)
                    record.update({'gate_status': statuses[0], 'anchor_status': statuses[1],
                                   'group_signal_issued': signal_state['issued'], 'cleanup_complete': True})
                except BaseException as group_error:
                    statuses = kill_and_reap_direct_children((('gate', gate), ('anchor', anchor)),
                        min(closure_deadline, time.monotonic() + 5), record.setdefault('direct_kill_issued', {}))
                    record.update({'gate_status': statuses[0], 'anchor_status': statuses[1],
                        'group_signal_issued': signal_state['issued'],
                        'cleanup_complete': not released})
                    if released:
                        raise RuntimeError('post-release group cleanup uncertain; exact children reaped but runtime retained') from group_error
            elif gate is not None:
                if waitid_nonreap(custody, gate.pid) is None:
                    gate.kill()
                record['gate_status'] = gate.wait(timeout=2)
                record['cleanup_complete'] = True
        except BaseException as cleanup_error:
            cleanup_failure = cleanup_error
        for sig, handler in old.items(): signal.signal(sig, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        record['setup_complete'] = False
        if cleanup_failure is not None:
            phase = 'post-release' if released else 'pre-release'
            raise RuntimeError(f'{phase} custody setup cleanup incomplete; retain runtime: {cleanup_failure}') from setup_error
        raise
    finally:
        for fd in (release_r, release_w, ready_r, ready_w):
            if fd >= 0:
                try: os.close(fd)
                except OSError: pass


def stop_anchored(custody, gate, anchor, group_pgid, deadline, signal_state):
    if not signal_state['issued']:
        if waitid_nonreap(custody, anchor.pid) is not None:
            raise RuntimeError('anchor is not live; refusing numeric group signal')
        if os.getpgid(anchor.pid) != group_pgid or group_pgid != gate.pid:
            raise RuntimeError('anchor/group identity changed; refusing group signal')
        signal_state['issued'] = True
        os.killpg(group_pgid, signal.SIGKILL)
    failures = []
    statuses = []
    for child, label in ((gate, 'gate'), (anchor, 'anchor')):
        try: statuses.append(child.wait(timeout=max(0, deadline - time.monotonic())))
        except (OSError, subprocess.TimeoutExpired, ChildProcessError) as exc:
            failures.append(f'{label} pid={child.pid}: {type(exc).__name__}: {exc}')
            statuses.append(None)
    if failures:
        raise RuntimeError('group signalled once; exact child reap incomplete: ' + '; '.join(failures))
    return statuses


def owned_command(custody, argv, cwd, env, output, deadline, closure_deadline, conn=None,
                  stderr_path=None, monitor=False, runtime=None, control_context=None):
    require_active(deadline, 'owned command spawn')
    gate, anchor, ready, old, blocked, signal_state, record = spawn_anchored(
        custody, argv, cwd, env, output, deadline, closure_deadline, stderr_path)
    failure = None
    last_sample = None
    last_readiness_probe = None
    ready_event = None
    control_consumed = False
    wait_statuses = None
    try:
        while waitid_nonreap(custody, gate.pid) is None:
            now = time.monotonic()
            if REQUESTED_SIGNAL is not None:
                failure = InterruptedError(f'custodian received signal {REQUESTED_SIGNAL}')
                break
            if conn is not None and client_gone(conn):
                failure = BrokenPipeError('harness client disconnected during owned command')
                break
            if control_context is not None:
                controller, selected_case, client_proc = control_context
                if ready_event is None and (last_readiness_probe is None or now-last_readiness_probe >= 0.1):
                    last_readiness_probe = now
                    try:
                        ready_event = observe_case_ready(custody, selected_case, argv,
                            gate, anchor, client_proc, min(deadline, time.monotonic()+2), runtime)
                    except (OSError, RuntimeError, ValueError, TimeoutError):
                        ready_event = None
                    else:
                        record.update({'control_case': selected_case,
                                       'control_readiness_event': ready_event})
                        controller.sendall(json.dumps(ready_event, sort_keys=True).encode()+b'\n')
                if ready_event is not None and selected_case != 'deadline':
                    control_action = service_controller(controller, selected_case,
                        ready_event, control_consumed, client_proc, gate, closure_deadline)
                    if control_action is not None:
                        record['control_action'] = control_action
                        control_consumed = True
                        failure = InterruptedError('selected control case interrupted its exact registered child')
                        break
            if now >= deadline:
                failure = TimeoutError('owned command deadline expired')
                break
            if monitor and (last_sample is None or now - last_sample >= 1):
                last_sample = now
                sample_owned_resources(custody, runtime, env, deadline, closure_deadline)
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        statuses = stop_anchored(custody, gate, anchor, gate.pid,
                                 min(closure_deadline, time.monotonic() + 5), signal_state)
        wait_statuses = statuses
        record['cleanup_complete'] = True
        managed_action = record.get('control_action')
        if (control_context is not None and control_context[1] == 'managed'
                and isinstance(managed_action, dict)
                and managed_action.get('action') == 'managed-host-interrupted'):
            if statuses[0] != -signal.SIGKILL:
                raise RuntimeError('Managed gate status does not confirm its requested exact-child KILL')
            managed_action['status'] = statuses[0]
            controller, case, _client = control_context
            controller.sendall(json.dumps({'event': 'managed-host-reaped', 'case': case,
                'event_id': managed_action['event_id'], 'status': statuses[0]},
                sort_keys=True).encode() + b'\n')
        if (control_context is not None and control_context[1] == 'deadline'
                and isinstance(failure, TimeoutError) and ready_event is not None):
            record['control_stop_reason'] = 'work-deadline-expired'
            record['control_completion_event'] = {
                'event': 'deadline-expired', 'case': 'deadline',
                'event_id': ready_event['event_id'],
                'reason': 'work-deadline-expired', 'command_status': gate.returncode}
            control_context[0].sendall(json.dumps(
                record['control_completion_event'], sort_keys=True).encode() + b'\n')
        print(f'custodian_command_reaped gate={statuses[0]} anchor={statuses[1]} '
              f'pgid={gate.pid} group_signal_issued={signal_state["issued"]}', flush=True)
        if control_context is not None and control_context[1] == 'deadline' \
                and isinstance(failure, TimeoutError):
            return gate.returncode, gate.pid, ready
        if (control_context is not None and control_context[1] == 'managed'
                and record.get('control_action', {}).get('action') == 'managed-host-interrupted'):
            return gate.returncode, gate.pid, ready
        if failure:
            raise RuntimeError(f'owned command stopped after interruption/limit: {failure}')
        return gate.returncode, gate.pid, ready
    finally:
        if gate.returncode is None or anchor.returncode is None:
            try:
                wait_statuses = stop_anchored(custody, gate, anchor, gate.pid,
                              min(closure_deadline, time.monotonic() + 5), signal_state)
                record['cleanup_complete'] = True
            except BaseException as cleanup_error:
                try:
                    wait_statuses = kill_and_reap_direct_children((('gate', gate), ('anchor', anchor)),
                        min(closure_deadline, time.monotonic() + 5), record.setdefault('direct_kill_issued', {}))
                except BaseException as exact_error:
                    cleanup_error = RuntimeError(f'{cleanup_error}; {exact_error}')
                record['cleanup_complete'] = False
                print(f'custodian_command_cleanup_incomplete={type(cleanup_error).__name__}: {cleanup_error} '
                      'runtime_retained=true', flush=True)
        for sig, handler in old.items(): signal.signal(sig, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        record.update({'group_signal_issued': signal_state['issued'],
            'gate_status': None if not wait_statuses else wait_statuses[0],
            'anchor_status': None if not wait_statuses else wait_statuses[1]})


def internal_command(custody, argv, cwd, env, output, deadline, closure_deadline, stderr_path=None):
    status, pgid, _ready = owned_command(custody, argv, cwd, env, output, deadline,
                                         closure_deadline, stderr_path=stderr_path)
    return status, pgid, Path(output).read_bytes()


def run_deadline_control(custody, runtime, env, work_deadline, closure_deadline, controller):
    return owned_command(custody, DEADLINE_CONTROL_ARGV, runtime, env,
        runtime / 'deadline-control.out', work_deadline, closure_deadline,
        monitor=False, runtime=runtime,
        control_context=(controller, 'deadline', None))


def _identity_key(row):
    return (row.get('pid'), row.get('start_seconds'), row.get('start_microseconds'))


def _write_ledger(state, complete=False):
    if LEDGER_PATH is None:
        raise RuntimeError('adapter custody ledger was not initialized')
    data = {
        'sampling': 'one-second samples; RSS/storage checks are not continuous enforcement',
        'identity_observation': 'full PID/start tuples and resident-byte samples from one native complete census',
        'custodian_identity': CUSTODIAN_IDENTITY,
        'identities': sorted(CUSTODY_IDENTITIES.values(), key=_identity_key),
        'observed_identity_readback_complete': complete,
        'custody_state': state,
    }
    temporary = LEDGER_PATH.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, sort_keys=True) + '\n')
    os.replace(temporary, LEDGER_PATH)


def merge_observed_identities(rows):
    for row in rows:
        CUSTODY_IDENTITIES.setdefault(_identity_key(row), row)
    _write_ledger('monitoring', complete=False)


def record_registered_processes(custody, pids, deadline):
    """Persist exact gate/anchor identities from one complete native census."""
    reader = getattr(custody, '_adapter_process_reader', None)
    if reader is None:
        raise RuntimeError('native process reader is unavailable for custody registration')
    rows = reader.complete_listing(deadline)
    by_pid = {row.get('pid'): row for row in rows if not row.get('foreign')}
    selected = [by_pid.get(pid) for pid in pids]
    if any(row is None for row in selected):
        raise RuntimeError('complete native census omitted an exact registered command or anchor')
    merge_observed_identities(selected)
    return selected


def initialize_ledger(runtime, reader, deadline):
    global LEDGER_PATH, CUSTODIAN_IDENTITY
    rows = reader.complete_listing(deadline)
    found = [row for row in rows if row.get('pid') == os.getpid() and not row.get('foreign')]
    if len(found) != 1:
        raise RuntimeError('adapter self identity is missing or ambiguous; runtime retained')
    CUSTODIAN_IDENTITY = found[0]
    LEDGER_PATH = runtime / 'owned-process-ledger.json'
    CUSTODY_IDENTITIES.clear()
    _write_ledger('setup-in-progress', complete=False)


def record_sampled_descendants(custody, runtime, deadline):
    """Persist one native census before validating its resource sample."""
    reader = custody._adapter_process_reader
    native_rows = reader.complete_listing(deadline)
    native_by_pid = {row['pid']: row for row in native_rows}
    root_pid = os.getpid()
    root = native_by_pid.get(root_pid)
    descendants = custody.descendants(native_by_pid, root_pid)
    # Record every exact observed descendant before later resource bounds can
    # reject the sample or custody checks, preserving the strongest census.
    merge_observed_identities(descendants)
    if root is None or root.get('foreign'):
        raise RuntimeError('custodian absent from complete native process census')
    if _identity_key(root) != _identity_key(CUSTODIAN_IDENTITY):
        raise RuntimeError('custodian identity changed during native resource sample')
    return [root, *descendants]


def sample_owned_resources(custody, runtime, env, deadline, closure_deadline):
    if deadline - time.monotonic() <= 0:
        raise TimeoutError('no work deadline remains for resource sample')
    reader = custody._adapter_process_reader
    live = record_sampled_descendants(custody, runtime,
                                      min(closure_deadline, time.monotonic() + 5))
    rss_kib = reader.resident_kib(live)
    module = custody
    module.enforce_process_sample(live, rss_kib)
    print(f'custodian_owned_descendants={len(live)-1} custodian_tree_rss_kib={rss_kib} '
          f'limit_descendants={module.MAX_DESCENDANTS} limit_rss_kib={module.MAX_RSS_KIB} '
          'sample_interval_seconds=1 continuous_enforcement=false', flush=True)

    last_error = None
    for attempt in (1, 2):
        du_path = runtime / f'custodian-storage-{attempt}.out'
        try:
            status, _pgid, data = internal_command(custody,
                ['/usr/bin/du', '-sk', str(runtime)], runtime, env,
                du_path, min(deadline, time.monotonic() + 5), closure_deadline)
            fields = data.decode(errors='replace').strip().split(maxsplit=1)
            if status or len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(runtime):
                raise RuntimeError(f'invalid storage sample status={status}: {data!r}')
            kib = int(fields[0])
            print(f'custodian_storage_sample_attempt={attempt} kib={kib}', flush=True)
            if kib >= module.LIMIT:
                raise RuntimeError(f'sampled storage reached {module.LIMIT} KiB')
            return
        except (OSError, RuntimeError, TimeoutError) as exc:
            last_error = exc
            if attempt == 2:
                break
    raise RuntimeError(f'two custodian storage samples failed: {last_error}')


def _private_path(path, runtime, evidence, label):
    if not path.is_absolute() or path.is_symlink():
        raise RuntimeError(f'invalid {label} path')
    resolved = path.resolve(strict=False)
    if not any(resolved == parent or parent in resolved.parents
               for parent in (runtime, evidence)):
        raise RuntimeError(f'{label} path escapes private runtime/evidence roots')
    return resolved


def serve_requests(custody, conn, runtime, work_deadline, closure_deadline,
                   control_context=None):
    while True:
        require_active(work_deadline, 'RPC dispatch')
        request = read_line(conn, work_deadline)
        if request is None:
            return 'client-eof'
        if not isinstance(request, dict) or request.get('op') != 'command':
            raise RuntimeError('invalid custody RPC operation')
        argv = request.get('argv')
        env = request.get('env')
        output = Path(request.get('output', ''))
        cwd = Path(request.get('cwd', ''))
        if not isinstance(argv, list) or not argv or not all(type(arg) is str and '\0' not in arg for arg in argv):
            raise RuntimeError('invalid command argv in custody RPC')
        if len(json.dumps(request)) > 65535 or not isinstance(env, dict) or \
                not all(type(k) is str and type(v) is str for k, v in env.items()):
            raise RuntimeError('invalid custody RPC environment or size')
        expected_env = custody.build_environment(runtime)
        if env != expected_env:
            raise RuntimeError('custody RPC environment differs from closed adapter environment')
        allowed_executables = {
            str(custody.CARGO), str(custody.RUSTC), str(custody.RUSTDOC),
            '/usr/bin/git', '/usr/bin/tar', '/bin/ps', '/usr/bin/du',
            '/usr/bin/xcrun', str(XCODE_TOOLS/'cc'), str(XCODE_TOOLS/'clang'),
            str(XCODE_TOOLS/'ld'), str(XCODE_TOOLS/'dsymutil'),
        }
        managed_host = runtime/'target/debug/examples/macos-managed-capture-companion'
        if argv[0] == str(managed_host):
            if (control_context is None or control_context[1] != 'managed'
                    or not managed_host.is_file() or managed_host.is_symlink()):
                raise RuntimeError('Managed companion is allowed only for its selected finite control')
            validate_managed_command_argv(argv, runtime)
            allowed_executables.add(str(managed_host))
        if argv[0] not in allowed_executables:
            raise RuntimeError('custody RPC executable is outside the audited command set')
        if argv[0] in {'/usr/bin/xcrun', str(XCODE_TOOLS/'cc'), str(XCODE_TOOLS/'clang'),
                       str(XCODE_TOOLS/'ld'), str(XCODE_TOOLS/'dsymutil')} and not is_exact_xcode_preflight(argv):
            raise RuntimeError('Xcode tool preflight argv is outside the exact reviewed query set')
        if type(request.get('monitor_resources', False)) is not bool:
            raise RuntimeError('resource monitor request must be a boolean')
        evidence = (REPO/'.scratch/all-tickets/macos-process-overhead-evidence').resolve()
        output = _private_path(output, runtime, evidence, 'command output')
        if request.get('stderr') is not None:
            stderr = Path(request['stderr'])
            stderr = _private_path(stderr, runtime, evidence, 'command stderr')
        else:
            stderr = None
        cwd = cwd.resolve(strict=True)
        repo = REPO.resolve()
        if cwd != repo and cwd != runtime and runtime not in cwd.parents:
            raise RuntimeError('custody RPC working directory is outside repository/runtime')
        requested_deadline = request.get('deadline')
        if type(requested_deadline) not in (int, float) or not math.isfinite(requested_deadline):
            raise RuntimeError('custody RPC deadline must be a finite number')
        command_deadline = min(float(requested_deadline), work_deadline)
        if command_deadline <= time.monotonic():
            raise TimeoutError('client command deadline expired')
        try:
            status, pgid, ready = owned_command(custody, argv, cwd, env, output,
                command_deadline, closure_deadline, conn=conn, stderr_path=stderr,
                monitor=request.get('monitor_resources', False), runtime=runtime,
                control_context=control_context)
            response = {'status': status, 'output': str(output), 'pgid': pgid,
                        'anchor_ready': ready, 'group_signal_issued': True}
        except BaseException as exc:
            if client_gone(conn):
                return 'client-eof'
            response = {'error': f'{type(exc).__name__}: {exc}', 'output': str(output)}
            latest = CUSTODY_RECORDS[-1] if CUSTODY_RECORDS else None
            stop_reason = ('custody-incomplete' if latest is not None and
                           not latest.get('cleanup_complete', False) else
                           'cancelled' if interruption_pending() else 'command-failed')
        else:
            stop_reason = None
        try:
            conn.sendall(json.dumps(response, sort_keys=True).encode() + b'\n')
        except (BrokenPipeError, ConnectionResetError):
            return 'client-eof'
        if stop_reason is not None:
            return stop_reason


def records_closed(records):
    return bool(records) and all(
        r.get('setup_complete') is True
        and r.get('group_signal_issued') is True
        and r.get('gate_status') is not None
        and r.get('anchor_status') is not None
        and r.get('cleanup_complete') is True
        for r in records)


def control_finalization_complete(case, records, ledger, candidate_absence,
                                  live_identities, groups_absent_observations,
                                  disconnect, client_status, command_status):
    """Accept a control only from its recorded action and complete final readback."""
    try:
        if case not in ('setup', 'build', 'managed', 'deadline') or not records_closed(records):
            raise ValueError('command records are incomplete')
        if type(ledger) is not dict or ledger.get('observed_identity_readback_complete') is not True:
            raise ValueError('identity ledger readback is incomplete')
        if (type(candidate_absence) is not dict or candidate_absence.get('complete') is not True
                or candidate_absence.get('candidates') != []):
            raise ValueError('candidate absence is incomplete')
        if live_identities or groups_absent_observations < 2:
            raise ValueError('final native identity/group readback is incomplete')
        matching = [record for record in records
                    if record.get('control_case') == case
                    and type(record.get('control_readiness_event')) is dict]
        if len(matching) != 1:
            raise ValueError('one recorded readiness event is required')
        record = matching[0]
        event = record['control_readiness_event']
        if (event.get('event') != 'case-ready' or event.get('case') != case
                or type(event.get('event_id')) is not str or not event['event_id']
                or make_case_ready_event(case, event['event_id'], event.get('identities'),
                                         event.get('evidence')) != event):
            raise ValueError('readiness event is malformed')
        if case in ('setup', 'build'):
            action = record.get('control_action')
            allowed_statuses = {-getattr(signal, 'SIG' + CONTROL_CASES[case]['signal'])}
            if case == 'setup':
                allowed_statuses.add(-signal.SIGKILL)
            if (type(action) is not dict or action.get('action') != 'client-interrupted'
                    or action.get('case') != case or action.get('event_id') != event['event_id']
                    or type(action.get('status')) is not int
                    or action['status'] not in allowed_statuses
                    or disconnect != 'client-eof' or client_status != action['status']
                    or command_status is not None):
                raise ValueError('consumed client action is missing or mismatched')
        elif case == 'managed':
            action = record.get('control_action')
            host_identity = event['identities']['managed_host']
            if (type(action) is not dict or action.get('action') != 'managed-host-interrupted'
                    or action.get('case') != case or action.get('event_id') != event['event_id']
                    or type(action.get('status')) is not int or action['status'] != -signal.SIGKILL
                    or host_identity['pid'] != record.get('command_pid')
                    or disconnect != 'client-eof' or client_status != 1 or command_status is not None):
                raise ValueError('exact Managed host interruption action is missing or mismatched')
        else:
            completion = record.get('control_completion_event')
            expected = {'event': 'deadline-expired', 'case': 'deadline',
                'event_id': event['event_id'], 'reason': 'work-deadline-expired',
                'command_status': -signal.SIGKILL}
            if (record.get('control_action') is not None
                    or record.get('control_stop_reason') != 'work-deadline-expired'
                    or completion != expected or disconnect != 'deadline-control-stop'
                    or client_status is not None or command_status != -signal.SIGKILL):
                raise ValueError('actual deadline cleanup event is missing or mismatched')
        return True
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f'control finalization rejected: {exc}') from exc


def clean_interruption(disconnect, client_status, records):
    return (disconnect == 'client-eof' and type(client_status) is int
            and client_status < 0 and records_closed(records))


def require_complete_custody(clean_success, disconnect, client_status, records):
    interrupted_cleanly = clean_interruption(disconnect, client_status, records)
    if not (clean_success or interrupted_cleanly):
        raise RuntimeError('client ended without a complete custody receipt; runtime retained')
    return clean_success


def wait_for_client_connection(server, proc, work_deadline):
    """Wait only through work stop; finally retains closure time for exact reap."""
    while True:
        require_active(work_deadline, 'RPC client connection')
        try:
            conn, _ = server.accept()
            return conn
        except BlockingIOError:
            if proc.poll() is not None:
                raise RuntimeError(f'harness client exited before RPC connection status={proc.returncode}')
            time.sleep(min(0.02, max(0, work_deadline - time.monotonic())))


def read_live_identities(runtime, deadline, reader):
    ledger_path = runtime / 'owned-process-ledger.json'
    if not ledger_path.is_file() or ledger_path.is_symlink():
        raise RuntimeError('missing or invalid process identity ledger; runtime retained')
    ledger = json.loads(ledger_path.read_text())
    rows = ledger.get('identities')
    if type(rows) is not list:
        raise RuntimeError('invalid process identity ledger; runtime retained')
    if deadline <= time.monotonic():
        raise RuntimeError('no scoped time remains for final process identity readback; runtime retained')
    live_rows = reader.complete_listing(deadline)
    if time.monotonic() >= deadline:
        raise RuntimeError('final process identity readback exceeded its reserved deadline; runtime retained')
    live = {_identity_key(row) for row in live_rows if not row.get('foreign')}
    owned_live = [row for row in rows if _identity_key(row) in live]
    if owned_live:
        return owned_live
    _write_ledger('readback-complete', complete=True)
    return []


def parse_adapter_arguments(args):
    if (len(args) not in (2, 4) or args[0] != '--timeout'
            or (len(args) == 4 and args[2] != '--control-case')):
        raise ValueError('usage: run-macos-process-overhead-scoped.py --timeout SECONDS [--control-case CASE]')
    timeout = float(args[1])
    control_case = validate_control_case(args[3]) if len(args) == 4 else None
    if not math.isfinite(timeout) or timeout <= 0 or timeout > 585:
        raise ValueError('timeout must be positive and at most 585 seconds')
    return timeout, control_case


def main():
    try:
        timeout, control_case = parse_adapter_arguments(sys.argv[1:])
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    started = time.monotonic()
    deadline = started + timeout
    work_deadline = min(started + 560, deadline - 15)
    closure_deadline = min(started + 575, deadline - 10)
    readback_deadline = min(started + 580, deadline - 5)
    scope_text = os.environ.get('AGENT_BUILD_SCOPE')
    if not scope_text:
        raise RuntimeError('wrapper must provide a unique AGENT_BUILD_SCOPE before custodian start')
    scope_input = Path(scope_text).absolute()
    if scope_input.is_symlink() or not scope_input.is_dir():
        raise RuntimeError('invalid agent-build scope')
    scope = scope_input.resolve(strict=True)
    if scope != scope_input:
        raise RuntimeError('agent-build scope resolves through a redirected path')
    tmp_text = os.environ.get('TMPDIR')
    tmp_input = Path(tmp_text).absolute() if tmp_text else None
    if (tmp_input is None or tmp_input.is_symlink() or tmp_input.name != 'tmp'
            or tmp_input.resolve(strict=True).parent != scope or tmp_input.resolve() != tmp_input):
        raise RuntimeError('wrapper TMPDIR must be the absolute private scope tmp directory')
    runtime = scope / 'runtime'
    if runtime.exists() or runtime.is_symlink():
        raise RuntimeError('unique agent-build scope already contains a runtime')
    os.environ['AGENT_RUNTIME_DIR'] = str(runtime)
    repo = REPO
    evidence = repo / '.scratch/all-tickets/macos-process-overhead-evidence'
    log_base_text = os.environ.get('RHAI_OVERHEAD_LOG_BASE')
    if not log_base_text:
        raise RuntimeError('wrapper must provide the fixed evidence log base')
    log_base = Path(log_base_text).absolute()
    if (log_base.is_symlink() or not evidence.is_dir() or evidence.is_symlink()
            or log_base.parent.resolve() != evidence.resolve()):
        raise RuntimeError('wrapper evidence log base escapes the project evidence directory')
    driver = repo / '.scratch/all-tickets/macos-process-overhead.py'
    print(f'runtime_path={runtime}', flush=True)
    print(f'custodian_pid={os.getpid()} client_path={driver} scope={scope}', flush=True)
    spec = __import__('importlib.util').util.spec_from_file_location('macos_process_overhead_custody', driver)
    custody = __import__('importlib.util').util.module_from_spec(spec)
    spec.loader.exec_module(custody)
    # Resolve source gate and waitid capability before the adapter launches even
    # its nonspawning client. Child commands cannot start if either is absent.
    custody.require_launch_readiness()
    custody.require_nonreaping_waitid()
    reader_spec = __import__('importlib.util').util.spec_from_file_location(
        'darwin_process_reader_custodian', repo / '.scratch/all-tickets/darwin-process-reader.py')
    reader_module = __import__('importlib.util').util.module_from_spec(reader_spec)
    reader_spec.loader.exec_module(reader_module)
    reader = reader_module.DarwinProcessReader()
    custody._adapter_process_reader = reader
    runtime.mkdir(mode=0o700)
    identity = runtime.lstat()
    for child in ('tmp', 'home', 'target', 'cargo-home', 'rustup-home'):
        (runtime / child).mkdir(mode=0o700)
    initialize_ledger(runtime, reader, readback_deadline)
    env = dict(os.environ, AGENT_RUNTIME_DIR=str(runtime))
    env.update({key: str(runtime / 'tmp') for key in ('TMPDIR', 'TMP', 'TEMP')})
    os.environ.update(env)
    evidence.mkdir(parents=True, exist_ok=True)
    sock_path = runtime / 'custody.sock'
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    os.chmod(sock_path, 0o600)
    server.listen(1)
    server.setblocking(False)
    controller_path = runtime / 'controller.sock'
    controller_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    controller_server.bind(str(controller_path))
    os.chmod(controller_path, 0o600)
    controller_server.listen(1)
    client_env = {
        'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME': str(runtime / 'home'),
        'TMPDIR': str(runtime / 'tmp'), 'TMP': str(runtime / 'tmp'), 'TEMP': str(runtime / 'tmp'),
        'AGENT_RUNTIME_DIR': str(runtime),
        'RHAI_OVERHEAD_LOG_BASE': os.environ['RHAI_OVERHEAD_LOG_BASE'],
        'RHAI_CUSTODY_SOCKET': str(sock_path),
        'RHAI_CUSTODY_WORK_DEADLINE': repr(work_deadline),
    }
    if not callable(getattr(signal, 'pthread_sigmask', None)):
        raise RuntimeError('cannot safely block interruption across exact client registration')
    old = {sig: signal.signal(sig, note_signal) for sig in (signal.SIGINT, signal.SIGTERM)}
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    mask_arg = _mask_argument(blocked)
    proc = None
    conn = None
    controller = None
    client_status = None
    disconnect = None
    try:
        if control_case is not None:
            print(f'control_socket_path={controller_path} control_case={control_case}', flush=True)
            controller_server.settimeout(max(0, work_deadline - time.monotonic()))
            controller = accept_controller(controller_server, control_case, work_deadline)
        custodian_env = custody.build_environment(runtime)
        command_status = None
        if control_case == 'deadline':
            command_status, _command_pid, _ready = run_deadline_control(
                custody, runtime, custodian_env, work_deadline, closure_deadline, controller)
            disconnect = 'deadline-control-stop'
        else:
            require_active(work_deadline, 'RPC client spawn')
            if control_case in ('setup', 'build', 'managed'):
                client_env['RHAI_CONTROL_CASE'] = control_case
            proc = subprocess.Popen(client_argv(driver, mask_arg), env=client_env,
                                    stdin=subprocess.DEVNULL, stdout=None, stderr=None,
                                    close_fds=True)
            signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
            conn = wait_for_client_connection(server, proc, work_deadline)
            conn.setblocking(True)
            disconnect = serve_requests(custody, conn, runtime, work_deadline, closure_deadline,
                                        control_context=((controller, control_case, proc)
                                                         if control_case is not None else None))
            try:
                client_status = proc.wait(timeout=max(0, closure_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                raise RuntimeError('client failed to exit by closure deadline; runtime retained')
        live = read_live_identities(runtime, readback_deadline, reader)
        print(f'client_status={client_status} command_status={command_status} '
              f'disconnect={disconnect} final_identity_readback_live={len(live)}', flush=True)
        if live:
            raise RuntimeError('recorded process identities remain live; runtime retained at ' + str(runtime))
        ledger = json.loads((runtime / 'owned-process-ledger.json').read_text()) if (runtime / 'owned-process-ledger.json').exists() else {}
        closed_records = records_closed(CUSTODY_RECORDS)
        normal_success = client_status == 0 and control_case is None
        clean_success = (normal_success
                         and ledger.get('observed_identity_readback_complete') is True
                         and closed_records)
        absence = reader_module.candidate_absence(reader, runtime,
                                                    min(readback_deadline, time.monotonic() + 10))
        groups = {r['pgid'] for r in CUSTODY_RECORDS}
        groups_absent_observations = 0
        for observation in range(2):
            rows = reader.complete_listing(min(readback_deadline, time.monotonic() + 5))
            if any(row.get('pgid') in groups for row in rows):
                raise RuntimeError('owned process group remains during final custody readback')
            owned_pids = ({proc.pid} if proc is not None else set()) | {pid for record in CUSTODY_RECORDS
                                      for pid in (record.get('command_pid'), record.get('anchor_pid')) if pid}
            if any(row.get('pid') in owned_pids for row in rows):
                raise RuntimeError('recorded command/anchor PID remains during final custody readback')
            groups_absent_observations += 1
        if control_case is not None:
            clean_success = control_finalization_complete(
                control_case, CUSTODY_RECORDS, ledger, absence, live,
                groups_absent_observations, disconnect, client_status, command_status)
        elif not clean_success:
            clean_success = require_complete_custody(False, disconnect, client_status, CUSTODY_RECORDS)
        receipt = runtime / 'custody-receipt.json'
        receipt.write_text(json.dumps({'schema': 1, 'control_case': control_case,
            'commands': CUSTODY_RECORDS,
            'client_status': client_status, 'disconnect': disconnect,
            'client_pid': None if proc is None else proc.pid,
            'command_status': command_status,
            'identity_ledger': ledger,
            'candidate_absence': absence, 'groups_absent_observations': groups_absent_observations,
            'runtime_device': identity.st_dev, 'runtime_inode': identity.st_ino,
            'complete': clean_success}, sort_keys=True, indent=2) + '\n')
        receipt_export = Path(os.environ['RHAI_OVERHEAD_LOG_BASE'] + '.custody.json')
        with receipt_export.open('xb') as exported:
            exported.write(receipt.read_bytes())
        current = runtime.lstat()
        if runtime.is_symlink() or (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise RuntimeError('runtime identity changed; refusing removal: ' + str(runtime))
        shutil.rmtree(runtime)
        if runtime.exists() or runtime.is_symlink():
            raise RuntimeError('runtime cleanup readback failed: ' + str(runtime))
        return 0 if clean_success else 1
    except BaseException:
        # On uncertainty retain exact runtime and all command/custody evidence.
        raise
    finally:
        if proc is not None and proc.returncode is None:
            try:
                # This is the exact, unreaped direct child and the RPC client
                # has no process-spawning API. Its EOF makes the adapter close
                # active command groups before the runtime can be accepted.
                client_status = terminate_and_reap_client(proc, closure_deadline)
                print(f'client_direct_child_terminated_and_reaped status={client_status}', flush=True)
            except BaseException as cleanup_error:
                print(f'client_direct_child_reap_incomplete={type(cleanup_error).__name__}: {cleanup_error} '
                      f'runtime_retained=true path={runtime}', flush=True)
        if conn is not None:
            conn.close()
        if controller is not None:
            controller.close()
        controller_server.close()
        server.close()
        for sig, handler in old.items(): signal.signal(sig, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)


if __name__ == '__main__':
    sys.exit(main())
