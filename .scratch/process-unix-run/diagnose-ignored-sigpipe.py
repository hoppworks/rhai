import os
import subprocess
from pathlib import Path

lines = []
for label, argv in [
    ('printf_with_ignored_sigpipe', ['/bin/sh', '-c', "trap '' PIPE; /usr/bin/printf x"]),
    ('python_os_write_with_ignored_sigpipe', ['/bin/sh', '-c', "trap '' PIPE; /usr/bin/python3 -c \"import os; os.write(1, b'x')\""]),
]:
    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    try:
        proc = subprocess.run(argv, stdout=write_fd, stderr=subprocess.PIPE, pass_fds=(write_fd,), timeout=5)
        lines.append(f'{label}: returncode={proc.returncode} stderr={proc.stderr.decode(errors="replace")!r}')
    finally:
        os.close(write_fd)
Path('.scratch/process-unix-run/evidence/ignored-sigpipe-diagnostic.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
