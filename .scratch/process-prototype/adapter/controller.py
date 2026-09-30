#!/usr/bin/env python3
"""Outer exact-child owner for one bounded local custodian run."""
import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = Path(__file__).resolve().parent
CASE_DEADLINE = 30.0
CHILD_REAP_DEADLINE = 5.0
OUTER_CLEANUP_DEADLINE = 10.0
OUTER_DEADLINE = CASE_DEADLINE + CHILD_REAP_DEADLINE + OUTER_CLEANUP_DEADLINE


def quiescent_readback(runtime, identity, custodian_pid):
    path = runtime / 'custody-quiescent.json'
    data = json.loads(path.read_text())
    st = runtime.lstat()
    if runtime.is_symlink() or (st.st_dev, st.st_ino) != (identity.st_dev, identity.st_ino):
        raise RuntimeError('runtime identity mismatch; refusing custodian fallback')
    if data.get('custodian_pid') != custodian_pid or data.get('runtime_identity') != [identity.st_dev, identity.st_ino]:
        raise RuntimeError('quiescence authority mismatch; refusing custodian fallback')
    children = data.get('children', {})
    if children.get('cleanup_errors') or data.get('cleanup_errors'):
        raise RuntimeError('cleanup errors in quiescence record; refusing custodian fallback')
    if data.get('custodian_fds_closed') is not True:
        raise RuntimeError('custodian descriptors not confirmed closed; refusing fallback')
    for role in ('runner', 'leader', 'anchor', 'sentinel'):
        if type(children.get(role, {}).get('wait_status')) is not int:
            raise RuntimeError('incomplete quiescence readback; refusing custodian fallback')
    if 'cleanup_errors' in data or 'error' in data:
        raise RuntimeError('cleanup errors in quiescence record; refusing custodian fallback')
    holder = children.get('holder')
    if holder is not None and type(holder.get('wait_status')) is not int:
        raise RuntimeError('holder not reaped; refusing custodian fallback')
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--binary', required=True)
    ap.add_argument('--control', choices=('normal', 'cancel', 'assert', 'timeout', 'kill'), default='normal')
    args = ap.parse_args()
    runs = ROOT / 'runs'
    runs.mkdir(exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix='custody-run-', dir=runs))
    (runtime / 'tmp').mkdir()
    identity = runtime.lstat()
    cmd = [sys.executable, str(ADAPTER / 'custodian.py'), '--runtime', str(runtime),
           '--runner', str(ADAPTER / 'run_scoped.py'), '--binary', args.binary,
           '--control', args.control]
    proc = subprocess.Popen(cmd, close_fds=True, start_new_session=True)
    deadline = time.monotonic() + OUTER_DEADLINE
    try:
        try:
            status = proc.wait(timeout=max(0.0, deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            # The outer owner never interrupts the sole child reaper until an
            # identity-checked receipt proves every process and descriptor quiescent.
            try:
                quiescent_readback(runtime, identity, proc.pid)
            except BaseException as exc:
                failure = {'custodian_pid': proc.pid, 'runtime': str(runtime),
                           'runtime_identity': [identity.st_dev, identity.st_ino],
                           'outcome': 'incomplete_cleanup_retained', 'reason': repr(exc)}
                evidence = ROOT / 'evidence' / ('outer-incomplete-' + str(proc.pid) + '.json')
                temporary = evidence.with_suffix('.tmp')
                temporary.write_text(json.dumps(failure, sort_keys=True) + '\n')
                os.replace(temporary, evidence)
                if json.loads(evidence.read_text()) != failure:
                    raise RuntimeError('outer incomplete-cleanup evidence readback failed') from exc
                print('incomplete cleanup: exact custodian PID ' + str(proc.pid) +
                      ' remains the resource owner; retained runtime ' + str(runtime) +
                      '; readback ' + str(evidence), file=sys.stderr)
                raise TimeoutError('outer bound expired; runtime and live custodian retained') from exc
            os.kill(proc.pid, 9)
            proc.wait(timeout=CHILD_REAP_DEADLINE)
            raise TimeoutError('custodian exceeded its outer bound after quiescence; runtime retained at ' + str(runtime))
        receipt = runtime / 'receipt.json'
        data = json.loads(receipt.read_text())
        if status != 0 or data.get('runtime_identity') != [identity.st_dev, identity.st_ino]:
            raise RuntimeError('custodian status or runtime identity failed; retained ' + str(runtime))
        tmp_st = (runtime / 'tmp').lstat()
        if stat.S_ISLNK(tmp_st.st_mode) or [tmp_st.st_dev, tmp_st.st_ino] != data.get('tmp_identity'):
            raise RuntimeError('runtime tmp identity mismatch; retained ' + str(runtime))
        evidence = ROOT / 'evidence' / ('custodian-' + str(proc.pid) + '-' + args.control + '.json')
        temporary = evidence.with_suffix('.tmp')
        temporary.write_text(json.dumps(data, sort_keys=True) + '\n')
        os.replace(temporary, evidence)
        if json.loads(evidence.read_text()) != data:
            raise RuntimeError('exported evidence readback failed; retained ' + str(runtime))
        current = runtime.lstat()
        if runtime.is_symlink() or (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise RuntimeError('runtime identity changed; refusing removal: ' + str(runtime))
        shutil.rmtree(runtime)
        if runtime.exists() or runtime.is_symlink():
            raise RuntimeError('runtime removal readback failed; inspect ' + str(runtime))
        return 0
    except BaseException:
        # Preserve the exact path and receipt whenever bounded cleanup/readback failed.
        raise


if __name__ == '__main__':
    sys.exit(main())
