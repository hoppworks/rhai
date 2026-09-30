#!/usr/bin/env python3
"""Run only the missing f32 eight-target combined row in a scoped runtime."""
import hashlib
import json
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
OUT = ROOT / '.scratch/combined-package-proof/f32-followup'
RUNTIME = pathlib.Path(os.environ['AGENT_RUNTIME_DIR'])
TARGET = RUNTIME / 'target'
SOURCE = RUNTIME / 'source'
CARGO_HOME = RUNTIME / 'cargo-home'
SOURCE_REVISION = 'c2c76a1fac0ed48c5f7bae189c1eb0569ff7d756'
DEADLINE = datetime(2026, 9, 30, 19, 18, 29, tzinfo=timezone.utc).timestamp()
PREEMPT_KIB = 1536 * 1024
HARD_KIB = 2 * 1024 * 1024
MAX_DESCENDANTS = 16
TARGETS = ('combined_sys_net', 'sys_env', 'sys_fs', 'sys_policy',
           'net_connect', 'net_listen', 'net_reads', 'net_writes')
active = [None]
sample_stop = threading.Event()
sample_lock = threading.Lock()
identity_lock = threading.Lock()
seen_identities = set()
peaks = {'storage_kib': 0, 'descendants': 0}


def emit(value):
    print(value, flush=True)


def utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def ps_snapshot():
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


def record_identity(label, pid, rows):
    row = rows.get(int(pid))
    if row is None:
        row = {'pid': str(pid), 'ppid': 'unavailable', 'pgid': 'unavailable',
               'start': 'unavailable', 'command': 'unavailable'}
    key = (label, row['pid'], row['start'])
    with identity_lock:
        if key in seen_identities:
            return
        seen_identities.add(key)
        with (OUT / 'process-identities.tsv').open('a') as stream:
            stream.write('\t'.join([label, row['pid'], row['ppid'], row['pgid'],
                                    row['start'], row['command']]) + '\n')
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


def append_du_observation(record):
    with sample_lock:
        with (OUT / 'du-observations.jsonl').open('a') as stream:
            stream.write(json.dumps(record, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())


def du_once():
    return subprocess.run(['du', '-sk', str(RUNTIME)], text=True, capture_output=True)


def size_sample():
    first = du_once()
    record = {'utc': utc(), 'first': {'status': first.returncode,
                                      'stdout': first.stdout, 'stderr': first.stderr}}
    if first.returncode == 0:
        try:
            size = int(first.stdout.split()[0])
        except (IndexError, ValueError) as exc:
            record['decision'] = 'invalid-first-output'
            append_du_observation(record)
            raise RuntimeError(f'du returned invalid size: {first.stdout!r}') from exc
        record['decision'] = 'first-observation-used'
        append_du_observation(record)
        peaks['storage_kib'] = max(peaks['storage_kib'], size)
        return size

    diagnostics = first.stderr.splitlines()
    disappeared = []
    exact = re.compile(r'^du: (.+): No such file or directory$')
    for diagnostic in diagnostics:
        match = exact.fullmatch(diagnostic)
        if not match:
            record['decision'] = 'first-error-not-eligible-for-rescan'
            append_du_observation(record)
            raise RuntimeError(f'du failed closed without eligible target ENOENT: {diagnostic}')
        path = pathlib.Path(match.group(1))
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(TARGET.resolve(strict=True))
        except (OSError, ValueError) as exc:
            record['decision'] = 'first-error-outside-private-target'
            append_du_observation(record)
            raise RuntimeError(f'du ENOENT was outside exact private Cargo target: {path}') from exc
        if path.exists():
            record['decision'] = 'reported-target-file-still-exists'
            append_du_observation(record)
            raise RuntimeError(f'du ENOENT target path still exists: {path}')
        disappeared.append(str(path))
    if not diagnostics:
        record['decision'] = 'first-error-had-no-diagnostics'
        append_du_observation(record)
        raise RuntimeError(f'du failed without diagnostics ({first.returncode})')

    record['bounded_rescan_for_disappeared_target_files'] = disappeared
    second = du_once()
    record['second'] = {'status': second.returncode, 'stdout': second.stdout, 'stderr': second.stderr}
    if second.returncode != 0:
        record['decision'] = 'second-observation-failed-stop'
        append_du_observation(record)
        raise RuntimeError(f'bounded du rescan failed ({second.returncode}): {second.stderr.strip()}')
    try:
        size = int(second.stdout.split()[0])
    except (IndexError, ValueError) as exc:
        record['decision'] = 'invalid-second-output-stop'
        append_du_observation(record)
        raise RuntimeError(f'du rescan returned invalid size: {second.stdout!r}') from exc
    record['decision'] = 'eligible-disappeared-target-files-rescanned-once'
    append_du_observation(record)
    peaks['storage_kib'] = max(peaks['storage_kib'], size)
    return size


def stop(reason, status):
    with (OUT / 'STOP-REASON.txt').open('a') as stream:
        stream.write(f'{utc()} status={status} {reason}\n')
        stream.flush()
        os.fsync(stream.fileno())
    emit('STOP: ' + reason)
    proc = active[0]
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
    os._exit(status)  # run_scoped owns and reaps the complete process group.


def sample_boundary(label):
    size = size_sample()
    if size >= PREEMPT_KIB or peaks['storage_kib'] >= PREEMPT_KIB:
        raise RuntimeError(f'preemptive 1.5 GiB guard reached {label}: current={size}, sampled={peaks["storage_kib"]}')
    if size >= HARD_KIB or peaks['storage_kib'] >= HARD_KIB:
        raise RuntimeError(f'2 GiB hard cap reached {label}: current={size}, sampled={peaks["storage_kib"]}')
    if time.time() >= DEADLINE:
        raise TimeoutError('absolute UTC execution cutoff 2026-09-30T19:18:29Z reached')
    return size


def sampler():
    with (OUT / 'storage-samples.tsv').open('w', buffering=1) as storage, \
         (OUT / 'process-samples.tsv').open('w', buffering=1) as processes:
        storage.write('utc_epoch\truntime_kib\tsample\n')
        processes.write('utc_epoch\towned_descendants\tgroup_pids\n')
        while not sample_stop.wait(1):
            try:
                size = size_sample()
                rows = ps_snapshot()
                child_pids = descendants(os.getpid(), rows)
                pgid = os.getpgrp()
                group_pids = sorted(pid for pid, row in rows.items() if int(row['pgid']) == pgid)
            except Exception as exc:
                stop(f'resource/process sampler failed closed: {type(exc).__name__}: {exc}', 89)
            peaks['storage_kib'] = max(peaks['storage_kib'], size)
            peaks['descendants'] = max(peaks['descendants'], len(child_pids))
            stamp = f'{time.time():.3f}'
            storage.write(f'{stamp}\t{size}\twhole-runtime du -sk; see du-observations.jsonl\n')
            processes.write(f'{stamp}\t{len(child_pids)}\t{",".join(map(str, group_pids))}\n')
            for pid in group_pids:
                record_identity('sampled-group-member', pid, rows)
            if len(child_pids) > MAX_DESCENDANTS:
                stop(f'scoped descendants {len(child_pids)} exceeded 16', 87)
            if size >= PREEMPT_KIB:
                stop(f'sampled private runtime reached 1.5 GiB guard: {size} KiB', 86)
            if size >= HARD_KIB:
                stop(f'sampled private runtime reached 2 GiB hard cap: {size} KiB', 90)
            if time.time() >= DEADLINE:
                stop('absolute UTC execution cutoff 2026-09-30T19:18:29Z reached', 88)


def run_case(label, command, env, expected, expected_targets=()):
    size = sample_boundary(label + '-before')
    emit(f'PRIVATE_RUNTIME {label}-before: {size} KiB; sampled maximum {peaks["storage_kib"]} KiB')
    log = OUT / f'{label}.log'
    emit('COMMAND ' + label + ': ' + ' '.join(command))
    with log.open('w', buffering=1) as output:
        proc = subprocess.Popen(command, cwd=SOURCE, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        active[0] = proc
        record_identity(label, proc.pid, ps_snapshot())
        try:
            if proc.stdout is None:
                raise RuntimeError('Cargo stdout pipe missing')
            for line in proc.stdout:
                sys.stdout.write(line)
                output.write(line)
                if time.time() >= DEADLINE:
                    proc.terminate()
                    raise TimeoutError('absolute UTC execution cutoff reached during Cargo case')
            status = proc.wait()
        finally:
            active[0] = None
    (OUT / f'{label}.status').write_text(f'{status}\n')
    with (OUT / 'case-status.tsv').open('a') as statuses:
        statuses.write(f'{label}\t{status}\t{utc()}\n')
        statuses.flush()
        os.fsync(statuses.fileno())
    emit(f'STATUS {label}: {status}')
    size = sample_boundary(label + '-after')
    emit(f'PRIVATE_RUNTIME {label}-after: {size} KiB; sampled maximum {peaks["storage_kib"]} KiB')
    data = log.read_text(errors='replace')
    if status != expected:
        raise RuntimeError(f'{label}: expected exit {expected}, received {status}')
    if expected_targets:
        counts = [int(x) for x in re.findall(r'test result: ok\.\s+(\d+) passed', data)]
        if len(counts) != len(expected_targets) or any(n == 0 for n in counts):
            raise RuntimeError(f'{label}: expected {len(expected_targets)} nonzero target results, found {counts}')
        if re.search(r'(?m)^test result: FAILED|^error: test failed', data):
            raise RuntimeError(f'{label}: failure marker in successful output')


try:
    started = utc()
    gate_revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain=v1', '--', '.',
                                     ':(exclude).scratch/combined-package-proof/f32-followup'], text=True)
    if dirty.strip():
        raise RuntimeError('source gate worktree is dirty outside exact owned f32 evidence subtree')
    if (OUT / 'source-gate-head.txt').read_text().strip() != gate_revision:
        raise RuntimeError('launcher source HEAD differs from clean driver source HEAD')
    OUT.mkdir(parents=True, exist_ok=True)
    OUT.joinpath('runtime-path.txt').write_text(str(RUNTIME) + '\n')
    OUT.joinpath('process-identities.tsv').write_text('label\tpid\tppid\tpgid\tstart\tcommand\n')
    OUT.joinpath('case-status.tsv').write_text('case\texit_status\tend_utc\n')
    OUT.joinpath('du-observations.jsonl').write_text('')
    initial_rows = ps_snapshot()
    chain, pid = [], os.getpid()
    while pid in initial_rows:
        row = initial_rows[pid]
        chain.append(row)
        if 'run_scoped.py _supervise' in row['command']:
            break
        pid = int(row['ppid'])
    if not chain or 'run_scoped.py _supervise' not in chain[-1]['command']:
        raise RuntimeError('could not establish run_scoped supervisor ancestry from one ps snapshot')
    supervisor_pgid = int(chain[-1]['pgid'])
    if os.getpgrp() != supervisor_pgid:
        raise RuntimeError(f'driver escaped scoped group: {os.getpgrp()} != {supervisor_pgid}')
    for item in chain:
        record_identity('launcher-ancestry', item['pid'], initial_rows)
    OUT.joinpath('run-state.txt').write_text(
        f'gate_revision={gate_revision}\nsource_revision={SOURCE_REVISION}\nruntime={RUNTIME}\n'
        f'scoped_supervisor_pid={chain[-1]["pid"]}\nscoped_process_group={supervisor_pgid}\n'
        f'invocation_start_utc={started}\nabsolute_deadline_utc=2026-09-30T19:18:29Z\n')
    sampler_thread = threading.Thread(target=sampler, name='private-runtime-sampler', daemon=True)
    sampler_thread.start()
    SOURCE.mkdir()
    subprocess.run(['git', '-C', str(ROOT), 'archive', '--format=tar', SOURCE_REVISION,
                    '-o', str(RUNTIME / 'source.tar')], check=True)
    archive = RUNTIME / 'source.tar'
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    subprocess.run(['tar', '-xf', str(archive), '-C', str(SOURCE)], check=True)
    OUT.joinpath('run-state.txt').write_text(
        f'gate_revision={gate_revision}\nsource_revision={SOURCE_REVISION}\nsource_archive_sha256={archive_hash}\n'
        f'runtime={RUNTIME}\nscoped_supervisor_pid={chain[-1]["pid"]}\nscoped_process_group={supervisor_pgid}\n'
        f'invocation_start_utc={started}\nabsolute_deadline_utc=2026-09-30T19:18:29Z\n')
    cargo = shutil.which('cargo')
    rustc = shutil.which('rustc')
    if not cargo or not rustc:
        raise RuntimeError('native Cargo/Rust compiler unavailable')
    os.environ.update({'CARGO_HOME': str(CARGO_HOME), 'CARGO_TARGET_DIR': str(TARGET),
                       'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
                       'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0',
                       'TMPDIR': str(RUNTIME / 'tmp'), 'TMP': str(RUNTIME / 'tmp'),
                       'TEMP': str(RUNTIME / 'tmp')})
    (RUNTIME / 'tmp').mkdir(exist_ok=True)
    for key in ('RUSTC', 'RUSTDOC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTUP_TOOLCHAIN'):
        os.environ.pop(key, None)
    env = dict(os.environ)
    OUT.joinpath('environment.txt').write_text(
        f'gate_revision={gate_revision}\nsource_revision={SOURCE_REVISION}\nsource_archive_sha256={archive_hash}\n'
        f'scoped_runtime={RUNTIME}\nscoped_supervisor_pid={chain[-1]["pid"]}\nscoped_process_group={supervisor_pgid}\n'
        f'start_utc={started}\nabsolute_deadline_utc=2026-09-30T19:18:29Z\n'
        + subprocess.check_output(['uname', '-a'], text=True)
        + subprocess.check_output([rustc, '--version', '--verbose'], text=True)
        + subprocess.check_output([cargo, '--version', '--verbose'], text=True)
        + 'private Cargo home/target/tmp; jobs=2; dev/test debug=0; incremental=0; serial tests\n')
    (SOURCE / 'Cargo.lock').unlink(missing_ok=True)
    run_case('lockfile-resolution', [cargo, 'generate-lockfile'], env, 0)
    lock = SOURCE / 'Cargo.lock'
    if not lock.is_file():
        raise RuntimeError('Cargo generate-lockfile produced no lock')
    lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
    shutil.copy2(lock, OUT / 'Cargo.lock.generated')
    OUT.joinpath('lock-identities.txt').write_text(f'generated_sha256={lock_hash}\n')
    command = [cargo, 'test', '--locked', '--jobs', '2', '--features', 'testing-environ,sys,net,f32_float']
    for target in TARGETS:
        command += ['--test', target]
    command += ['--', '--test-threads=1', '--nocapture']
    run_case('f32-full-row', command, env, 0, expected_targets=TARGETS)
    final_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
    if final_hash != lock_hash:
        raise RuntimeError('Cargo.lock changed during the locked f32 run')
    shutil.copy2(lock, OUT / 'Cargo.lock.final')
    OUT.joinpath('lock-identities.txt').write_text(f'generated_sha256={lock_hash}\nfinal_sha256={final_hash}\n')
    sample_stop.set()
    sampler_thread.join(timeout=2)
    OUT.joinpath('resource-maxima.txt').write_text(
        f'sampled_runtime_kib_max={peaks["storage_kib"]}\nsampled_owned_descendants_max={peaks["descendants"]}\n'
        'method=one-second whole-runtime du -sk plus one-snapshot ps ancestry; sampled maxima only\n')
    OUT.joinpath('result.txt').write_text('The missing f32 full eight-target row passed.\n')
    emit('ACCEPTED missing f32 full eight-target row passed')
except BaseException as exc:
    try:
        OUT.joinpath('driver-error.txt').write_text(f'{type(exc).__name__}: {exc}\n')
    except Exception:
        pass
    emit(f'F32_STOP {type(exc).__name__}: {exc}')
    sys.exit(1)
finally:
    sample_stop.set()
