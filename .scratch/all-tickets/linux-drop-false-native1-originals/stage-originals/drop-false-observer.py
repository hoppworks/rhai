#!/usr/bin/env python3
"""Identity-bound callback used only while the exact test is held at its handshake."""
from __future__ import annotations
import json, os, re, subprocess, time
from pathlib import Path


def atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + f'.tmp-{os.getpid()}')
    with tmp.open('x', encoding='utf-8') as out:
        out.write(text)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)


def proc(pid: int) -> dict[str, int | str]:
    raw = Path('/proc', str(pid), 'stat').read_text(encoding='ascii')
    prefix = f'{pid} ('
    close = raw.rfind(')')
    if not raw.startswith(prefix) or close < len(prefix) or raw[close + 1:close + 2] != ' ':
        raise ValueError(f'malformed proc stat for {pid}')
    fields = raw[close + 2:].split()
    if (len(fields) < 20 or len(fields[0]) != 1 or fields[0] not in 'RSDZTtXxKWPI'
            or not all(re.fullmatch(r'-?[0-9]+', value) for value in fields[1:20])):
        raise ValueError(f'truncated or malformed proc stat for {pid}')
    state = fields[0]
    ppid, pgid, start = int(fields[1]), int(fields[2]), int(fields[19])
    if pid <= 0 or start <= 0 or pgid <= 0 or state == 'Z':
        raise ValueError(f'not a positive live identity: pid={pid} pgid={pgid} start={start} state={state}')
    return {'pid': pid, 'ppid': ppid, 'pgid': pgid, 'start_ticks': start, 'state': state}


def parse_request_bytes(raw: bytes, case: str) -> dict[str, str]:
    text = raw.decode('utf-8', errors='strict')
    fields: dict[str, str] = {}
    for token in text.split():
        if '=' not in token:
            raise ValueError(f'malformed request token: {token!r}')
        key, value = token.split('=', 1)
        if not key or key in fields:
            raise ValueError(f'duplicate/empty request key: {key!r}')
        fields[key] = value
    request_id = fields.get('request_id', '')
    test_pid = fields.get('test_pid', '')
    if (fields.get('case') != case or not re.fullmatch(rf'{case}-[1-9][0-9]*', request_id)
            or request_id != f'{case}-{test_pid}'):
        raise ValueError('request name/case/test PID binding mismatch')
    if not re.fullmatch(r'[1-9][0-9]*', test_pid):
        raise ValueError('invalid test PID')
    required = {'request_id', 'case', 'test_pid', 'test_start_ticks', 'fixture_root'}
    required |= ({'child_pid', 'child_start_ticks', 'child_pgid', 'challenge_ack', 'completion'}
                 if case == 'direct' else
                 {'sentinel_pid', 'sentinel_start_ticks', 'sentinel_pgid', 'leader_pid',
                  'leader_start_ticks', 'leader_pgid', 'worker_pid', 'worker_start_ticks', 'worker_pgid', 'leaf_pid',
                  'leaf_start_ticks', 'leaf_pgid', 'group', 'challenge_ack_count', 'challenge_ok'})
    if set(fields) != required:
        raise ValueError(f'request fields differ from exact {case} schema')
    for key in required - {'request_id', 'case', 'fixture_root', 'completion'}:
        if not re.fullmatch(r'[1-9][0-9]*', fields[key]):
            raise ValueError(f'invalid positive numeric request field: {key}')
    return fields


def observe(directory: Path, case: str, runtime: Path, done, result: dict) -> None:
    """Poll one case; on any error save it and never release the held fixture."""
    deadline = None
    result['live'] = {'complete': False, 'case': case, 'identities': {}}
    try:
        while not done.is_set() and (deadline is None or time.monotonic() < deadline):
            candidates = sorted(directory.glob('*.request'))
            if not candidates:
                time.sleep(.005)
                continue
            if len(candidates) != 1:
                raise ValueError(f'expected exactly one request, found {len(candidates)}')
            request_path = candidates[0]
            original_request = request_path.read_bytes()
            fields = parse_request_bytes(original_request, case)
            if request_path.name != fields['request_id'] + '.request':
                raise ValueError('request filename does not bind to parsed request ID')
            if deadline is None:
                deadline = time.monotonic() + 8
            root = Path(fields['fixture_root'])
            if root.is_symlink() or not root.is_dir() or not root.resolve().is_relative_to(runtime.resolve()):
                raise ValueError('fixture root is absent, symlinked, or outside this private runtime')
            host_pid = int(fields['test_pid'])
            host = proc(host_pid)
            result['live'].update({'request': fields, 'host': host, 'fixture_root': str(root.resolve())})
            cargo = result.get('cargo_process_identity')
            if not cargo or not re.fullmatch(r'[1-9][0-9]*', str(cargo.get('start_ticks', ''))):
                raise ValueError('recorded Cargo command identity is incomplete')
            cargo_live = proc(int(cargo['pid']))
            result['live']['cargo'] = cargo_live
            if (host['ppid'] != int(cargo['pid']) or int(cargo_live['start_ticks']) != int(cargo['start_ticks'])
                    or int(cargo_live['pid']) != int(cargo['pid'])):
                raise ValueError('test host parent does not bind to the live recorded Cargo PID/start identity')
            if host['start_ticks'] != int(fields['test_start_ticks']):
                raise ValueError('test host PID/start identity mismatch')
            identities: dict[str, dict] = {}
            if case == 'direct':
                if fields.get('completion') != 'false' or fields.get('challenge_ack') != '1':
                    raise ValueError('direct fixture has not proven the held challenge phase')
                identities['child'] = proc(int(fields['child_pid']))
                result['live']['identities'] = dict(identities)
                if identities['child']['pid'] == host_pid or identities['child']['ppid'] != host_pid:
                    raise ValueError('direct child identity/parent does not bind to test host')
                if identities['child']['start_ticks'] != int(fields['child_start_ticks']):
                    raise ValueError('direct child PID/start identity mismatch')
                if identities['child']['pgid'] != int(fields['child_pgid']):
                    raise ValueError('direct child PID/PGID identity mismatch')
                if not (root / 'record.challenge-ack').is_file() or (root / 'record.complete').exists():
                    raise ValueError('direct challenge/completion records disagree with request')
            elif case == 'managed':
                if fields.get('challenge_ack_count') != '3' or fields.get('challenge_ok') != '1':
                    raise ValueError('managed fixture has not proven all member challenges')
                group = int(fields['group'])
                sentinel_pid = int(fields['sentinel_pid'])
                sentinel_pgid = int(fields['sentinel_pgid'])
                identities['sentinel'] = proc(sentinel_pid)
                result['live']['identities'] = dict(identities)
                identities['leader'] = proc(int(fields['leader_pid']))
                result['live']['identities'] = dict(identities)
                identities['worker'] = proc(int(fields['worker_pid']))
                result['live']['identities'] = dict(identities)
                identities['leaf'] = proc(int(fields['leaf_pid']))
                result['live']['identities'] = dict(identities)
                for name in ('sentinel', 'leader', 'worker', 'leaf'):
                    if identities[name]['start_ticks'] != int(fields[name + '_start_ticks']):
                        raise ValueError(f'{name} PID/start identity mismatch')
                if len({host_pid, *[v['pid'] for v in identities.values()]}) != 5:
                    raise ValueError('managed host/sentinel/member PIDs are not distinct')
                if identities['sentinel']['pgid'] != sentinel_pgid or sentinel_pgid != sentinel_pid or identities['sentinel']['ppid'] != host_pid:
                    raise ValueError('sentinel identity/group mismatch')
                if (group <= 0 or group in {int(host['pgid']), sentinel_pgid}
                        or int(fields['leader_pgid']) != group or int(fields['worker_pgid']) != group or int(fields['leaf_pgid']) != group
                        or any(identities[n]['pgid'] != group for n in ('leader', 'worker', 'leaf'))
                        or int(identities['leader']['pid']) != group or identities['leader']['ppid'] != host_pid
                        or identities['worker']['ppid'] != identities['leader']['pid']
                        or identities['leaf']['ppid'] != identities['worker']['pid']):
                    raise ValueError('managed member parent/group identity mismatch')
                for name in ('ack-leader', 'ack-worker', 'ack-leaf'):
                    if not (root / name).is_file():
                        raise ValueError(f'managed challenge acknowledgement missing: {name}')
            else:
                raise ValueError('unexpected case')
            result['live'].update({'request': fields, 'host': host, 'identities': identities,
                                   'fixture_root': str(root.resolve()), 'observed_monotonic': time.monotonic()})
            if request_path.read_bytes() != original_request:
                raise ValueError('request bytes changed during observer validation')
            atomic(directory / (fields['request_id'] + '.ack'),
                   original_request.decode('utf-8', errors='strict') + 'observer_ack=true\n')
            result['live']['complete'] = True
            result['ack_written'] = True
            return
        if not done.is_set():
            raise TimeoutError('observer saw no request before bounded deadline')
    except BaseException as exc:
        result['live']['error'] = f'{type(exc).__name__}: {exc}'
        result['error'] = f'{type(exc).__name__}: {exc}'


def terminal(result: dict, case: str, evidence: Path) -> None:
    """Fresh post-command exact PID/start checks and managed group census."""
    out = evidence / f'{case}-observer-readback.json'
    partial = evidence / f'{case}-observer-readback.partial.json'
    receipt = {'case': case, 'complete': False, 'terminal_identities': [], 'groups_censused': []}
    partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    try:
        live = result.get('live')
        if not live or not result.get('ack_written'):
            raise RuntimeError(result.get('error', 'observer did not record/ack a live request'))
        receipt['live_observation'] = live
        rows = receipt['terminal_identities']
        partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        for label, expected in [('host', live['host']), *live['identities'].items()]:
            pid, start = int(expected['pid']), int(expected['start_ticks'])
            try:
                now = proc(pid)
                if int(now['start_ticks']) == start:
                    raise RuntimeError(f'owned identity remains: {label} pid={pid} start={start}')
                row = {'label': label, 'pid': pid, 'start_ticks': start,
                       'pid_reused_with_different_start': True, 'current': now}
            except FileNotFoundError:
                row = {'label': label, 'pid': pid, 'start_ticks': start, 'absent': True}
            rows.append(row)
            partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        groups = sorted({int(v['pgid']) for v in live['identities'].values()}) if case == 'managed' else []
        receipt['groups_censused'] = groups
        partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        ps = subprocess.check_output(['/bin/ps', '-e', '-o', 'pid=,pgid='], text=True, timeout=5)
        found = []
        for line in ps.splitlines():
            f = line.split()
            if len(f) != 2 or not all(x.isdecimal() for x in f):
                raise RuntimeError(f'malformed ps process census line: {line!r}')
            pid, pgid = map(int, f)
            if pgid in groups:
                found.append({'pid': pid, 'pgid': pgid})
        receipt['remaining_group_members'] = found
        partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        if found:
            raise RuntimeError(f'managed/sentinel process group remains populated: {found!r}')
        root = Path(live['fixture_root'])
        if root.exists() or root.is_symlink():
            raise RuntimeError('fixture temporary root remains after test completion')
        receipt.update({'fixture_root_absent': True, 'readback_time_monotonic': time.monotonic(), 'complete': True})
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        partial.unlink()
    except BaseException as exc:
        receipt['error'] = f'{type(exc).__name__}: {exc}'
        partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        raise

def _control_terminal_impl(stderr: str, case: str, evidence: Path) -> None:
    """Read back fixture identities emitted before the intentional assertion panic."""
    partial = evidence / f'{case}-red-terminal.partial.json'
    receipt = {'case': case, 'complete': False, 'terminal_identities': {}}
    partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    marker = 'direct_drop_after_final_client_drop ' if case == 'direct' else 'managed_drop_false_terminal '
    rows = [line.split(marker, 1)[1] for line in stderr.splitlines() if marker in line]
    if len(rows) != 1:
        raise RuntimeError(f'{case} RED lacks exactly one pre-assertion custody marker')
    fields = {}
    for token in rows[0].split():
        if '=' not in token:
            raise RuntimeError(f'malformed {case} RED custody token {token!r}')
        key, value = token.split('=', 1)
        if key in fields:
            raise RuntimeError(f'duplicate {case} RED custody key {key}')
        fields[key] = value
    root = Path(fields.get('fixture_root', ''))
    expected = {'host_pid', 'host_start_ticks', 'fixture_root'}
    expected |= ({'child_pid', 'child_start_ticks', 'child_ppid', 'child_pgid', 'alive', 'challenge_ack', 'completion_exists'}
                 if case == 'direct' else
                 {'sentinel_pid', 'sentinel_start_ticks', 'sentinel_ppid', 'sentinel_pgid', 'leader_pid', 'leader_start_ticks', 'leader_ppid', 'leader_pgid',
                  'worker_pid', 'worker_start_ticks', 'worker_ppid', 'worker_pgid', 'leaf_pid', 'leaf_start_ticks', 'leaf_ppid', 'leaf_pgid', 'group', 'challenge_ack_count', 'challenge_ok'})
    receipt['marker'] = fields
    partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if set(fields) != expected or not root.is_absolute():
        raise RuntimeError(f'{case} RED custody marker schema/path mismatch')
    if case == 'direct' and (fields['alive'] != 'true' or fields['challenge_ack'] != 'true' or fields['completion_exists'] != 'false'):
        raise RuntimeError('direct RED did not capture the completed challenge before the survival assertion')
    if case == 'managed' and (fields['challenge_ack_count'] != '3' or fields['challenge_ok'] != '1'):
        raise RuntimeError('managed RED did not capture all fixture challenges before the survival assertion')
    if case == 'direct' and int(fields['child_ppid']) != int(fields['host_pid']):
        raise RuntimeError('direct RED child parent does not bind to host')
    if case == 'managed' and (int(fields['sentinel_pid']) != int(fields['sentinel_pgid']) or int(fields['group']) <= 0 or int(fields['group']) != int(fields['leader_pid']) or int(fields['group']) == int(fields['sentinel_pgid'])
            or len({int(fields[k]) for k in ('host_pid','sentinel_pid','leader_pid','worker_pid','leaf_pid')}) != 5
            or int(fields['sentinel_ppid']) != int(fields['host_pid'])
            or int(fields['leader_ppid']) != int(fields['host_pid'])
            or int(fields['worker_ppid']) != int(fields['leader_pid'])
            or int(fields['leaf_ppid']) != int(fields['worker_pid'])):
        raise RuntimeError('managed RED parent ancestry mismatch')
    identity_names = ['host'] + (['child'] if case == 'direct' else ['sentinel', 'leader', 'worker', 'leaf'])
    live = {}
    for name in identity_names:
        pid_key = 'host_pid' if name == 'host' else name + '_pid'
        start_key = 'host_start_ticks' if name == 'host' else name + '_start_ticks'
        pid, start = int(fields[pid_key]), int(fields[start_key])
        if pid <= 0 or start <= 0:
            raise RuntimeError(f'{case} RED has invalid {name} identity')
        try:
            now = proc(pid)
        except FileNotFoundError:
            live[name] = {'pid': pid, 'start_ticks': start, 'absent': True}
            receipt['terminal_identities'] = dict(live)
            partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            continue
        if int(now['start_ticks']) == start:
            raise RuntimeError(f'{case} RED exact {name} identity remains live')
        live[name] = {'pid': pid, 'start_ticks': start, 'pid_reused_with_different_start': True,
                      'current': now}
        receipt['terminal_identities'] = dict(live)
        partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    groups = [] if case == 'direct' else sorted({int(fields['sentinel_pgid']), int(fields['group'])})
    if case == 'managed':
        ps = subprocess.check_output(['/bin/ps', '-e', '-o', 'pid=,pgid='], text=True, timeout=5)
        remaining = []
        for line in ps.splitlines():
            f = line.split()
            if len(f) != 2 or not all(x.isdecimal() for x in f):
                raise RuntimeError(f'malformed managed RED group census line {line!r}')
            pid, pgid = map(int, f)
            if pgid in groups:
                remaining.append([pid, pgid])
        if remaining:
            raise RuntimeError(f'managed RED process groups remain populated: {remaining!r}')
    if root.exists() or root.is_symlink():
        raise RuntimeError(f'{case} RED fixture root remains: {root}')
    out = evidence / f'{case}-red-terminal.json'
    receipt.update({'groups_censused': groups, 'fixture_root_absent': True,
                    'readback_time_monotonic': time.monotonic(), 'complete': True})
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    partial.unlink()


def control_terminal(stderr: str, case: str, evidence: Path) -> None:
    partial = evidence / f'{case}-red-terminal.partial.json'
    try:
        _control_terminal_impl(stderr, case, evidence)
    except BaseException as exc:
        try:
            receipt = json.loads(partial.read_text(encoding='utf-8'))
        except (FileNotFoundError, ValueError):
            receipt = {'case': case, 'complete': False}
        receipt['error'] = f'{type(exc).__name__}: {exc}'
        partial.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        raise
