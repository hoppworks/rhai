#!/usr/bin/env python3
"""Bounded private Rust 1.77.2 Darwin sys/net Engine and OS behavior package."""
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

SOURCE_REVISION = '2f795ecee8edd6ddf348f382e5397cc6e348ad37'
SOURCE_ARCHIVE_SHA256 = '43c8b8e43a2bcd3e74dd0be3d60a0dea2eab50eb5bfe65cc736684631523d52b'
LOCK_SHA256 = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
RUSTUP = Path.home() / '.cargo/bin/rustup'
TOOLCHAIN = '1.77.2-aarch64-apple-darwin'
EXPECTED_RUN_SCOPED_SHA256 = '9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d'
EXPECTED_INIT_SHA256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
EXPECTED_PYGUARD_SHA256 = 'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f'
EXPECTED_STAGE = Path(os.environ.get('DARWIN_PROOF_STAGE', ''))
SESSION_ID = 'current-darwin-sys-net-behavior-2f795ece-sampler2-20261002'
EXPECTED_SCOPE = Path.home() / '.local/share/agent-builds/rhai' / SESSION_ID
STAGE = EXPECTED_STAGE
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
    ('combined-baseline', 'testing-environ,sys,net',
     ('sys_env', 'sys_fs', 'sys_policy', 'net_connect', 'net_listen',
      'net_reads', 'net_writes', 'combined_sys_net')),
    ('combined-no-index', 'testing-environ,sys,net,no_index',
     ('sys_fs', 'net_reads', 'net_writes', 'combined_sys_net')),
    ('net-no-object', 'testing-environ,net,no_object', ('net_no_object',)),
    ('combined-metadata-serde', 'testing-environ,sys,net,metadata,serde',
     ('sys_policy', 'net_metadata')),
    ('combined-sync', 'testing-environ,sys,net,sync',
     ('sys_fs', 'sys_policy', 'net_connect', 'net_listen', 'net_reads', 'net_writes', 'combined_sys_net')),
    ('combined-i32-no-float', 'testing-environ,sys,net,only_i32,no_float',
     ('sys_fs', 'sys_policy', 'net_connect', 'net_listen', 'net_reads', 'net_writes', 'combined_sys_net')),
    ('combined-unchecked', 'testing-environ,sys,net,unchecked',
     ('sys_fs', 'sys_policy', 'net_connect', 'net_listen', 'net_reads', 'net_writes', 'combined_sys_net')),
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
MANIFEST_HASHES: dict[str, str] = {}
RECORDED_PIDS: set[int] = set()
ACTIVE_CHILD: subprocess.Popen[bytes] | None = None
INTERRUPTED: int | None = None
EILSEQ_MARKER = 'filesystem rejects non-UTF-8 fixture with EILSEQ:'
EILSEQ_PRODUCER = ('sys_fs', 'test_non_utf8_file_name')


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
            raise TimeoutError('540-second helper budget, including setup and export, expired')
        raise TimeoutError('510-second work budget expired; 30 seconds reserved for export')
    if INTERRUPTED is not None and not during_export:
        raise InterruptedError(f'interrupted by signal {INTERRUPTED}')


def process_identity(pid: int) -> tuple[int, int, int, str] | None:
    """Return PPID, PGID, stable start-time digest, and command for one PID on Darwin."""
    try:
        result = subprocess.run(['/bin/ps', '-p', str(pid), '-o', 'ppid=,pgid=,lstart=,command='],
                                capture_output=True, text=True, check=True, timeout=5)
        fields = result.stdout.strip().split(None, 7)
        if len(fields) != 8:
            return None
        ppid, pgid = int(fields[0]), int(fields[1])
        start = ' '.join(fields[2:7])
        command = fields[7]
        start_digest = int(hashlib.sha256(start.encode()).hexdigest()[:12], 16)
        return ppid, pgid, start_digest, command
    except (OSError, subprocess.SubprocessError, IndexError, ValueError):
        return None


def record_process_identity(label: str, pid: int, identity: tuple[int, int, int, str] | None) -> None:
    path = EVIDENCE / 'process-identities.tsv'
    if identity is None:
        with path.open('a', encoding='utf-8') as stream:
            stream.write(f'{label}\t{pid}\t<identity-unavailable>\n')
        return
    ppid, pgid, start_ticks, command = identity
    RECORDED_PIDS.add(pid)
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


def validate_stage_scope(stage: Path, runtime: Path) -> None:
    if stage.name != SESSION_ID:
        raise RuntimeError(f'DARWIN_PROOF_STAGE must use the prescribed unique stage name: {SESSION_ID}')
    if runtime.parent.resolve() != EXPECTED_SCOPE.resolve():
        raise RuntimeError(f'private runtime is outside the prescribed project scope: {EXPECTED_SCOPE}')


def validate_stage_inputs() -> None:
    """Fail closed on any stage other than the prescribed canonical directory."""
    if not STAGE.is_absolute() or not STAGE.is_dir() or STAGE.is_symlink():
        raise RuntimeError('DARWIN_PROOF_STAGE must be the existing absolute real input stage')
    validate_stage_scope(STAGE, RUNTIME)
    for path in (STAGE / 'source.tar', STAGE / 'Cargo.lock.accepted'):
        if not path.is_file():
            raise FileNotFoundError(f'required explicitly staged input missing: {path}')
    for name in ('contract.md', 'run-sys-net-behavior.py'):
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
    observer = subprocess.Popen(['/bin/ps', '-axo', 'pid=,ppid=,rss='],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        ps_stdout, ps_stderr = observer.communicate(timeout=5)
    except BaseException as original_error:
        cleanup_error = None
        try:
            observer.terminate()
        except ProcessLookupError:
            pass
        except BaseException as error:
            cleanup_error = error
        if cleanup_error is None:
            try:
                observer.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                cleanup_error = TimeoutError('observer did not stop after terminate')
            except BaseException as error:
                cleanup_error = error
        if cleanup_error is not None:
            try:
                observer.kill()
                observer.communicate(timeout=1)
            except BaseException as kill_error:
                raise RuntimeError(
                    f'resource census observer cleanup failed; exact PID {observer.pid} may remain: '
                    f'{type(kill_error).__name__}: {kill_error}') from original_error
        if isinstance(original_error, subprocess.TimeoutExpired):
            raise TimeoutError('resource process census exceeded five seconds') from original_error
        raise
    observer_status = observer.returncode
    if observer_status != 0:
        raise subprocess.CalledProcessError(observer_status, observer.args,
                                            output=ps_stdout, stderr=ps_stderr)
    processes: dict[int, tuple[int, int]] = {}
    root_pid = os.getpid()
    observer_seen = False
    for line in ps_stdout.splitlines():
        pid, ppid, rss = map(int, line.split())
        if pid in processes:
            raise RuntimeError(f'duplicate PID in resource sample: {pid}')
        if pid == observer.pid:
            if observer_seen:
                raise RuntimeError(f'duplicate PID in resource sample: {pid}')
            if ppid != root_pid or observer_status is None:
                raise RuntimeError('resource census observer identity was not the waited direct child')
            observer_seen = True
            continue
        processes[pid] = (ppid, rss)
    if observer_status is None:
        raise RuntimeError('resource census observer was not waited and reaped')
    if root_pid not in processes:
        raise RuntimeError('helper PID absent from resource sample')
    owned = {root_pid}
    while True:
        children = {pid for pid, (ppid, _rss) in processes.items() if ppid in owned} - owned
        if not children:
            break
        owned.update(children)
    for pid in sorted(owned):
        if pid not in RECORDED_PIDS:
            identity = process_identity(pid)
            if identity is None:
                raise RuntimeError(f'cannot record exact identity for owned descendant {pid}')
            record_process_identity('sampled-descendant', pid, identity)
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
            if child.pid not in RECORDED_PIDS:
                raise RuntimeError(f'cannot record exact identity for command process {child.pid}')
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


def _cfg_enabled(expression: str, features: set[str]) -> bool:
    expression = expression.strip()
    if expression.startswith('not(') and expression.endswith(')'):
        return not _cfg_enabled(expression[4:-1], features)
    for operator in ('all(', 'any('):
        if expression.startswith(operator) and expression.endswith(')'):
            inner = expression[len(operator):-1]
            parts, depth, begin = [], 0, 0
            for index, char in enumerate(inner):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                elif char == ',' and depth == 0:
                    parts.append(inner[begin:index]); begin = index + 1
            parts.append(inner[begin:])
            values = [_cfg_enabled(part, features) for part in parts]
            return all(values) if operator == 'all(' else any(values)
    if expression == 'unix' or expression == 'target_os = "macos"':
        return True
    if expression in ('windows', 'target_os = "linux"'):
        return False
    if expression.startswith('feature = '):
        return expression.split('"')[1] in features
    raise ValueError(f'unsupported cfg expression in frozen test inventory: {expression}')


def frozen_test_inventory(source: Path, features: str) -> dict[str, list[str]]:
    """Read exact active #[test] function names from frozen integration sources."""
    import re

    feature_set = set(features.split(','))
    inventory: dict[str, list[str]] = {}
    for path in sorted((source / 'tests').glob('*.rs')):
        target = path.stem
        text = path.read_text(encoding='utf-8')
        names: list[str] = []
        pending_cfg: list[str] = []
        lines = text.splitlines()
        for index, line in enumerate(lines):
            cfg = re.match(r'^\s*#\[cfg\((.*)\)\]\s*$', line)
            if cfg:
                pending_cfg.append(cfg.group(1))
                continue
            if re.match(r'^\s*#\[test\]\s*$', line):
                function = next((re.match(r'^\s*fn\s+([A-Za-z0-9_]+)\s*\(', following)
                                 for following in lines[index + 1:] if following.strip()), None)
                if function and all(_cfg_enabled(item, feature_set) for item in pending_cfg):
                    names.append(function.group(1))
                pending_cfg = []
                continue
            if line.strip() and not line.lstrip().startswith('//'):
                pending_cfg = []
        if names:
            inventory[target] = names
    return inventory


def positive_test_coverage(output: str, targets: tuple[str, ...],
                           expected_tests: dict[str, list[str]],
                           diagnostic_inputs: list[dict[str, object]] | None = None) -> dict[str, object]:
    """Require each frozen named test and exactly one complete summary per target."""
    import re

    running = re.compile(r'^\s*Running tests/([A-Za-z0-9_]+)\.rs(?:\s|$)', re.MULTILINE)
    result = re.compile(
        r'^test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; '
        r'(\d+) measured; (\d+) filtered out;', re.MULTILINE)
    lines = output.splitlines()
    ignored_tests: list[str] = []
    observed_targets: list[str] = []
    summaries: dict[str, list[dict[str, int]]] = {}
    observed_tests: dict[str, list[str]] = {}
    test_outcomes: dict[str, dict[str, str]] = {}
    diagnostic_inputs = list(diagnostic_inputs or [])
    current: str | None = None
    pending_test: str | None = None
    for line in lines:
        ignored = re.match(r'^test ([A-Za-z0-9_]+) \.\.\. ignored(?:,.*)?$', line)
        if ignored:
            ignored_tests.append(ignored.group(1))
        match = running.match(line)
        if match:
            current = match.group(1)
            observed_targets.append(current)
            observed_tests[current] = []
            test_outcomes[current] = {}
        test_line = re.match(r'^test ([A-Za-z0-9_]+) \.\.\. (.*)$', line)
        if current is not None and test_line:
            test_name, result_text = test_line.groups()
            pending_test = test_name
            if test_name in observed_tests[current]:
                observed_tests[current].append(test_name + '#duplicate')
            else:
                observed_tests[current].append(test_name)
            outcome = re.search(r'\b(ok|ignored(?:,.*)?|FAILED)\s*$', result_text)
            if outcome:
                test_outcomes[current][test_name] = outcome.group(1).split(',')[0]
                pending_test = None
            if EILSEQ_MARKER in result_text:
                diagnostic_inputs.append({'stream': 'stdout', 'line': line,
                                          'inline_target': current, 'inline_test': test_name})
        elif current is not None and pending_test is not None:
            outcome = re.match(r'^\s*(ok|ignored(?:,.*)?|FAILED)\s*$', line)
            if outcome:
                test_outcomes[current][pending_test] = outcome.group(1).split(',')[0]
                pending_test = None
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
    final_rows = [{'target': target, **summaries[target][0],
                   'summary_count': len(summaries[target]),
                   'expected_tests': expected_tests.get(target, []),
                   'observed_tests': observed_tests.get(target, []),
                   'test_outcomes': test_outcomes.get(target, {})}
                  for target in targets if target in summaries]
    skipped_tests: list[dict[str, object]] = []
    unresolved_diagnostics: list[dict[str, object]] = []
    resolved_occurrences: list[dict[str, object]] = []
    for diagnostic in diagnostic_inputs:
        record = dict(diagnostic)
        text = str(record.get('text', record.get('line', '')))
        if EILSEQ_MARKER not in text:
            continue
        inline_pair = (record.get('inline_target'), record.get('inline_test'))
        if inline_pair != (None, None):
            resolved = inline_pair == EILSEQ_PRODUCER
            reason = 'inline producer conflicts with frozen source mapping'
        else:
            resolved = (EILSEQ_PRODUCER[0] in targets and
                        expected_tests.get(EILSEQ_PRODUCER[0], []).count(EILSEQ_PRODUCER[1]) == 1)
            reason = 'frozen producer is not selected exactly once in the named inventory'
        if resolved:
            resolved_occurrences.append(record)
        else:
            record['resolution_error'] = reason
            unresolved_diagnostics.append(record)
    if resolved_occurrences:
        skipped_tests.append({'target': EILSEQ_PRODUCER[0], 'test': EILSEQ_PRODUCER[1],
                              'reason': 'Darwin EILSEQ rejected fixture; producer returned early',
                              'occurrence_count': len(resolved_occurrences),
                              'occurrences': resolved_occurrences})
    named_complete = len(final_rows) == len(targets) and all(
        row['summary_count'] == 1 and row['expected_tests']
        and sorted(row['observed_tests']) == sorted(row['expected_tests'])
        for row in final_rows)
    for row in final_rows:
        skipped_names = {item['test'] for item in skipped_tests if item['target'] == row['target']}
        provisional = sorted(
            name for name in row['expected_tests']
            if row['test_outcomes'].get(name) == 'ok' and name not in skipped_names)
        row['provisional_completed_named_tests'] = provisional
        row['completion_certified'] = not unresolved_diagnostics
        row['completed_named_tests'] = [] if unresolved_diagnostics else provisional
        row['uncovered_named_tests'] = sorted(set(row['expected_tests']) -
                                              set(row['completed_named_tests']))
    named_complete = named_complete and all(
        len(row['completed_named_tests']) == len(row['expected_tests']) for row in final_rows)
    all_executed = named_complete and not skipped_tests and not unresolved_diagnostics and all(
        row['passed'] == len(row['completed_named_tests']) and row['failed'] == 0 and row['ignored'] == 0
        and row['measured'] == 0 and row['filtered_out'] == 0 for row in final_rows)
    return {'target_results': final_rows, 'expected_targets': list(targets),
            'all_selected_targets_ran_once': exact_targets,
            'all_tests_passed_without_ignored_or_filtered': all_executed,
            'ignored_tests': ignored_tests, 'skipped_tests': skipped_tests,
            'unresolved_diagnostics': unresolved_diagnostics,
            'named_test_coverage_found': named_complete,
            'coverage_found': exact_targets and all_executed}


def should_continue_positive_rows(status: int, coverage_found: bool) -> bool:
    return status == 0 and not coverage_found


def positive_rows_summary(results: list[dict[str, object]], expected_count: int) -> dict[str, object]:
    successful = sum(row.get('status') == 0 and row.get('coverage_found') for row in results)
    return {'positive_row_count': expected_count, 'successful_positive_rows': successful,
            'all_positive_rows_succeeded': len(results) == expected_count and successful == expected_count,
            'uncovered_positive_rows': [row.get('row') for row in results
                                        if row.get('status') != 0 or not row.get('coverage_found')]}


def derive_target_order_parser_input(stdout: str, stderr: str, targets: tuple[str, ...],
                                     expected_tests: dict[str, list[str]]) -> dict[str, object]:
    """Associate Cargo stderr target headers with successive complete stdout libtest blocks."""
    import re

    header_pattern = re.compile(r'^\s*Running tests/([A-Za-z0-9_]+)\.rs(?:\s|$)')
    summary_pattern = re.compile(r'^test result: (?:ok|FAILED)\.')
    headers = [match.group(1) for line in stderr.splitlines()
               if (match := header_pattern.match(line))]
    stderr_diagnostics = [line for line in stderr.splitlines()
                          if not header_pattern.match(line)]
    diagnostic_inputs = [{'stream': 'stderr', 'line_number': index, 'text': line}
                         for index, line in enumerate(stderr.splitlines(), 1)
                         if EILSEQ_MARKER in line]
    if len(headers) != len(targets) or set(headers) != set(targets) or len(set(headers)) != len(headers):
        raise RuntimeError(f'stderr target headers do not match selected targets exactly once: {headers}')

    lines = stdout.splitlines()
    blocks: list[list[str]] = []
    outside: list[str] = []
    current: list[str] | None = None
    for line in lines:
        if re.match(r'^running \d+ tests?$', line):
            if current is not None:
                raise RuntimeError('stdout libtest block began before prior block summary')
            current = [line]
        elif current is None:
            outside.append(line)
        else:
            current.append(line)
            if summary_pattern.match(line):
                blocks.append(current)
                current = None
    if current is not None:
        raise RuntimeError('stdout ended with incomplete libtest block')
    if len(blocks) != len(headers):
        raise RuntimeError(f'stdout complete libtest blocks ({len(blocks)}) do not match '
                           f'stderr target headers ({len(headers)})')

    entries: list[str] = []
    for target, block in zip(headers, blocks):
        # Validate association against the exact selected inventory before combining
        # streams. EILSEQ can still be associated because it produces a named result.
        standalone = '     Running tests/' + target + '.rs (derived target order)\n' + '\n'.join(block) + '\n'
        check = positive_test_coverage(standalone, (target,), expected_tests)
        row = check['target_results'][0] if check['target_results'] else {}
        if (row.get('summary_count') != 1
                or sorted(row.get('observed_tests', [])) != sorted(expected_tests.get(target, []))):
            raise RuntimeError(f'stdout block does not match named inventory for {target}')
        entries.append('     Running tests/' + target + '.rs (derived target order)\n'
                       + '\n'.join(block) + '\n')
    parser_core = ('--- derived target order from stderr headers and successive stdout blocks; '
                    'this is not captured cross-stream chronology ---\n'
                    + ('--- stdout outside complete libtest blocks ---\n' + '\n'.join(outside) + '\n'
                       if outside else '') + ''.join(entries))
    parser_input = (parser_core + ('--- stderr diagnostics outside target headers ---\n'
                                   + '\n'.join(stderr_diagnostics) + '\n'
                                   if stderr_diagnostics else ''))
    coverage = positive_test_coverage(parser_core, targets, expected_tests, diagnostic_inputs)
    return {'label': 'derived target order from stderr headers and successive stdout blocks',
            'target_order': headers, 'parser_input': parser_input, 'coverage': coverage}


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
        **positive_rows_summary(POSITIVE_RESULTS, len(TEST_ROWS)),
        'assertion_controls': CONTROL_RESULTS,
        'all_assertion_controls_are_meaningful_red': len(CONTROL_RESULTS) == len(ASSERTION_CONTROLS)
            and all(row.get('status') == 101 and row.get('diagnostic_found') for row in CONTROL_RESULTS),
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
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    capture_runtime_proof()
    validate_stage_inputs()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('prepared proof requires native Darwin arm64')
    staged_contract = STAGE / 'contract.md'
    staged_helper = STAGE / 'run-sys-net-behavior.py'
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
        'run-sys-net-behavior.py': {'path': str(staged_helper), 'sha256': sha256(staged_helper)},
        'contract.md': {'path': str(staged_contract), 'sha256': sha256(staged_contract)},
        'run_scoped.py': {'path': str(STAGE / 'runner/tools/run_scoped.py'),
                          'sha256': runner_hashes['run_scoped.py']},
        'agentskills/__init__.py': {'path': str(STAGE / 'runner/tools/agentskills/__init__.py'),
                                    'sha256': runner_hashes['agentskills/__init__.py']},
        'agentskills/pyguard.py': {'path': str(STAGE / 'runner/tools/agentskills/pyguard.py'),
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
    if not rustc_output.startswith('rustc 1.77.2 ') or 'host: aarch64-apple-darwin' not in rustc_output:
        raise RuntimeError('direct private rustc did not match Rust 1.77.2 Darwin arm64')
    run_command('cargo-version', [str(cargo), '--version', '--verbose'], env)
    if not (EVIDENCE / 'cargo-version.stdout').read_text(errors='replace').startswith('cargo 1.77.2 '):
        raise RuntimeError('direct private Cargo did not match 1.77.2')
    write_json(EVIDENCE / 'host.json', {
        'platform_system': platform.system(), 'platform_machine': platform.machine(),
        'uname': subprocess.run(['/usr/bin/uname', '-a'], capture_output=True,
                                text=True, check=True, timeout=5).stdout.strip(),
        'os_release': subprocess.run(['/usr/bin/sw_vers'], capture_output=True,
                                     text=True, check=True, timeout=5).stdout,
        'rustup_binary': str(RUSTUP), 'rustup_sha256': sha256(RUSTUP),
        'rustc_binary': str(rustc), 'rustc_sha256': sha256(rustc),
        'cargo_binary': str(cargo), 'cargo_sha256': sha256(cargo),
    })

    def verify_immutable_inputs(label: str) -> None:
        if sha256(private_lock) != LOCK_SHA256:
            raise RuntimeError(f'Cargo.lock changed {label}')
        current = {manifest.relative_to(SOURCE).as_posix(): sha256(manifest)
                   for manifest in sorted(SOURCE.rglob('Cargo.toml'))
                   if manifest.is_file() and not manifest.is_symlink()}
        if current != MANIFEST_HASHES:
            raise RuntimeError(f'Cargo manifests changed {label}')

    for control_name, features, target, test_name, env_name, required_context in ASSERTION_CONTROLS:
        verify_immutable_inputs('before control ' + control_name)
        argv = [str(cargo), 'test', '--locked', '--features', features,
                '--test', target, test_name, '--', '--exact', '--nocapture', '--test-threads=1']
        status = run_command('control-' + control_name, argv, env, expected_status=None,
                             cwd=SOURCE, env_overrides={env_name: '1'})
        output = ((EVIDENCE / f'control-{control_name}.stdout').read_text(errors='replace') +
                  (EVIDENCE / f'control-{control_name}.stderr').read_text(errors='replace'))
        classification = classify_assertion_control(status, output, target, test_name, required_context)
        found = bool(classification['diagnostic_found'])
        CONTROL_RESULTS.append({
            'name': control_name, 'features': features, 'target': target,
            'test': test_name, 'environment_control': env_name, 'status': status,
            'expected_status': 101, **classification,
        })
        write_json(EVIDENCE / 'controls-in-progress.json', CONTROL_RESULTS)
        if status != 101 or not found:
            raise RuntimeError(f'{control_name} did not produce its intended assertion failure')
        verify_immutable_inputs('after control ' + control_name)

    for row_name, features, targets in TEST_ROWS:
        check_deadline()
        verify_immutable_inputs('before behavior row ' + row_name)
        argv = [str(cargo), 'test', '--locked', '--features', features]
        for target in targets:
            argv.extend(['--test', target])
        argv.extend(['--', '--nocapture', '--test-threads=1'])
        status = run_command('behavior-' + row_name, argv, env, expected_status=None,
                             cwd=SOURCE)
        stdout = (EVIDENCE / f'behavior-{row_name}.stdout').read_text(errors='replace')
        stderr = (EVIDENCE / f'behavior-{row_name}.stderr').read_text(errors='replace')
        inventory = frozen_test_inventory(SOURCE, features)
        expected_tests = {target: inventory.get(target, []) for target in targets}
        derived = derive_target_order_parser_input(stdout, stderr, targets, expected_tests)
        output = derived['parser_input']
        (EVIDENCE / f'behavior-{row_name}.parser-input.txt').write_text(output, encoding='utf-8')
        coverage = derived['coverage']
        result = {'row': row_name, 'features': features, 'targets': list(targets),
                  'status': status, 'argv': argv, **coverage,
                  'parser_order_label': derived['label'],
                  'derived_target_order': derived['target_order'],
                  'stdout': f'behavior-{row_name}.stdout',
                  'stderr': f'behavior-{row_name}.stderr',
                  'parser_input': f'behavior-{row_name}.parser-input.txt',
                  'expected_tests': expected_tests}
        POSITIVE_RESULTS.append(result)
        write_json(EVIDENCE / 'positive-rows-in-progress.json', POSITIVE_RESULTS)
        if status != 0 or not coverage['coverage_found']:
            if status != 0:
                raise RuntimeError(f'behavior row {row_name} expected status 0, got {status}')
            if should_continue_positive_rows(status, bool(coverage['coverage_found'])):
                print(f'coverage_incomplete={row_name}; continuing independent rows', flush=True)
        verify_immutable_inputs('after behavior row ' + row_name)
    write_json(EVIDENCE / 'result.json', {
        **positive_rows_summary(POSITIVE_RESULTS, len(TEST_ROWS)),
        'all_behavior_rows_passed': positive_rows_summary(POSITIVE_RESULTS, len(TEST_ROWS))[
            'all_positive_rows_succeeded'],
        'all_controls_are_meaningful_red': len(CONTROL_RESULTS) == len(ASSERTION_CONTROLS)
            and all(row.get('status') == 101 and row.get('diagnostic_found') for row in CONTROL_RESULTS),
        'positive_rows': POSITIVE_RESULTS, 'assertion_controls': CONTROL_RESULTS,
        'acceptance_marker': ('all-controls-and-positive-runs-passed'
            if positive_rows_summary(POSITIVE_RESULTS, len(TEST_ROWS))['all_positive_rows_succeeded']
            else 'incomplete-unaccepted'),
    })
    export_evidence()
    return 0 if len(POSITIVE_RESULTS) == len(TEST_ROWS) and all(
        row.get('status') == 0 and row.get('coverage_found') for row in POSITIVE_RESULTS) else 1


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
        print('darwin_current_sys_net_behavior=pass', flush=True)
    else:
        print('darwin_current_sys_net_behavior=incomplete_or_failed', flush=True)
    sys.exit(exit_status)
