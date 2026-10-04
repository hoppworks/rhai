"""Run frozen sys/net/process examples with private Rust 1.77.2 and bounded evidence."""
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

REVISION = '60048ec4d3d615fac3250404ce61b8cae14dfcb8'
SOURCE_ARCHIVE_SHA256 = 'ce8bcb76a6e839a5ee293f53d70784731bcfbb65b6694aa0e5b1ded2b00661d6'
LOCK_SHA256 = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
EXPECTED_RUN_SCOPED_SHA256 = '9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d'
EXPECTED_RUNNER_INIT_SHA256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
EXPECTED_PYGUARD_SHA256 = 'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f'
INPUT_STAGE = Path(os.environ.get('PROOF_STAGE', ''))
EXPECTED_STAGE = Path(os.environ.get('EXPECTED_PROOF_STAGE', ''))
RUSTUP = Path(os.environ.get('RUSTUP_BIN', ''))
TOOLCHAIN = '1.77.2-x86_64-unknown-linux-gnu'
FEATURES = 'testing-environ,sys,net'
PRESCRIBED_STAGE = Path('/root/rhai-linux-sys-process-example-60048ec4-20261004')
PRESCRIBED_SCOPE = Path('/root/.local/share/agent-builds/rhai/linux-sys-process-example-60048ec4-20261004')
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR'])
START = time.monotonic()
DEADLINE = START + 540
WORK_DEADLINE = DEADLINE - 30
SAMPLE_INTERVAL = 1.0
PREEMPTIVE_STORAGE_KIB = 1_572_864
HARD_STORAGE_KIB = 2 * 1024 * 1024
HARD_RSS_KIB = 2 * 1024 * 1024
MAX_DESCENDANTS = 16
HELPER_EXIT_STATUS = 1

STAGE = RUNTIME / 'evidence'
EVIDENCE = EXPECTED_STAGE / 'proof-evidence'
CONTRACT = INPUT_STAGE / 'contract.md'
SOURCE_ARCHIVE = INPUT_STAGE / 'source.tar'
LOCK_SOURCE = INPUT_STAGE / 'Cargo.lock.accepted'
INTERRUPT_REQUEST = Path(os.environ.get('INTERRUPT_REQUEST', ''))
SOURCE = RUNTIME / 'source'
CARGO_HOME = RUNTIME / 'cargo-home'
RUSTUP_HOME = RUNTIME / 'rustup-home'
TARGET = RUNTIME / 'target'
PRIVATE_HOME = RUNTIME / 'home'
PRIVATE_TMP = Path(os.environ.get('TMPDIR', ''))
SAMPLES: list[dict[str, object]] = []
MAXIMA = {'storage_kib': 0, 'rss_kib': 0, 'descendants': 0}
COMMANDS: list[dict[str, object]] = []
ORIGINAL_EXAMPLES: dict[Path, bytes] = {}
ORIGINAL_EXAMPLE_HASHES: dict[str, str] = {}
INJECTED_EXAMPLE_HASHES: dict[str, str] = {}
CONTROL_RESULTS: list[dict[str, object]] = []
ACTIVE_CHILD: subprocess.Popen[bytes] | None = None
INTERRUPTED: int | None = None
IDENTITY_ROWS: list[tuple[str, dict[str, object] | None]] = []


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def process_identity(pid: int) -> dict[str, object] | None:
    proc = Path('/proc') / str(pid)
    try:
        stat = (proc / 'stat').read_text(encoding='ascii')
        fields = stat[stat.rfind(')') + 2:].split()
        command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(
            'utf-8', errors='replace').strip()
        return {'pid': pid, 'ppid': int(fields[1]), 'pgid': int(fields[2]),
                'start_ticks': fields[19], 'cmdline': command}
    except (FileNotFoundError, ProcessLookupError):
        return None
    except (PermissionError, OSError, IndexError, ValueError) as exc:
        raise RuntimeError(f'cannot capture exact process identity for PID {pid}: {exc}') from exc


def record_process_identity(label: str, pid: int,
                            identity: dict[str, object] | None) -> None:
    if identity is None and label.startswith('command:'):
        return
    IDENTITY_ROWS.append((label, identity))
    path = STAGE / 'process-identities.tsv'
    if not path.exists():
        path.write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n', encoding='utf-8')
    if identity is None:
        row = f'{label}\t{pid}\t<identity-unavailable>\t<identity-unavailable>\t<identity-unavailable>\t\n'
    else:
        row = (f"{label}\t{pid}\t{identity['ppid']}\t{identity['pgid']}\t"
               f"{identity['start_ticks']}\t{identity['cmdline']}\n")
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row)
        stream.flush()
        os.fsync(stream.fileno())


def capture_runtime_proof() -> None:
    print(f'PRIVATE_RUNTIME {RUNTIME}', flush=True)
    if not RUNTIME.is_absolute() or not RUNTIME.is_dir():
        raise RuntimeError('AGENT_RUNTIME_DIR must be an existing absolute scoped runtime')
    STAGE.mkdir(mode=0o700, parents=True)
    helper_pid = os.getpid()
    supervisor_pid = os.getppid()
    identity_errors: dict[str, str] = {}
    try:
        helper = process_identity(helper_pid)
    except Exception as exc:
        helper = None
        identity_errors['helper'] = repr(exc)
    try:
        supervisor = process_identity(supervisor_pid)
    except Exception as exc:
        supervisor = None
        identity_errors['scoped_supervisor'] = repr(exc)
    record_process_identity('helper', helper_pid, helper)
    record_process_identity('scoped-supervisor', supervisor_pid, supervisor)
    write_json(STAGE / 'early-runtime-identity.json', {
        'runtime': str(RUNTIME), 'helper': helper, 'scoped_supervisor': supervisor,
        'identity_errors': identity_errors,
        'captured_before_stage_validation_or_external_command': True,
    })
    if helper is None or supervisor is None:
        raise RuntimeError('helper or scoped-supervisor identity unavailable/unknown; failing before commands')


def validate_stage_inputs() -> None:
    for label, path in (('input stage', INPUT_STAGE), ('expected stage', EXPECTED_STAGE)):
        if not path.is_absolute() or not path.is_dir() or path.is_symlink():
            raise RuntimeError(f'{label} must be an existing absolute real directory: {path}')
    if INPUT_STAGE.resolve() != EXPECTED_STAGE.resolve():
        raise RuntimeError('staged input and expected output must identify the same canonical stage')
    if EXPECTED_STAGE.resolve() != PRESCRIBED_STAGE.resolve():
        raise RuntimeError(f'expected stage is not the prescribed unique directory: {PRESCRIBED_STAGE}')
    if RUNTIME.parent.resolve() != PRESCRIBED_SCOPE.resolve():
        raise RuntimeError(f'private runtime is outside the prescribed project scope: {PRESCRIBED_SCOPE}')
    for label, path in (('source archive', SOURCE_ARCHIVE), ('compatible lock', LOCK_SOURCE),
                        ('contract', CONTRACT), ('rustup executable', RUSTUP)):
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f'{label} is absent or not a regular non-symlink file: {path}')
    if sha256(SOURCE_ARCHIVE) != SOURCE_ARCHIVE_SHA256:
        raise RuntimeError('staged source archive hash mismatch')
    if sha256(LOCK_SOURCE) != LOCK_SHA256:
        raise RuntimeError('staged compatible lock hash mismatch')
    if EVIDENCE.exists():
        raise FileExistsError(f'evidence destination already exists; preserve it: {EVIDENCE}')
    if not PRIVATE_TMP.is_absolute():
        raise RuntimeError('private temporary-directory path must be absolute')
    if INTERRUPT_REQUEST.exists():
        raise InterruptedError('launcher cancellation request exists before helper setup')


def export_destination_is_safe() -> bool:
    return (INPUT_STAGE.is_absolute() and EXPECTED_STAGE.is_absolute()
            and INPUT_STAGE.is_dir() and EXPECTED_STAGE.is_dir()
            and not INPUT_STAGE.is_symlink() and not EXPECTED_STAGE.is_symlink()
            and INPUT_STAGE.resolve() == EXPECTED_STAGE.resolve())


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
    if INTERRUPTED is not None and not during_export:
        raise InterruptedError(f'interrupted by signal {INTERRUPTED}')
    if INTERRUPT_REQUEST.is_file() and not during_export:
        raise InterruptedError('launcher cancellation request observed')


def sample_resources() -> None:
    check_deadline()
    def capture(name: str, argv: list[str]) -> str:
        child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, close_fds=True)
        try:
            record_process_identity(f'command:{name}', child.pid, process_identity(child.pid))
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stop_child(child)
            raise TimeoutError(f'{name} sampling command exceeded five seconds')
        except BaseException:
            stop_child(child)
            raise
        if child.returncode != 0:
            raise RuntimeError(f'{name} sampling command failed: {stderr[-500:]}')
        return stdout

    storage_output = capture('du', ['/usr/bin/du', '-sk', str(RUNTIME)])
    storage = int(storage_output.split()[0])
    ps_output = capture('ps', ['/bin/ps', '-e', '-o', 'pid=,ppid=,rss='])
    rows: dict[int, tuple[int, int]] = {}
    for line in ps_output.splitlines():
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


def run_command(name: str, argv: list[str], env: dict[str, str], *,
                expected_status: int | None = 0, cwd: Path | None = None,
                binary_stdout: Path | None = None,
                env_overrides: dict[str, str] | None = None) -> int:
    global ACTIVE_CHILD
    check_deadline()
    stdout_path = binary_stdout or (STAGE / f'{name}.stdout')
    stderr_path = STAGE / f'{name}.stderr'
    status_path = STAGE / f'{name}.status'
    command_cwd = SOURCE if cwd is None else cwd
    if not command_cwd.is_dir():
        raise RuntimeError(f'command working directory does not exist: {command_cwd}')
    command_env = dict(env)
    if env_overrides:
        command_env.update(env_overrides)
    record: dict[str, object] = {
        'name': name, 'argv': argv, 'expected_status': expected_status,
        'stdout': str(stdout_path.relative_to(RUNTIME)),
        'stderr': str(stderr_path.relative_to(RUNTIME)), 'cwd': str(command_cwd),
        'env_overrides': env_overrides or {},
        'started_monotonic_seconds': round(time.monotonic() - START, 3),
    }
    COMMANDS.append(record)
    print(f'command={name} argv={argv!r}', flush=True)
    next_sample = time.monotonic()
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        child = subprocess.Popen(argv, cwd=command_cwd, env=command_env,
                                 stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        ACTIVE_CHILD = child
        record['spawned'] = True
        record_process_identity(f'command:{name}', child.pid, process_identity(child.pid))
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
    return status


def extract_archive(archive_path: Path) -> None:
    """Extract a git archive while rejecting paths or links outside the runtime."""
    root = SOURCE.resolve()
    SOURCE.mkdir()
    with tarfile.open(archive_path, 'r:') as archive:
        for member in archive.getmembers():
            check_deadline()
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
    if SOURCE.exists():
        raise RuntimeError('frozen source must not exist before its archive is created')
    if not SOURCE_ARCHIVE.is_file():
        raise RuntimeError(f'frozen source archive is absent: {SOURCE_ARCHIVE}')
    return INPUT_STAGE


def manifest_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    for manifest in sorted(SOURCE.rglob('Cargo.toml')):
        if manifest.is_file() and not manifest.is_symlink():
            result[manifest.relative_to(SOURCE).as_posix()] = sha256(manifest)
    return result


def inject_expected_value(file_name: str, anchor: str, replacement: str) -> None:
    path = SOURCE / file_name
    original = path.read_bytes()
    ORIGINAL_EXAMPLES[path] = original
    relative = path.relative_to(SOURCE).as_posix()
    ORIGINAL_EXAMPLE_HASHES[relative] = sha256_bytes(original)
    text = original.decode('utf-8')
    if text.count(anchor) != 1:
        raise RuntimeError(f'expected exactly one source assertion anchor in {relative}')
    changed = text.replace(anchor, replacement, 1).encode('utf-8')
    path.write_bytes(changed)
    INJECTED_EXAMPLE_HASHES[relative] = sha256(path)


def record_original_example(file_name: str) -> None:
    path = SOURCE / file_name
    original = path.read_bytes()
    ORIGINAL_EXAMPLES[path] = original
    relative = path.relative_to(SOURCE).as_posix()
    ORIGINAL_EXAMPLE_HASHES[relative] = sha256_bytes(original)


def restore_example_sources() -> None:
    for path, original in ORIGINAL_EXAMPLES.items():
        path.write_bytes(original)
        actual = sha256(path)
        expected = ORIGINAL_EXAMPLE_HASHES[path.relative_to(SOURCE).as_posix()]
        if actual != expected:
            raise RuntimeError(f'private example source restoration mismatch: {path.name}')


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='replace')


def verify_control(name: str, status: int, expected_status: int,
                   stderr: str, required_diagnostics: list[str], *,
                   stdout: str = '', required_output: list[str] | None = None) -> None:
    missing = [item for item in required_diagnostics if item not in stderr]
    missing_output = [item for item in (required_output or []) if item not in stdout]
    if status != expected_status or missing or missing_output:
        raise RuntimeError(f'{name} did not fail at its intended assertion; '
                           f'status={status}, missing diagnostics={missing!r}, '
                           f'missing stdout readbacks={missing_output!r}')
    CONTROL_RESULTS.append({
        'name': name, 'status': status, 'expected_status': expected_status,
        'intended_assertion_observed': True,
        'required_diagnostics': required_diagnostics,
        'required_output': required_output or [],
    })
    write_json(STAGE / 'control-results.json', CONTROL_RESULTS)


def verify_pass(name: str, status: int, stdout: str, expected_output: str | list[str]) -> None:
    required = [expected_output] if isinstance(expected_output, str) else expected_output
    missing = [item for item in required if item not in stdout]
    if status != 0 or missing:
        raise RuntimeError(f'{name} positive run failed or lacked independent readback; '
                           f'status={status}, missing output={missing!r}')
    CONTROL_RESULTS.append({
        'name': name, 'status': status, 'expected_status': 0,
        'independent_readback': required,
    })
    write_json(STAGE / 'control-results.json', CONTROL_RESULTS)


def export_evidence() -> None:
    check_deadline(during_export=True)
    if not export_destination_is_safe():
        raise RuntimeError('refusing evidence export: expected stage canonical identity is unverified')
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
    write_json(STAGE / 'source-restoration.json', {
        'original_example_sha256': ORIGINAL_EXAMPLE_HASHES,
        'injected_example_sha256': INJECTED_EXAMPLE_HASHES,
        'restored_examples_match_original_bytes': bool(ORIGINAL_EXAMPLES)
            and all(sha256(path) == ORIGINAL_EXAMPLE_HASHES[path.relative_to(SOURCE).as_posix()]
                    for path in ORIGINAL_EXAMPLES),
        'manifests_sha256_after_restoration': manifest_hashes() if SOURCE.is_dir() else {},
        'cargo_lock_sha256_after_execution': sha256(SOURCE / 'Cargo.lock')
            if (SOURCE / 'Cargo.lock').is_file() else None,
    })
    write_json(STAGE / 'package-result.json', {
        'source_revision': REVISION, 'compatible_lock_sha256': LOCK_SHA256,
        'features': FEATURES, 'examples': ['sys', 'net', 'sys_process'],
        'cargo_build_invocations': sum(
            row.get('name') == 'cargo-build-examples' and row.get('spawned') is True
            for row in COMMANDS),
        'controls': CONTROL_RESULTS,
        'all_controls_and_positive_runs_passed': len(CONTROL_RESULTS) == 6
            and all(row.get('status') == row.get('expected_status') for row in CONTROL_RESULTS),
        'helper_exit_status': HELPER_EXIT_STATUS,
        'scope': 'Rust 1.77.2 Linux x86_64 examples through real Engine; '
                 'host file, loopback peer and self-reexecuted process fixture',
    })
    write_json(STAGE / 'export.json', {
        'runtime': str(RUNTIME), 'expected_outer_scope': str(RUNTIME.parent),
        'evidence_destination': str(EVIDENCE),
        'elapsed_seconds_at_export': round(time.monotonic() - START, 3),
        'helper_deadline_seconds': 540, 'helper_work_deadline_seconds': 510,
        'export_deadline_checks_between_items': True,
        'individual_copy_operations_preemptible': False,
        'partial_evidence_may_remain_if_export_fails': True,
        'runtime_cleanup_owner': 'run_scoped.py; coordinator must independently read back',
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
    capture_runtime_proof()
    validate_stage_inputs()
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise RuntimeError('prepared proof requires native Linux x86_64')
    shutil.copy2(Path(__file__), STAGE / 'helper-used.py')
    shutil.copy2(CONTRACT, STAGE / 'contract.md')
    (STAGE / 'contract-sha256.txt').write_text(sha256(CONTRACT) + '\n', encoding='ascii')
    if not LOCK_SOURCE.is_file() or sha256(LOCK_SOURCE) != LOCK_SHA256:
        raise RuntimeError('staged compatible lock is absent or has the wrong SHA-256')
    if not PRIVATE_TMP.is_absolute():
        raise RuntimeError('private temporary-directory path must be absolute')
    if PRIVATE_TMP.exists():
        if PRIVATE_TMP.is_symlink() or not PRIVATE_TMP.is_dir():
            raise RuntimeError('runner-provided private tmp path is not a real directory')
    else:
        PRIVATE_TMP.mkdir(mode=0o700)
    if Path(os.environ.get('TMPDIR', '')).resolve() != PRIVATE_TMP.resolve():
        raise RuntimeError('runner TMPDIR does not name AGENT_RUNTIME_DIR/tmp')
    if not PRIVATE_TMP.resolve().is_relative_to(RUNTIME.resolve()):
        raise RuntimeError('private temporary directory escaped AGENT_RUNTIME_DIR')
    CARGO_HOME.mkdir(mode=0o700)
    RUSTUP_HOME.mkdir(mode=0o700)
    PRIVATE_HOME.mkdir(mode=0o700)
    env = {
        'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME': str(PRIVATE_HOME), 'TMPDIR': str(PRIVATE_TMP),
        'TMP': str(PRIVATE_TMP), 'TEMP': str(PRIVATE_TMP),
        'CARGO_HOME': str(CARGO_HOME), 'RUSTUP_HOME': str(RUSTUP_HOME),
        'CARGO_TARGET_DIR': str(TARGET), 'CARGO_BUILD_JOBS': '2',
        'CARGO_INCREMENTAL': '0', 'CARGO_PROFILE_DEV_DEBUG': '0',
        'CARGO_TERM_COLOR': 'never', 'RUST_BACKTRACE': '0',
    }
    for forbidden in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER',
                      'RUSTC_WORKSPACE_WRAPPER', 'CARGO_HOME_CONFIG'):
        if forbidden in env:
            raise RuntimeError(f'unexpected compiler override in private environment: {forbidden}')
    source_archive = RUNTIME / 'frozen-source.tar'
    shutil.copy2(SOURCE_ARCHIVE, source_archive)
    archive_sha = sha256(source_archive)
    if archive_sha != SOURCE_ARCHIVE_SHA256:
        raise RuntimeError('staged source archive hash mismatch')
    extract_archive(source_archive)
    source_archive.unlink()
    for config_path in (SOURCE / '.cargo/config', SOURCE / '.cargo/config.toml'):
        if config_path.exists():
            raise RuntimeError(f'frozen source contains Cargo config override: {config_path.name}')
    if (SOURCE / 'Cargo.lock').exists():
        raise RuntimeError('unexpected root Cargo.lock in frozen archive; preserve lock provenance')
    private_lock = SOURCE / 'Cargo.lock'
    shutil.copy2(LOCK_SOURCE, private_lock)
    if sha256(private_lock) != LOCK_SHA256:
        raise RuntimeError('private compatible lock hash mismatch')
    shutil.copy2(private_lock, STAGE / 'Cargo.lock')
    before_manifests = manifest_hashes()
    write_json(STAGE / 'source-lock-manifests.json', {
        'revision': REVISION, 'archive_sha256': archive_sha,
        'lock_source': str(LOCK_SOURCE), 'lock_sha256': LOCK_SHA256,
        'cargo_manifests_sha256': before_manifests,
        'tracked_root_cargo_config': False,
        'private_environment_sets_rustflags_or_wrappers': False,
    })
    sample_resources()
    run_command('rustup-install', [str(RUSTUP), 'toolchain', 'install', TOOLCHAIN,
                                   '--profile', 'minimal', '--no-self-update'],
                env, cwd=RUNTIME)
    toolchain_bin = RUSTUP_HOME / 'toolchains' / TOOLCHAIN / 'bin'
    rustc, cargo = toolchain_bin / 'rustc', toolchain_bin / 'cargo'
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError('private Rustup install lacks direct rustc or cargo binary')
    env['PATH'] = str(toolchain_bin) + ':/usr/bin:/bin:/usr/sbin:/sbin'
    env['RUSTC'] = str(rustc)
    run_command('rustc-version', [str(rustc), '--version', '--verbose'], env)
    rustc_text = read_text(STAGE / 'rustc-version.stdout')
    if not rustc_text.startswith('rustc 1.77.2 ') or 'host: x86_64-unknown-linux-gnu' not in rustc_text:
        raise RuntimeError('direct private rustc version or host did not match Rust 1.77.2 Linux x86_64')
    run_command('cargo-version', [str(cargo), '--version', '--verbose'], env)
    cargo_text = read_text(STAGE / 'cargo-version.stdout')
    if not cargo_text.startswith('cargo 1.77.2 '):
        raise RuntimeError('direct private Cargo version did not match 1.77.2')
    write_json(STAGE / 'tool-versions.json', {
        'rustc_argv': [str(rustc), '--version', '--verbose'], 'rustc_stdout': rustc_text,
        'cargo_argv': [str(cargo), '--version', '--verbose'], 'cargo_stdout': cargo_text,
        'rustup_executable': str(RUSTUP), 'toolchain': TOOLCHAIN,
    })

    sys_anchor = '    assert_eq!(host_contents, "Rhaiting data");'
    sys_replacement = (
        '    let expected_host_contents = std::env::var("RHAI_EXAMPLE_SYS_EXPECTED_HOST")\n'
        '        .unwrap_or_else(|_| "Rhaiting data".to_owned());\n'
        '    assert_eq!(host_contents, expected_host_contents, "host file independent readback");'
    )
    net_anchor = '        received, b"ping",\n        "independent peer received the script bytes"'
    net_replacement = (
        '        received.as_slice(),\n'
        '        std::env::var("RHAI_EXAMPLE_NET_EXPECTED_PEER")\n'
        '            .unwrap_or_else(|_| "ping".to_owned()).as_bytes(),\n'
        '        "independent peer received the script bytes"'
    )
    inject_expected_value('examples/sys.rs', sys_anchor, sys_replacement)
    inject_expected_value('examples/net.rs', net_anchor, net_replacement)
    record_original_example('examples/sys_process.rs')
    sample_resources()
    if sha256(private_lock) != LOCK_SHA256:
        raise RuntimeError('Cargo.lock changed before example build')
    for config_path in (CARGO_HOME / 'config', CARGO_HOME / 'config.toml'):
        if config_path.exists():
            raise RuntimeError(f'private Cargo home contains config override: {config_path.name}')
    build_argv = [str(cargo), 'build', '--locked', '--example', 'sys', '--example', 'net',
                  '--example', 'sys_process',
                  '--features', FEATURES]
    run_command('cargo-build-examples', build_argv, env)
    if sha256(private_lock) != LOCK_SHA256:
        raise RuntimeError('Cargo.lock changed during example build')
    if manifest_hashes() != before_manifests:
        raise RuntimeError('Cargo manifests changed during private example build')
    restore_example_sources()
    if manifest_hashes() != before_manifests or sha256(private_lock) != LOCK_SHA256:
        raise RuntimeError('restored frozen manifests/lock do not match their pre-build hashes')
    write_json(STAGE / 'source-restoration-before-runs.json', {
        'original_example_sha256': ORIGINAL_EXAMPLE_HASHES,
        'injected_example_sha256': INJECTED_EXAMPLE_HASHES,
        'restored_example_sha256': {
            path.relative_to(SOURCE).as_posix(): sha256(path) for path in ORIGINAL_EXAMPLES
        },
        'manifests_unchanged': True, 'cargo_lock_sha256': sha256(private_lock),
    })
    for example in ('sys', 'net', 'sys_process'):
        binary = TARGET / 'debug/examples' / example
        if not binary.is_file():
            raise RuntimeError(f'Cargo did not produce expected example executable: {binary}')

    sys_wrong = 'deliberately wrong host contents'
    sys_status = run_command('sys-red', [str(TARGET / 'debug/examples/sys')], env,
                             expected_status=101,
                             env_overrides={'RHAI_EXAMPLE_SYS_EXPECTED_HOST': sys_wrong})
    sys_stderr = read_text(STAGE / 'sys-red.stderr')
    verify_control('sys-red', sys_status, 101, sys_stderr, [
        'host file independent readback', 'left: "Rhaiting data"',
        f'right: {json.dumps(sys_wrong)}',
    ])
    sys_status = run_command('sys-green', [str(TARGET / 'debug/examples/sys')], env)
    verify_pass('sys-green', sys_status, read_text(STAGE / 'sys-green.stdout'),
                'host file now contains "Rhaiting data"')

    net_wrong = 'wrong peer bytes'
    net_status = run_command('net-red', [str(TARGET / 'debug/examples/net')], env,
                             expected_status=101,
                             env_overrides={'RHAI_EXAMPLE_NET_EXPECTED_PEER': net_wrong})
    net_stderr = read_text(STAGE / 'net-red.stderr')
    wrong_peer_debug = '[' + ', '.join(str(byte) for byte in net_wrong.encode()) + ']'
    verify_control('net-red', net_status, 101, net_stderr, [
        'independent peer received the script bytes',
        'left: [112, 105, 110, 103]', f'right: {wrong_peer_debug}',
    ])
    net_status = run_command('net-green', [str(TARGET / 'debug/examples/net')], env)
    verify_pass('net-green', net_status, read_text(STAGE / 'net-green.stdout'),
                'Peer received ping; script received pong.')

    process_binary = str(TARGET / 'debug/examples/sys_process')
    process_status = run_command(
        'sys-process-red', [process_binary], env, expected_status=101,
        env_overrides={'RHAI_SYS_PROCESS_EXAMPLE_EXPECTED_EXIT': '8'})
    process_stderr = read_text(STAGE / 'sys-process-red.stderr')
    process_stdout = read_text(STAGE / 'sys-process-red.stdout')
    verify_control('sys-process-red', process_status, 101, process_stderr, [
        'RED control changes only the expected exit', 'left: 7', 'right: 8',
    ], stdout=process_stdout, required_output=[
        'Host read back run child record:',
        'Host read back spawned child record:',
        'Spawn wait was pending, then both cloned handles returned the same result.',
    ])
    process_status = run_command('sys-process-green', [process_binary], env)
    verify_pass('sys-process-green', process_status,
                read_text(STAGE / 'sys-process-green.stdout'), [
                    'Host read back run child record: "run child wrote its record\\n"',
                    'Host read back spawned child record: "spawn child observed release\\n"',
                    'Spawn wait was pending, then both cloned handles returned the same result.',
                ])

    leftovers = sorted(
        path.name for prefix in ('rhai-sys-example-*', 'rhai-sys-process-example-*')
        for path in PRIVATE_TMP.glob(prefix))
    write_json(STAGE / 'cleanup-readback.json', {
        'private_tmp': str(PRIVATE_TMP),
        'example_directory_prefixes': ['rhai-sys-example-*', 'rhai-sys-process-example-*'],
        'remaining_example_directories': leftovers,
        'all_scoped_example_directories_removed': not leftovers,
        'net_peer_joined_before_its_assertion': True,
    })
    if leftovers:
        raise RuntimeError(f'an example left its scoped temporary directories: {leftovers!r}')
    if len(CONTROL_RESULTS) != 6:
        raise RuntimeError('expected three intentional controls and three positive example runs')
    (STAGE / 'result.txt').write_text(
        'sys, net and sys_process example binaries built together once with private '
        'Rust/Cargo 1.77.2; each wrong-expectation control failed at its named assertion, '
        'then the default expectation passed with independent host readback. Examples only; '
        'not full release acceptance.\n', encoding='utf-8')
    return 0


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
        except BaseException as record_error:
            print(f'failure_record_error={record_error!r}', file=sys.stderr, flush=True)
        exit_status = 1
    finally:
        if INTERRUPTED is not None:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            if ORIGINAL_EXAMPLES:
                restore_example_sources()
        except BaseException:
            restoration_error = traceback.format_exc()
            try:
                STAGE.mkdir(mode=0o700, exist_ok=True)
                (STAGE / 'restoration-failure.txt').write_text(restoration_error, encoding='utf-8')
            except BaseException:
                pass
            print('source_restoration_failed:\n' + restoration_error, file=sys.stderr, flush=True)
            exit_status = 1
        try:
            HELPER_EXIT_STATUS = exit_status
            if STAGE.is_dir() and not EVIDENCE.exists():
                export_evidence()
        except BaseException:
            print('evidence_export_failed:\n' + traceback.format_exc(), file=sys.stderr, flush=True)
            exit_status = 1
    if error_text:
        print(error_text, file=sys.stderr, flush=True)
    if exit_status == 0:
        print('current_msrv_examples=pass', flush=True)
    else:
        print('current_msrv_examples=incomplete_or_failed', flush=True)
    sys.exit(exit_status)
