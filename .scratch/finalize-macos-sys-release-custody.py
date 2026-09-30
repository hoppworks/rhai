#!/usr/bin/env python3
"""Read back scoped-runtime cleanup and exact recorded process identities."""
import pathlib
import json
import subprocess

repo = pathlib.Path('/Users/hoppworks/projects/rhai-macos-sys-release-features')
evidence = repo / '.scratch/macos-sys-release-evidence'
state = evidence / 'run-state.txt'
if not state.exists():
    raise SystemExit('missing run-state.txt; cleanup cannot be attested')
values = dict(line.split('=', 1) for line in state.read_text().splitlines() if '=' in line and not line.startswith('ancestry='))
runtime = pathlib.Path(values['runtime'])
report = ['run_scoped_runtime_removed=' + str(not runtime.exists())]
for line in (evidence / 'live-identities.txt').read_text().splitlines():
    fields = json.loads(line)
    recorded_pid = str(fields['pid'])
    result = subprocess.run(['ps', '-p', recorded_pid, '-o', 'pid=,ppid=,pgid=,lstart=,command='], text=True, capture_output=True)
    raw = result.stdout.strip()
    if not raw:
        verdict, current = 'absent', 'missing'
    else:
        parts = raw.split(None, 8)
        current = {'pid': parts[0], 'ppid': parts[1], 'pgid': parts[2],
                   'start': ' '.join(parts[3:8]), 'command': parts[8] if len(parts) > 8 else ''}
        same = all(str(fields.get(key, '')) == str(current.get(key, '')) for key in ('pid', 'ppid', 'pgid', 'start', 'command'))
        verdict = 'same process still live' if same else 'PID reused or identity changed'
        current = json.dumps(current, sort_keys=True)
    report.append(f"role={fields.get('role')} label={fields.get('label', '')} pid={recorded_pid} cleanup={verdict} current={current}")
(evidence / 'cleanup-readback.txt').write_text('\n'.join(report) + '\n')
print('\n'.join(report))
if runtime.exists():
    raise SystemExit('private runtime remains after wrapper exit')
