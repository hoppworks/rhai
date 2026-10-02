#!/usr/bin/env python3
"""Bounded private Rust 1.77.2 Linux follow-up for the two uncovered feature rows."""
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

SOURCE_REVISION = 'a2d7a8c2ace21e63c18b2e64cdce74e5e10afc94'
SOURCE_ARCHIVE_SHA256 = '551c03dbe3f4550db1b144b3e65d83f5bc66c132c1a9cffa59c83fce16bc41e1'
LOCK_SHA256 = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
RUSTUP = Path('/root/.cargo/bin/rustup')
TOOLCHAIN = '1.77.2-x86_64-unknown-linux-gnu'
EXPECTED_RUN_SCOPED_SHA256 = '9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d'
EXPECTED_INIT_SHA256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
EXPECTED_PYGUARD_SHA256 = 'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f'
EXPECTED_STAGE = Path('/root/rhai-linux-current-sys-net-behavior-a2d7a8c2-20261002-policy2')
EXPECTED_SCOPE = Path('/root/.local/share/agent-builds/rhai/linux-current-sys-net-behavior-a2d7a8c2-20261002-policy2')
REUSED_HELPER_SHA256 = 'f5461ba793c28da589afc9a75289156a42eb339ca8a453ff4f53ff70881093c3'
REUSED_EVIDENCE_SHA256 = {
    'source-lock-manifests.json': '579bb5b7fb6ef2c79104ed5addbbc1b75c3eb135ca73c8e5efde4db10e3c27b2',
    'positive-rows-in-progress.json': 'd6dfd6936b3b3faa29eb2731459df8507c9cb37f22097660a1b08be4937f35fd',
    'controls-in-progress.json': 'ff064e1e3ebdf098a4945df296a0dc6550102144d602f529d35b32e20eae4d4b',
    'commands.json': 'b2589420c8078975ee53bdb5eeb81ed08c28bc71a0b5447a82a13e3046973607',
    'host.json': '51be03f870b6f0ed37973d15100b2eb40cf452fb5cf68e5dad3510fa9d0bbb03',
    'rustc-version.stdout': 'f4679d0dda28ffcd994b39583743b88e06b6fe4a89fd7359aa1d147e5e660f11',
    'cargo-version.stdout': 'bd859f92e30f43b3d238342da4f9a98eaecf6fb4d9dcf317c4e27346f28b4a69',
    'helper-used.py': REUSED_HELPER_SHA256,
    'control-sys-filesystem-wrong-readback.stdout': 'c2c70d343903f8f8a2cda6a9ead4400e78ff713f6acb9b57a3a47ef3729f92cd',
    'control-sys-filesystem-wrong-readback.stderr': '650177feb4302d0715ab5efe6e4ca7f9fe05c4319fa5f8940c7d20a2f3b08a38',
    'control-sys-filesystem-wrong-readback.status': '39b8dc3fc8b44765c8e6f1adee04c5b465e555ab791cc42d0d9e810d5b64297c',
    'control-tcp-wrong-peer-readback.stdout': '0f4887639eaa5052f39d006881fde26c93d5af273bb9239d7de6c84c8ddbf20d',
    'control-tcp-wrong-peer-readback.stderr': '8688a71fc97f8103fa6963d0f4d08ed780735595169063d61f982216821722e5',
    'control-tcp-wrong-peer-readback.status': '39b8dc3fc8b44765c8e6f1adee04c5b465e555ab791cc42d0d9e810d5b64297c',
    'control-tcp-wrong-peer-writeback.stdout': 'e16861abb209f9f3d0a6e108f1ab126abfbe121850e3fcd8a3f7ec9957c42735',
    'control-tcp-wrong-peer-writeback.stderr': '514dc112f3d41dad8d2fe0f5154ab344cf1c7180e6ac73638da77c4cd29d6811',
    'control-tcp-wrong-peer-writeback.status': '39b8dc3fc8b44765c8e6f1adee04c5b465e555ab791cc42d0d9e810d5b64297c',
    'control-combined-wrong-host-readback.stdout': 'a3c59d1cf98836739e15784b35a24541a069ba3ad8c765e52d8da179fc7971f8',
    'control-combined-wrong-host-readback.stderr': '6d0d3fca882149f3cc8c81c39076a751f26f3da0336553061124d9d42b8ec590',
    'control-combined-wrong-host-readback.status': '39b8dc3fc8b44765c8e6f1adee04c5b465e555ab791cc42d0d9e810d5b64297c',
    'control-net-no-object-wrong-peer.stdout': '6d8b53aa5423044c96ffe4271d7ae8cb790485800b68f3b2b978c309c1e47292',
    'control-net-no-object-wrong-peer.stderr': 'a614dc867f437e8bbe9435aa23570f90ebb34613340f6a76e0d98c0b8432cac2',
    'control-net-no-object-wrong-peer.status': '39b8dc3fc8b44765c8e6f1adee04c5b465e555ab791cc42d0d9e810d5b64297c',
}
ACCEPTED_POLICY1_ROWS = (
    'combined-baseline', 'combined-no-index', 'net-no-object',
    'combined-metadata-serde', 'combined-sync', 'combined-i32-no-float',
    'combined-unchecked',
)
PLANNED_REMAINING_ROWS = ('combined-no-index-sync-metadata', 'combined-f32')
STAGE = Path(os.environ.get('PROOF_STAGE', ''))
REUSED_EVIDENCE = STAGE / 'reused-policy1'
RUNTIME = Path(os.environ.get('AGENT_RUNTIME_DIR', ''))
INTERRUPT_REQUEST = Path(os.environ.get('INTERRUPT_REQUEST', ''))
EVIDENCE = RUNTIME / 'evidence'
SOURCE = RUNTIME / 'source'
CARGO_HOME = RUNTIME / 'cargo-home'
RUSTUP_HOME = RUNTIME / 'rustup-home'
TARGET = RUNTIME / 'target'
PRIVATE_HOME = RUNTIME / 'home'
HELPER_DEADLINE_SECONDS = 540
WORK_DEADLINE_SECONDS = 510
EXPORT_RESERVE_SECONDS = 30
CARGO_JOBS = '2'
START = time.monotonic()
DEADLINE = START + HELPER_DEADLINE_SECONDS
WORK_DEADLINE = START + WORK_DEADLINE_SECONDS
SAMPLE_INTERVAL = 1.0
PREEMPTIVE_STORAGE_KIB = 1_572_864
HARD_STORAGE_KIB = 2_097_152
HARD_RSS_KIB = 2_097_152
MAX_DESCENDANTS = 16

TEST_ROWS = (
    ('combined-no-index-sync-metadata', 'testing-environ,sys,net,no_index,sync,metadata',
     ('sys_fs', 'sys_policy', 'net_connect', 'net_listen', 'net_reads', 'net_writes', 'combined_sys_net', 'net_metadata')),
    ('combined-f32', 'testing-environ,sys,net,f32_float',
     ('sys_fs', 'sys_policy', 'net_connect', 'net_listen', 'net_reads', 'net_writes', 'combined_sys_net')),
)
ASSERTION_CONTROLS = (
    ('sys-filesystem-wrong-readback', 'testing-environ,sys,net', 'sys_fs',
     'test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving',
     'RHAI_FILE_READ_WRONG_EXPECTATION',
     ('left: "abc"', 'right: "wrong expectation"')),
    ('tcp-wrong-peer-readback', 'testing-environ,sys,net', 'net_reads',
     'stream_read_string_returns_exact_lossy_text_from_peer_bytes',
     'RHAI_NET_WRONG_READ_EXPECTATION',
     ('left: "a�b"', 'right: "wrong peer payload"')),
    ('tcp-wrong-peer-writeback', 'testing-environ,sys,net', 'net_writes',
     'script_write_blob_preserves_exact_bytes',
     'RHAI_NET_WRONG_WRITE_EXPECTATION',
     ('left: [0, 255, 65]', 'right: [0, 254, 65]')),
    ('combined-wrong-host-readback', 'testing-environ,sys,net', 'combined_sys_net',
     'sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors',
     'RHAI_COMBINED_WRONG_EXPECTATION',
     ('fresh host readback must match independent expected bytes',
      'actual="filesystem-payload"', 'expected="incorrect filesystem expectation"')),
    ('net-no-object-wrong-peer', 'testing-environ,net,no_object', 'net_no_object',
     'registered_stream_functions_work_without_dot_syntax',
     'RHAI_NET_NO_OBJECT_WRONG_PEER_EXPECTATION',
     ('deliberately wrong independent peer expectation',
      'left: [112, 105, 110, 103]', 'right: [112, 97, 110, 103]')),
)


SAMPLES: list[dict[str, int | float]] = []
MAXIMA = {'storage_kib': 0, 'rss_kib': 0, 'descendants': 0}
COMMANDS: list[dict[str, object]] = []
POSITIVE_RESULTS: list[dict[str, object]] = []
CONTROL_RESULTS: list[dict[str, object]] = []
REUSE_RESULT: dict[str, object] = {}
MANIFEST_HASHES: dict[str, str] = {}
ACTIVE_CHILD: subprocess.Popen[bytes] | None = None
INTERRUPTED: int | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def validate_reused_evidence(receipt_dir: Path) -> dict[str, object]:
    """Verify the pinned policy1 proof before relying on its unaffected rows."""
    for name, expected in REUSED_EVIDENCE_SHA256.items():
        path = receipt_dir / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f'reused evidence SHA-256 mismatch: {name}')

    source = json.loads((receipt_dir / 'source-lock-manifests.json').read_text())
    if (source.get('source_revision') != SOURCE_REVISION
            or source.get('source_archive_sha256') != SOURCE_ARCHIVE_SHA256
            or source.get('lock_sha256') != LOCK_SHA256
            or source.get('tracked_cargo_config') is not False):
        raise RuntimeError('reused source, archive, lock, or Cargo configuration differs')

    prior_rows = json.loads((receipt_dir / 'positive-rows-in-progress.json').read_text())
    prior_names = tuple(row.get('row') for row in prior_rows)
    if prior_names != ACCEPTED_POLICY1_ROWS or any(
            row.get('status') != 0 or row.get('coverage_found') is not True
            or row.get('all_selected_targets_ran_once') is not True
            or row.get('all_tests_passed_without_ignored_or_filtered') is not True
            for row in prior_rows):
        raise RuntimeError('reused positive rows do not match the seven accepted policy1 rows')

    controls = json.loads((receipt_dir / 'controls-in-progress.json').read_text())
    expected_controls = tuple(control[0] for control in ASSERTION_CONTROLS)
    if tuple(row.get('name') for row in controls) != expected_controls or any(
            row.get('status') != 101 or row.get('expected_status') != 101
            or row.get('diagnostic_found') is not True
            or row.get('named_test_failed') is not True
            for row in controls):
        raise RuntimeError('reused five-control receipt is incomplete or not meaningful RED')
    for name, _features, target, test_name, _environment_control, context in ASSERTION_CONTROLS:
        output = ''.join((receipt_dir / f'control-{name}.{stream}').read_text(errors='replace')
                         for stream in ('stdout', 'stderr'))
        status = int((receipt_dir / f'control-{name}.status').read_text().strip())
        classification = classify_assertion_control(status, output, target, test_name, context)
        if status != 101 or not classification['diagnostic_found']:
            raise RuntimeError(f'reused raw control output is not the intended named RED: {name}')

    # The previous accepted helper is itself pinned, and its original plan must
    # contain exactly the seven accepted rows plus these two remaining rows.
    import ast
    prior_helper = (receipt_dir / 'helper-used.py').read_text(encoding='utf-8')
    prior_tree = ast.parse(prior_helper)
    prior_assignments = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in prior_tree.body if isinstance(node, ast.Assign)
        and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {'SOURCE_REVISION', 'SOURCE_ARCHIVE_SHA256', 'LOCK_SHA256',
                                   'TEST_ROWS', 'ASSERTION_CONTROLS'}
    }
    if (prior_assignments.get('SOURCE_REVISION') != SOURCE_REVISION
            or prior_assignments.get('SOURCE_ARCHIVE_SHA256') != SOURCE_ARCHIVE_SHA256
            or prior_assignments.get('LOCK_SHA256') != LOCK_SHA256
            or tuple(row[0] for row in prior_assignments.get('TEST_ROWS', ()))
            != ACCEPTED_POLICY1_ROWS + PLANNED_REMAINING_ROWS
            or tuple(row[0] for row in prior_assignments.get('ASSERTION_CONTROLS', ()))
            != expected_controls):
        raise RuntimeError('reused helper source/check logic is not the accepted nine-row plan')

    commands = json.loads((receipt_dir / 'commands.json').read_text())
    by_name = {row.get('name'): row for row in commands}
    required_statuses = {
        **{f'behavior-{name}': 0 for name in ACCEPTED_POLICY1_ROWS},
        **{f'control-{name}': 101 for name in expected_controls},
    }
    for name, status in required_statuses.items():
        command = by_name.get(name)
        if command is None or command.get('status') != status:
            raise RuntimeError(f'reused command receipt missing expected status: {name}')
        argv = command.get('argv', [])
        if '--locked' not in argv or 'test' not in argv:
            raise RuntimeError(f'reused command did not use locked Cargo test: {name}')

    host = json.loads((receipt_dir / 'host.json').read_text())
    if host.get('platform_system') != 'Linux' or host.get('platform_machine') != 'x86_64':
        raise RuntimeError('reused proof host is not Linux x86_64')
    rustc_version = (receipt_dir / 'rustc-version.stdout').read_bytes()
    cargo_version = (receipt_dir / 'cargo-version.stdout').read_bytes()
    if (not rustc_version.startswith(b'rustc 1.77.2 ')
            or b'host: x86_64-unknown-linux-gnu' not in rustc_version
            or not cargo_version.startswith(b'cargo 1.77.2 ')
            or b'host: x86_64-unknown-linux-gnu' not in cargo_version):
        raise RuntimeError('reused proof toolchain is not Rust/Cargo 1.77.2 Linux x86_64')

    return {
        'receipt_verified': True,
        'source_revision': SOURCE_REVISION,
        'source_archive_sha256': SOURCE_ARCHIVE_SHA256,
        'lock_sha256': LOCK_SHA256,
        'positive_rows_reused': list(ACCEPTED_POLICY1_ROWS),
        'controls_reused': list(expected_controls),
        'raw_control_logs_reclassified': True,
        'controls_executed_this_invocation': 0,
        'reused_receipt_directory': str(receipt_dir),
        'reused_receipt_files_sha256': dict(REUSED_EVIDENCE_SHA256),
        'previous_platform': host['platform_system'],
        'previous_machine': host['platform_machine'],
        'previous_rustc_version_sha256': REUSED_EVIDENCE_SHA256['rustc-version.stdout'],
        'previous_cargo_version_sha256': REUSED_EVIDENCE_SHA256['cargo-version.stdout'],
    }


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
            raise TimeoutError('540-second helper budget, including setup and export, expired')
        raise TimeoutError('510-second work budget expired; 30 seconds reserved for export')
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
        'captured_before_stage_validation_or_external_command': True,
    })
    if helper_identity is None or supervisor_identity is None:
        raise RuntimeError('required helper or scoped supervisor identity unavailable')


def validate_stage_inputs() -> None:
    """Fail closed on any stage other than the prescribed canonical directory."""
    if not STAGE.is_absolute() or not STAGE.is_dir() or STAGE.is_symlink():
        raise RuntimeError('PROOF_STAGE must be the existing absolute real input stage')
    if RUNTIME.parent.resolve() != EXPECTED_SCOPE.resolve():
        raise RuntimeError(f'private runtime is outside the prescribed project scope: {EXPECTED_SCOPE}')
    if not stage_identity_matches(STAGE, EXPECTED_STAGE):
        raise RuntimeError(f'PROOF_STAGE must resolve to the prescribed unique stage: {EXPECTED_STAGE}')
    for path in (STAGE / 'source.tar', STAGE / 'Cargo.lock.accepted'):
        if not path.is_file():
            raise FileNotFoundError(f'required explicitly staged input missing: {path}')
    for name in ('contract.md', 'run-sys-net-policy2.py'):
        if not (STAGE / name).is_file():
            raise FileNotFoundError(f'reviewed staged input missing: {STAGE / name}')
    for name in REUSED_EVIDENCE_SHA256:
        if not (REUSED_EVIDENCE / name).is_file():
            raise FileNotFoundError(f'reused accepted receipt missing: {REUSED_EVIDENCE / name}')
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
                expected_status: int | None = 0, cwd: Path | None = None,
                env_overrides: dict[str, str] | None = None,
                merge_streams: bool = False) -> int:
    global ACTIVE_CHILD
    check_deadline()
    stdout_path = EVIDENCE / f'{name}.stdout'
    stderr_path = EVIDENCE / f'{name}.stderr'
    status_path = EVIDENCE / f'{name}.status'
    command_cwd = RUNTIME if cwd is None else cwd
    if not command_cwd.is_dir():
        raise RuntimeError(f'command working directory does not exist: {command_cwd}')
    command_env = dict(env)
    if env_overrides:
        command_env.update(env_overrides)
    record: dict[str, object] = {
        'name': name, 'argv': argv, 'expected_status': expected_status,
        'stdout': stdout_path.name, 'stderr': stderr_path.name, 'cwd': str(command_cwd),
        'env_overrides': env_overrides or {}, 'merge_streams': merge_streams,
        'started_monotonic_seconds': round(time.monotonic() - START, 3),
    }
    COMMANDS.append(record)
    print(f'command={name} argv={argv!r}', flush=True)
    next_sample = time.monotonic()
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        child = subprocess.Popen(argv, cwd=command_cwd, env=command_env, stdin=subprocess.DEVNULL,
                                 stdout=stdout, stderr=subprocess.STDOUT if merge_streams else stderr)
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


def classify_assertion_control(status: int, output: str, target: str, test_name: str,
                               required_context: tuple[str, ...]) -> dict[str, object]:
    """Accept only the named, executed test's intended assertion failure."""
    import re

    named_failure = re.compile(rf'^    {re.escape(test_name)}$', re.MULTILINE)
    panic = re.compile(
        rf"^thread '{re.escape(test_name)}'(?: \((?:pid )?\d+\))? panicked at "
        rf'tests/{re.escape(target)}\.rs:\d+:\d+:', re.MULTILINE)
    result_pattern = re.compile(
        r'^test result: FAILED\. 0 passed; 1 failed; 0 ignored; 0 measured; \d+ filtered out;',
        re.MULTILINE)
    named_test_failed = bool(named_failure.search(output)) and bool(panic.search(output))
    one_test_failed = bool(result_pattern.search(output)) and 'running 1 test' in output
    context_found = bool(required_context) and all(item in output for item in required_context)
    standard_assertion = ('assertion `left == right` failed' in output
                          or bool(re.search(r'assertion failed(?::|\b)', output)))
    combined_host_assertion = (
        target == 'combined_sys_net'
        and test_name == 'sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors'
        and 'fresh host readback must match independent expected bytes' in output
        and 'actual="filesystem-payload"' in output
        and 'expected="incorrect filesystem expectation"' in output)
    assertion_context_found = standard_assertion or combined_host_assertion
    accepted = (status == 101 and named_test_failed and one_test_failed
                and assertion_context_found and context_found)
    return {
        'status_is_101': status == 101,
        'named_test_failed': named_test_failed,
        'exactly_one_test_ran_and_failed': one_test_failed,
        'assertion_panic_context_found': assertion_context_found,
        'intended_assertion_context_found': context_found,
        'required_assertion_context': list(required_context),
        'diagnostic_found': accepted,
    }


def positive_test_coverage(output: str, targets: tuple[str, ...]) -> dict[str, object]:
    """Require every selected integration binary to execute all tests successfully."""
    import re

    running = re.compile(r'^\s*Running tests/([A-Za-z0-9_]+)\.rs(?:\s|$)', re.MULTILINE)
    result = re.compile(
        r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; '
        r'(\d+) measured; (\d+) filtered out;', re.MULTILINE)
    lines = output.splitlines()
    observed_targets: list[str] = []
    summaries: dict[str, list[dict[str, int]]] = {}
    current: str | None = None
    for line in lines:
        match = running.match(line)
        if match:
            current = match.group(1)
            observed_targets.append(current)
        match = result.match(line)
        if match:
            if current is None:
                raise RuntimeError('test result appeared without a selected integration target')
            passed, failed, ignored, measured, filtered = map(int, match.groups())
            summaries.setdefault(current, []).append({
                'passed': passed, 'failed': failed, 'ignored': ignored,
                'measured': measured, 'filtered_out': filtered,
            })
    exact_targets = (len(observed_targets) == len(targets)
                     and set(observed_targets) == set(targets))
    final_rows = [{'target': target, **summaries[target][-1]}
                  for target in targets if target in summaries]
    all_executed = len(final_rows) == len(targets) and all(
        row['passed'] > 0 and row['failed'] == 0 and row['ignored'] == 0
        and row['measured'] == 0 and row['filtered_out'] == 0 for row in final_rows)
    return {'target_results': final_rows, 'expected_targets': list(targets),
            'all_selected_targets_ran_once': exact_targets,
            'all_tests_passed_without_ignored_or_filtered': all_executed,
            'coverage_found': exact_targets and all_executed}


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
        'positive_rows_executed': POSITIVE_RESULTS,
        'remaining_positive_row_count': len(TEST_ROWS),
        'remaining_planned_rows': list(PLANNED_REMAINING_ROWS),
        'previously_accepted_rows_reused': list(ACCEPTED_POLICY1_ROWS),
        'previously_accepted_controls_reused': REUSE_RESULT.get('controls_reused', []),
        'controls_executed_this_invocation': len(CONTROL_RESULTS),
        'successful_positive_rows': sum(row.get('status') == 0 for row in POSITIVE_RESULTS),
        'all_positive_rows_succeeded': len(POSITIVE_RESULTS) == len(TEST_ROWS)
            and all(row.get('status') == 0 for row in POSITIVE_RESULTS),
        'controls_executed_this_invocation_results': CONTROL_RESULTS,
        'reused_receipt_verified': bool(REUSE_RESULT.get('receipt_verified')),
    })
    write_json(EVIDENCE / 'export.json', {
        'source_revision': SOURCE_REVISION,
        'source_archive_sha256': SOURCE_ARCHIVE_SHA256,
        'compatible_lock_sha256': LOCK_SHA256,
        'runtime': str(RUNTIME), 'evidence_destination': str(destination),
        'elapsed_seconds_at_export': round(time.monotonic() - START, 3),
        'helper_deadline_seconds': HELPER_DEADLINE_SECONDS,
        'work_deadline_seconds': WORK_DEADLINE_SECONDS,
        'export_reserve_seconds': EXPORT_RESERVE_SECONDS,
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
    global REUSE_RESULT
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    capture_runtime_proof()
    validate_stage_inputs()
    REUSE_RESULT = validate_reused_evidence(REUSED_EVIDENCE)
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise RuntimeError('prepared proof requires native Linux x86_64')
    staged_contract = STAGE / 'contract.md'
    staged_helper = STAGE / 'run-sys-net-policy2.py'
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
        raise RuntimeError('executed helper path differs from explicitly staged helper')
    shutil.copy2(staged_helper, EVIDENCE / 'helper-used.py')
    shutil.copy2(staged_contract, EVIDENCE / 'contract.md')
    write_json(EVIDENCE / 'staged-input-identities.json', {
        'source.tar': {'path': str(STAGE / 'source.tar'), 'sha256': sha256(STAGE / 'source.tar')},
        'Cargo.lock.accepted': {'path': str(STAGE / 'Cargo.lock.accepted'),
                                'sha256': sha256(STAGE / 'Cargo.lock.accepted')},
        'run-sys-net-policy2.py': {'path': str(staged_helper), 'sha256': sha256(staged_helper)},
        'contract.md': {'path': str(staged_contract), 'sha256': sha256(staged_contract)},
        'run_scoped.py': {'path': str(STAGE / 'runner/tools/run_scoped.py'),
                          'sha256': runner_hashes['run_scoped.py']},
        'agentskills/__init__.py': {'path': str(STAGE / 'runner/tools/agentskills/__init__.py'),
                                    'sha256': runner_hashes['agentskills/__init__.py']},
        'agentskills/pyguard.py': {'path': str(STAGE / 'runner/tools/agentskills/pyguard.py'),
                                   'sha256': runner_hashes['agentskills/pyguard.py']},
        'reused_policy1_receipts': {
            name: {'path': str(REUSED_EVIDENCE / name), 'sha256': sha256(REUSED_EVIDENCE / name)}
            for name in REUSED_EVIDENCE_SHA256
        },
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
        'CARGO_TARGET_DIR': str(TARGET), 'CARGO_BUILD_JOBS': CARGO_JOBS,
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
    manifests = {manifest.relative_to(SOURCE).as_posix(): sha256(manifest)
                 for manifest in sorted(SOURCE.rglob('Cargo.toml'))
                 if manifest.is_file() and not manifest.is_symlink()}
    MANIFEST_HASHES.update(manifests)
    write_json(EVIDENCE / 'source-lock-manifests.json', {
        'source_revision': SOURCE_REVISION, 'source_archive_sha256': SOURCE_ARCHIVE_SHA256,
        'lock_sha256': LOCK_SHA256, 'cargo_manifests_sha256': manifests,
        'tracked_cargo_config': False,
    })
    sample_resources()
    run_command('rustup-version', [str(RUSTUP), '--version'], env)
    run_command('rustup-install', [str(RUSTUP), 'toolchain', 'install', '1.77.2',
                                   '--profile', 'minimal', '--no-self-update'], env)
    toolchain_bin = RUSTUP_HOME / 'toolchains' / TOOLCHAIN / 'bin'
    rustc, cargo = toolchain_bin / 'rustc', toolchain_bin / 'cargo'
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError('private Rustup installation lacks direct rustc or cargo binary')
    env['PATH'] = str(toolchain_bin) + ':/usr/bin:/bin:/usr/sbin:/sbin'
    env['RUSTC'] = str(rustc)
    run_command('rustc-version', [str(rustc), '--version', '--verbose'], env)
    rustc_output = (EVIDENCE / 'rustc-version.stdout').read_text(errors='replace')
    if not rustc_output.startswith('rustc 1.77.2 ') or 'host: x86_64-unknown-linux-gnu' not in rustc_output:
        raise RuntimeError('direct private rustc did not match Rust 1.77.2 Linux x86_64')
    run_command('cargo-version', [str(cargo), '--version', '--verbose'], env)
    if not (EVIDENCE / 'cargo-version.stdout').read_text(errors='replace').startswith('cargo 1.77.2 '):
        raise RuntimeError('direct private Cargo did not match 1.77.2')
    write_json(EVIDENCE / 'host.json', {
        'platform_system': platform.system(), 'platform_machine': platform.machine(),
        'uname': subprocess.run(['/usr/bin/uname', '-a'], capture_output=True,
                                text=True, check=True, timeout=5).stdout.strip(),
        'os_release': Path('/etc/os-release').read_text(encoding='utf-8', errors='replace'),
        'rustup_binary': str(RUSTUP), 'rustup_sha256': sha256(RUSTUP),
        'rustc_binary': str(rustc), 'rustc_sha256': sha256(rustc),
        'cargo_binary': str(cargo), 'cargo_sha256': sha256(cargo),
    })

    current_host = json.loads((EVIDENCE / 'host.json').read_text())
    previous_host = json.loads((REUSED_EVIDENCE / 'host.json').read_text())
    if (current_host['platform_system'] != previous_host['platform_system']
            or current_host['platform_machine'] != previous_host['platform_machine']
            or current_host['os_release'] != previous_host['os_release']):
        raise RuntimeError('current Linux OS differs from the accepted policy1 environment')
    if (sha256(EVIDENCE / 'rustc-version.stdout')
            != REUSED_EVIDENCE_SHA256['rustc-version.stdout']
            or sha256(EVIDENCE / 'cargo-version.stdout')
            != REUSED_EVIDENCE_SHA256['cargo-version.stdout']):
        raise RuntimeError('current Rust/Cargo version output differs from accepted policy1')
    REUSE_RESULT['current_platform_system'] = current_host['platform_system']
    REUSE_RESULT['current_platform_machine'] = current_host['platform_machine']
    REUSE_RESULT['current_os_release'] = current_host['os_release']
    REUSE_RESULT['current_rustc_version_sha256'] = sha256(EVIDENCE / 'rustc-version.stdout')
    REUSE_RESULT['current_cargo_version_sha256'] = sha256(EVIDENCE / 'cargo-version.stdout')
    write_json(EVIDENCE / 'reused-acceptance.json', REUSE_RESULT)

    def verify_immutable_inputs(label: str) -> None:
        if sha256(private_lock) != LOCK_SHA256:
            raise RuntimeError(f'Cargo.lock changed {label}')
        current = {manifest.relative_to(SOURCE).as_posix(): sha256(manifest)
                   for manifest in sorted(SOURCE.rglob('Cargo.toml'))
                   if manifest.is_file() and not manifest.is_symlink()}
        if current != MANIFEST_HASHES:
            raise RuntimeError(f'Cargo manifests changed {label}')

    for row_name, features, targets in TEST_ROWS:
        check_deadline()
        verify_immutable_inputs('before behavior row ' + row_name)
        argv = [str(cargo), 'test', '--locked', '--features', features]
        for target in targets:
            argv.extend(['--test', target])
        argv.extend(['--', '--nocapture', '--test-threads=1'])
        status = run_command('behavior-' + row_name, argv, env, expected_status=None,
                             cwd=SOURCE, merge_streams=True)
        output = ((EVIDENCE / f'behavior-{row_name}.stdout').read_text(errors='replace') +
                  (EVIDENCE / f'behavior-{row_name}.stderr').read_text(errors='replace'))
        coverage = positive_test_coverage(output, targets)
        result = {'row': row_name, 'features': features, 'targets': list(targets),
                  'status': status, 'argv': argv, **coverage,
                  'stdout': f'behavior-{row_name}.stdout',
                  'stderr': f'behavior-{row_name}.stderr'}
        POSITIVE_RESULTS.append(result)
        write_json(EVIDENCE / 'positive-rows-in-progress.json', POSITIVE_RESULTS)
        if status != 0 or not coverage['coverage_found']:
            raise RuntimeError(f'behavior row {row_name} expected status 0, got {status}')
        verify_immutable_inputs('after behavior row ' + row_name)
    write_json(EVIDENCE / 'result.json', {
        'all_remaining_rows_passed': len(POSITIVE_RESULTS) == len(PLANNED_REMAINING_ROWS)
            and all(row.get('status') == 0 for row in POSITIVE_RESULTS),
        'remaining_planned_rows': list(PLANNED_REMAINING_ROWS),
        'previously_accepted_rows_reused': list(ACCEPTED_POLICY1_ROWS),
        'previously_accepted_controls_reused': REUSE_RESULT['controls_reused'],
        'controls_executed_this_invocation': 0,
        'reuse_receipt_verified': REUSE_RESULT['receipt_verified'],
        'positive_rows': POSITIVE_RESULTS,
        'controls_executed_this_invocation_results': CONTROL_RESULTS,
        'acceptance_marker': 'all-remaining-positive-rows-passed',
    })
    export_evidence()
    return 0


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
        print('linux_current_sys_net_policy2=pass', flush=True)
    else:
        print('linux_current_sys_net_policy2=incomplete_or_failed', flush=True)
    sys.exit(exit_status)
