#!/usr/bin/env python3
"""Bounded private Rust 1.77.2 Linux feature-gate compilation package."""
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

SOURCE_REVISION = '1ca21e32eed2aa40287ba7e1282000add1dd49c7'
SOURCE_ARCHIVE_SHA256 = '8251e0429d51ffd330e7eac596a1513d836e43e549ca761852cafc642a2a8155'
LOCK_SHA256 = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
EXPECTED_DIAGNOSTIC = (
    'the `sys` feature requires object maps; it cannot be combined with `no_object`'
)
RUSTUP = Path('/root/.cargo/bin/rustup')
TOOLCHAIN = '1.77.2-x86_64-unknown-linux-gnu'
EXPECTED_RUN_SCOPED_SHA256 = '9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d'
EXPECTED_INIT_SHA256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
EXPECTED_PYGUARD_SHA256 = 'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f'
EXPECTED_STAGE = Path('/root/rhai-linux-current-features-v2-1ca21e32-20261002')
STAGE = Path(os.environ['PROOF_STAGE'])
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR'])
INTERRUPT_REQUEST = Path(os.environ['INTERRUPT_REQUEST'])
EVIDENCE = RUNTIME / 'evidence'
SOURCE = RUNTIME / 'source'
CARGO_HOME = RUNTIME / 'cargo-home'
RUSTUP_HOME = RUNTIME / 'rustup-home'
TARGET = RUNTIME / 'target'
PRIVATE_HOME = RUNTIME / 'home'
START = time.monotonic()
DEADLINE = START + 530
WORK_DEADLINE = DEADLINE - 30
SAMPLE_INTERVAL = 1.0
PREEMPTIVE_STORAGE_KIB = 1_572_864
HARD_STORAGE_KIB = 2 * 1024 * 1024
HARD_RSS_KIB = 2 * 1024 * 1024
MAX_DESCENDANTS = 16

POSITIVE_ROWS = (
    ('baseline-sys-net', 'testing-environ,sys,net'),
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
NEGATIVE_ROW = ('sys-no-object-negative', 'testing-environ,sys,no_object')

SAMPLES: list[dict[str, int | float]] = []
MAXIMA = {'storage_kib': 0, 'rss_kib': 0, 'descendants': 0}
COMMANDS: list[dict[str, object]] = []
POSITIVE_RESULTS: list[dict[str, object]] = []
NEGATIVE_RESULT: dict[str, object] | None = None
MANIFEST_HASHES: dict[str, str] = {}
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
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    raise InterruptedError(f'interrupted by signal {signum}')


def check_deadline(*, during_export: bool = False) -> None:
    global INTERRUPTED
    if INTERRUPTED is None and INTERRUPT_REQUEST.is_file():
        INTERRUPTED = signal.SIGTERM
    limit = DEADLINE if during_export else WORK_DEADLINE
    if time.monotonic() >= limit:
        if during_export:
            raise TimeoutError('530-second helper budget, including setup and export, expired')
        raise TimeoutError('500-second work budget expired; 30 seconds reserved for export')
    if INTERRUPTED is not None and not during_export:
        raise InterruptedError(f'interrupted by signal {INTERRUPTED}')


def process_identity(pid: int) -> tuple[int, int, int, str] | None:
    """Return PPID, PGID, start ticks, and command line for one exact PID."""
    proc = Path('/proc') / str(pid)
    try:
        raw = (proc / 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        ppid, pgid, start_ticks = int(fields[1]), int(fields[2]), int(fields[19])
        command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(
            errors='replace').strip()
        return ppid, pgid, start_ticks, command
    except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
        return None


def record_process_identity(label: str, pid: int, identity: tuple[int, int, int, str] | None) -> None:
    path = EVIDENCE / 'process-identities.tsv'
    if identity is None:
        with path.open('a', encoding='utf-8') as stream:
            stream.write(f'{label}\t{pid}\t<identity-unavailable>\n')
        return
    ppid, pgid, start_ticks, command = identity
    with path.open('a', encoding='utf-8') as stream:
        stream.write(f'{label}\t{pid}\t{ppid}\t{pgid}\t{start_ticks}\t{command}\n')


def record_process(label: str, pid: int) -> None:
    record_process_identity(label, pid, process_identity(pid))


def stage_identity_matches(candidate: Path, expected: Path) -> bool:
    """Accept only paths resolving to the same existing stage directory."""
    try:
        return candidate.resolve(strict=True) == expected.resolve(strict=True)
    except (OSError, RuntimeError):
        return False


def capture_runtime_proof() -> None:
    """Persist runtime and direct process identities before stage validation."""
    if not RUNTIME.is_absolute() or not RUNTIME.is_dir():
        raise RuntimeError('AGENT_RUNTIME_DIR must be an existing absolute scoped runtime')
    if EVIDENCE.exists():
        raise FileExistsError(f'private runtime evidence already exists; preserve it: {EVIDENCE}')
    EVIDENCE.mkdir(mode=0o700)
    print(f'PRIVATE_RUNTIME {RUNTIME}', flush=True)
    (EVIDENCE / 'process-identities.tsv').write_text(
        'label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n', encoding='utf-8')
    helper_pid = os.getpid()
    supervisor_pid = os.getppid()
    helper_identity = process_identity(helper_pid)
    supervisor_identity = process_identity(supervisor_pid)
    record_process_identity('helper', helper_pid, helper_identity)
    record_process_identity('scoped-supervisor', supervisor_pid, supervisor_identity)
    if helper_identity is not None:
        print(f'HELPER_IDENTITY {helper_pid} {helper_identity[2]}', flush=True)
    write_json(EVIDENCE / 'early-runtime-identity.json', {
        'runtime': str(RUNTIME), 'helper_pid': helper_pid,
        'helper_start_ticks': None if helper_identity is None else helper_identity[2],
        'supervisor_pid': supervisor_pid,
        'supervisor_start_ticks': None if supervisor_identity is None else supervisor_identity[2],
        'identity_receipt': 'process-identities.tsv',
    })
    if helper_identity is None or supervisor_identity is None:
        raise RuntimeError('required helper or scoped supervisor identity unavailable')


def validate_stage_inputs() -> None:
    """Fail closed on any stage other than the prescribed canonical directory."""
    if not STAGE.is_absolute() or not STAGE.is_dir():
        raise RuntimeError('PROOF_STAGE must be the existing absolute input stage')
    if not stage_identity_matches(STAGE, EXPECTED_STAGE):
        raise RuntimeError(f'PROOF_STAGE must resolve to the prescribed unique stage: {EXPECTED_STAGE}')
    for path in (STAGE / 'source.tar', STAGE / 'Cargo.lock.accepted'):
        if not path.is_file():
            raise FileNotFoundError(f'required explicitly staged input missing: {path}')
    for name in ('contract.md', 'run-feature-compilation.py'):
        if not (STAGE / name).is_file():
            raise FileNotFoundError(f'reviewed staged input missing: {STAGE / name}')
    for relative in ('runner/tools/run_scoped.py', 'runner/tools/agentskills/__init__.py',
                     'runner/tools/agentskills/pyguard.py'):
        if not (STAGE / relative).is_file():
            raise FileNotFoundError(f'existing scoped runner package file missing: {STAGE / relative}')
    expected_interrupt_parent = STAGE / 'outer-evidence'
    if not INTERRUPT_REQUEST.is_absolute() or \
            INTERRUPT_REQUEST.parent.resolve() != expected_interrupt_parent.resolve() or \
            INTERRUPT_REQUEST.name != 'interrupt.request':
        raise RuntimeError('INTERRUPT_REQUEST must be the exact private stage control path')
    if (STAGE / 'proof-evidence').exists():
        raise FileExistsError('proof-evidence destination exists; preserve prior evidence')
    if not RUSTUP.is_file():
        raise FileNotFoundError(f'authorized existing rustup binary not found: {RUSTUP}')


def sample_resources() -> None:
    check_deadline()
    du = subprocess.run(['/usr/bin/du', '-sk', str(RUNTIME)], capture_output=True,
                        text=True, check=True, timeout=5)
    storage = int(du.stdout.split()[0])
    ps = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,rss='], capture_output=True,
                        text=True, check=True, timeout=5)
    processes: dict[int, tuple[int, int]] = {}
    for line in ps.stdout.splitlines():
        pid, ppid, rss = map(int, line.split())
        if pid in processes:
            raise RuntimeError(f'duplicate PID in resource sample: {pid}')
        processes[pid] = (ppid, rss)
    root_pid = os.getpid()
    if root_pid not in processes:
        raise RuntimeError('helper PID absent from resource sample')
    owned = {root_pid}
    while True:
        children = {pid for pid, (ppid, _rss) in processes.items() if ppid in owned} - owned
        if not children:
            break
        owned.update(children)
    rss = sum(processes[pid][1] for pid in owned)
    descendants = len(owned) - 1
    current = {'monotonic_seconds': round(time.monotonic() - START, 3),
               'storage_kib': storage, 'rss_kib': rss, 'descendants': descendants}
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


def run_command(name: str, argv: list[str], env: dict[str, str], *,
                expected_status: int | None = 0, cwd: Path | None = None) -> int:
    global ACTIVE_CHILD
    check_deadline()
    stdout_path = EVIDENCE / f'{name}.stdout'
    stderr_path = EVIDENCE / f'{name}.stderr'
    status_path = EVIDENCE / f'{name}.status'
    command_cwd = RUNTIME if cwd is None else cwd
    if not command_cwd.is_dir():
        raise RuntimeError(f'command working directory does not exist: {command_cwd}')
    record: dict[str, object] = {
        'name': name, 'argv': argv, 'expected_status': expected_status,
        'stdout': stdout_path.name, 'stderr': stderr_path.name, 'cwd': str(command_cwd),
        'started_monotonic_seconds': round(time.monotonic() - START, 3),
    }
    COMMANDS.append(record)
    print(f'command={name} argv={argv!r}', flush=True)
    next_sample = time.monotonic()
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        child = subprocess.Popen(argv, cwd=command_cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=stderr)
        ACTIVE_CHILD = child
        record_process(name, child.pid)
        try:
            while child.poll() is None:
                check_deadline()
                now = time.monotonic()
                if now >= next_sample:
                    sample_resources()
                    next_sample = now + SAMPLE_INTERVAL
                time.sleep(min(0.1, max(0.01, WORK_DEADLINE - time.monotonic())))
            status = child.wait()
            sample_resources()
        except BaseException:
            stop_child(child)
            status = child.returncode if child.returncode is not None else 125
            status_path.write_text(str(status) + '\n', encoding='ascii')
            record['status'] = status
            record['finished_monotonic_seconds'] = round(time.monotonic() - START, 3)
            write_json(EVIDENCE / 'commands.json', COMMANDS)
            raise
        finally:
            ACTIVE_CHILD = None
    status_path.write_text(str(status) + '\n', encoding='ascii')
    record['status'] = status
    record['finished_monotonic_seconds'] = round(time.monotonic() - START, 3)
    write_json(EVIDENCE / 'commands.json', COMMANDS)
    print(f'status={name}:{status}', flush=True)
    if expected_status is not None and status != expected_status:
        raise RuntimeError(f'{name} expected status {expected_status}, got {status}')
    return status


def extract_archive(archive_path: Path) -> None:
    """Extract the staged git archive while rejecting escaping paths and links."""
    root = SOURCE.resolve()
    SOURCE.mkdir(mode=0o700)
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


def export_evidence() -> None:
    check_deadline(during_export=True)
    destination = EXPECTED_STAGE / 'proof-evidence'
    if not EXPECTED_STAGE.is_dir():
        raise RuntimeError(f'prescribed evidence stage is unavailable: {EXPECTED_STAGE}')
    if destination.exists():
        raise FileExistsError(f'proof evidence destination already exists; preserve it: {destination}')
    write_json(EVIDENCE / 'resource-maxima.json', {
        'maxima': MAXIMA, 'sample_count': len(SAMPLES),
        'samples_are_periodic_not_continuous_peak': True,
        'storage_preemptive_stop_kib': PREEMPTIVE_STORAGE_KIB,
        'storage_hard_stop_kib': HARD_STORAGE_KIB,
        'rss_hard_stop_kib': HARD_RSS_KIB,
        'descendant_hard_stop': MAX_DESCENDANTS,
    })
    (EVIDENCE / 'resource-samples.jsonl').write_text(
        ''.join(json.dumps(row, sort_keys=True) + '\n' for row in SAMPLES), encoding='utf-8')
    write_json(EVIDENCE / 'rows.json', {
        'positive_rows': POSITIVE_RESULTS,
        'positive_row_count': len(POSITIVE_ROWS),
        'successful_positive_rows': sum(row.get('status') == 0 for row in POSITIVE_RESULTS),
        'all_positive_rows_succeeded': len(POSITIVE_RESULTS) == len(POSITIVE_ROWS)
            and all(row.get('status') == 0 for row in POSITIVE_RESULTS),
        'negative_prerequisite': NEGATIVE_RESULT,
    })
    write_json(EVIDENCE / 'export.json', {
        'source_revision': SOURCE_REVISION,
        'source_archive_sha256': SOURCE_ARCHIVE_SHA256,
        'compatible_lock_sha256': LOCK_SHA256,
        'runtime': str(RUNTIME), 'evidence_destination': str(destination),
        'elapsed_seconds_at_export': round(time.monotonic() - START, 3),
        'helper_deadline_seconds': 530,
        'runtime_cleanup_owner': 'run_scoped.py; independently read back by coordinator',
    })
    destination.mkdir(mode=0o700)
    for item in EVIDENCE.iterdir():
        check_deadline(during_export=True)
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    print(f'evidence_exported={destination}', flush=True)


def main() -> int:
    global NEGATIVE_RESULT
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    capture_runtime_proof()
    validate_stage_inputs()
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise RuntimeError('prepared proof requires native Linux x86_64')
    staged_contract = STAGE / 'contract.md'
    staged_helper = STAGE / 'run-feature-compilation.py'
    runner_hashes = {
        'run_scoped.py': sha256(STAGE / 'runner/tools/run_scoped.py'),
        'agentskills/__init__.py': sha256(STAGE / 'runner/tools/agentskills/__init__.py'),
        'agentskills/pyguard.py': sha256(STAGE / 'runner/tools/agentskills/pyguard.py'),
    }
    expected_runner_hashes = {
        'run_scoped.py': EXPECTED_RUN_SCOPED_SHA256,
        'agentskills/__init__.py': EXPECTED_INIT_SHA256,
        'agentskills/pyguard.py': EXPECTED_PYGUARD_SHA256,
    }
    if runner_hashes != expected_runner_hashes:
        raise RuntimeError(f'scoped runner package hash mismatch: {runner_hashes!r}')
    if (STAGE / 'proof-evidence').exists():
        raise FileExistsError('proof-evidence destination exists; preserve prior evidence')
    if not RUSTUP.is_file():
        raise FileNotFoundError(f'authorized existing rustup binary not found: {RUSTUP}')

    if Path(__file__).resolve() != staged_helper.resolve():
        raise RuntimeError('executed helper path differs from the explicitly staged helper')
    shutil.copy2(staged_helper, EVIDENCE / 'helper-used.py')
    shutil.copy2(staged_contract, EVIDENCE / 'contract.md')
    write_json(EVIDENCE / 'staged-input-identities.json', {
        'source.tar': {'path': str(STAGE / 'source.tar'), 'sha256': sha256(STAGE / 'source.tar')},
        'Cargo.lock.accepted': {'path': str(STAGE / 'Cargo.lock.accepted'),
                                'sha256': sha256(STAGE / 'Cargo.lock.accepted')},
        'run-feature-compilation.py': {'path': str(staged_helper),
                                       'sha256': sha256(staged_helper)},
        'contract.md': {'path': str(staged_contract), 'sha256': sha256(staged_contract)},
        'run_scoped.py': {'path': str(STAGE / 'runner/tools/run_scoped.py'),
                          'sha256': runner_hashes['run_scoped.py']},
        'agentskills/__init__.py': {
            'path': str(STAGE / 'runner/tools/agentskills/__init__.py'),
            'sha256': runner_hashes['agentskills/__init__.py']},
        'agentskills/pyguard.py': {
            'path': str(STAGE / 'runner/tools/agentskills/pyguard.py'),
            'sha256': runner_hashes['agentskills/pyguard.py']},
    })
    private_tmp = Path(os.environ['TMPDIR'])
    if not private_tmp.is_absolute() or not private_tmp.resolve().is_relative_to(RUNTIME.resolve()):
        raise RuntimeError('TMPDIR must be inside AGENT_RUNTIME_DIR')
    CARGO_HOME.mkdir(mode=0o700)
    RUSTUP_HOME.mkdir(mode=0o700)
    PRIVATE_HOME.mkdir(mode=0o700)
    env = {
        'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME': str(PRIVATE_HOME), 'TMPDIR': str(private_tmp),
        'TMP': str(private_tmp), 'TEMP': str(private_tmp),
        'CARGO_HOME': str(CARGO_HOME), 'RUSTUP_HOME': str(RUSTUP_HOME),
        'CARGO_TARGET_DIR': str(TARGET), 'CARGO_BUILD_JOBS': '2',
        'CARGO_INCREMENTAL': '0', 'CARGO_PROFILE_DEV_DEBUG': '0',
        'CARGO_PROFILE_TEST_DEBUG': '0', 'RUSTFLAGS': '-C debuginfo=0',
        'CARGO_TERM_COLOR': 'never',
    }
    archive_path = STAGE / 'source.tar'
    lock_candidate = STAGE / 'Cargo.lock.accepted'
    archive_copy = RUNTIME / 'frozen-source.tar'
    shutil.copy2(archive_path, archive_copy)
    if sha256(archive_copy) != SOURCE_ARCHIVE_SHA256:
        raise RuntimeError('staged frozen source archive SHA-256 mismatch')
    if sha256(lock_candidate) != LOCK_SHA256:
        raise RuntimeError('staged accepted compatible lock SHA-256 mismatch')
    extract_archive(archive_copy)
    archive_copy.unlink()
    for config_path in (SOURCE / '.cargo/config', SOURCE / '.cargo/config.toml'):
        if config_path.exists():
            raise RuntimeError(f'frozen source contains Cargo config override: {config_path.name}')
    if (SOURCE / 'Cargo.lock').exists():
        raise RuntimeError('unexpected root Cargo.lock in archive; preserve exact lock provenance')
    private_lock = SOURCE / 'Cargo.lock'
    shutil.copy2(lock_candidate, private_lock)
    if sha256(private_lock) != LOCK_SHA256:
        raise RuntimeError('private source Cargo.lock SHA-256 mismatch')
    shutil.copy2(private_lock, EVIDENCE / 'Cargo.lock')
    manifests: dict[str, str] = {}
    for manifest in sorted(SOURCE.rglob('Cargo.toml')):
        if manifest.is_file() and not manifest.is_symlink():
            manifests[manifest.relative_to(SOURCE).as_posix()] = sha256(manifest)
    MANIFEST_HASHES.update(manifests)
    write_json(EVIDENCE / 'source-lock-manifests.json', {
        'source_revision': SOURCE_REVISION, 'source_archive_stage_path': str(archive_path),
        'source_archive_sha256': SOURCE_ARCHIVE_SHA256,
        'lock_candidate_stage_path': str(lock_candidate), 'lock_sha256': LOCK_SHA256,
        'cargo_manifests_sha256': manifests, 'tracked_cargo_config': False,
    })

    sample_resources()
    run_command('rustup-version', [str(RUSTUP), '--version'], env)
    run_command('rustup-install', [str(RUSTUP), 'toolchain', 'install', '1.77.2',
                                   '--profile', 'minimal', '--no-self-update'], env)
    toolchain_bin = RUSTUP_HOME / 'toolchains' / TOOLCHAIN / 'bin'
    rustc = toolchain_bin / 'rustc'
    cargo = toolchain_bin / 'cargo'
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError('private Rustup installation lacks direct rustc or cargo binary')
    env['PATH'] = str(toolchain_bin) + ':/usr/bin:/bin:/usr/sbin:/sbin'
    env['RUSTC'] = str(rustc)
    rustc_version = run_command('rustc-version', [str(rustc), '--version', '--verbose'], env)
    rustc_output = (EVIDENCE / 'rustc-version.stdout').read_text(errors='replace')
    if rustc_version != 0 or not rustc_output.startswith('rustc 1.77.2 ') or \
            'host: x86_64-unknown-linux-gnu' not in rustc_output:
        raise RuntimeError('direct private rustc version or host did not match Rust 1.77.2 Linux x86_64')
    cargo_version = run_command('cargo-version', [str(cargo), '--version', '--verbose'], env)
    cargo_output = (EVIDENCE / 'cargo-version.stdout').read_text(errors='replace')
    if cargo_version != 0 or not cargo_output.startswith('cargo 1.77.2 '):
        raise RuntimeError('direct private Cargo version did not match 1.77.2')

    write_json(EVIDENCE / 'host.json', {
        'platform_system': platform.system(), 'platform_machine': platform.machine(),
        'uname': subprocess.run(['/usr/bin/uname', '-a'], capture_output=True,
                                text=True, check=True, timeout=5).stdout.strip(),
        'os_release': Path('/etc/os-release').read_text(encoding='utf-8', errors='replace'),
        'rustup_binary': str(RUSTUP), 'rustup_sha256': sha256(RUSTUP),
        'rustup_version_command': str(EVIDENCE / 'rustup-version.stdout'),
        'rustc_binary': str(rustc), 'rustc_sha256': sha256(rustc),
        'cargo_binary': str(cargo), 'cargo_sha256': sha256(cargo),
        'rustc_version_command': str(EVIDENCE / 'rustc-version.stdout'),
        'cargo_version_command': str(EVIDENCE / 'cargo-version.stdout'),
    })

    for row_name, features in POSITIVE_ROWS:
        check_deadline()
        if sha256(private_lock) != LOCK_SHA256:
            raise RuntimeError('Cargo.lock changed before positive row ' + row_name)
        if {manifest.relative_to(SOURCE).as_posix(): sha256(manifest)
                for manifest in sorted(SOURCE.rglob('Cargo.toml'))
                if manifest.is_file() and not manifest.is_symlink()} != MANIFEST_HASHES:
            raise RuntimeError('Cargo manifests changed before positive row ' + row_name)
        argv = [str(cargo), 'check', '--locked', '--lib', '--features', features]
        status = run_command('cargo-' + row_name, argv, env,
                             expected_status=None, cwd=SOURCE)
        POSITIVE_RESULTS.append({
            'row': row_name, 'features': features, 'status': status,
            'argv': argv, 'stdout': f'cargo-{row_name}.stdout',
            'stderr': f'cargo-{row_name}.stderr',
        })
        write_json(EVIDENCE / 'positive-rows-in-progress.json', POSITIVE_RESULTS)
        if sha256(private_lock) != LOCK_SHA256:
            raise RuntimeError('Cargo.lock changed during positive row ' + row_name)
        if {manifest.relative_to(SOURCE).as_posix(): sha256(manifest)
                for manifest in sorted(SOURCE.rglob('Cargo.toml'))
                if manifest.is_file() and not manifest.is_symlink()} != MANIFEST_HASHES:
            raise RuntimeError('Cargo manifests changed during positive row ' + row_name)

    check_deadline()
    if sha256(private_lock) != LOCK_SHA256:
        raise RuntimeError('Cargo.lock changed before negative prerequisite')
    if {manifest.relative_to(SOURCE).as_posix(): sha256(manifest)
            for manifest in sorted(SOURCE.rglob('Cargo.toml'))
            if manifest.is_file() and not manifest.is_symlink()} != MANIFEST_HASHES:
        raise RuntimeError('Cargo manifests changed before negative prerequisite')
    negative_name, negative_features = NEGATIVE_ROW
    negative_argv = [str(cargo), 'check', '--locked', '--lib', '--features', negative_features]
    negative_status = run_command('cargo-' + negative_name, negative_argv, env,
                                  expected_status=None, cwd=SOURCE)
    negative_text = ''.join((EVIDENCE / f'cargo-{negative_name}.{suffix}').read_text(
        errors='replace') for suffix in ('stdout', 'stderr'))
    diagnostic_present = EXPECTED_DIAGNOSTIC in negative_text
    NEGATIVE_RESULT = {
        'row': negative_name, 'features': negative_features, 'status': negative_status,
        'expected_status': 101, 'exact_diagnostic': EXPECTED_DIAGNOSTIC,
        'exact_diagnostic_present': diagnostic_present,
        'argv': negative_argv, 'stdout': f'cargo-{negative_name}.stdout',
        'stderr': f'cargo-{negative_name}.stderr',
        'accepted': negative_status == 101 and diagnostic_present,
    }
    write_json(EVIDENCE / 'negative-prerequisite.json', NEGATIVE_RESULT)
    if sha256(private_lock) != LOCK_SHA256:
        raise RuntimeError('Cargo.lock changed during negative prerequisite')
    if {manifest.relative_to(SOURCE).as_posix(): sha256(manifest)
            for manifest in sorted(SOURCE.rglob('Cargo.toml'))
            if manifest.is_file() and not manifest.is_symlink()} != MANIFEST_HASHES:
        raise RuntimeError('Cargo manifests changed during negative prerequisite')
    if negative_status != 101:
        raise RuntimeError(f'negative prerequisite expected Cargo status 101, got {negative_status}')
    if not diagnostic_present:
        raise RuntimeError('negative prerequisite omitted the exact intentional sys/no_object diagnostic')

    positive_pass = len(POSITIVE_RESULTS) == len(POSITIVE_ROWS) and all(
        row['status'] == 0 for row in POSITIVE_RESULTS)
    (EVIDENCE / 'result.txt').write_text(
        f"positive_rows={sum(row['status'] == 0 for row in POSITIVE_RESULTS)}/"
        f'{len(POSITIVE_ROWS)}; negative_prerequisite='
        f"{'accepted' if NEGATIVE_RESULT['accepted'] else 'failed'}; "
        'compiler-only on frozen native Linux source; no runtime behavior proven.\n',
        encoding='utf-8')
    return 0 if positive_pass and NEGATIVE_RESULT['accepted'] else 1


if __name__ == '__main__':
    exit_status = 1
    error_text = None
    try:
        exit_status = main()
    except BaseException as exc:
        error_text = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        try:
            EVIDENCE.mkdir(mode=0o700, exist_ok=True)
            (EVIDENCE / 'failure.txt').write_text(error_text, encoding='utf-8')
            if ACTIVE_CHILD is not None:
                stop_child(ACTIVE_CHILD)
        except BaseException as export_error:
            print(f'failure_record_error={export_error!r}', file=sys.stderr, flush=True)
        exit_status = 1
    finally:
        try:
            if EVIDENCE.is_dir() and EXPECTED_STAGE.is_dir() \
                    and not (EXPECTED_STAGE / 'proof-evidence').exists():
                export_evidence()
        except BaseException:
            print('evidence_export_failed:\n' + traceback.format_exc(), file=sys.stderr, flush=True)
            exit_status = 1
    if error_text:
        print(error_text, file=sys.stderr, flush=True)
    if exit_status == 0:
        print('linux_current_feature_compilation=pass', flush=True)
    else:
        print('linux_current_feature_compilation=incomplete_or_failed', flush=True)
    sys.exit(exit_status)
