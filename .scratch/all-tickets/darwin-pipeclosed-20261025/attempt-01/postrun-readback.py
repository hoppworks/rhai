from pathlib import Path
import errno
import os
import re

attempt = Path(__file__).resolve().parent
evidence = attempt / 'evidence'
scope = Path('/Users/hoppworks/.local/share/agent-builds/rhai/darwin-pipeclosed-20261025-01')
rows = []
counts = {'flows': 0, 'pid_checks': 0, 'managed_group_checks': 0}

def absent(identity, group=False):
    try:
        (os.killpg if group else os.kill)(identity, 0)
    except OSError as error:
        if error.errno == errno.ESRCH:
            return True
        raise
    return False

for log in sorted(evidence.glob('*.log')):
    if log.name == 'run-scoped.log':
        continue
    text = log.read_text()
    returned = re.findall(r'darwin_pipe_return scope=(DirectChild|Managed) .*?leader=(\d+) ', text)
    terminals = re.findall(r'darwin_pipe_terminal leader=(\d+) worker=(\d+) leaf=(\d+) '
                           r'all_absent=true sentinel=(\d+) sentinel_absent=true', text)
    assert len(returned) == len(terminals), (log, returned, terminals)
    expected = 2 if log.name == 'base-regression-green.log' else 1
    assert len(terminals) == expected, (log, terminals)
    for (kind, leader), terminal in zip(returned, terminals):
        assert leader == terminal[0], (log, leader, terminal)
        counts['flows'] += 1
        for pid in map(int, terminal):
            value = absent(pid)
            rows.append(f'{log.name}: scope={kind} pid={pid} absent={value}')
            assert value, rows[-1]
            counts['pid_checks'] += 1
        if kind == 'Managed':
            value = absent(int(leader), True)
            rows.append(f'{log.name}: managed_pgid={leader} absent={value}')
            assert value, rows[-1]
            counts['managed_group_checks'] += 1
assert counts == {'flows': 9, 'pid_checks': 36, 'managed_group_checks': 4}, counts
(evidence / 'post-run-readback.txt').write_text('\n'.join(rows) + f'\ncounts={counts}\n')
assert scope.is_absolute() and not scope.is_symlink()
assert scope.stat().st_uid == os.getuid()
assert not list(scope.iterdir()), scope
scope.rmdir()
(evidence / 'cleanup-status.txt').write_text(f'scope={scope}\nscope_absent={not scope.exists()}\n'
                                           'private runtime removed; no retained build/cache\n')
print(f'Independent readback: {counts}; exact empty scope retired.')
