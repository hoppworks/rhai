from pathlib import Path
import os
import re
import sys
evidence=Path(sys.argv[1])
log=(evidence/'green.log').read_text()
rows=re.findall(r'managed-scope-setup operation=(run|spawn) child_pid=([0-9]+) failure_point=KernelSetpgidDenial pid=ESRCH group=ESRCH reservation=retired marker=absent', log)
assert len(rows)==2 and {name for name,_ in rows}=={'run','spawn'}, rows
for operation, raw in rows:
    pid=int(raw)
    for label, probe in [('pid',lambda: os.kill(pid,0)), ('group',lambda: os.killpg(pid,0))]:
        try:
            probe()
        except ProcessLookupError:
            continue
        raise AssertionError(f'{operation} {label} {pid} still exists')
    print(f'operation={operation} pid={pid} pid_absent=true group_absent=true')
