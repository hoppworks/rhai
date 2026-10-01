import os
import re
import subprocess
import tempfile
from pathlib import Path

source = Path('src/packages/sys/process/unix.rs').read_text()
match = re.search(r'let probe_script = r#"(.*?)"#;', source, re.S)
assert match
script = match.group(1)
with tempfile.TemporaryDirectory(prefix='rhai-raw-probe-') as temp:
    results = {}
    for label, target in [('stdout', 1), ('stderr', 2)]:
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        path = Path(temp) / f'{label}.result'
        env = dict(os.environ, RHAI_TEST_OWNER_PROBE_SCRIPT=script)
        command = f"trap '' PIPE; /usr/bin/python3 -c \"$RHAI_TEST_OWNER_PROBE_SCRIPT\" {label} {path}"
        kwargs = {'stdout': write_fd} if target == 1 else {'stderr': write_fd}
        try:
            proc = subprocess.run(['/bin/sh', '-c', command], env=env, pass_fds=(write_fd,), timeout=5, **kwargs)
        finally:
            os.close(write_fd)
        assert proc.returncode == 0, (label, proc.returncode)
        results[label] = path.read_text().strip()
    assert results == {'stdout': 'errno=32', 'stderr': 'errno=32'}, results
    print(f'raw_probe_closed_readers={results}')
