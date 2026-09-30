#!/usr/bin/env python3
"""Frozen native macOS sys feature proof. Run only through run_scoped.py."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path('/Users/hoppworks/projects/rhai-macos-sys-release-features')
LOCK = pathlib.Path('/Users/hoppworks/projects/rhai-all-tickets/.scratch/optional-msrv-proof/evidence/Cargo.lock')
EXPECTED_LOCK = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
REV = 'efddae9e7a7b18f86d4ff1901ae7c28b4c22fc9f'
OUT = ROOT / '.scratch/macos-sys-release-evidence'
RUNTIME = pathlib.Path(os.environ['AGENT_RUNTIME_DIR'])
SOURCE = RUNTIME / 'source'
TARGET = RUNTIME / 'target'
CONTROL = 'test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving'
ROWS = [
    ('baseline', 'testing-environ,sys'),
    ('sync', 'testing-environ,sys,sync'),
    ('no-index', 'testing-environ,sys,no_index'),
    ('metadata-serde', 'testing-environ,sys,metadata,serde'),
    ('only-i32-no-float', 'testing-environ,sys,only_i32,no_float'),
    ('unchecked', 'testing-environ,sys,unchecked'),
    ('no-index-sync-metadata', 'testing-environ,sys,no_index,sync,metadata'),
    ('f32-float', 'testing-environ,sys,f32_float'),
]
TARGETS = ('sys_policy', 'sys_env', 'sys_fs')
OUT.mkdir(parents=True, exist_ok=True)
HARD_KIB = 2 * 1024 * 1024
PREEMPT_KIB = 1536 * 1024
DEADLINE = 1790799540  # 2026-09-30T17:39:00Z
active = [None]
sample_stop = threading.Event()
sample_peaks = {'storage_kib': 0, 'descendants': 0}


def emit(s):
    print(s, flush=True)


def identity(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'pid=,ppid=,pgid=,lstart=,command='],
                            text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else 'missing'


def identity_record(pid):
    raw = identity(pid)
    if raw == 'missing':
        return {'pid': pid, 'missing': True}
    fields = raw.split(None, 8)
    return {'pid': fields[0], 'ppid': fields[1], 'pgid': fields[2],
            'start': ' '.join(fields[3:8]), 'command': fields[8] if len(fields) > 8 else ''}


def ancestry():
    table = {}
    for line in subprocess.check_output(['ps', '-axo', 'pid=,ppid=,pgid=,lstart=,command='], text=True).splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) == 4:
            table[int(fields[0])] = (int(fields[1]), fields[2], fields[3])
    chain, pid = [], os.getpid()
    while pid in table:
        ppid, pgid, cmd = table[pid]
        chain.append((pid, ppid, pgid, cmd))
        if ppid == pid:
            break
        pid = ppid
    return chain


def sample_resources():
    with (OUT / 'resource-samples.tsv').open('w', buffering=1) as storage, (OUT / 'process-samples.tsv').open('w', buffering=1) as processes:
        storage.write('utc_epoch\tsampled_runtime_kib\n')
        processes.write('utc_epoch\towned_descendants\n')
        while not sample_stop.wait(1):
            try:
                size = int(subprocess.check_output(['du', '-sk', str(RUNTIME)], text=True).split()[0])
                parents = {}
                for line in subprocess.check_output(['ps', '-axo', 'pid=,ppid='], text=True).splitlines():
                    fields = line.split()
                    if len(fields) >= 2:
                        parents[int(fields[0])] = int(fields[1])
                found, todo = set(), [os.getpid()]
                while todo:
                    parent = todo.pop()
                    children = [pid for pid, ppid in parents.items() if ppid == parent and pid not in found]
                    found.update(children)
                    todo.extend(children)
                count = len(found)
            except Exception as exc:
                reason, status = f'sampler failed closed: {type(exc).__name__}: {exc}', 89
            else:
                reason, status = None, 0
                sample_peaks['storage_kib'] = max(sample_peaks['storage_kib'], size)
                sample_peaks['descendants'] = max(sample_peaks['descendants'], count)
                storage.write(f'{time.time():.3f}\t{size}\n')
                processes.write(f'{time.time():.3f}\t{count}\n')
                if size >= PREEMPT_KIB:
                    reason, status = f'preemptive sampled storage ceiling reached: {size} KiB', 86
                elif count > 16:
                    reason, status = f'owned descendants exceeded 16: {count}', 87
                elif time.time() >= DEADLINE:
                    reason, status = 'fixed execution deadline reached', 88
            if reason:
                (OUT / 'STOP-REASON.txt').write_text(reason + '\n')
                if active[0] is not None and active[0].poll() is None:
                    active[0].terminate()
                os._exit(status)


def run(label, args, env=None, expected=0, control=False):
    log = OUT / f'{label}.log'
    cmd = [str(cargo), 'test', '--locked', '--features', feature]
    cmd += list(args)
    emit(f'COMMAND {label}: ' + ' '.join(cmd))
    emit(f'RAW_LOG {label}: {log}')
    with log.open('w', buffering=1) as stream:
        p = subprocess.Popen(cmd, cwd=SOURCE, env=env or base_env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1)
        active[0] = p
        out = OUT / 'live-identities.txt'
        with out.open('a') as ids:
            ids.write(json.dumps({'role': 'child', 'label': label, **identity_record(p.pid)}) + '\n')
        for line in p.stdout:
            sys.stdout.write(line)
            stream.write(line)
        status = p.wait()
        active[0] = None
    emit(f'RAW_STATUS {label}: {status}')
    if status != expected:
        raise RuntimeError(f'{label}: expected exit {expected}, received {status}')
    data = log.read_text(errors='replace')
    if control and not all(s in data for s in ('running 1 test', 'test result: FAILED', 'left: "abc"', 'right: "wrong expectation"')):
        raise RuntimeError('negative control did not show exact expected assertion failure')
    if label == 'restored-baseline-control' and not ('test result: ok. 1 passed' in data):
        raise RuntimeError('restored targeted test did not pass exactly once')
    if label.startswith('fixture-'):
        counts = [int(x) for x in __import__('re').findall(r'running (\d+) tests?\b', data)]
        if not counts or max(counts) == 0:
            raise RuntimeError(f'{label}: zero/missing harness tests')
        if 'independent host readback:' not in data and label.endswith('sys_fs'):
            raise RuntimeError('sys_fs did not record independent host readback')


if subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip() != REV:
    raise RuntimeError('source revision changed after root source gate')
if subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain=v1', '--untracked-files=no'], text=True).strip():
    raise RuntimeError('tracked source tree is dirty')
lock_hash = hashlib.sha256(LOCK.read_bytes()).hexdigest()
if lock_hash != EXPECTED_LOCK:
    raise RuntimeError(f'accepted lock hash mismatch: {lock_hash}')
archive = subprocess.run(['git', '-C', str(ROOT), 'archive', REV], check=True, stdout=subprocess.PIPE)
SOURCE.mkdir()
subprocess.run(['tar', '-x', '-C', str(SOURCE)], input=archive.stdout, check=True)
shutil.copy2(LOCK, SOURCE / 'Cargo.lock')
lock_hash2 = hashlib.sha256((SOURCE / 'Cargo.lock').read_bytes()).hexdigest()
if lock_hash2 != EXPECTED_LOCK:
    raise RuntimeError('archived lock copy hash mismatch')
base_env = dict(os.environ)
base_env.update({'CARGO_HOME': str(RUNTIME / 'cargo-home'), 'CARGO_TARGET_DIR': str(TARGET),
                 'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
                 'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0',
                 'RUSTFLAGS': '-C debuginfo=0'})
for key in ('RUSTC', 'RUSTDOC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTUP_TOOLCHAIN'):
    base_env.pop(key, None)
cargo = shutil.which('cargo')
if cargo is None or shutil.which('rustc') is None:
    raise RuntimeError('native Rust toolchain is unavailable on PATH')
OUT.joinpath('proof-limits.txt').write_text(
    'whole private allocation <= 2 GiB; 1 s du -sk sample; preempt at 1.5 GiB; '
    'max 16 owned descendants; two Cargo jobs; debug=0; incremental=0; '
    'deadline=2026-09-30T17:39:00Z\n')
sampler_thread = threading.Thread(target=sample_resources, name='private-resource-sampler', daemon=True)
sampler_thread.start()
OUT.joinpath('native-versions.txt').write_text(
    subprocess.check_output(['uname', '-a'], text=True) +
    subprocess.check_output(['rustc', '--version', '--verbose'], text=True) +
    subprocess.check_output(['cargo', '--version', '--verbose'], text=True))
OUT.joinpath('run-state.txt').write_text(
    f'source_revision={REV}\nlock_sha256={lock_hash2}\nruntime={RUNTIME}\n'
    f'native_identity={subprocess.check_output(["uname", "-sm"], text=True).strip()}\n'
    f'python_pid={os.getpid()}\nancestry={ancestry()}\n')
with OUT.joinpath('live-identities.txt').open('w') as f:
    for pid, ppid, pgid, cmd in ancestry():
        f.write(json.dumps({'role': 'runner-chain', **identity_record(pid)}) + '\n')

for row, feature in ROWS:
    emit(f'FEATURE_ROW {row}: {feature}')
    run(f'compile-{row}', ['--no-run'] + sum((['--test', t] for t in TARGETS), []))
    if row == 'baseline':
        wrong_env = dict(base_env, RHAI_FILE_READ_WRONG_EXPECTATION='1')
        run('wrong-expectation-control', ['--test', 'sys_fs', CONTROL, '--', '--exact', '--nocapture', '--test-threads=1'], env=wrong_env, expected=101, control=True)
        run('restored-baseline-control', ['--test', 'sys_fs', CONTROL, '--', '--exact', '--nocapture', '--test-threads=1'])
    for target in TARGETS:
        run(f'fixture-{row}-{target}', ['--test', target, '--', '--test-threads=1', '--nocapture'])
emit('ACCEPTED all eight native macOS package-alone sys feature rows completed')
shutil.copy2(SOURCE / 'Cargo.lock', OUT / 'Cargo.lock')
OUT.joinpath('final-lock-sha256.txt').write_text(hashlib.sha256((OUT / 'Cargo.lock').read_bytes()).hexdigest() + '\n')
sample_stop.set()
sampler_thread.join(timeout=2)
OUT.joinpath('resource-maxima.txt').write_text(
    f'sampled_storage_max_kib={sample_peaks["storage_kib"]}\n'
    f'sampled_owned_descendant_max={sample_peaks["descendants"]}\n'
    'method=1 second du -sk and ps PID/PPID ancestry; sampled maxima, not physical peaks\n')
