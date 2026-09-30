#!/usr/bin/env python3
"""Independent post-run PID/start-time, process-group and runtime readback."""
import pathlib
import subprocess
import sys

out = pathlib.Path(__file__).resolve().parent / 'followup'
state = out / 'run-state.txt'
if not state.is_file():
    raise SystemExit('run-state missing; custody cannot be read back')
values = dict(line.split('=', 1) for line in state.read_text().splitlines() if '=' in line)
runtime = pathlib.Path(values['runtime'])
expected_pgid = values['scoped_process_group']
rows = (out / 'process-identities.tsv').read_text().splitlines()[1:]
report = [f'runtime_absent={not runtime.exists()} runtime={runtime}']
failed = runtime.exists()
ps_output = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,pgid=,lstart=,command='], text=True)
current_rows = {}
for line in ps_output.splitlines():
    parts = line.strip().split(None, 8)
    if len(parts) >= 8:
        current_rows[parts[0]] = (parts, ' '.join(parts[3:8]))
for row in rows:
    fields = row.split('\t', 5)
    if len(fields) != 6:
        raise SystemExit('malformed process identity row: '+row)
    label, pid, _ppid, _pgid, start, _command = fields
    if start == 'unavailable':
        failed = True
        report.append(f'{label} pid={pid} start=unavailable readback=identity-missing')
        continue
    current = current_rows.get(pid)
    if current is None:
        status = 'absent'
    else:
        parts, current_start = current
        status = 'PID-reused' if current_start != start else 'same-process-live'
        if status == 'same-process-live':
            failed = True
    report.append(f'{label} pid={pid} start={start} readback={status}')
launch_rows = (out / 'launcher-identities.tsv').read_text().splitlines()[1:]
for row in launch_rows:
    label, identity = row.split('\t', 1)
    fields = identity.split(None, 8)
    pid = fields[0]
    start = ' '.join(fields[3:8])
    if start == 'unavailable':
        failed = True
        report.append(f'{label} pid={pid} start=unavailable readback=identity-missing')
        continue
    current = current_rows.get(pid)
    if current:
        parts, current_start = current
        if current_start == start:
            failed = True
            report.append(f'{label} pid={pid} start={start} readback=same-process-live')
        else:
            report.append(f'{label} pid={pid} start={start} readback=PID-reused')
    else:
        report.append(f'{label} pid={pid} start={start} readback=absent')
groups = subprocess.run(['ps', '-axo', 'pid=,pgid='], text=True, capture_output=True, check=True)
members = [line.split()[0] for line in groups.stdout.splitlines()
           if len(line.split()) == 2 and line.split()[1] == expected_pgid]
report.append(f'scoped_pgid={expected_pgid} remaining_members={members}')
if members:
    failed = True
(out / 'cleanup-readback.txt').write_text('\n'.join(report)+'\n')
print('\n'.join(report))
if failed:
    raise SystemExit('runtime/PID/start/group cleanup readback failed')
