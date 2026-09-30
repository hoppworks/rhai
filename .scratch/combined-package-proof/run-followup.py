#!/usr/bin/env python3
"""Bounded native macOS combined sys/net follow-up; always run via run_scoped."""
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / '.scratch/combined-package-proof/followup'
RUNTIME = pathlib.Path(os.environ['AGENT_RUNTIME_DIR'])
SOURCE = RUNTIME / 'source'
TARGET = RUNTIME / 'target'
CARGO_HOME = RUNTIME / 'cargo-home'
DEADLINE = datetime(2026, 9, 30, 18, 19, 18, tzinfo=timezone.utc).timestamp()
PREEMPT_KIB = 1536 * 1024
HARD_KIB = 2 * 1024 * 1024
MAX_DESCENDANTS = 16
TEST_NAME = 'sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors'
PROFILES = [
    ('baseline', 'testing-environ,sys,net'),
    ('sync', 'testing-environ,sys,net,sync'),
    ('no-index', 'testing-environ,sys,net,no_index'),
    ('metadata-serde', 'testing-environ,sys,net,metadata,serde'),
    ('only-i32-no-float', 'testing-environ,sys,net,only_i32,no_float'),
    ('unchecked', 'testing-environ,sys,net,unchecked'),
    ('no-index-sync-metadata', 'testing-environ,sys,net,no_index,sync,metadata'),
    ('f32-float', 'testing-environ,sys,net,f32_float'),
]
ALL_TARGETS = ('combined_sys_net', 'sys_env', 'sys_fs', 'sys_policy',
               'net_connect', 'net_listen', 'net_reads', 'net_writes')
active = [None]
sample_stop = threading.Event()
peaks = {'storage_kib': 0, 'descendants': 0}
identities = {}


def emit(value):
    print(value, flush=True)


def ps_rows():
    result = subprocess.run(['ps', '-axo', 'pid=,ppid=,pgid=,lstart=,command='],
                            text=True, capture_output=True, check=True)
    rows = {}
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 8)
        if len(fields) >= 8:
            rows[int(fields[0])] = {
                'pid': fields[0], 'ppid': fields[1], 'pgid': fields[2],
                'start': ' '.join(fields[3:8]),
                'command': fields[8] if len(fields) > 8 else '',
            }
    return rows


def record_identity(label, pid):
    row = ps_rows().get(int(pid))
    if row is None:
        row = {'pid': str(pid), 'ppid': 'unavailable', 'pgid': 'unavailable',
               'start': 'unavailable', 'command': 'unavailable'}
    row = dict(row, label=label)
    identities[(row['pid'], row['start'])] = row
    with (OUT / 'process-identities.tsv').open('a') as stream:
        stream.write('\t'.join(row[k] for k in ('label', 'pid', 'ppid', 'pgid', 'start', 'command')) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def descendants(root_pid, rows):
    result, frontier = set(), [root_pid]
    while frontier:
        parent = frontier.pop()
        for pid, row in rows.items():
            if int(row['ppid']) == parent and pid not in result:
                result.add(pid)
                frontier.append(pid)
    return result


def stop(reason, status):
    (OUT / 'STOP-REASON.txt').write_text(reason + '\n')
    emit('STOP: ' + reason)
    proc = active[0]
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
    os._exit(status)  # run_scoped owns and reaps the complete process group.


def sampled_size():
    result = subprocess.run(['du', '-sk', str(RUNTIME)], text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f'du failed closed ({result.returncode}): {result.stderr.strip()}')
    try:
        return int(result.stdout.split()[0])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f'du returned invalid size: {result.stdout!r}') from exc


def sampler():
    with (OUT / 'storage-samples.tsv').open('w', buffering=1) as storage, \
         (OUT / 'process-samples.tsv').open('w', buffering=1) as processes:
        storage.write('utc_epoch\tsampled_runtime_kib\n')
        processes.write('utc_epoch\towned_descendants\tgroup_pids\n')
        while not sample_stop.wait(1):
            try:
                size = sampled_size()
                rows = ps_rows()
                child_pids = descendants(os.getpid(), rows)
                pgid = os.getpgrp()
                group_pids = sorted(pid for pid, row in rows.items() if int(row['pgid']) == pgid)
            except Exception as exc:
                stop(f'resource/process sampler failed closed: {type(exc).__name__}: {exc}', 89)
            peaks['storage_kib'] = max(peaks['storage_kib'], size)
            peaks['descendants'] = max(peaks['descendants'], len(child_pids))
            stamp = f'{time.time():.3f}'
            storage.write(f'{stamp}\t{size}\n')
            processes.write(f'{stamp}\t{len(child_pids)}\t{",".join(map(str, group_pids))}\n')
            for pid in group_pids:
                row = rows.get(pid)
                if row is not None:
                    record_identity('sampled-group-member', pid)
            if len(child_pids) > MAX_DESCENDANTS:
                stop(f'scoped descendants {len(child_pids)} exceeded 16', 87)
            if size >= PREEMPT_KIB:
                stop(f'sampled private runtime reached 1.5 GiB guard: {size} KiB', 86)
            if size >= HARD_KIB:
                stop(f'sampled private runtime reached 2 GiB hard cap: {size} KiB', 90)
            if time.time() >= DEADLINE:
                stop('absolute UTC execution cutoff 2026-09-30T18:19:18Z reached', 88)


def check_boundary(label):
    if time.time() >= DEADLINE:
        raise TimeoutError('absolute UTC execution cutoff 2026-09-30T18:19:18Z reached')
    size = sampled_size()
    emit(f'PRIVATE_RUNTIME {label}: {size} KiB; sampled maximum {peaks["storage_kib"]} KiB')
    if size >= PREEMPT_KIB or peaks['storage_kib'] >= PREEMPT_KIB:
        raise RuntimeError(f'preemptive 1.5 GiB guard reached after {label}: current={size}, sampled={peaks["storage_kib"]}')
    if size >= HARD_KIB or peaks['storage_kib'] >= HARD_KIB:
        raise RuntimeError(f'2 GiB hard cap reached after {label}')


def run(label, args, env, expected=0, control=False, targets=(), mode='test'):
    check_boundary(label + '-before')
    log = OUT / f'{label}.log'
    command = ([CARGO, 'generate-lockfile'] if mode == 'generate-lockfile'
               else [CARGO, 'test', '--locked', '--jobs', '2', *args])
    emit(f'COMMAND {label}: ' + ' '.join(command))
    with log.open('w', buffering=1) as stream:
        proc = subprocess.Popen(command, cwd=SOURCE, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        active[0] = proc
        record_identity(label, proc.pid)
        try:
            if proc.stdout is None:
                raise RuntimeError('cargo stdout pipe missing')
            for line in proc.stdout:
                sys.stdout.write(line)
                stream.write(line)
                if time.time() >= DEADLINE:
                    proc.terminate()
                    raise TimeoutError('absolute UTC execution cutoff reached during cargo case')
            status = proc.wait()
        finally:
            active[0] = None
    (OUT / f'{label}.status').write_text(f'{status}\n')
    with (OUT / 'case-status.tsv').open('a') as statuses:
        statuses.write(f'{label}\t{status}\t{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}\n')
        statuses.flush()
        os.fsync(statuses.fileno())
    emit(f'STATUS {label}: {status}')
    check_boundary(label + '-after')
    data = log.read_text(errors='replace')
    if status != expected:
        raise RuntimeError(f'{label}: expected exit {expected}, received {status}')
    if control:
        panic = re.compile(rf"thread '{re.escape(TEST_NAME)}'(?: \(\d+\))? panicked")
        if not all((
            'running 1 test' in data,
            'test result: FAILED' in data,
            'fresh host readback must match independent expected bytes' in data,
            'actual="filesystem-payload"' in data,
            'expected="incorrect filesystem expectation"' in data,
            panic.search(data),
        )):
            raise RuntimeError('wrong-value control did not prove the exact named test and actual/expected host-file values')
    if targets:
        counts = [int(x) for x in re.findall(r'test result: ok\.\s+(\d+) passed', data)]
        if len(counts) != len(targets) or any(n == 0 for n in counts):
            raise RuntimeError(f'{label}: expected {len(targets)} nonzero target results, found {counts}')
        if 'FAILED' in data or 'error: test failed' in data:
            raise RuntimeError(f'{label}: failure marker in successful output')
    return data


try:
    started = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain=v1', '--', '.',
                                     ':(exclude).scratch/combined-package-proof/followup'], text=True)
    if dirty.strip():
        raise RuntimeError('source gate worktree is dirty outside the exact owned follow-up evidence subtree')
    shell_revision = (OUT / 'source-gate-head.txt').read_text().strip()
    if shell_revision != revision:
        raise RuntimeError(f'launcher source revision {shell_revision} differs from clean driver revision {revision}')
    OUT.mkdir(parents=True, exist_ok=True)
    OUT.joinpath('runtime-path.txt').write_text(str(RUNTIME) + '\n')
    OUT.joinpath('process-identities.tsv').write_text('label\tpid\tppid\tpgid\tstart\tcommand\n')
    OUT.joinpath('case-status.tsv').write_text('case\texit_status\tend_utc\n')
    record_identity('driver', os.getpid())
    rows = ps_rows()
    chain, pid = [], os.getpid()
    while pid in rows:
        row = rows[pid]
        chain.append(row)
        if 'run_scoped.py _supervise' in row['command']:
            break
        pid = int(row['ppid'])
    else:
        raise RuntimeError('could not establish run_scoped supervisor ancestry')
    if not chain or 'run_scoped.py _supervise' not in chain[-1]['command']:
        raise RuntimeError('run_scoped supervisor identity was not found')
    for item in chain:
        record_identity('launcher-ancestry', item['pid'])
    supervisor_pgid = int(chain[-1]['pgid'])
    if os.getpgrp() != supervisor_pgid:
        raise RuntimeError(f'driver escaped scoped group: driver={os.getpgrp()} supervisor={supervisor_pgid}')
    OUT.joinpath('run-state.txt').write_text(
        f'source_revision={revision}\nruntime={RUNTIME}\n'
        f'scoped_supervisor_pid={chain[-1]["pid"]}\nscoped_process_group={supervisor_pgid}\n'
        f'invocation_start_utc={started}\nabsolute_deadline_utc=2026-09-30T18:19:18Z\n')
    sampler_thread = threading.Thread(target=sampler, name='private-runtime-sampler', daemon=True)
    sampler_thread.start()
    archive = RUNTIME / 'source.tar'
    subprocess.run(['git', '-C', str(ROOT), 'archive', '--format=tar', revision, '-o', str(archive)], check=True)
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    SOURCE.mkdir()
    subprocess.run(['tar', '-xf', str(archive), '-C', str(SOURCE)], check=True)
    OUT.joinpath('run-state.txt').write_text(
        f'source_revision={revision}\nsource_archive_sha256={archive_hash}\nruntime={RUNTIME}\n'
        f'scoped_supervisor_pid={chain[-1]["pid"]}\nscoped_process_group={supervisor_pgid}\n'
        f'invocation_start_utc={started}\nabsolute_deadline_utc=2026-09-30T18:19:18Z\n')
    CARGO = shutil.which('cargo')
    rustc = shutil.which('rustc')
    if not CARGO or not rustc:
        raise RuntimeError('native Cargo/Rust compiler unavailable on PATH')
    os.environ.update({'CARGO_HOME': str(CARGO_HOME), 'CARGO_TARGET_DIR': str(TARGET),
                       'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
                       'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0',
                       'TMPDIR': str(RUNTIME / 'tmp'), 'TMP': str(RUNTIME / 'tmp'), 'TEMP': str(RUNTIME / 'tmp')})
    (RUNTIME / 'tmp').mkdir(exist_ok=True)
    for key in ('RUSTC', 'RUSTDOC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTUP_TOOLCHAIN'):
        os.environ.pop(key, None)
    env = dict(os.environ)
    OUT.joinpath('environment.txt').write_text(
        f'source_revision={revision}\nsource_archive_sha256={archive_hash}\nscoped_runtime={RUNTIME}\n'
        f'scoped_supervisor_pid={chain[-1]["pid"]}\nscoped_process_group={supervisor_pgid}\n'
        f'start_utc={started}\nabsolute_deadline_utc=2026-09-30T18:19:18Z\n'
        + subprocess.check_output(['uname', '-a'], text=True)
        + subprocess.check_output([rustc, '--version', '--verbose'], text=True)
        + subprocess.check_output([CARGO, '--version', '--verbose'], text=True)
        + 'private Cargo home/target/tmp; jobs=2; debug=0; incremental=0; serial tests\n')

    (SOURCE / 'Cargo.lock').unlink(missing_ok=True)
    run('lockfile-resolution', [], env, expected=0, mode='generate-lockfile')
    lock = SOURCE / 'Cargo.lock'
    if not lock.is_file():
        raise RuntimeError('cargo generate-lockfile succeeded without producing Cargo.lock')
    lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
    shutil.copy2(lock, OUT / 'Cargo.lock.generated')
    OUT.joinpath('lock-identities.txt').write_text(f'generated_sha256={lock_hash}\n')
    run('wrong-fresh-file-control', ['--features', PROFILES[0][1], '--test', 'combined_sys_net',
        TEST_NAME, '--', '--exact', '--test-threads=1', '--nocapture'],
        dict(env, RHAI_COMBINED_WRONG_EXPECTATION='1'), expected=101, control=True)
    run('restored-baseline', ['--features', PROFILES[0][1], '--test', 'combined_sys_net', '--',
        '--test-threads=1', '--nocapture'], env, targets=('combined_sys_net',))
    for label, features in PROFILES[1:7]:
        run('combined-' + label, ['--features', features, '--test', 'combined_sys_net', '--',
            '--test-threads=1', '--nocapture'], env, targets=('combined_sys_net',))
    f32_args = ['--features', PROFILES[7][1]]
    for target in ALL_TARGETS:
        f32_args += ['--test', target]
    f32_args += ['--', '--test-threads=1', '--nocapture']
    run('f32-full-row', f32_args, env, targets=ALL_TARGETS)
    final_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
    if final_hash != lock_hash:
        raise RuntimeError('Cargo.lock changed after the locked test runs')
    shutil.copy2(lock, OUT / 'Cargo.lock.final')
    with (OUT / 'lock-identities.txt').open('a') as stream:
        stream.write(f'final_sha256={final_hash}\n')
        stream.flush()
        os.fsync(stream.fileno())
    sample_stop.set()
    sampler_thread.join(timeout=2)
    (OUT / 'resource-maxima.txt').write_text(
        f'sampled_runtime_kib_max={peaks["storage_kib"]}\n'
        f'sampled_owned_descendants_max={peaks["descendants"]}\n'
        'method=1-second du -sk plus ps parent ancestry; sampled maxima only\n')
    (OUT / 'result.txt').write_text('All authorized corrected-source follow-up cases passed.\n')
    emit('ACCEPTED all eight corrected combined profiles; full f32 eight-target row; exact wrong-value control and restored baseline')
except BaseException as exc:
    try:
        OUT.joinpath('driver-error.txt').write_text(f'{type(exc).__name__}: {exc}\n')
    except Exception:
        pass
    emit(f'FOLLOWUP_STOP {type(exc).__name__}: {exc}')
    sys.exit(1)
finally:
    sample_stop.set()
