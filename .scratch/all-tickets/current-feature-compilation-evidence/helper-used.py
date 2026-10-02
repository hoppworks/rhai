"""Bounded private Rust 1.77.2 feature-gate compilation for frozen source."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import traceback

REPO = Path('/Users/hoppworks/projects/rhai-all-tickets')
REVISION = '4baf3b20ba8335fbe9dab21236182429a97f51ec'
LOCK_SOURCE = REPO / '.scratch/all-tickets/macos-selected-graph-evidence-03/Cargo.lock'
LOCK_SHA256 = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
RUSTUP = Path('/Users/hoppworks/.cargo/bin/rustup')
TOOLCHAIN = '1.77.2-aarch64-apple-darwin'
EVIDENCE = REPO / '.scratch/all-tickets/current-feature-compilation-evidence'
CONTRACT = REPO / '.scratch/all-tickets/current-feature-compilation-contract.md'
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR'])
START = time.monotonic()
DEADLINE = START + 540
WORK_DEADLINE = DEADLINE - 30
SAMPLE_INTERVAL = 1.0
PREEMPTIVE_STORAGE_KIB = 1_572_864
HARD_STORAGE_KIB = 2 * 1024 * 1024
HARD_RSS_KIB = 2 * 1024 * 1024
MAX_DESCENDANTS = 16

# The accepted testing-environ,sys,net baseline from 9f84aa6 is applicable to
# this production/manifests/lock-identical descendant and is intentionally omitted.
FEATURE_ROWS = (
    ('sys-alone', 'testing-environ,sys'),
    ('net-alone', 'testing-environ,net'),
    ('net-no-object', 'testing-environ,net,no_object'),
    ('combined-sync', 'testing-environ,sys,net,sync'),
    ('combined-no-index', 'testing-environ,sys,net,no_index'),
    ('combined-metadata-serde', 'testing-environ,sys,net,metadata,serde'),
    ('combined-only-i32-no-float', 'testing-environ,sys,net,only_i32,no_float'),
    ('combined-unchecked', 'testing-environ,sys,net,unchecked'),
    ('combined-no-index-sync-metadata',
     'testing-environ,sys,net,no_index,sync,metadata'),
    ('combined-f32-float', 'testing-environ,sys,net,f32_float'),
)

STAGE = RUNTIME / 'evidence'
SOURCE = RUNTIME / 'source'
CARGO_HOME = RUNTIME / 'cargo-home'
RUSTUP_HOME = RUNTIME / 'rustup-home'
TARGET = RUNTIME / 'target'
PRIVATE_HOME = RUNTIME / 'home'
SAMPLES: list[dict[str, object]] = []
MAXIMA = {'storage_kib': 0, 'rss_kib': 0, 'descendants': 0}
COMMANDS: list[dict[str, object]] = []
ROW_RESULTS: list[dict[str, object]] = []
ACTIVE_CHILD: subprocess.Popen[bytes] | None = None
INTERRUPTED: int | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def on_signal(signum: int, _frame: object) -> None:
    global INTERRUPTED
    INTERRUPTED = signum
    raise InterruptedError(f'interrupted by signal {signum}')


def check_deadline(*, during_export: bool = False) -> None:
    limit = DEADLINE if during_export else WORK_DEADLINE
    if time.monotonic() >= limit:
        if during_export:
            raise TimeoutError('540-second helper budget, including setup and export, expired')
        raise TimeoutError('510-second work budget expired; 30 seconds reserved for export')
    if INTERRUPTED is not None:
        raise InterruptedError(f'interrupted by signal {INTERRUPTED}')


def sample_resources() -> None:
    check_deadline()
    du = subprocess.run(['/usr/bin/du', '-sk', str(RUNTIME)], capture_output=True,
                        text=True, check=True, timeout=5)
    storage = int(du.stdout.split()[0])
    ps = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,rss='], capture_output=True,
                        text=True, check=True, timeout=5)
    rows: dict[int, tuple[int, int]] = {}
    for line in ps.stdout.splitlines():
        pid, ppid, rss = map(int, line.split())
        if pid in rows:
            raise RuntimeError(f'duplicate PID in resource sample: {pid}')
        rows[pid] = (ppid, rss)
    root_pid = os.getpid()
    if root_pid not in rows:
        raise RuntimeError('helper PID absent from resource sample')
    owned = {root_pid}
    while True:
        children = {pid for pid, (ppid, _rss) in rows.items() if ppid in owned} - owned
        if not children:
            break
        owned.update(children)
    rss = sum(rows[pid][1] for pid in owned)
    descendants = len(owned) - 1
    current = {'monotonic_seconds': round(time.monotonic() - START, 3),
               'storage_kib': storage, 'rss_kib': rss,
               'descendants': descendants}
    SAMPLES.append(current)
    MAXIMA['storage_kib'] = max(MAXIMA['storage_kib'], storage)
    MAXIMA['rss_kib'] = max(MAXIMA['rss_kib'], rss)
    MAXIMA['descendants'] = max(MAXIMA['descendants'], descendants)
    print('sample=' + json.dumps(current, sort_keys=True), flush=True)
    if storage >= PREEMPTIVE_STORAGE_KIB:
        raise RuntimeError('sampled private storage reached 1.5 GiB preemptive stop')
    if storage >= HARD_STORAGE_KIB or rss >= HARD_RSS_KIB:
        raise RuntimeError('sampled private storage/RSS reached 2 GiB hard stop')
    if descendants > MAX_DESCENDANTS:
        raise RuntimeError('sampled helper descendants exceeded 16')


def stop_child(child: subprocess.Popen[bytes]) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=3)


def run_command(name: str, argv: list[str], env: dict[str, str],
                expected_status: int | None = 0, binary_stdout: Path | None = None,
                cwd: Path | None = None) -> str:
    global ACTIVE_CHILD
    check_deadline()
    stdout_path = binary_stdout or (STAGE / f'{name}.stdout')
    stderr_path = STAGE / f'{name}.stderr'
    status_path = STAGE / f'{name}.status'
    command_cwd = SOURCE if cwd is None else cwd
    if not command_cwd.is_dir():
        raise RuntimeError(f'command working directory does not exist: {command_cwd}')
    record: dict[str, object] = {
        'name': name, 'argv': argv, 'expected_status': expected_status,
        'stdout': str(stdout_path.relative_to(RUNTIME)),
        'stderr': str(stderr_path.relative_to(RUNTIME)), 'cwd': str(command_cwd),
        'started_monotonic_seconds': round(time.monotonic() - START, 3),
    }
    COMMANDS.append(record)
    print(f'command={name} argv={argv!r}', flush=True)
    next_sample = time.monotonic()
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        child = subprocess.Popen(argv, cwd=command_cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        ACTIVE_CHILD = child
        try:
            while child.poll() is None:
                check_deadline()
                now = time.monotonic()
                if now >= next_sample:
                    sample_resources()
                    next_sample = now + SAMPLE_INTERVAL
                time.sleep(min(0.1, max(0.01, DEADLINE - time.monotonic())))
            status = child.wait()
            sample_resources()
        except BaseException:
            stop_child(child)
            status = child.returncode if child.returncode is not None else 125
            status_path.write_text(str(status) + '\n', encoding='ascii')
            record['status'] = status
            record['finished_monotonic_seconds'] = round(time.monotonic() - START, 3)
            write_json(STAGE / 'commands.json', COMMANDS)
            raise
        finally:
            ACTIVE_CHILD = None
    status_path.write_text(str(status) + '\n', encoding='ascii')
    record['status'] = status
    record['finished_monotonic_seconds'] = round(time.monotonic() - START, 3)
    write_json(STAGE / 'commands.json', COMMANDS)
    print(f'status={name}:{status}', flush=True)
    if expected_status is not None and status != expected_status:
        raise RuntimeError(f'{name} expected status {expected_status}, got {status}')
    return stdout_path.read_text(errors='replace') if binary_stdout is None else ''


def extract_archive(archive_path: Path) -> None:
    """Extract a git archive while rejecting paths or links outside the runtime."""
    root = SOURCE.resolve()
    SOURCE.mkdir()
    with tarfile.open(archive_path, 'r:') as archive:
        for member in archive.getmembers():
            rel = PurePosixPath(member.name)
            if rel.is_absolute() or not rel.parts or any(part in ('', '.', '..') for part in rel.parts):
                raise RuntimeError(f'unsafe path in frozen archive: {member.name!r}')
            dest = SOURCE.joinpath(*rel.parts)
            if not dest.parent.resolve().is_relative_to(root):
                raise RuntimeError(f'archive parent escapes source root: {member.name!r}')
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            if member.issym():
                link = Path(member.linkname)
                if link.is_absolute() or not (dest.parent / link).resolve().is_relative_to(root):
                    raise RuntimeError(f'archive symlink escapes source root: {member.name!r}')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.symlink_to(member.linkname)
                continue
            if not member.isfile():
                raise RuntimeError(f'unsupported archive member: {member.name!r}')
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.parent.resolve().is_relative_to(root):
                raise RuntimeError(f'archive destination escapes source root: {member.name!r}')
            source_file = archive.extractfile(member)
            if source_file is None:
                raise RuntimeError(f'cannot read archive member: {member.name!r}')
            with source_file, dest.open('wb') as output:
                shutil.copyfileobj(source_file, output)
            dest.chmod(member.mode & 0o777)


def archive_command_cwd() -> Path:
    """Choose an existing cwd because SOURCE does not exist before extraction."""
    if SOURCE.exists():
        raise RuntimeError('frozen source must not exist before its archive is created')
    if not RUNTIME.is_dir():
        raise RuntimeError('private runtime must exist before source archival')
    return RUNTIME


def export_evidence() -> None:
    check_deadline(during_export=True)
    if EVIDENCE.exists():
        raise FileExistsError(f'evidence destination already exists; preserve it: {EVIDENCE}')
    write_json(STAGE / 'sampled-maxima.json', {
        'maxima': MAXIMA, 'sample_count': len(SAMPLES),
        'samples_are_periodic_not_continuous_peak': True,
        'storage_preemptive_stop_kib': PREEMPTIVE_STORAGE_KIB,
        'storage_hard_stop_kib': HARD_STORAGE_KIB,
        'rss_hard_stop_kib': HARD_RSS_KIB,
        'descendant_hard_stop': MAX_DESCENDANTS,
    })
    (STAGE / 'resource-samples.jsonl').write_text(
        ''.join(json.dumps(row, sort_keys=True) + '\n' for row in SAMPLES), encoding='utf-8')
    write_json(STAGE / 'rows.json', {
        'baseline_reused': {
            'source_revision': '9f84aa6d8163257b4e3f3c2fe4a1c7d7b7c3cce6',
            'features': 'testing-environ,sys,net',
            'evidence': str(REPO / '.scratch/all-tickets/current-optional-msrv-evidence'),
            'accepted_result': 'cargo check --locked --lib exited 0',
        },
        'requested_rows': ROW_RESULTS,
        'requested_row_count': len(FEATURE_ROWS),
        'successful_rows': sum(row.get('status') == 0 for row in ROW_RESULTS),
        'all_requested_rows_succeeded': len(ROW_RESULTS) == len(FEATURE_ROWS)
            and all(row.get('status') == 0 for row in ROW_RESULTS),
    })
    write_json(STAGE / 'export.json', {
        'runtime': str(RUNTIME), 'expected_outer_scope': str(RUNTIME.parent),
        'evidence_destination': str(EVIDENCE),
        'elapsed_seconds_at_export': round(time.monotonic() - START, 3),
        'helper_deadline_seconds': 540,
        'runtime_cleanup_owner': 'run_scoped.py; independently read back by coordinator',
    })
    EVIDENCE.mkdir(mode=0o700)
    for item in STAGE.iterdir():
        check_deadline(during_export=True)
        target = EVIDENCE / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    print(f'evidence_exported={EVIDENCE}', flush=True)


def main() -> int:
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    if platform.system() != 'Darwin' or platform.machine() not in ('arm64', 'aarch64'):
        raise RuntimeError('prepared proof requires native Darwin arm64')
    if not RUNTIME.is_absolute() or not RUNTIME.is_dir():
        raise RuntimeError('AGENT_RUNTIME_DIR must be an existing absolute scoped runtime')
    if EVIDENCE.exists():
        raise FileExistsError(f'evidence destination already exists; preserve it: {EVIDENCE}')
    if not RUSTUP.is_file():
        raise FileNotFoundError(f'existing rustup binary not found: {RUSTUP}')
    if not CONTRACT.is_file():
        raise FileNotFoundError(f'contract missing: {CONTRACT}')
    STAGE.mkdir(mode=0o700)
    shutil.copy2(Path(__file__), STAGE / 'helper-used.py')
    shutil.copy2(CONTRACT, STAGE / 'contract.md')
    (STAGE / 'contract-sha256.txt').write_text(sha256(CONTRACT) + '\n', encoding='ascii')
    private_tmp = Path(os.environ['TMPDIR'])
    if not private_tmp.is_absolute() or not private_tmp.resolve().is_relative_to(RUNTIME.resolve()):
        raise RuntimeError('TMPDIR must be inside AGENT_RUNTIME_DIR')
    CARGO_HOME.mkdir(mode=0o700)
    RUSTUP_HOME.mkdir(mode=0o700)
    PRIVATE_HOME.mkdir(mode=0o700)
    env = {
        'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME': str(PRIVATE_HOME),
        'TMPDIR': str(private_tmp), 'TMP': str(private_tmp), 'TEMP': str(private_tmp),
        'CARGO_HOME': str(CARGO_HOME), 'RUSTUP_HOME': str(RUSTUP_HOME),
        'CARGO_TARGET_DIR': str(TARGET), 'CARGO_BUILD_JOBS': '2',
        'CARGO_INCREMENTAL': '0', 'CARGO_PROFILE_DEV_DEBUG': '0',
        'CARGO_TERM_COLOR': 'never',
    }
    source_archive = RUNTIME / 'frozen-source.tar'
    archive_cwd = archive_command_cwd()
    run_command('source-archive', ['/usr/bin/git', '-C', str(REPO), 'archive', REVISION],
                env, binary_stdout=source_archive, cwd=archive_cwd)
    archive_sha = sha256(source_archive)
    extract_archive(source_archive)
    source_archive.unlink()
    for config_path in (SOURCE / '.cargo/config', SOURCE / '.cargo/config.toml'):
        if config_path.exists():
            raise RuntimeError(f'frozen source contains Cargo config override: {config_path.name}')
    if (SOURCE / 'Cargo.lock').exists():
        raise RuntimeError('unexpected root Cargo.lock in archive; preserve exact lock provenance')
    private_lock = SOURCE / 'Cargo.lock'
    shutil.copy2(LOCK_SOURCE, private_lock)
    actual_lock_sha = sha256(private_lock)
    if actual_lock_sha != LOCK_SHA256:
        raise RuntimeError(f'compatible lock hash mismatch: {actual_lock_sha}')
    shutil.copy2(private_lock, STAGE / 'Cargo.lock')
    manifests = {}
    for manifest in sorted(SOURCE.rglob('Cargo.toml')):
        if manifest.is_file() and not manifest.is_symlink():
            manifests[manifest.relative_to(SOURCE).as_posix()] = sha256(manifest)
    write_json(STAGE / 'source-lock-manifests.json', {
        'revision': REVISION, 'archive_sha256': archive_sha,
        'lock_source': str(LOCK_SOURCE), 'lock_sha256': actual_lock_sha,
        'cargo_manifests_sha256': manifests,
        'tracked_cargo_config': False,
    })
    sample_resources()
    run_command('rustup-install', [str(RUSTUP), 'toolchain', 'install', TOOLCHAIN,
                                   '--profile', 'minimal', '--no-self-update'], env)
    toolchain_bin = RUSTUP_HOME / 'toolchains' / TOOLCHAIN / 'bin'
    rustc = toolchain_bin / 'rustc'
    cargo = toolchain_bin / 'cargo'
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError('private Rustup install lacks direct rustc or cargo binary')
    env['PATH'] = str(toolchain_bin) + ':/usr/bin:/bin:/usr/sbin:/sbin'
    env['RUSTC'] = str(rustc)
    rustc_version = run_command('rustc-version', [str(rustc), '--version', '--verbose'], env)
    if not rustc_version.startswith('rustc 1.77.2 ') or 'host: aarch64-apple-darwin' not in rustc_version:
        raise RuntimeError('direct private rustc version or host did not match Rust 1.77.2 Darwin arm64')
    cargo_version = run_command('cargo-version', [str(cargo), '--version', '--verbose'], env)
    if not cargo_version.startswith('cargo 1.77.2 '):
        raise RuntimeError('direct private Cargo version did not match 1.77.2')
    for row_name, features in FEATURE_ROWS:
        check_deadline()
        if sha256(private_lock) != LOCK_SHA256:
            raise RuntimeError('Cargo.lock changed before feature row ' + row_name)
        check_argv = [str(cargo), 'check', '--locked', '--lib', '--features', features]
        status_path = STAGE / f'cargo-{row_name}.status'
        try:
            run_command('cargo-' + row_name, check_argv, env,
                        expected_status=None, cwd=SOURCE)
            status = int(status_path.read_text(encoding='ascii').strip())
            ROW_RESULTS.append({'row': row_name, 'features': features, 'status': status,
                                'stdout': f'cargo-{row_name}.stdout',
                                'stderr': f'cargo-{row_name}.stderr'})
            write_json(STAGE / 'rows-in-progress.json', ROW_RESULTS)
            if sha256(private_lock) != LOCK_SHA256:
                raise RuntimeError('Cargo.lock changed during feature row ' + row_name)
        except BaseException:
            if not any(row['row'] == row_name for row in ROW_RESULTS):
                status = (int(status_path.read_text(encoding='ascii').strip())
                          if status_path.is_file() else None)
                ROW_RESULTS.append({
                    'row': row_name, 'features': features, 'status': status,
                    'outcome': 'interrupted-or-not-started',
                    'stdout': f'cargo-{row_name}.stdout' if (STAGE / f'cargo-{row_name}.stdout').exists() else None,
                    'stderr': f'cargo-{row_name}.stderr' if (STAGE / f'cargo-{row_name}.stderr').exists() else None,
                })
            write_json(STAGE / 'rows-in-progress.json', ROW_RESULTS)
            raise
    success = len(ROW_RESULTS) == len(FEATURE_ROWS) and all(
        row['status'] == 0 for row in ROW_RESULTS)
    (STAGE / 'result.txt').write_text(
        f'{sum(row["status"] == 0 for row in ROW_RESULTS)}/{len(FEATURE_ROWS)} '
        'uncovered cargo check --locked --lib feature rows exited 0 on frozen source; '
        'compilation only. Baseline testing-environ,sys,net is referenced from accepted '
        'prior evidence and was not rerun.\n', encoding='utf-8')
    return 0 if success else 1


if __name__ == '__main__':
    exit_status = 1
    error_text = None
    try:
        exit_status = main()
    except BaseException as exc:
        error_text = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        try:
            STAGE.mkdir(mode=0o700, exist_ok=True)
            (STAGE / 'failure.txt').write_text(error_text, encoding='utf-8')
            if ACTIVE_CHILD is not None:
                stop_child(ACTIVE_CHILD)
        except BaseException as export_error:
            print(f'failure_record_error={export_error!r}', file=sys.stderr, flush=True)
        exit_status = 1
    finally:
        try:
            if STAGE.is_dir() and not EVIDENCE.exists():
                export_evidence()
        except BaseException:
            print('evidence_export_failed:\n' + traceback.format_exc(), file=sys.stderr, flush=True)
            exit_status = 1
    if error_text:
        print(error_text, file=sys.stderr, flush=True)
    if exit_status == 0:
        print('current_feature_compilation=pass', flush=True)
    else:
        print('current_feature_compilation=incomplete_or_failed', flush=True)
    sys.exit(exit_status)
