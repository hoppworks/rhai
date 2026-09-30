#!/usr/bin/env python3
"""Independent post-launch readback for the one f32 scoped invocation."""
import pathlib
import subprocess
import sys

OUT = pathlib.Path(__file__).resolve().parent / 'f32-followup'
state = OUT / 'run-state.txt'
if not state.is_file():
    raise SystemExit('run-state missing; cleanup custody cannot be checked')
values = dict(line.split('=', 1) for line in state.read_text().splitlines() if '=' in line)
runtime = pathlib.Path(values['runtime'])
expected_group = values['scoped_process_group']
report = [f'runtime_absent={not runtime.exists()} runtime={runtime}']
failed = runtime.exists()
snapshot = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,pgid=,lstart=,command='], text=True)
current = {}
for line in snapshot.splitlines():
    fields = line.strip().split(None, 8)
    if len(fields) >= 8:
        current[fields[0]] = (' '.join(fields[3:8]), fields[2], fields)
identities = (OUT / 'process-identities.tsv').read_text().splitlines()[1:]
unavailable = set()
known = set()
for line in identities:
    fields = line.split('\t', 5)
    if len(fields) != 6:
        raise SystemExit('malformed identity row: ' + line)
    label, pid, _ppid, _pgid, start, _command = fields
    if start == 'unavailable':
        unavailable.add(pid)
        report.append(f'{label} pid={pid} start=unavailable readback=identity-missing')
        failed = True
        continue
    known.add(pid)
    found = current.get(pid)
    if found is None:
        result = 'absent'
    elif found[0] != start:
        result = 'PID-reused'
    else:
        result = 'same-process-live'
        failed = True
    report.append(f'{label} pid={pid} start={start} readback={result}')
launcher_rows = (OUT / 'launcher-identities.tsv').read_text().splitlines()[1:]
for line in launcher_rows:
    label, identity = line.split('\t', 1)
    fields = identity.split(None, 8)
    pid = fields[0]
    start = ' '.join(fields[3:8])
    found = current.get(pid)
    result = 'absent' if found is None else ('PID-reused' if found[0] != start else 'same-process-live')
    report.append(f'{label} pid={pid} start={start} readback={result}')
    if result == 'same-process-live':
        failed = True
members = [pid for pid, (_start, pgid, _fields) in current.items() if pgid == expected_group]
report.append(f'scoped_pgid={expected_group} remaining_members={members}')
report.append(f'identity_pid_counts=known:{len(known)} unavailable:{len(unavailable)}')
if members:
    failed = True
(OUT / 'cleanup-readback.txt').write_text('\n'.join(report) + '\n')
print('\n'.join(report[-len(launcher_rows)-3:]))
print(f'unique known PID identities={len(known)}; unavailable unique PIDs={len(unavailable)}')
if failed:
    raise SystemExit('runtime/PID/start/group cleanup readback failed')
