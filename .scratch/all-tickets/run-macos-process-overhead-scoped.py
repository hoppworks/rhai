#!/usr/bin/env python3
"""Narrow runtime custodian for the macOS overhead source harness."""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def read_live_identities(runtime, timeout=5):
    ledger_path = runtime / 'owned-process-ledger.json'
    if not ledger_path.is_file() or ledger_path.is_symlink():
        raise RuntimeError('missing or invalid process identity ledger; runtime retained')
    ledger = json.loads(ledger_path.read_text())
    rows = ledger.get('identities')
    if type(rows) is not list:
        raise RuntimeError('invalid process identity ledger; runtime retained')
    if ledger.get('observed_identity_readback_complete') is not True:
        if ledger.get('custody_state') == 'no-process-started':
            return []
        raise RuntimeError('process custody was interrupted before final identity readback; runtime retained')
    if timeout <= 0:
        raise RuntimeError('no scoped time remains for final process identity readback; runtime retained')
    result = subprocess.run(
        ['ps', '-axo', 'pid=,ppid=,pgid=,rss=,state=,lstart='],
        capture_output=True, text=True, timeout=min(5, timeout), check=False,
    )
    if result.returncode:
        raise RuntimeError('process identity readback failed; runtime retained')
    live = set()
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 5)
        if len(fields) != 6:
            raise RuntimeError('malformed final process snapshot; runtime retained')
        pid = int(fields[0])
        start = fields[5]
        live.add((pid, start))
    return [row for row in rows if (row.get('pid'), row.get('start')) in live]


def main():
    if len(sys.argv) != 3 or sys.argv[1] != '--timeout':
        raise SystemExit('usage: run-macos-process-overhead-scoped.py --timeout SECONDS')
    timeout = float(sys.argv[2])
    if timeout <= 0 or timeout > 585:
        raise SystemExit('timeout must be positive and at most 585 seconds')
    runtime = Path(tempfile.mkdtemp(prefix='agent-build-'))
    identity = runtime.lstat()
    (runtime / 'tmp').mkdir()
    env = dict(os.environ, AGENT_RUNTIME_DIR=str(runtime))
    env.update({key: str(runtime / 'tmp') for key in ('TMPDIR', 'TMP', 'TEMP')})
    repo = Path('/Users/hoppworks/projects/rhai-all-tickets')
    driver = repo / '.scratch/all-tickets/macos-process-overhead.py'
    print(f'runtime_path={runtime}', flush=True)
    print(f'custodian_pid={os.getpid()} driver_path={driver}', flush=True)
    proc = None
    requested_signal = None

    def forward(signum, _frame):
        nonlocal requested_signal
        requested_signal = signum
        if proc is not None and proc.poll() is None:
            proc.send_signal(signum)  # Exact direct driver child only.

    old = {sig: signal.signal(sig, forward) for sig in (signal.SIGINT, signal.SIGTERM)}
    if not callable(getattr(signal, 'pthread_sigmask', None)):
        raise RuntimeError('cannot safely block interruption across exact driver child registration')
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    try:
        proc = subprocess.Popen([sys.executable, str(driver)], env=env, start_new_session=True)
    except BaseException:
        for sig, handler in old.items():
            signal.signal(sig, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        raise
    signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
    deadline = time.monotonic() + timeout
    # Reserve five seconds for exact-driver cancellation and five for final
    # identity readback within the scoped outer deadline.
    stop_deadline = deadline - 10
    cleanup_deadline = None
    try:
        while proc.poll() is None:
            now = time.monotonic()
            if requested_signal is None and now >= stop_deadline:
                requested_signal = signal.SIGTERM
                cleanup_deadline = deadline
                print('custodian_timeout=true signal=SIGTERM exact_driver=true', flush=True)
                proc.send_signal(signal.SIGTERM)
            if requested_signal is not None and proc.poll() is None:
                if cleanup_deadline is None:
                    cleanup_deadline = min(deadline, now + 5)
                try:
                    proc.wait(timeout=max(0, cleanup_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    print('driver_cancellation_deadline_exceeded exact_driver_kill=true runtime_retained=true', flush=True)
                    proc.kill()
                    try:
                        proc.wait(timeout=max(0, deadline - time.monotonic()))
                    except subprocess.TimeoutExpired as exc:
                        raise RuntimeError('exact driver remains unreaped; runtime retained at ' + str(runtime)) from exc
                break
            time.sleep(0.05)
        status = proc.wait()
        remaining = deadline - time.monotonic()
        live = read_live_identities(runtime, timeout=remaining)
        print(f'driver_status={status} final_identity_readback_live={len(live)}', flush=True)
        if live:
            print('incomplete_cleanup_live_identities=' + repr(live), flush=True)
            raise RuntimeError('recorded process identities remain live; runtime retained at ' + str(runtime))
        if requested_signal is not None:
            raise RuntimeError(f'driver interrupted by signal {requested_signal}; runtime retained at {runtime}')
        current = runtime.lstat()
        if runtime.is_symlink() or (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise RuntimeError('runtime identity changed; refusing removal: ' + str(runtime))
        shutil.rmtree(runtime)
        if runtime.exists() or runtime.is_symlink():
            raise RuntimeError('runtime cleanup readback failed: ' + str(runtime))
        return status
    except BaseException:
        # Keep the exact runtime if process custody or identity readback is uncertain.
        raise
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)


if __name__ == '__main__':
    sys.exit(main())
