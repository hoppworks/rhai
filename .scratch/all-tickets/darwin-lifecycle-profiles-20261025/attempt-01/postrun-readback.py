from pathlib import Path
import errno
import os
import re

attempt = Path(__file__).resolve().parent
evidence = attempt / 'evidence'
scope = Path('/Users/hoppworks/.local/share/agent-builds/rhai/darwin-lifecycle-profiles-20261025-01')
counts = {'kill': 0, 'drop': 0, 'capture': 0, 'pid_checks': 0, 'group_checks': 0}
rows = []

def absent(identity, group=False):
    try:
        (os.killpg if group else os.kill)(identity, 0)
    except OSError as error:
        if error.errno == errno.ESRCH:
            return True
        raise
    return False

for log in sorted(evidence.glob('testing-*.log')):
    text = log.read_text()
    if 'finishes_capture_when_escaped' in log.name or 'post_reap_cancel' in log.name:
        counts['capture'] += 1
        found = re.findall(r'managed_escaped_pipe_terminal leader=Some\((\d+)\) leader_esrch=true '
                           r'holder=Some\((\d+)\) holder_esrch=true sentinel=(\d+) sentinel_esrch=true', text)
        assert len(found) == 1, (log, found)
        pids = list(map(int, found[0]))
        groups = []
    else:
        kind = 'drop' if 'final_clone_drop' in log.name else 'kill'
        counts[kind] += 1
        marker = 'managed_spawn_drop_started' if kind == 'drop' else 'managed_spawn_kill_started'
        found = re.findall(marker + r' root=\S+ test_pid=\d+ sentinel_pid=(\d+) '
                           r'sentinel_pgid=(\d+) leader=(\d+) worker=(\d+) leaf=(\d+) group=(\d+)', text)
        assert len(found) == 1, (log, found)
        sentinel, sentinel_group, leader, worker, leaf, group = map(int, found[0])
        assert sentinel == sentinel_group and leader == group
        pids = [leader, worker, leaf, sentinel]
        groups = [group, sentinel_group]
    for pid in pids:
        value = absent(pid)
        rows.append(f'{log.name}: pid={pid} absent={value}')
        assert value, rows[-1]
        counts['pid_checks'] += 1
    for group in groups:
        value = absent(group, True)
        rows.append(f'{log.name}: pgid={group} absent={value}')
        assert value, rows[-1]
        counts['group_checks'] += 1
assert counts == {'kill': 2, 'drop': 3, 'capture': 6, 'pid_checks': 38, 'group_checks': 10}, counts
(evidence / 'post-run-readback.txt').write_text('\n'.join(rows) + f'\ncounts={counts}\n')
assert scope.is_absolute() and not scope.is_symlink()
assert scope.stat().st_uid == os.getuid()
assert not list(scope.iterdir()), scope
scope.rmdir()
(evidence / 'cleanup-status.txt').write_text(f'scope={scope}\nscope_absent={not scope.exists()}\n'
                                           'private runtime removed; no retained build/cache\n')
print(f'Independent readback: {counts}; exact empty scope retired.')
