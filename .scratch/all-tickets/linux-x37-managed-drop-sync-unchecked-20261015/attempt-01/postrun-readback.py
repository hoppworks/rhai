from pathlib import Path
import os,re,sys
text=Path(sys.argv[1]).read_text(errors='replace')
start=re.search(r'managed_spawn_drop_started root=.*? sentinel_pid=(\d+) sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)',text)
assert start, 'start identity record missing'
sentinel_pid,sentinel_pgid,leader,worker,leaf,managed_pgid=map(int,start.groups())
final=re.search(r'managed_spawn_final_drop .*?all_esrch=true sentinel=(\d+) live=true',text)
cleanup=re.search(r'sentinel_cleanup pid=(\d+) esrch=true',text)
assert final and int(final.group(1))==sentinel_pid, 'sentinel not live at managed final-drop boundary'
assert cleanup and int(cleanup.group(1))==sentinel_pid, 'exact sentinel cleanup missing'
assert sentinel_pgid==sentinel_pid
rows=[('leader',leader),('worker',worker),('leaf',leaf),('sentinel',sentinel_pid)]
for name,pid in rows:
    try: os.kill(pid,0)
    except ProcessLookupError: pass
    else: raise AssertionError(f'{name} pid {pid} still exists')
for name,pgid in [('managed_group',managed_pgid),('sentinel_group',sentinel_pgid)]:
    try: os.killpg(pgid,0)
    except ProcessLookupError: pass
    else: raise AssertionError(f'{name} pgid {pgid} still exists')
print(f'managed leader={leader} worker={worker} leaf={leaf} pgid={managed_pgid} absent=true')
print(f'sentinel pid={sentinel_pid} pgid={sentinel_pgid} absent=true')
