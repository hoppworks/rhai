#!/usr/bin/env python3
"""Pure acceptance-boundary checks for the two-row Linux follow-up."""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

HERE = Path(__file__).resolve().parent
ROOT_EVIDENCE = Path(
    '/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/'
    '.scratch/all-tickets/linux-policy-package-evidence')
HELPER = HERE / 'check-linux-current-sys-net-policy2.py'
CONTRACT = HERE / 'linux-current-sys-net-policy2-contract.md'
STAGE_SCRIPT = HERE / 'stage-linux-current-sys-net-policy2.sh'
LAUNCH_SCRIPT = HERE / 'launch-linux-current-sys-net-policy2.sh'


def load_helper():
    spec = importlib.util.spec_from_file_location('linux_policy2_helper_test', HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_two_remaining_rows_are_exact_and_ordered() -> None:
    module = load_helper()
    assert tuple(row[0] for row in module.TEST_ROWS) == module.PLANNED_REMAINING_ROWS
    assert module.PLANNED_REMAINING_ROWS == (
        'combined-no-index-sync-metadata', 'combined-f32')
    assert tuple(row[0] for row in module.TEST_ROWS) == (
        'combined-no-index-sync-metadata', 'combined-f32')
    assert tuple(module.ACCEPTED_POLICY1_ROWS) == (
        'combined-baseline', 'combined-no-index', 'net-no-object',
        'combined-metadata-serde', 'combined-sync',
        'combined-i32-no-float', 'combined-unchecked')
    assert len(module.ASSERTION_CONTROLS) == 5
    assert all('--test-threads=1' not in str(row) for row in module.TEST_ROWS)
    assert 'sys_process' not in HELPER.read_text(encoding='utf-8')
    source = HELPER.read_text(encoding='utf-8')
    assert 'for control_name, features, target, test_name' not in source
    assert source.index('REUSE_RESULT = validate_reused_evidence(REUSED_EVIDENCE)') < source.index(
        'for row_name, features, targets in TEST_ROWS:')
    assert "current_host['os_release'] != previous_host['os_release']" in source
    assert "sha256(EVIDENCE / 'rustc-version.stdout')" in source
    assert "sha256(EVIDENCE / 'cargo-version.stdout')" in source
    assert 'Each row uses one locked Cargo test invocation' in CONTRACT.read_text(encoding='utf-8')


def test_reuse_receipts_validate_exact_source_rows_controls_and_environment() -> None:
    module = load_helper()
    with tempfile.TemporaryDirectory(prefix='linux-policy2-reused-') as temporary:
        receipt_dir = Path(temporary) / 'reused-policy1'
        receipt_dir.mkdir()
        for name in module.REUSED_EVIDENCE_SHA256:
            shutil.copy2(ROOT_EVIDENCE / name, receipt_dir / name)
        accepted = module.validate_reused_evidence(receipt_dir)
        assert accepted['receipt_verified'] is True
        assert accepted['positive_rows_reused'] == list(module.ACCEPTED_POLICY1_ROWS)
        assert accepted['controls_reused'] == [control[0] for control in module.ASSERTION_CONTROLS]
        assert accepted['controls_executed_this_invocation'] == 0
        assert accepted['source_revision'] == module.SOURCE_REVISION
        assert accepted['lock_sha256'] == module.LOCK_SHA256


def test_reuse_refuses_tampered_source_receipt_and_check_logic() -> None:
    module = load_helper()
    with tempfile.TemporaryDirectory(prefix='linux-policy2-reused-red-') as temporary:
        receipt_dir = Path(temporary) / 'reused-policy1'
        receipt_dir.mkdir()
        for name in module.REUSED_EVIDENCE_SHA256:
            shutil.copy2(ROOT_EVIDENCE / name, receipt_dir / name)

        source_receipt = receipt_dir / 'source-lock-manifests.json'
        value = json.loads(source_receipt.read_text())
        value['source_revision'] = 'unrelated-source'
        source_receipt.write_text(json.dumps(value), encoding='utf-8')
        try:
            module.validate_reused_evidence(receipt_dir)
        except RuntimeError as error:
            assert 'SHA-256 mismatch' in str(error)
        else:
            raise AssertionError('tampered source receipt was reused')

        shutil.copy2(ROOT_EVIDENCE / 'source-lock-manifests.json', source_receipt)
        check_logic = receipt_dir / 'helper-used.py'
        check_logic.write_bytes(check_logic.read_bytes() + b'\n# changed check logic\n')
        try:
            module.validate_reused_evidence(receipt_dir)
        except RuntimeError as error:
            assert 'SHA-256 mismatch' in str(error)
        else:
            raise AssertionError('changed prior acceptance logic was reused')


def test_staging_and_launcher_use_new_private_identity_and_preserve_prior_receipt() -> None:
    module = load_helper()
    stage = STAGE_SCRIPT.read_text(encoding='utf-8')
    launcher = LAUNCH_SCRIPT.read_text(encoding='utf-8')
    expected_stage = str(module.EXPECTED_STAGE)
    expected_scope = str(module.EXPECTED_SCOPE)
    assert expected_stage.endswith('-policy2') and expected_scope.endswith('-policy2')
    assert expected_stage in stage and expected_stage in launcher
    assert expected_scope in launcher
    assert 'linux-policy-package-evidence' in stage
    assert 'git -C "$repo" archive --format=tar "$source_rev"' in stage
    assert 'run-sys-net-policy2.py' in stage and 'run-sys-net-policy2.py' in launcher
    assert 'reused-policy1' in stage
    receipt_match = re.search(r'^receipt_names=\(([^)]*)\)$', stage, re.MULTILINE)
    assert receipt_match
    staged_names = receipt_match.group(1).split()
    assert staged_names == list(module.REUSED_EVIDENCE_SHA256)
    assert len(staged_names) == len(set(staged_names))
    identity_line = next(line for line in stage.splitlines()
                         if 'sha256sum source.tar ' in line and '> input-identities.sha256' in line)
    identity_names = [value.removeprefix('reused-policy1/')
                      for value in identity_line.split('sha256sum ', 1)[1]
                      .split(' > input-identities.sha256', 1)[0].split()
                      if value.startswith('reused-policy1/')]
    assert identity_names == staged_names
    assert 'interrupt.request' in launcher and 'rmdir "$scope"' in launcher
    assert 'python3 "$runner" --timeout 600 --' in launcher
    assert 'behavior-combined-baseline' not in launcher
    assert 'kill ' not in launcher
    for path in (STAGE_SCRIPT, LAUNCH_SCRIPT):
        import subprocess
        subprocess.run(['/bin/bash', '-n', str(path)], check=True, timeout=5)
    lines = launcher.splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        if lines[index].strip().endswith("<<'PY'"):
            index += 1
            body = []
            while index < len(lines) and lines[index] != 'PY':
                body.append(lines[index])
                index += 1
            assert index < len(lines), 'unterminated Python heredoc'
            blocks.append('\n'.join(body))
        index += 1
    assert len(blocks) == 2
    for body in blocks:
        ast.parse(body)


def main() -> None:
    test_two_remaining_rows_are_exact_and_ordered()
    test_reuse_receipts_validate_exact_source_rows_controls_and_environment()
    test_reuse_refuses_tampered_source_receipt_and_check_logic()
    test_staging_and_launcher_use_new_private_identity_and_preserve_prior_receipt()
    print('exact_two_row_followup_plan=PASS')
    print('pinned_prior_rows_controls_and_environment_reuse=PASS')
    print('tampered_source_and_check_receipts_fail_closed=PASS')
    print('unique_stage_scope_and_wrapper_syntax=PASS')


if __name__ == '__main__':
    main()
