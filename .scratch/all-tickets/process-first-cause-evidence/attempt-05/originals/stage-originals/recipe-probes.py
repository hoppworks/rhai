#!/usr/bin/env python3
"""Exercise the first-cause package's local, bounded preparation contracts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path


EXPECTED_ARGV = [
    '/usr/bin/python3', '-c',
    "exec(open(__import__('os').environ['RHAI_FIRST_SCRIPT']).read())",
]
EXPECTED_ARGV_JSON = json.dumps(EXPECTED_ARGV, separators=(',', ':'))
TESTS = {
    'direct': 'packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_direct_child',
    'managed': 'packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_managed',
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(action, error_type, message: str) -> None:
    try:
        action()
    except error_type:
        return
    raise AssertionError(message)


def probe_archive_builder(evidence: Path, repository: Path) -> None:
    builder = load('first_cause_archive_builder', evidence / 'archive-build-source.py')
    adapted = builder.build_archive(str(repository), 'HEAD', evidence / 'fixture-adapter.patch')
    with tarfile.open(fileobj=io.BytesIO(adapted), mode='r:') as archive:
        members = [item for item in archive.getmembers()
                   if item.name == 'src/packages/sys/process/unix.rs']
        assert len(members) == 1 and members[0].isfile()
        archived_source = archive.extractfile(members[0]).read()
    current = (repository / 'src/packages/sys/process/unix.rs').read_bytes()
    fixed = b'''        if let Some(error) = &state.error {\n            let report = child_process_report(&state);\n            return Err(SysError::Process {\n                cause: error.clone(),\n                report,\n            }\n            .into());\n        }\n'''
    baseline = b'''        if let Some(error) = &state.error {\n            let stdout = String::from_utf8_lossy(&state.stdout);\n            let stderr = String::from_utf8_lossy(&state.stderr);\n            let cause = if state.engine_limit > 0\n                && (stdout.len() > state.engine_limit || stderr.len() > state.engine_limit)\n            {\n                ProcessCause::OutputLimit(format!(\n                    \"decoded process output exceeded the engine string limit of {} bytes\",\n                    state.engine_limit\n                ))\n            } else {\n                error.clone()\n            };\n            let report = child_process_report(&state);\n            return Err(SysError::Process { cause, report }.into());\n        }\n'''
    assert current.count(fixed) == 1
    expected = current.replace(fixed, baseline, 1)
    assert archived_source == expected, 'archive differs from the reviewed fixture adapter and intended production baseline'
    for marker in ('identity_ack', 'identity-wait', 'parent-confirmed-live-child-identity'):
        assert marker.encode() in archived_source, f'archive omits synchronization marker: {marker}'

    producer = load('first_cause_producer_for_patch_probe', evidence / 'linux-process-first-cause-proof.py')
    assert producer.apply_patch_bytes(archived_source) != archived_source
    assert hashlib.sha256(adapted).hexdigest() != hashlib.sha256(b'').hexdigest()

    patch_text = (evidence / 'fixture-adapter.patch').read_text()
    bad_text = patch_text.replace(
        '     stdin: Option<ChildStdin>,',
        '     stdin: Option<ChildStdinXYZ>,', 1)
    assert bad_text != patch_text
    with tempfile.TemporaryDirectory(prefix='first-cause-bad-patch-') as raw:
        bad_patch = Path(raw) / 'bad.patch'
        bad_patch.write_text(bad_text)
        expect_error(lambda: builder.build_archive(str(repository), 'HEAD', bad_patch),
                     subprocess.CalledProcessError,
                     'archive builder accepted a corrupted test-adapter patch')


def receipt(mode: str = 'direct', *, argv_hex: str | None = None,
            argv_count: str = '3', identity_confirmed: str = 'true',
            identity_gate_released: str = 'true', identity_wait: str = 'acknowledged') -> tuple[str, dict[str, str]]:
    vector = b'\0'.join(value.encode() for value in EXPECTED_ARGV) + b'\0'
    observed = vector.hex() if argv_hex is None else argv_hex
    values = {
        'child_pid': '123', 'child_start_ticks': '456',
        'child_pgid': '123' if mode == 'managed' else '90',
        'expected_program': '/usr/bin/python3', 'expected_argv_count': argv_count,
        'child_cmdline_hex': observed, 'identity_confirmed': identity_confirmed,
        'identity_gate_released': identity_gate_released, 'identity_wait': identity_wait,
        'stdout_write': 'acknowledged',
        'stdout_committed': 'true', 'stderr_write': 'acknowledged',
        'stderr_overflow': 'observed', 'reap': 'ESRCH',
        'group_closed': 'true' if mode == 'managed' else 'false',
    }
    raw = (f'test {TESTS[mode]} ... first-cause mode={mode} '
           + ' '.join(f'{k}={v}' for k, v in values.items()))
    return raw, values


def libtest_output(mode: str, outcome: str) -> str:
    raw, _ = receipt(mode)
    summary = ('test result: ok. 1 passed; 0 failed;'
               if outcome == 'ok' else 'test result: FAILED. 0 passed; 1 failed;')
    return f'running 1 test\n{raw}\n{outcome}\n\n{summary}\n'


def ledger_row(mode: str = 'direct', **changes: str) -> tuple[dict[str, str], str]:
    raw, values = receipt(mode, **changes)
    row = {
        'case': f'baseline-red-{mode}', 'pid': values['child_pid'],
        'start_ticks': values['child_start_ticks'], 'pgid': values['child_pgid'],
        'expected_argv': EXPECTED_ARGV_JSON,
        'observed_cmdline_hex': values['child_cmdline_hex'],
        'identity_confirmed': values['identity_confirmed'],
        'identity_gate_released': values['identity_gate_released'],
        'identity_wait': values['identity_wait'],
        'stdout_write': values['stdout_write'], 'stdout_committed': values['stdout_committed'],
        'stderr_write': values['stderr_write'], 'stderr_overflow': values['stderr_overflow'],
        'reap': values['reap'], 'group_closed': values['group_closed'],
    }
    return row, raw


def probe_receipt_contracts(evidence: Path) -> None:
    producer = load('first_cause_producer_for_receipt_probe', evidence / 'linux-process-first-cause-proof.py')
    collector = load('first_cause_collector_for_receipt_probe', evidence / 'collect-first-cause-originals.py')
    closure = load('first_cause_closure_for_receipt_probe', evidence / 'linux-process-first-cause-fresh-closure.py')
    raw, _ = receipt()
    parsed = producer.parse_fixture_receipt(raw, 'direct', 'probe')
    assert parsed['child_cmdline_hex'] == receipt()[1]['child_cmdline_hex']
    assert closure.fixture_receipt(raw, 'direct', 'probe').startswith(
        f'first-cause mode=direct child_pid={receipt()[1]["child_pid"]}')
    green_stdout = libtest_output('direct', 'ok')
    red_stdout = libtest_output('direct', 'FAILED')
    for module in (producer, collector, closure):
        assert module.selected_test_status(green_stdout, 'direct', 'ok')
        assert module.selected_test_status(red_stdout, 'direct', 'FAILED')
        assert not module.selected_test_status(green_stdout, 'direct', 'FAILED')
        assert not module.selected_test_status(green_stdout.replace('\nok\n', '\n', 1), 'direct', 'ok')
    wrong_test_prefix = raw.replace(f'test {TESTS["direct"]} ... ', 'test unrelated ... ', 1)
    expect_error(lambda: producer.parse_fixture_receipt(
        wrong_test_prefix, 'direct', 'wrong-test-prefix'), RuntimeError,
        'producer accepted a receipt attached to the wrong selected test')
    expect_error(lambda: producer.parse_fixture_receipt(
        raw + '\n' + raw, 'direct', 'duplicate-receipt'), RuntimeError,
        'producer accepted duplicate raw child receipts')
    expect_error(lambda: closure.fixture_receipt(
        wrong_test_prefix, 'direct', 'wrong-test-prefix'), ValueError,
        'closure accepted a receipt attached to the wrong selected test')
    expect_error(lambda: closure.fixture_receipt(
        raw + '\n' + raw, 'direct', 'duplicate-receipt'), ValueError,
        'closure accepted duplicate raw child receipts')
    expect_error(lambda: producer.parse_fixture_receipt(
        receipt(argv_hex='00')[0], 'direct', 'bad-argv'), RuntimeError,
        'producer accepted a mismatched observed argv')
    expect_error(lambda: producer.parse_fixture_receipt(
        receipt(argv_count='4')[0], 'direct', 'bad-count'), RuntimeError,
        'producer accepted an incorrect argv count')
    expect_error(lambda: producer.parse_fixture_receipt(
        receipt(identity_confirmed='false')[0], 'direct', 'identity-not-confirmed'), RuntimeError,
        'producer accepted a missing live-child identity readback')
    expect_error(lambda: producer.parse_fixture_receipt(
        receipt(identity_wait='deadline')[0], 'direct', 'identity-ack-timeout'), RuntimeError,
        'producer accepted a timed-out identity acknowledgement')

    row, raw = ledger_row()
    collector.bind_fixture_row(row, raw, row['case'])
    wrong_test_prefix = raw.replace(f'test {TESTS["direct"]} ... ', 'test unrelated ... ', 1)
    expect_error(lambda: collector.bind_fixture_row(row, wrong_test_prefix, row['case']),
                 ValueError, 'collector accepted a receipt attached to the wrong selected test')
    expect_error(lambda: collector.bind_fixture_row(row, raw + '\n' + raw, row['case']),
                 ValueError, 'collector accepted duplicate raw child receipts')
    corrupted = dict(row, observed_cmdline_hex='00')
    expect_error(lambda: collector.bind_fixture_row(corrupted, raw, row['case']),
                 ValueError, 'collector accepted a mismatched observed argv')
    corrupted = dict(row, expected_argv='["/usr/bin/python3"]')
    expect_error(lambda: collector.bind_fixture_row(corrupted, raw, row['case']),
                 ValueError, 'collector accepted a mismatched expected argv')


def probe_source_phase_contract(evidence: Path) -> None:
    collector = load('first_cause_collector_for_phase_probe', evidence / 'collect-first-cause-originals.py')
    rows = [
        {'phase': 'baseline', 'sha256': 'a' * 64},
        {'phase': 'proposed-fix', 'sha256': 'b' * 64},
        {'phase': 'stderr-overwrite-mutant', 'sha256': 'c' * 64},
        {'phase': 'restored-fix', 'sha256': 'b' * 64},
        {'phase': 'pre-restoration', 'sha256': 'b' * 64},
        {'phase': 'final-baseline-restored', 'sha256': 'a' * 64},
    ]
    collector.validate_source_phases(rows, 'a' * 64, 'd' * 64, 'd' * 64, True)
    wrong_pre_restoration = [dict(row) for row in rows]
    wrong_pre_restoration[-2]['sha256'] = 'c' * 64
    expect_error(lambda: collector.validate_source_phases(
        wrong_pre_restoration, 'a' * 64, 'd' * 64, 'd' * 64, True), ValueError,
        'collector accepted a source that was not the restored fix before baseline cleanup')
    expect_error(lambda: collector.validate_source_phases(
        rows, 'a' * 64, 'd' * 64, 'e' * 64, True), ValueError,
        'collector accepted a wrong production patch hash')
    wrong_restoration = [dict(row) for row in rows]
    wrong_restoration[-1]['sha256'] = 'c' * 64
    expect_error(lambda: collector.validate_source_phases(
        wrong_restoration, 'a' * 64, 'd' * 64, 'd' * 64, True), ValueError,
        'collector accepted an unrestored baseline')


def probe_partial_evidence(evidence: Path) -> None:
    producer = load('first_cause_producer_for_export_probe', evidence / 'linux-process-first-cause-proof.py')
    with tempfile.TemporaryDirectory(prefix='first-cause-partial-export-') as raw:
        root = Path(raw)
        stage, destination = root / 'stage', root / 'destination'
        stage.mkdir(); (stage / 'a.txt').write_text('first\n'); (stage / 'b.txt').write_text('second\n')
        checks = {'count': 0}

        def fail_after_one(*, during_export: bool = False):
            assert during_export is True
            checks['count'] += 1
            if checks['count'] == 2:
                raise TimeoutError('injected bounded export interruption')

        expect_error(lambda: producer.preserve_partial_evidence(
            stage, destination, check_deadline=fail_after_one,
            destination_is_safe=lambda: True), TimeoutError,
            'partial exporter did not surface an injected deadline')
        assert (destination / 'a.txt').read_text() == 'first\n'
        assert not (destination / 'b.txt').exists()
        producer.preserve_partial_evidence(
            stage, destination, check_deadline=lambda **_: None,
            destination_is_safe=lambda: True)
        assert (destination / 'a.txt').read_text() == 'first\n'
        assert (destination / 'b.txt').read_text() == 'second\n'

        (destination / 'a.txt').write_text('conflict\n')
        expect_error(lambda: producer.preserve_partial_evidence(
            stage, destination, check_deadline=lambda **_: None,
            destination_is_safe=lambda: True), RuntimeError,
            'partial exporter overwrote conflicting preserved evidence')
        expect_error(lambda: producer.preserve_partial_evidence(
            stage, destination, check_deadline=lambda **_: None,
            destination_is_safe=lambda: False), RuntimeError,
            'partial exporter ignored an unsafe destination')

        (stage / 'linked.txt').symlink_to(stage / 'a.txt')
        expect_error(lambda: producer.preserve_partial_evidence(
            stage, destination, check_deadline=lambda **_: None,
            destination_is_safe=lambda: True), RuntimeError,
            'partial exporter followed a source symlink')

    with tempfile.TemporaryDirectory(prefix='first-cause-final-export-') as raw:
        root = Path(raw)
        stage, destination = root / 'stage', root / 'destination'
        stage.mkdir()
        (stage / 'package-result.json').write_text('{"package_status":"complete"}\n')
        (stage / 'export-budget.json').write_text('{}\n')
        checks = {'count': 0}

        def checked_deadline(*, during_export: bool = False):
            assert during_export is True
            checks['count'] += 1

        def prepare_final_item(path: Path):
            assert path.name == 'export-budget.json'
            path.write_text('{"elapsed_seconds_before_budget_receipt_copy":1.25}\n')

        producer.preserve_partial_evidence(
            stage, destination, check_deadline=checked_deadline,
            destination_is_safe=lambda: True, final_item_name='export-budget.json',
            prepare_final_item=prepare_final_item)
        assert sorted(p.name for p in destination.iterdir()) == ['export-budget.json', 'package-result.json']
        budget = json.loads((destination / 'export-budget.json').read_text())
        assert budget['elapsed_seconds_before_budget_receipt_copy'] == 1.25
        assert checks['count'] >= 4


def probe_required_export_receipts(evidence: Path) -> None:
    producer = load('first_cause_producer_for_receipt_set_probe', evidence / 'linux-process-first-cause-proof.py')
    collector = load('first_cause_collector_for_resource_probe', evidence / 'collect-first-cause-originals.py')
    with tempfile.TemporaryDirectory(prefix='first-cause-required-receipts-') as raw:
        stage = Path(raw)
        for name in producer.REQUIRED_EXPORT_RECEIPTS - {'sampled-maxima.json', 'resource-samples.jsonl'}:
            (stage / name).write_text('{}\n')
        expect_error(lambda: producer.validate_export_receipt_set(stage), RuntimeError,
                     'export preflight accepted missing resource receipts')

        samples = [{'monotonic_seconds': 1.0, 'storage_kib': 80,
                    'rss_kib': 120, 'descendants': 2}]

        def write_json(path: Path, value: object) -> None:
            path.write_text(json.dumps(value, sort_keys=True) + '\n')

        class ResourceBase:
            pass

        base = ResourceBase()
        base.MAXIMA = {'storage_kib': 80, 'rss_kib': 120, 'descendants': 2}
        base.SAMPLES = samples
        base.PREEMPTIVE_STORAGE_KIB = 1572864
        base.HARD_STORAGE_KIB = 2097152
        base.HARD_RSS_KIB = 2097152
        base.MAX_DESCENDANTS = 16
        base.write_json = write_json
        producer.write_resource_evidence(base, stage)
        producer.validate_export_receipt_set(stage)
        maxima = json.loads((stage / 'sampled-maxima.json').read_text())
        rows = [json.loads(line) for line in (stage / 'resource-samples.jsonl').read_text().splitlines()]
        collector.validate_resource_receipts(rows, maxima)
        assert maxima['sample_count'] == 1
        assert maxima['samples_are_periodic_not_continuous_peak'] is True


def probe_early_abort_export(evidence: Path) -> None:
    producer = load('first_cause_producer_for_early_abort_probe', evidence / 'linux-process-first-cause-proof.py')
    with tempfile.TemporaryDirectory(prefix='first-cause-early-abort-export-') as raw:
        root = Path(raw)
        stage, destination = root / 'stage', root / 'destination'
        stage.mkdir()
        (stage / 'failure.txt').write_text('toolchain setup failed before selected controls\n')
        (stage / 'process-identities.tsv').write_text('pid\tstart_ticks\tpgid\n123\t456\t123\n')
        (stage / 'early-runtime-identity.json').write_text('{"runtime_pid":123}\n')

        class PartialBase:
            START = 0.0
            RUNTIME = root / 'runtime'
            EVIDENCE = destination
            STAGE = stage
            MAXIMA = {'storage_kib': 8, 'rss_kib': 16, 'descendants': 1}
            SAMPLES = []
            PREEMPTIVE_STORAGE_KIB = 1572864
            HARD_STORAGE_KIB = 2097152
            HARD_RSS_KIB = 2097152
            MAX_DESCENDANTS = 16

            @staticmethod
            def write_json(path: Path, value: object) -> None:
                path.write_text(json.dumps(value, sort_keys=True) + '\n')

            @staticmethod
            def check_deadline(*, during_export: bool = False) -> None:
                assert during_export is True

            @staticmethod
            def export_destination_is_safe() -> bool:
                return True

        producer.BASE = PartialBase()
        expect_error(lambda: producer.validate_export_receipt_set(stage, require_complete=True),
                     RuntimeError, 'complete export accepted an early-abort receipt set')
        producer.export_package_evidence(require_complete=False)

        for name in ('failure.txt', 'process-identities.tsv', 'early-runtime-identity.json',
                     'sampled-maxima.json', 'resource-samples.jsonl', 'export.json',
                     'export-budget.json'):
            assert (destination / name).is_file(), f'early-abort export lost {name}'
        result = json.loads((destination / 'export-budget.json').read_text())
        assert result['elapsed_seconds_before_budget_receipt_copy'] >= 0


def probe_generator(evidence: Path, generator_path: Path, source_revision: str) -> None:
    generator = load('first_cause_admission_generator', generator_path)
    names = [
        'source.tar', 'Cargo.lock.accepted', 'archive-build-source.py',
        'check-linux-current-msrv-examples.py', 'source-freeze.json', 'contract.md',
        'linux-process-first-cause-proof.py', 'fixture-adapter.patch',
        'preserve-primary-cause.patch', 'collect-first-cause-originals.py',
        'linux-process-first-cause-fresh-closure.py', 'recipe-probes.py', 'launch.sh',
        'runner/tools/run_scoped.py', 'runner/tools/agentskills/__init__.py',
        'runner/tools/agentskills/pyguard.py',
    ]
    pins = {name: hashlib.sha256((evidence / name).read_bytes()).hexdigest()
            if (evidence / name).is_file() else hashlib.sha256(name.encode()).hexdigest()
            for name in names if not name.startswith('runner/tools/')}
    pins.update({
        'runner/tools/run_scoped.py': '1' * 64,
        'runner/tools/agentskills/__init__.py': '2' * 64,
        'runner/tools/agentskills/pyguard.py': '3' * 64,
    })
    assert len(pins) == 16
    guard, wrapper, remote = generator.derive(source_revision, pins)
    compile(guard, '<generated-preflight>', 'exec')
    compile(wrapper, '<generated-slot-wrapper>', 'exec')
    assert 'native_launch=1,campaign_allocation=5,' in wrapper
    assert all(name in remote for name in names)
    assert generator.NEW_STAGE in remote
    assert generator.NEW_PHYSICAL_STAGE in remote
    assert 'parserfix-01' not in remote, 'generated preflight retains a retired stage identity'
    assert generator.NEW_SCOPE in remote

    with tempfile.TemporaryDirectory(prefix='first-cause-admission-output-') as raw:
        output = Path(raw)
        result = generator.write_outputs(output, source_revision, pins)
        assert result['inputs'] == 16
        generator.write_outputs(output, source_revision, pins)
        expect_error(lambda: generator.write_outputs(output, source_revision, dict(pins, **{'source.tar': 'f' * 64})),
                     ValueError, 'admission generator overwrote a conflicting exact output')


def probe_campaign_allocation_receipt(evidence: Path) -> None:
    wrapper = (evidence / 'linux-process-first-cause-slot-wrapper.py').read_text()
    assert 'native_launch=1,campaign_allocation=5,' in wrapper, (
        'receipt must keep its archive-local launch identity and cumulative allocation'
    )


def probe_stage_transfer_destinations(evidence: Path) -> None:
    stage = (evidence / 'stage.sh').read_text()
    transfers = re.findall(r'\bscp\s+"[^"]+"\s+"([^"]+)"', stage)
    assert len(transfers) == 5, 'stager must transfer the five declared input groups'
    for destination in transfers:
        assert destination.startswith('workhorse:'), f'stage destination is not Workhorse: {destination}'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--repository', type=Path)
    parser.add_argument('--generator', type=Path)
    parser.add_argument('--skip-admission-generation', action='store_true')
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    if not evidence.is_dir() or evidence.is_symlink():
        raise SystemExit('evidence directory must be an existing real directory')
    required = ('archive-build-source.py', 'linux-process-first-cause-proof.py',
                'collect-first-cause-originals.py', 'fixture-adapter.patch',
                'preserve-primary-cause.patch')
    if any(not (evidence / name).is_file() or (evidence / name).is_symlink() for name in required):
        raise SystemExit('a required preparation input is absent or symlinked')
    syntax_inputs = [
        'archive-build-source.py', 'check-linux-current-msrv-examples.py',
        'linux-process-first-cause-proof.py', 'collect-first-cause-originals.py',
        'linux-process-first-cause-fresh-closure.py', 'recipe-probes.py',
        'linux-process-first-cause-preflight.py',
        'linux-process-first-cause-slot-wrapper.py',
    ]
    for name in syntax_inputs:
        path = evidence / name
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise SystemExit(f'syntax input is not a regular file: {name}')
            compile(path.read_text(), str(path), 'exec')
    if not args.skip_admission_generation:
        if args.generator is None or args.repository is None:
            raise SystemExit('local probes require the source repository and admission generator')
        revision = subprocess.check_output(
            ['git', '-C', str(args.repository), 'rev-parse', '--verify', 'HEAD^{commit}'], text=True
        ).strip()
        probe_archive_builder(evidence, args.repository)
        probe_generator(evidence, args.generator, revision)
        probe_stage_transfer_destinations(evidence)
    probe_receipt_contracts(evidence)
    probe_source_phase_contract(evidence)
    probe_partial_evidence(evidence)
    probe_required_export_receipts(evidence)
    probe_early_abort_export(evidence)
    probe_campaign_allocation_receipt(evidence)
    print('first_cause_recipe_probes=pass')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
