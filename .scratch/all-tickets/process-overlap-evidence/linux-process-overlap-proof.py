#!/usr/bin/env python3
"""Custodied native Linux overlap proof using the accepted scoped-runner base."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import shutil
import signal
import sys
import time
import traceback
from pathlib import Path

STAGE_PATH = Path('/root/rhai-linux-process-overlap-d79-20261004-1259')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/linux-process-overlap-d79-20261004-1259')
BASE = None
PINS: dict[str, str] = {}
TESTS = {
    'direct': 'packages::sys::process::unix::tests::readable_output_overflow_wins_when_deadline_expires_direct_child',
    'managed': 'packages::sys::process::unix::tests::readable_output_overflow_wins_when_deadline_expires_managed',
}
CAUSE = 'overflow must win over the simultaneously expired deadline'
EXPECTED_MUTANT_SHA256 = '53ce5a454661ffd08e6f3d0a9bbac15c8ccd8f1ea397c042b777a066be756b23'
SOURCE_REL = 'src/packages/sys/process/unix.rs'
START = '        // Drain readable bytes first so observed output overflow wins when it coincides with\n'
READ = '        if fds[0].revents != 0 {\n'
LOOP_END = '    }\n    let status = status.unwrap();\n'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    spec = importlib.util.spec_from_file_location('overlap_accepted_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load accepted base helper')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def receipt(stdout: str, stderr: str, mode: str) -> str:
    lines = [line for line in (stdout + '\n' + stderr).splitlines()
             if line.startswith(f'overlap-fixture mode={mode} ')]
    if len(lines) != 1:
        raise RuntimeError(f'{mode} requires exactly one public fixture receipt')
    required = ('child_pid=', 'child_start_ticks=', 'child_pgid=',
                'child_write=acknowledged', 'deadline=expired',
                'poll=stdout-readable', 'reap=ESRCH', 'owner=closed')
    if any(value not in lines[0] for value in required):
        raise RuntimeError(f'{mode} fixture receipt lacks exact child/readiness/closure evidence')
    return lines[0]


def append_fixture_row(label: str, line: str) -> None:
    values = dict(part.split('=', 1) for part in line.split()[1:])
    row = '\t'.join((label, values['child_pid'], values['child_start_ticks'],
                     values['child_pgid'], values['child_write'], values['deadline'],
                     values['poll'], values['overflow_observed'], values['reap'],
                     values['owner'], '/bin/sleep 30')) + '\n'
    path = BASE.STAGE / 'fixture-identities.tsv'
    if not path.exists():
        path.write_text('case\tpid\tstart_ticks\tpgid\twrite\tdeadline\tpoll\toverflow\treap\towner\texpected_command\n', encoding='utf-8')
    with path.open('a', encoding='utf-8') as stream:
        stream.write(row)
        stream.flush()
        os.fsync(stream.fileno())


def move_timeout_before_read(source: Path) -> tuple[bytes, bytes]:
    original = source.read_bytes()
    text = original.decode('utf-8')
    if text.count(START) != 1 or text.count(READ) != 1 or text.count(LOOP_END) != 1:
        raise RuntimeError('timeout-ordering mutation anchors missing or ambiguous')
    start = text.index(START)
    end = text.index(LOOP_END, start)
    block = text[start:end]
    if 'if expired {' not in block or block.count('ProcessCause::Timeout') != 1:
        raise RuntimeError('expired cleanup block does not match reviewed baseline')
    changed = text[:start] + text[end:]
    insertion = changed.index(READ)
    changed = changed[:insertion] + block + changed[insertion:]
    if changed.index(START) >= changed.index(READ):
        raise RuntimeError('timeout control was not placed after poll and before stdout read')
    return original, changed.encode('utf-8')


def run_case(mode: str, kind: str, cargo: Path, env: dict[str, str], source: Path) -> None:
    label = f'{kind}-{mode}'
    test_name = TESTS[mode]
    argv = [str(cargo), 'test', '--locked', '--lib', '--features',
            'testing-environ,sys', test_name, '--', '--exact', '--nocapture',
            '--test-threads=1']
    expected = 101 if kind == 'timeout-first' else 0
    status = BASE.run_command(label, argv, env, expected_status=expected)
    stdout = BASE.read_text(BASE.STAGE / f'{label}.stdout')
    stderr = BASE.read_text(BASE.STAGE / f'{label}.stderr')
    combined = stdout + '\n' + stderr
    line = receipt(stdout, stderr, mode)
    append_fixture_row(label, line)
    if kind == 'timeout-first':
        if ('overflow_observed=false' not in line or CAUSE not in combined
                or f"thread '{test_name}' panicked at {SOURCE_REL}:" not in combined):
            raise RuntimeError(f'{label} did not fail at the intended OutputLimit cause assertion')
        BASE.verify_control(label, status, expected, combined, [CAUSE],
                            stdout=combined, required_output=[line])
    else:
        if ('overflow_observed=true' not in line
                or f'test {test_name} ... ok' not in stdout
                or 'test result: ok. 1 passed; 0 failed;' not in stdout):
            raise RuntimeError(f'{label} did not pass exactly one restored public regression')
        BASE.verify_pass(label, status, stdout + stderr,
                         [f'test {test_name} ... ok', line,
                          'test result: ok. 1 passed; 0 failed;'])


def main() -> int:
    global BASE, PINS
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
    BASE.CONTRACT = stage / 'contract.md'
    BASE.SOURCE_ARCHIVE = stage / 'source.tar'
    BASE.LOCK_SOURCE = stage / 'Cargo.lock.accepted'
    BASE.RUSTUP = Path(os.environ['RUSTUP_BIN'])
    BASE.REVISION = os.environ['OVERLAP_SOURCE_REV']
    BASE.TOOLCHAIN = '1.77.2-x86_64-unknown-linux-gnu'
    BASE.FEATURES = 'testing-environ,sys'
    BASE.SOURCE = runtime / 'source'
    BASE.CARGO_HOME = runtime / 'cargo-home'
    BASE.RUSTUP_HOME = runtime / 'rustup-home'
    BASE.TARGET = runtime / 'target'
    BASE.PRIVATE_HOME = runtime / 'home'
    BASE.PRIVATE_TMP = Path(os.environ['TMPDIR'])
    BASE.SOURCE_ARCHIVE_SHA256 = os.environ['OVERLAP_ARCHIVE_SHA256']
    BASE.LOCK_SHA256 = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
    PINS = {'source_revision': BASE.REVISION,
            'source_archive_sha256': BASE.SOURCE_ARCHIVE_SHA256,
            'source_sha256': os.environ['OVERLAP_TEST_SHA256'],
            'base_helper_sha256': os.environ['OVERLAP_BASE_SHA256'],
            'lock_sha256': BASE.LOCK_SHA256}
    signal.signal(signal.SIGTERM, BASE.on_signal)
    signal.signal(signal.SIGINT, BASE.on_signal)
    BASE.capture_runtime_proof()
    BASE.validate_stage_inputs()
    if platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise RuntimeError('native Linux x86_64 required')
    if sha(stage / 'check-linux-current-msrv-examples.py') != PINS['base_helper_sha256']:
        raise RuntimeError('accepted helper input hash mismatch')
    if sha(BASE.SOURCE_ARCHIVE) != PINS['source_archive_sha256'] or sha(BASE.LOCK_SOURCE) != PINS['lock_sha256']:
        raise RuntimeError('frozen source archive or compatible lock hash mismatch')
    shutil.copy2(Path(__file__), BASE.STAGE / 'helper-used.py')
    for path in (BASE.CARGO_HOME, BASE.RUSTUP_HOME, BASE.PRIVATE_HOME, BASE.PRIVATE_TMP):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(BASE.PRIVATE_HOME),
           'TMPDIR': str(BASE.PRIVATE_TMP), 'TMP': str(BASE.PRIVATE_TMP),
           'TEMP': str(BASE.PRIVATE_TMP), 'CARGO_HOME': str(BASE.CARGO_HOME),
           'RUSTUP_HOME': str(BASE.RUSTUP_HOME), 'CARGO_TARGET_DIR': str(BASE.TARGET),
           'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
           'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_TERM_COLOR': 'never',
           'RUST_BACKTRACE': '0'}
    BASE.run_command('rustup-install', [str(BASE.RUSTUP), 'toolchain', 'install',
        BASE.TOOLCHAIN, '--profile', 'minimal', '--no-self-update'], env, cwd=runtime)
    bindir = BASE.RUSTUP_HOME / 'toolchains' / BASE.TOOLCHAIN / 'bin'
    rustc, cargo = bindir / 'rustc', bindir / 'cargo'
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError('private Rust 1.77.2 toolchain is incomplete')
    env.update(PATH=f'{bindir}:/usr/bin:/bin:/usr/sbin:/sbin', RUSTC=str(rustc))
    BASE.run_command('rustc-version', [str(rustc), '--version', '--verbose'], env, cwd=runtime)
    BASE.run_command('cargo-version', [str(cargo), '--version', '--verbose'], env, cwd=runtime)
    rustc_text = BASE.read_text(BASE.STAGE / 'rustc-version.stdout')
    cargo_text = BASE.read_text(BASE.STAGE / 'cargo-version.stdout')
    if (not rustc_text.startswith('rustc 1.77.2 ')
            or 'host: x86_64-unknown-linux-gnu' not in rustc_text
            or not cargo_text.startswith('cargo 1.77.2 ')):
        raise RuntimeError('private toolchain version/host mismatch')
    archive_copy = runtime / 'source-input.tar'
    shutil.copy2(BASE.SOURCE_ARCHIVE, archive_copy)
    BASE.extract_archive(archive_copy)
    archive_copy.unlink()
    source = BASE.SOURCE / SOURCE_REL
    if sha(source) != PINS['source_sha256']:
        raise RuntimeError('frozen unix.rs source hash mismatch')
    original = source.read_bytes()
    BASE.ORIGINAL_EXAMPLES[source] = original
    BASE.ORIGINAL_EXAMPLE_HASHES[SOURCE_REL] = PINS['source_sha256']
    manifests = BASE.manifest_hashes()
    BASE.CARGO_MANIFESTS = manifests
    shutil.copy2(BASE.LOCK_SOURCE, BASE.SOURCE / 'Cargo.lock')
    if sha(BASE.SOURCE / 'Cargo.lock') != PINS['lock_sha256']:
        raise RuntimeError('private compatible lock hash mismatch')
    BASE.write_json(BASE.STAGE / 'source-inputs.json',
                    {**PINS, 'cargo_manifests_sha256': manifests,
                     'test_names': TESTS, 'features': BASE.FEATURES})
    try:
        changed = move_timeout_before_read(source)[1]
        source.write_bytes(changed)
        mutant_sha256 = hashlib.sha256(changed).hexdigest()
        if mutant_sha256 != EXPECTED_MUTANT_SHA256:
            raise RuntimeError(f'reviewed timeout-order mutant hash mismatch: {mutant_sha256}')
        BASE.INJECTED_EXAMPLE_HASHES['timeout-first-ordering'] = mutant_sha256
        for mode in ('direct', 'managed'):
            run_case(mode, 'timeout-first', cargo, env, source)
        source.write_bytes(original)
        if sha(source) != PINS['source_sha256']:
            raise RuntimeError('baseline source did not restore after both timeout controls')
        for mode in ('direct', 'managed'):
            run_case(mode, 'restored', cargo, env, source)
    finally:
        source.write_bytes(original)
        if sha(source) != PINS['source_sha256']:
            raise RuntimeError('final source restoration hash mismatch')
    if BASE.manifest_hashes() != manifests or sha(BASE.SOURCE / 'Cargo.lock') != PINS['lock_sha256']:
        raise RuntimeError('manifest or Cargo.lock changed during controls')
    BASE.write_json(BASE.STAGE / 'tool-versions.json',
                    {'rustc_stdout': rustc_text, 'cargo_stdout': cargo_text,
                     'toolchain': BASE.TOOLCHAIN})
    BASE.write_json(BASE.STAGE / 'package-result.json',
                    {**PINS, 'test_names': TESTS, 'features': BASE.FEATURES,
                     'commands': BASE.COMMANDS, 'controls': BASE.CONTROL_RESULTS,
                     'source_restored_to_baseline': True, 'acceptance_claim': False})
    return 0


def export() -> None:
    if BASE is None or not BASE.STAGE.is_dir():
        return
    try:
        BASE.restore_example_sources()
    except BaseException as exc:
        BASE.write_json(BASE.STAGE / 'source-restoration-error.json', {'error': repr(exc)})
    restored = bool(BASE.ORIGINAL_EXAMPLES) and all(
        p.exists() and sha(p) == BASE.ORIGINAL_EXAMPLE_HASHES[p.relative_to(BASE.SOURCE).as_posix()]
        for p in BASE.ORIGINAL_EXAMPLES)
    BASE.write_json(BASE.STAGE / 'source-restoration.json',
                    {'original_example_sha256': BASE.ORIGINAL_EXAMPLE_HASHES,
                     'injected_example_sha256': BASE.INJECTED_EXAMPLE_HASHES,
                     'restored_examples_match_original_bytes': restored,
                     'manifest_sha256': BASE.manifest_hashes() if BASE.SOURCE.is_dir() else {},
                     'cargo_lock_sha256_after_execution': sha(BASE.SOURCE / 'Cargo.lock')
                     if (BASE.SOURCE / 'Cargo.lock').is_file() else None,
                     'error': None if restored else 'restoration incomplete'})
    BASE.write_json(BASE.STAGE / 'sampled-maxima.json',
                    {'maxima': BASE.MAXIMA, 'sample_count': len(BASE.SAMPLES),
                     'samples_are_periodic_not_continuous_peak': True,
                     'storage_preemptive_stop_kib': 1572864,
                     'storage_hard_stop_kib': 2097152,
                     'rss_hard_stop_kib': 2097152, 'descendant_hard_stop': 16})
    (BASE.STAGE / 'resource-samples.jsonl').write_text(
        ''.join(json.dumps(row, sort_keys=True) + '\n' for row in BASE.SAMPLES), encoding='utf-8')
    if not BASE.export_destination_is_safe():
        raise RuntimeError('evidence export destination identity is unverified')
    BASE.check_deadline(during_export=True)
    export_started = time.monotonic()
    BASE.EVIDENCE.mkdir(mode=0o700)
    for item in sorted(BASE.STAGE.iterdir()):
        BASE.check_deadline(during_export=True)
        target = BASE.EVIDENCE / item.name
        shutil.copytree(item, target) if item.is_dir() else shutil.copy2(item, target)
    BASE.check_deadline(during_export=True)
    BASE.write_json(BASE.STAGE / 'export-budget.json', {
        'elapsed_seconds_at_export_start': round(export_started - BASE.START, 3),
        'elapsed_seconds_before_budget_receipt_copy': round(time.monotonic() - BASE.START, 3),
        'helper_deadline_seconds': 540, 'helper_work_deadline_seconds': 510,
        'deadline_checked_at_entry_between_items_and_after': True,
        'individual_copy_operations_preemptible': False,
        'deadline_checked_immediately_before_and_after_budget_receipt_copy': True,
        'partial_evidence_may_remain_if_export_fails': True,
    })
    # The budget receipt itself is one final non-preemptible copy; check immediately
    # before and after it so the recorded budget includes its completion.
    BASE.check_deadline(during_export=True)
    shutil.copy2(BASE.STAGE / 'export-budget.json', BASE.EVIDENCE / 'export-budget.json')
    BASE.check_deadline(during_export=True)
    print(f'evidence_exported={BASE.EVIDENCE}', flush=True)


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
