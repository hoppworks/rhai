#!/usr/bin/env python3
"""One bounded public-Engine Linux process measurement run."""
from __future__ import annotations
import hashlib, importlib.util, json, math, os, platform, shutil, signal, sys, traceback
from pathlib import Path

REV = '8c0ee4634355aee4e841b455461a7dd5aac2aa18'
ARCHIVE = '4f049fda78ab245c5e482eef9392f7e8ae059d4fd4fada904941c631c43611f4'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
BASE_HELPER = 'c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9'
ARCHIVE_HELPER = 'a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b'
CONTRACT = 'bb9981dbce7d4694660e20b6ec4d8fe9966d88645348d644eaea090c8422f551'
TEST = '78b057927126c3a6525ece12b193e1163330ac2fbd6630663164ddcac8e75489'
STAGE_PATH = Path('/root/rhai-linux-process-performance-8c0ee-20261004')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004')
BASE = None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    spec = importlib.util.spec_from_file_location('accepted_linux_process_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load pinned accepted base helper')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tagged_rows(text: str, tag: str) -> list[dict[str, str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith(tag + ','):
            continue
        fields = {}
        for item in line.split(',')[1:]:
            if '=' not in item:
                raise ValueError(f'{tag} malformed field: {item!r}')
            key, value = item.split('=', 1)
            if key in fields:
                raise ValueError(f'{tag} duplicate field: {key}')
            fields[key] = value
        rows.append(fields)
    return rows


def positive_float(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{key} must be finite and positive')
    return value

def positive_int(row: dict[str, str], key: str) -> int:
    value = int(row[key])
    if value <= 0:
        raise ValueError(f'{key} must be positive')
    return value


def record_tool_versions(base) -> dict[str, str]:
    receipt = {
        'toolchain': base.TOOLCHAIN,
        'rustc_stdout': base.read_text(base.STAGE / 'rustc-version.stdout'),
        'cargo_stdout': base.read_text(base.STAGE / 'cargo-version.stdout'),
    }
    base.write_json(base.STAGE / 'tool-versions.json', receipt)
    return receipt


def validate_control_receipts(text: str) -> None:
    rows = tagged_rows(text, 'PERF_CONTROL')
    kinds = [row.get('kind') for row in rows]
    if sorted(kinds) != ['byte-integrity', 'proc-census', 'resource-count']:
        raise ValueError('control receipt set is incomplete or duplicated')
    byte, resource = (next(row for row in rows if row['kind'] == kind) for kind in ('byte-integrity', 'resource-count'))
    census = next(row for row in rows if row['kind'] == 'proc-census')
    if any(census.get(key) != 'true' for key in ('malformed_rejected', 'unreadable_rejected', 'vanished_skipped', 'entry_error_rejected')):
        raise ValueError('proc census fail-closed controls are incomplete')
    if byte.get('captures') != '1' or byte.get('corrupted_copy_rejected') != 'true':
        raise ValueError('byte control receipt is not the expected single known-broken case')
    if resource.get('live_fixtures') != '1' or resource.get('zero_descriptor_control_rejected') != 'true':
        raise ValueError('resource control receipt is not the expected single live fixture case')
    positive_int(resource, 'pid'); positive_int(resource, 'start_ticks')


def validate_measurement_rows(text: str) -> dict[str, int]:
    expected = {'PERF_START': 10, 'PERF_CAPTURE': 6, 'PERF_RESOURCE': 2, 'PERF_RESOURCE_CLOSED': 2}
    rows = {tag: tagged_rows(text, tag) for tag in expected}
    for tag, count in expected.items():
        if len(rows[tag]) != count:
            raise ValueError(f'{tag} expected {count} rows, observed {len(rows[tag])}')
    for tag, per_mode in (('PERF_START', 5), ('PERF_CAPTURE', 3)):
        samples = {}
        for row in rows[tag]:
            index = int(row['index']); mode = row['mode']
            if mode not in ('direct', 'managed'):
                raise ValueError(f'{tag} has unknown mode')
            samples.setdefault(index, []).append(mode)
        expected_indices = range(per_mode)
        if set(samples) != set(expected_indices):
            raise ValueError(f'{tag} sample indices are incomplete')
        for index in expected_indices:
            order = ['direct', 'managed'] if index % 2 == 0 else ['managed', 'direct']
            if samples[index] != order:
                raise ValueError(f'{tag} order mismatch at index {index}')
        for row in rows[tag]:
            index = int(row['index'])
            order = 'direct>managed' if index % 2 == 0 else 'managed>direct'
            if row.get('order') != order:
                raise ValueError(f'{tag} raw order label mismatch')
            if tag == 'PERF_START':
                positive_int(row, 'pid'); positive_int(row, 'start_ticks'); positive_int(row, 'ready_latency_ns')
                int(row['pgid'])
            else:
                if int(row['bytes']) != 1048576:
                    raise ValueError('capture byte count mismatch')
                elapsed = positive_int(row, 'captured_run_elapsed_ns')
                observed_rate = positive_float(row, 'captured_run_bytes_per_second')
                expected_rate = 1048576 * 1_000_000_000 / elapsed
                if abs(observed_rate - expected_rate) > max(0.01, expected_rate * 5e-10):
                    raise ValueError('capture throughput does not match bytes/elapsed')
    resource_modes = sorted(row.get('mode', '') for row in rows['PERF_RESOURCE'])
    closed_modes = sorted(row.get('mode', '') for row in rows['PERF_RESOURCE_CLOSED'])
    if resource_modes != ['direct', 'managed'] or closed_modes != ['direct', 'managed']:
        raise ValueError('live/closed resource rows must contain both modes exactly once')
    for row in rows['PERF_RESOURCE']:
        if row.get('sample_index') != '0' or row.get('order') != 'direct>managed':
            raise ValueError('live resource sample index/order mismatch')
        positive_int(row, 'pid'); positive_int(row, 'start_ticks')
        positive_int(row, 'live_ready_latency_ns'); positive_int(row, 'group_members')
        positive_int(row, 'child_threads'); positive_int(row, 'child_fds')
        if row.get('group_members_owned') != str(row['mode'] == 'managed').lower():
            raise ValueError('group ownership label conflicts with process mode')
        if row['mode'] == 'managed' and int(row['pgid']) != int(row['pid']):
            raise ValueError('managed process group is not fixture-owned')
        if row['mode'] == 'managed' and int(row['group_members']) != 1:
            raise ValueError('managed fixture is not the sole process group member')
    live_by_mode = {row['mode']: row for row in rows['PERF_RESOURCE']}
    closed_by_mode = {row['mode']: row for row in rows['PERF_RESOURCE_CLOSED']}
    if len(live_by_mode) != 2 or len(closed_by_mode) != 2:
        raise ValueError('duplicate resource mode rows')
    for mode, row in live_by_mode.items():
        for key in ('host_threads_before', 'host_fds_before', 'host_threads_live', 'host_fds_live'):
            positive_int(row, key)
        closed = closed_by_mode[mode]
        after_threads = positive_int(closed, 'host_threads_after')
        after_fds = positive_int(closed, 'host_fds_after')
        if int(closed['host_threads_delta']) != after_threads - int(row['host_threads_before']):
            raise ValueError('post-close thread delta is not bound to same-mode observations')
        if int(closed['host_fds_delta']) != after_fds - int(row['host_fds_before']):
            raise ValueError('post-close descriptor delta is not bound to same-mode observations')
    return {tag: len(rows[tag]) for tag in expected}


def run_test(name: str, cargo: Path, env: dict[str, str]) -> tuple[int, str, str]:
    argv = [str(cargo), 'test', '--locked', '--test', 'linux_process_performance', '--features', 'testing-environ,sys', name, '--', '--exact', '--nocapture', '--test-threads=1']
    status = BASE.run_command('control-pass', argv, env, expected_status=0)
    stdout = BASE.read_text(BASE.STAGE / 'control-pass.stdout')
    stderr = BASE.read_text(BASE.STAGE / 'control-pass.stderr')
    return status, stdout, stderr


def main() -> int:
    global BASE
    stage = Path(os.environ['PROOF_STAGE'])
    runtime = Path(os.environ['AGENT_RUNTIME_DIR'])
    BASE = load(stage / 'check-linux-current-msrv-examples.py')
    BASE.INPUT_STAGE = stage
    BASE.EXPECTED_STAGE = Path(os.environ['EXPECTED_PROOF_STAGE'])
    BASE.PRESCRIBED_STAGE = STAGE_PATH
    BASE.PRESCRIBED_SCOPE = SCOPE_PATH
    BASE.RUNTIME = runtime
    BASE.STAGE = runtime / 'evidence'
    BASE.EVIDENCE = BASE.EXPECTED_STAGE / 'proof-evidence'
    BASE.CONTRACT = stage / 'measurement-contract.md'
    BASE.SOURCE_ARCHIVE = stage / 'source.tar'
    BASE.LOCK_SOURCE = stage / 'Cargo.lock.accepted'
    BASE.RUSTUP = Path(os.environ['RUSTUP_BIN'])
    BASE.SOURCE_ARCHIVE_SHA256 = ARCHIVE
    BASE.LOCK_SHA256 = LOCK
    BASE.REVISION = REV
    BASE.TOOLCHAIN = '1.77.2-x86_64-unknown-linux-gnu'
    BASE.FEATURES = 'testing-environ,sys'
    BASE.SOURCE = runtime / 'source'
    BASE.CARGO_HOME = runtime / 'cargo-home'
    BASE.RUSTUP_HOME = runtime / 'rustup-home'
    BASE.TARGET = runtime / 'target'
    BASE.PRIVATE_HOME = runtime / 'home'
    BASE.PRIVATE_TMP = Path(os.environ['TMPDIR'])
    signal.signal(signal.SIGTERM, BASE.on_signal)
    signal.signal(signal.SIGINT, BASE.on_signal)
    BASE.capture_runtime_proof()
    BASE.validate_stage_inputs()
    if platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise RuntimeError('native Linux x86_64 required')
    if sha(stage / 'check-linux-current-msrv-examples.py') != BASE_HELPER:
        raise RuntimeError('accepted base helper hash mismatch')
    if sha(stage / 'archive-build-source.py') != ARCHIVE_HELPER:
        raise RuntimeError('accepted archive helper hash mismatch')
    if sha(BASE.SOURCE_ARCHIVE) != ARCHIVE or sha(BASE.LOCK_SOURCE) != LOCK:
        raise RuntimeError('frozen source archive or lock mismatch')
    if sha(stage / 'linux_process_performance.rs') != TEST:
        raise RuntimeError('measurement harness hash mismatch')
    if sha(stage / 'measurement-contract.md') != CONTRACT or os.environ['CONTRACT_SHA256'] != CONTRACT:
        raise RuntimeError('measurement contract hash mismatch')
    shutil.copy2(Path(__file__), BASE.STAGE / 'proof-used.py')
    shutil.copy2(stage / 'measurement-contract.md', BASE.STAGE / 'measurement-contract.md')
    shutil.copy2(stage / 'linux_process_performance.rs', BASE.STAGE / 'linux_process_performance.rs')
    for path in (BASE.CARGO_HOME, BASE.RUSTUP_HOME, BASE.PRIVATE_HOME, BASE.PRIVATE_TMP):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    env = {
        'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(BASE.PRIVATE_HOME),
        'TMPDIR': str(BASE.PRIVATE_TMP), 'TMP': str(BASE.PRIVATE_TMP), 'TEMP': str(BASE.PRIVATE_TMP),
        'CARGO_HOME': str(BASE.CARGO_HOME), 'RUSTUP_HOME': str(BASE.RUSTUP_HOME),
        'CARGO_TARGET_DIR': str(BASE.TARGET), 'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
        'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_TERM_COLOR': 'never', 'RUST_BACKTRACE': '0',
        'RHAI_PROCESS_MEASUREMENT_RECORD_DIR': str(BASE.STAGE / 'fixture-originals'),
    }
    BASE.run_command('rustup-install', [str(BASE.RUSTUP), 'toolchain', 'install', BASE.TOOLCHAIN, '--profile', 'minimal', '--no-self-update'], env, cwd=runtime)
    bindir = BASE.RUSTUP_HOME / 'toolchains' / BASE.TOOLCHAIN / 'bin'
    rustc, cargo = bindir / 'rustc', bindir / 'cargo'
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError('private Rust 1.77.2 toolchain incomplete')
    env.update(PATH=f'{bindir}:/usr/bin:/bin:/usr/sbin:/sbin', RUSTC=str(rustc))
    BASE.run_command('rustc-version', [str(rustc), '--version', '--verbose'], env, cwd=runtime)
    BASE.run_command('cargo-version', [str(cargo), '--version', '--verbose'], env, cwd=runtime)
    if not BASE.read_text(BASE.STAGE / 'rustc-version.stdout').startswith('rustc 1.77.2 ') or not BASE.read_text(BASE.STAGE / 'cargo-version.stdout').startswith('cargo 1.77.2 '):
        raise RuntimeError('private Rust/Cargo version mismatch')
    record_tool_versions(BASE)
    archive_copy = runtime / 'source-input.tar'
    shutil.copy2(BASE.SOURCE_ARCHIVE, archive_copy)
    BASE.extract_archive(archive_copy)
    archive_copy.unlink()
    harness = BASE.SOURCE / 'tests' / 'linux_process_performance.rs'
    if harness.exists():
        raise RuntimeError('baseline unexpectedly already contains measurement harness')
    shutil.copy2(stage / 'linux_process_performance.rs', harness)
    shutil.copy2(BASE.LOCK_SOURCE, BASE.SOURCE / 'Cargo.lock')
    manifest = BASE.manifest_hashes()
    BASE.CARGO_MANIFESTS = manifest
    BASE.ORIGINAL_EXAMPLES[harness] = harness.read_bytes()
    BASE.ORIGINAL_EXAMPLE_HASHES['tests/linux_process_performance.rs'] = TEST
    BASE.write_json(BASE.STAGE / 'source-inputs.json', {
        'revision': REV, 'source_archive_sha256': ARCHIVE, 'lock_sha256': LOCK,
        'base_helper_sha256': BASE_HELPER, 'archive_helper_sha256': ARCHIVE_HELPER,
        'measurement_harness_sha256': TEST, 'contract_sha256': CONTRACT,
        'test_target': 'linux_process_performance', 'features': BASE.FEATURES,
        'production_source_changed': False,
    })
    control_status, control_out, control_err = run_test('measurement_controls_reject_corruption', cargo, env)
    if control_status != 0 or 'test result: ok. 1 passed; 0 failed;' not in control_out:
        raise RuntimeError('corruption controls did not pass exactly once')
    control_text = control_out + '\n' + control_err
    validate_control_receipts(control_text)
    BASE.verify_pass('control-pass', control_status, control_out, ['test measurement_controls_reject_corruption ... ok'])
    measure_argv = [str(cargo), 'test', '--locked', '--test', 'linux_process_performance', '--features', BASE.FEATURES, 'direct_managed_measurements', '--', '--exact', '--ignored', '--nocapture', '--test-threads=1']
    status = BASE.run_command('measurements', measure_argv, env, expected_status=0)
    stdout = BASE.read_text(BASE.STAGE / 'measurements.stdout')
    stderr = BASE.read_text(BASE.STAGE / 'measurements.stderr')
    combined = stdout + '\n' + stderr
    expected_counts = validate_measurement_rows(combined)
    if status != 0 or 'test result: ok. 1 passed; 0 failed;' not in stdout:
        raise RuntimeError('measurement target did not pass exactly once')
    BASE.verify_pass('measurements', status, stdout, ['test direct_managed_measurements ... ok'])
    if sha(harness) != TEST:
        raise RuntimeError('measurement harness changed during execution')
    BASE.write_json(BASE.STAGE / 'measurement-result.json', {
        'source_revision': REV, 'archive_sha256': ARCHIVE, 'lock_sha256': LOCK,
        'harness_sha256': TEST, 'features': BASE.FEATURES,
        'control_capture_processes': 1, 'control_live_fixture_processes': 1,
        'start_samples_per_mode': 5, 'capture_samples_per_mode': 3, 'capture_bytes': 1048576,
        'observed_row_counts': expected_counts, 'commands': BASE.COMMANDS,
        'controls': BASE.CONTROL_RESULTS, 'source_restored': True,
        'acceptance_claim': False,
    })
    return 0


def export() -> None:
    if BASE is None or not BASE.STAGE.is_dir():
        return
    BASE.check_deadline(during_export=True)
    try:
        try:
            BASE.restore_example_sources()
        except BaseException as exc:
            BASE.write_json(BASE.STAGE / 'source-restoration-error.json', {'error': repr(exc)})
        restored = BASE.SOURCE.is_dir() and all(
            path.exists() and sha(path) == BASE.ORIGINAL_EXAMPLE_HASHES[path.relative_to(BASE.SOURCE).as_posix()]
            for path in BASE.ORIGINAL_EXAMPLES
        )
        BASE.write_json(BASE.STAGE / 'source-restoration.json', {
            'restored_example_sha256': BASE.ORIGINAL_EXAMPLE_HASHES,
            'restored_examples_match_recorded_bytes': restored,
            'cargo_lock_sha256': sha(BASE.SOURCE / 'Cargo.lock') if (BASE.SOURCE / 'Cargo.lock').is_file() else None,
            'cargo_manifest_sha256': BASE.manifest_hashes() if BASE.SOURCE.is_dir() else {},
            'acceptance_claim': False,
        })
        BASE.write_json(BASE.STAGE / 'sampled-maxima.json', {
            'maxima': BASE.MAXIMA, 'sample_count': len(BASE.SAMPLES),
            'samples_are_periodic_not_continuous_peak': True,
            'storage_preemptive_stop_kib': 1572864,
            'storage_hard_stop_kib': 2097152,
            'rss_hard_stop_kib': 2097152,
            'descendant_hard_stop': 16,
        })
        (BASE.STAGE / 'resource-samples.jsonl').write_text(
            ''.join(json.dumps(row, sort_keys=True) + '\n' for row in BASE.SAMPLES), encoding='utf-8')
        if not BASE.export_destination_is_safe():
            raise RuntimeError('evidence export destination identity is unverified')
        BASE.EVIDENCE.mkdir(mode=0o700)
        progress = {'state': 'copying', 'copied': [], 'remaining': [], 'export_complete': False,
                    'periodic_sample_count': len(BASE.SAMPLES), 'acceptance_claim': False}
        items = sorted(BASE.STAGE.iterdir())
        progress['remaining'] = [item.name for item in items]
        def save_progress() -> None:
            BASE.write_json(BASE.EVIDENCE / 'export-progress.json', progress)
        save_progress()
        for item in items:
            BASE.check_deadline(during_export=True)
            target = BASE.EVIDENCE / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
            progress['copied'].append(item.name)
            progress['remaining'].remove(item.name)
            save_progress()
        BASE.check_deadline(during_export=True)
        progress['state'] = 'complete'
        progress['export_complete'] = True
        save_progress()
        print(f'evidence_exported={BASE.EVIDENCE}', flush=True)
    except BaseException as exc:
        if BASE.EVIDENCE.is_dir():
            try:
                BASE.write_json(BASE.EVIDENCE / 'export-failure.json', {
                    'error': repr(exc), 'partial_copy_preserved': True,
                    'export_progress': str(BASE.EVIDENCE / 'export-progress.json'),
                    'acceptance_claim': False,
                })
            except BaseException:
                pass
        raise


if __name__ == '__main__':
    status = 1
    try:
        status = main()
    except BaseException as exc:
        if BASE is not None and BASE.STAGE.is_dir():
            (BASE.STAGE / 'failure.txt').write_text(''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        traceback.print_exc()
        status = 1
    finally:
        try:
            export()
        except BaseException:
            traceback.print_exc()
            status = 1
    raise SystemExit(status)
