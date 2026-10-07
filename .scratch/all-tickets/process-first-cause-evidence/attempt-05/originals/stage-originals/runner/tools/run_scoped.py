#!/usr/bin/env python3
"""Run a build/verification command with automatic cleanup of its private runtime."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agentskills import pyguard
pyguard.ensure()

import argparse
import os
import shutil
import select
import signal
import time
import subprocess
import tempfile


class Stopped(BaseException):
    def __init__(self, signum):
        self.signum = signum


def supervisor(fd, command):
    # Keep the group leader alive until cleanup, so a reused PID cannot point
    # termination at another Session. Caught handlers reset on child exec.
    signal.signal(signal.SIGTERM, lambda *_: None)
    signal.signal(signal.SIGINT, lambda *_: None)
    os.set_inheritable(fd, False)
    try:
        code = subprocess.run(command).returncode
    except OSError as exc:
        print('run_scoped: ' + str(exc), file=sys.stderr)
        code = 127
    os.write(fd, (str(code) + '\n').encode())
    os.close(fd)
    while True:
        signal.pause()


def run_command(command, env, timeout):
    read_fd, write_fd = os.pipe()
    proc = None
    old_handlers = {}
    def stop(signum, _frame):
        raise Stopped(signum)
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            old_handlers[signum] = signal.signal(signum, stop)
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), '_supervise', str(write_fd), *command],
            env=env, start_new_session=True, pass_fds=(write_fd,))
        os.close(write_fd)
        write_fd = None
        deadline = time.monotonic() + timeout if timeout is not None else None
        while True:
            if deadline is not None and time.monotonic() >= deadline:
                print('run_scoped: command timed out', file=sys.stderr)
                return 124
            if select.select([read_fd], [], [], 0.1)[0]:
                data = os.read(read_fd, 64)
                if not data:
                    print('run_scoped: supervisor ended without a result', file=sys.stderr)
                    return 125
                code = int(data.strip())
                return code if code >= 0 else 128 - code
    except Stopped as exc:
        return 128 + exc.signum
    finally:
        # Ignore additional interrupts during the short owned-group cleanup.
        for signum in old_handlers:
            signal.signal(signum, signal.SIG_IGN)
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            time.sleep(0.2)
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('provide a command after --')
    if args.timeout is not None and args.timeout <= 0:
        parser.error('timeout must be positive')
    root = Path(tempfile.mkdtemp(prefix='agent-build-'))
    identity = root.stat()
    env = dict(os.environ, AGENT_RUNTIME_DIR=str(root))
    try:
        (root / 'tmp').mkdir()
        env.update({key: str(root / 'tmp') for key in ('TMPDIR', 'TMP', 'TEMP')})
        return run_command(command, env, args.timeout)
    finally:
        current = root.lstat()
        if root.is_symlink() or (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise RuntimeError('private runtime replaced; refusing cleanup: ' + str(root))
        shutil.rmtree(root)


if __name__ == '__main__':
    if sys.argv[1:2] == ['_supervise']:
        supervisor(int(sys.argv[2]), sys.argv[3:])
    else:
        sys.exit(main())
