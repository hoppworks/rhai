from pathlib import Path
import errno
import os
import re

attempt = Path(__file__).resolve().parent
evidence = attempt / 'evidence'
scope = Path('/Users/hoppworks/.local/share/agent-builds/rhai/x36-darwin-setup-20261025-01')
rows = []
counts = {'red': 0, 'green': 0}
for log in sorted(evidence.glob('*_testing-*.log')):
    phase = log.name.split('_', 1)[0]
    identities = re.findall(
        r'managed-scope-setup operation=(\w+) child_pid=(\d+) failure_point=(\w+) '
        r'pid=ESRCH group=ESRCH reservation=retired marker=absent',
        log.read_text(),
    )
    assert len(identities) == (1 if phase == 'red' else 2), (log, identities)
    for operation, pid_text, failure in identities:
        pid = int(pid_text)
        def absent(group=False):
            try:
                (os.killpg if group else os.kill)(pid, 0)
            except OSError as error:
                if error.errno == errno.ESRCH:
                    return True
                raise
            return False
        pid_absent = absent()
        group_absent = absent(True)
        rows.append(f'{log.name}: operation={operation} failure={failure} pid={pid} '
                    f'pid_absent={pid_absent} group_absent={group_absent}')
        assert pid_absent and group_absent, rows[-1]
        counts[phase] += 1
assert counts == {'red': 4, 'green': 32}, counts
(evidence / 'post-run-readback.txt').write_text('\n'.join(rows) + f'\ncounts={counts}\n')
assert scope.is_absolute() and not scope.is_symlink()
assert scope.stat().st_uid == os.getuid()
assert not list(scope.iterdir()), scope
scope.rmdir()
(evidence / 'cleanup-status.txt').write_text(f'scope={scope}\nscope_absent={not scope.exists()}\n'
                                           'private runtime removed; no retained build/cache\n')
print(f'Independent readback: {counts}; exact empty scope retired.')
