#!/usr/bin/env python3
"""Source-only contract checks for the prepared Darwin behavior runner."""
from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path
from unittest import mock
import contextlib
import io
import json
import sys
import tempfile

HERE = Path(__file__).resolve().parent
HELPER = HERE / 'check-current-darwin-sys-net-behavior.py'
CONTRACT = HERE / 'current-darwin-sys-net-behavior-contract.md'


def load_helper():
    with mock.patch.dict(os.environ, {'AGENT_RUNTIME_DIR': '/tmp/darwin-source-test/runtime'}):
        spec = importlib.util.spec_from_file_location('darwin_sys_net_behavior', HELPER)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def test_pins_and_rows():
    tree = ast.parse(HELPER.read_text(encoding='utf-8'))
    values = {node.targets[0].id: ast.literal_eval(node.value)
              for node in tree.body if isinstance(node, ast.Assign)
              and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
              and isinstance(node.value, ast.Constant)}
    assert values['SOURCE_REVISION'] == '2f795ecee8edd6ddf348f382e5397cc6e348ad37'
    assert values['SOURCE_ARCHIVE_SHA256'] == '43c8b8e43a2bcd3e74dd0be3d60a0dea2eab50eb5bfe65cc736684631523d52b'
    assert values['LOCK_SHA256'] == '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
    assert values['TOOLCHAIN'] == '1.77.2-aarch64-apple-darwin'
    rows = ast.literal_eval(next(node.value for node in tree.body if isinstance(node, ast.Assign)
                                 and getattr(node.targets[0], 'id', None) == 'TEST_ROWS'))
    assert [row[0] for row in rows] == [
        'combined-baseline', 'combined-no-index', 'net-no-object',
        'combined-metadata-serde', 'combined-sync', 'combined-i32-no-float',
        'combined-unchecked', 'combined-no-index-sync-metadata', 'combined-f32']


def test_controls_require_the_intended_red():
    module = load_helper()
    test_name = 'stream_read_string_returns_exact_lossy_text_from_peer_bytes'
    context = ('left: "a�b"', 'right: "wrong peer payload"')
    output = (f'running 1 test\ntest {test_name} ... FAILED\n'
              f"thread '{test_name}' panicked at tests/net_reads.rs:2:3:\n"
              'assertion `left == right` failed\n' + '\n'.join(context) + '\n'
              f'failures:\n    {test_name}\n'
              'test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 8 filtered out; finished in 0.00s\n')
    assert module.classify_assertion_control(101, output, 'net_reads', test_name, context)['diagnostic_found']
    assert not module.classify_assertion_control(
        101, output.replace('wrong peer payload', 'different error'),
        'net_reads', test_name, context)['diagnostic_found']
    assert not module.classify_assertion_control(101, 'error[E0432]: build failed',
                                                  'net_reads', test_name, context)['diagnostic_found']


def test_resource_census_excludes_only_its_reaped_ps_observer():
    module = load_helper()
    with tempfile.TemporaryDirectory() as temp:
        module.RUNTIME = Path(temp)
        module.RECORDED_PIDS = {100}
        module.SAMPLES.clear()
        module.MAXIMA.update(storage_kib=0, rss_kib=0, descendants=0)
        class Observer:
            pid = 777
            returncode = None
            def communicate(self, timeout):
                assert timeout == 5
                self.returncode = 0
                return ('100 1 120\n777 100 40\n', '')
        def run(command, **kwargs):
            if command[0] == '/usr/bin/du':
                return type('Completed', (), {'stdout': '1\t/tmp/runtime\n'})()
            assert command[0] == '/bin/ps'
            return type('Completed', (), {'stdout': '100 1 120\n777 100 40\n'})()
        with mock.patch.object(module.os, 'getpid', return_value=100), \
             mock.patch.object(module.subprocess, 'run', side_effect=run), \
             mock.patch.object(module.subprocess, 'Popen', return_value=Observer()), \
             mock.patch.object(module, 'process_identity', side_effect=AssertionError('observer must not be re-identified')):
            module.sample_resources()
        assert module.SAMPLES[-1]['rss_kib'] == 120
        assert module.SAMPLES[-1]['descendants'] == 0


def test_resource_census_still_fails_for_unknown_real_descendant():
    module = load_helper()
    with tempfile.TemporaryDirectory() as temp:
        module.RUNTIME = Path(temp)
        module.RECORDED_PIDS = {100}
        module.SAMPLES.clear()
        def run(command, **kwargs):
            return type('Completed', (), {'stdout': '1\t/tmp/runtime\n'})()
        class Observer:
            pid = 777
            returncode = None
            def communicate(self, timeout):
                self.returncode = 0
                return ('100 1 120\n777 100 40\n888 100 10\n', '')
        with mock.patch.object(module.os, 'getpid', return_value=100), \
             mock.patch.object(module.subprocess, 'run', side_effect=run), \
             mock.patch.object(module.subprocess, 'Popen', return_value=Observer()), \
             mock.patch.object(module, 'process_identity', return_value=None):
            try:
                module.sample_resources()
            except RuntimeError as error:
                assert 'owned descendant 888' in str(error)
            else:
                raise AssertionError('unknown real descendant identity did not fail closed')


def test_resource_census_interrupt_kills_and_reaps_exact_observer():
    module = load_helper()
    with tempfile.TemporaryDirectory() as temp:
        module.RUNTIME = Path(temp)
        module.RECORDED_PIDS = {100}
        module.SAMPLES.clear()
        class Observer:
            pid = 777
            returncode = None
            actions = []
            calls = 0
            def communicate(self, timeout):
                self.actions.append(('communicate', timeout))
                self.calls += 1
                if self.calls == 1:
                    raise KeyboardInterrupt()
                if self.calls == 2:
                    raise module.subprocess.TimeoutExpired('ps', timeout)
                self.returncode = -9
                return ('', '')
            def terminate(self):
                self.actions.append(('terminate',))
            def kill(self):
                self.actions.append(('kill',))
        observer = Observer()
        def run(command, **kwargs):
            return type('Completed', (), {'stdout': '1\t/tmp/runtime\n'})()
        with mock.patch.object(module.os, 'getpid', return_value=100), \
             mock.patch.object(module.subprocess, 'run', side_effect=run), \
             mock.patch.object(module.subprocess, 'Popen', return_value=observer):
            try:
                module.sample_resources()
            except KeyboardInterrupt:
                pass
            else:
                raise AssertionError('observer communication interruption was swallowed')
        assert observer.actions == [
            ('communicate', 5), ('terminate',), ('communicate', 1),
            ('kill',), ('communicate', 1)]


def test_darwin_early_return_and_named_coverage_are_uncovered():
    module = load_helper()
    text = ('     Running tests/sys_fs.rs (target/debug/deps/sys_fs-abc)\n'
            'running 2 tests\ntest filesystem_read ... ok\n'
            'test test_non_utf8_file_name ... filesystem rejects non-UTF-8 fixture with EILSEQ: Illegal byte sequence (os error 92)\n'
            'ok\ntest result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    expected = {'sys_fs': ['filesystem_read', 'test_non_utf8_file_name']}
    result = module.positive_test_coverage(text, ('sys_fs',), expected)
    assert result['coverage_found'] is False
    assert result['skipped_tests'][0]['test'] == 'test_non_utf8_file_name'
    sys_fs_row = result['target_results'][0]
    assert sys_fs_row['completed_named_tests'] == ['filesystem_read']
    assert sys_fs_row['uncovered_named_tests'] == ['test_non_utf8_file_name']
    no_skips = ('     Running tests/sys_fs.rs (target/debug/deps/sys_fs-abc)\n'
                'running 2 tests\ntest filesystem_read ... ok\ntest test_non_utf8_file_name ... ok\n'
                'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    assert module.positive_test_coverage(no_skips, ('sys_fs',), expected)['coverage_found']
    assert not module.positive_test_coverage(
        no_skips.replace('test test_non_utf8_file_name ... ok\n', ''), ('sys_fs',), expected)['coverage_found']
    duplicate = no_skips.replace('finished in 0.00s', 'finished in 0.00s', 1).replace(
        'test result:', 'test result:', 1) + 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
    assert not module.positive_test_coverage(duplicate, ('sys_fs',), expected)['coverage_found']
    inventory = module.frozen_test_inventory(HERE.parents[1], 'testing-environ,sys,net')
    assert 'test_non_utf8_file_name' in inventory['sys_fs']
    assert len(inventory['sys_fs']) > 2
    for _name, features, targets in module.TEST_ROWS:
        expected = module.frozen_test_inventory(HERE.parents[1], features)
        assert all(expected.get(target) for target in targets)


def test_cleanup_fails_closed_and_detects_reparented_process():
    spec = importlib.util.spec_from_file_location('darwin_cleanup', HERE / 'readback-current-darwin-sys-net-cleanup.py')
    cleanup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cleanup)
    with mock.patch.object(cleanup.subprocess, 'run', side_effect=PermissionError('denied')):
        try:
            cleanup.identity(123)
        except cleanup.CleanupUnknown:
            pass
        else:
            raise AssertionError('permission error was treated as confirmed process absence')
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); evidence = root / 'evidence'; evidence.mkdir()
        scope = root / 'scope'; scope.mkdir(); runtime = scope / 'runtime'
        (evidence / 'early-runtime-identity.json').write_text(json.dumps({'runtime': str(runtime)}))
        (evidence / 'process-identities.tsv').write_text(
            'label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n'
            'helper\t123\t9\t123\t456\tpython helper\n'
            'scoped-supervisor\t124\t9\t9\t457\tpython supervisor\n')
        with mock.patch.object(cleanup, 'identity', side_effect=[
                (1, 123, '456', 'python helper'), None]):
            with mock.patch.object(sys, 'argv', ['readback','--evidence',str(evidence),'--runtime',str(runtime),'--scope',str(scope)]):
                try:
                    cleanup.main()
                except SystemExit as exc:
                    assert 'process remains' in str(exc)
                else:
                    raise AssertionError('reparented process was treated as absent')


def test_cleanup_rejects_live_owned_process_group_member():
    spec = importlib.util.spec_from_file_location('darwin_cleanup_group', HERE / 'readback-current-darwin-sys-net-cleanup.py')
    cleanup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cleanup)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); evidence = root / 'evidence'; evidence.mkdir()
        scope = root / 'scope'; scope.mkdir(); runtime = scope / 'runtime'
        (evidence / 'early-runtime-identity.json').write_text(json.dumps({'runtime': str(runtime)}))
        (evidence / 'process-identities.tsv').write_text(
            'label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n'
            'helper\t123\t9\t123\t456\tpython helper\n'
            'scoped-supervisor\t124\t9\t9\t457\tpython supervisor\n')
        with mock.patch.object(cleanup, 'identity', side_effect=[None, None]), \
             mock.patch.object(cleanup, 'process_group_members', return_value=[(900, 1, 123, 'surviving child')]), \
             mock.patch.object(sys, 'argv', ['readback','--evidence',str(evidence),'--runtime',str(runtime),'--scope',str(scope)]):
            try:
                cleanup.main()
            except SystemExit as exc:
                assert 'process group has members' in str(exc)
            else:
                raise AssertionError('surviving owned group member was not detected')


def test_contract_describes_scope_and_cleanup():
    contract = CONTRACT.read_text(encoding='utf-8').lower()
    for phrase in ('darwin arm64', 'nine behavior rows', 'five assertion controls',
                   'eilseq', 'independent cleanup readback', 'no process api'):
        assert phrase in contract


def test_distinct_alias_fixture_and_raw_receipt_contract():
    source = (HERE.parents[1] / 'tests/sys_policy.rs').read_text(encoding='utf-8')
    assert 'fn macos_system_prefix_spellings' in source
    assert 'format!("/var/../../{suffix}")' in source
    assert 'format!("/private/var/../../{suffix}")' in source
    assert 'assert_ne!(var_path, private_var_path' in source
    assert source.count('canonicalize().unwrap(), canonical') >= 2
    helper = HELPER.read_text(encoding='utf-8')
    assert "cwd=SOURCE)" in helper
    assert "merge_streams=True" not in helper
    assert "parser-input.txt" in helper
    assert "row.get('status') == 0 and row.get('coverage_found')" in helper
    assert 'coverage_incomplete=' in helper


def test_split_stream_target_association():
    module = load_helper()
    expected = {
        'sys_fs': ['filesystem_read', 'test_non_utf8_file_name'],
        'sys_net': ['net_read'],
    }
    headers = ('warning: retained Cargo warning in stderr\n'
               '     Running tests/sys_net.rs (target/debug/deps/sys_net-a)\n'
               '     Running tests/sys_fs.rs (target/debug/deps/sys_fs-b)\n')
    # Cargo emits these target headers to stderr, separately from each successive
    # stdout libtest block. This order is intentionally opposite targets tuple.
    stdout = ('running 1 test\ntest net_read ... ok\n'
              'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
              'running 2 tests\ntest filesystem_read ... ok\n'
              'test test_non_utf8_file_name ... ok\n'
              'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    parse = getattr(module, 'derive_target_order_parser_input')
    derived = parse(stdout, headers, ('sys_fs', 'sys_net'), expected)
    assert derived['label'] == 'derived target order from stderr headers and successive stdout blocks'
    assert derived['target_order'] == ['sys_net', 'sys_fs']
    assert derived['coverage']['coverage_found']
    assert 'warning: retained Cargo warning in stderr' in derived['parser_input']

    for bad_headers, bad_stdout in (
            (headers.splitlines()[0] + '\n', stdout),
            (headers + headers.splitlines()[1] + '\n', stdout),
            (headers, stdout + 'running 0 tests\n'),
            (headers, stdout.replace('test filesystem_read ... ok\n', '')),
            (headers, stdout + 'running 1 test\ntest net_read ... ok\n'
             'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')):
        try:
            parse(bad_stdout, bad_headers, ('sys_fs', 'sys_net'), expected)
        except (RuntimeError, ValueError):
            pass
        else:
            raise AssertionError('mismatched split-stream headers/blocks were accepted')

    ordered = (headers.splitlines()[2] + '\n' +
               'running 2 tests\ntest filesystem_read ... ok\n'
               'test test_non_utf8_file_name ... ok\n'
               'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n' +
               headers.splitlines()[1] + '\n' +
               'running 1 test\ntest net_read ... ok\n'
               'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    assert module.positive_test_coverage(ordered, ('sys_fs', 'sys_net'), expected)['coverage_found']
    eilseq_stdout = stdout.replace('test test_non_utf8_file_name ... ok',
        'test test_non_utf8_file_name ... filesystem rejects non-UTF-8 fixture with EILSEQ: os error 92\nok')
    eilseq = parse(eilseq_stdout, headers, ('sys_fs', 'sys_net'), expected)
    assert not eilseq['coverage']['coverage_found']
    assert eilseq['coverage']['target_results'][0]['uncovered_named_tests'] == ['test_non_utf8_file_name']


def test_stderr_only_eilseq_is_mapped_to_frozen_producer():
    module = load_helper()
    targets = ('sys_fs', 'net_reads')
    expected = {
        'sys_fs': ['filesystem_read', 'test_non_utf8_file_name'],
        'net_reads': ['net_read', 'test_non_utf8_file_name'],
    }
    fs = ('running 2 tests\ntest filesystem_read ... ok\n'
          'test test_non_utf8_file_name ... ok\n'
          'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    net = ('running 2 tests\ntest net_read ... ok\n'
           'test test_non_utf8_file_name ... ok\n'
           'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    stdout = fs + net
    headers = ('     Running tests/sys_fs.rs (target/debug/deps/sys_fs-a)\n'
               'filesystem rejects non-UTF-8 fixture with EILSEQ: [Errno 84]\n'
               'test injected ... ok\n'
               'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
               '     Running tests/net_reads.rs (target/debug/deps/net_reads-b)\n')
    result = module.derive_target_order_parser_input(stdout, headers, targets, expected)
    coverage = result['coverage']
    assert coverage['coverage_found'] is False
    assert coverage['named_test_coverage_found'] is False
    assert coverage['all_tests_passed_without_ignored_or_filtered'] is False
    rows = {row['target']: row for row in coverage['target_results']}
    assert rows['sys_fs']['observed_tests'] == expected['sys_fs']
    assert rows['sys_fs']['test_outcomes']['test_non_utf8_file_name'] == 'ok'
    assert rows['sys_fs']['completed_named_tests'] == ['filesystem_read']
    assert rows['sys_fs']['uncovered_named_tests'] == ['test_non_utf8_file_name']
    assert rows['net_reads']['completed_named_tests'] == expected['net_reads']
    assert [item['target'] for item in coverage['skipped_tests']] == ['sys_fs']
    assert coverage['skipped_tests'][0]['occurrence_count'] == 1
    assert len(coverage['unresolved_diagnostics']) == 0
    assert len(coverage['target_results']) == 2
    summary = module.positive_rows_summary([
        {'row': 'incomplete-eilseq', 'status': 0, 'coverage_found': coverage['coverage_found']},
        {'row': 'later-complete-row', 'status': 0, 'coverage_found': True}], 2)
    assert summary == {'positive_row_count': 2, 'successful_positive_rows': 1,
                       'all_positive_rows_succeeded': False,
                       'uncovered_positive_rows': ['incomplete-eilseq']}
    assert module.should_continue_positive_rows(0, False)
    assert not module.should_continue_positive_rows(0, True)
    assert not module.should_continue_positive_rows(101, False)
    assert result['label'] == 'derived target order from stderr headers and successive stdout blocks'
    assert 'filesystem rejects non-UTF-8 fixture with EILSEQ:' in result['parser_input']
    repeated = module.derive_target_order_parser_input(
        stdout, headers.replace('     Running tests/net_reads.rs',
                                'filesystem rejects non-UTF-8 fixture with EILSEQ: second diagnostic\n'
                                '     Running tests/net_reads.rs'), targets, expected)['coverage']
    assert len(repeated['skipped_tests']) == 1
    assert repeated['skipped_tests'][0]['occurrence_count'] == 2


def test_unresolved_diagnostic_does_not_fabricate_skip_or_certify_rows():
    module = load_helper()
    stdout = ('running 1 test\ntest filesystem_read ... ok\n'
              'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    headers = ('     Running tests/sys_fs.rs (target/debug/deps/sys_fs-a)\n'
               'filesystem rejects non-UTF-8 fixture with EILSEQ: [Errno 84]\n')
    no_index = module.derive_target_order_parser_input(
        stdout, headers, ('sys_fs',), {'sys_fs': ['filesystem_read']})['coverage']
    assert no_index['coverage_found'] is False
    assert no_index['named_test_coverage_found'] is False
    assert no_index['all_tests_passed_without_ignored_or_filtered'] is False
    assert no_index['skipped_tests'] == []
    assert no_index['unresolved_diagnostics']
    row = no_index['target_results'][0]
    assert row['observed_tests'] == ['filesystem_read']
    assert row['provisional_completed_named_tests'] == ['filesystem_read']
    assert row['completed_named_tests'] == []
    assert row['completion_certified'] is False
    conflict = ('     Running tests/sys_fs.rs (derived target order)\n'
                'running 1 test\ntest unrelated_name ... filesystem rejects non-UTF-8 fixture with EILSEQ: os error 92\n'
                'ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    conflicting = module.positive_test_coverage(
        conflict, ('sys_fs',), {'sys_fs': ['unrelated_name']})
    assert conflicting['skipped_tests'] == []
    assert conflicting['unresolved_diagnostics']
    assert conflicting['coverage_found'] is False


def test_stage_scope_name_matches_pinned_source_contract():
    module = load_helper()
    assert module.SESSION_ID == 'current-darwin-sys-net-behavior-2f795ece-sampler2-20261002'
    contract = CONTRACT.read_text(encoding='utf-8')
    prep = (HERE / 'current-darwin-sys-net-behavior-source-prep.md').read_text(encoding='utf-8')
    assert contract.count(module.SESSION_ID) >= 2
    assert module.SESSION_ID in prep
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        scope = root / '.local/share/agent-builds/rhai' / module.SESSION_ID
        scope.mkdir(parents=True)
        stage = root / module.SESSION_ID
        stage.mkdir()
        runtime = scope / 'runtime'
        with mock.patch.object(module, 'EXPECTED_SCOPE', scope):
            module.validate_stage_scope(stage, runtime)
        wrong_stage = root / 'wrong-stage'; wrong_stage.mkdir()
        try:
            with mock.patch.object(module, 'EXPECTED_SCOPE', scope):
                module.validate_stage_scope(wrong_stage, runtime)
        except RuntimeError:
            pass
        else:
            raise AssertionError('wrong stage basename was accepted')
        wrong_scope_runtime = root / 'wrong-scope/runtime'
        try:
            with mock.patch.object(module, 'EXPECTED_SCOPE', scope):
                module.validate_stage_scope(stage, wrong_scope_runtime)
        except RuntimeError:
            pass
        else:
            raise AssertionError('wrong private scope was accepted')


if __name__ == '__main__':
    test_pins_and_rows()
    test_controls_require_the_intended_red()
    test_resource_census_excludes_only_its_reaped_ps_observer()
    test_resource_census_still_fails_for_unknown_real_descendant()
    test_resource_census_interrupt_kills_and_reaps_exact_observer()
    test_darwin_early_return_and_named_coverage_are_uncovered()
    test_cleanup_fails_closed_and_detects_reparented_process()
    test_cleanup_rejects_live_owned_process_group_member()
    test_contract_describes_scope_and_cleanup()
    test_distinct_alias_fixture_and_raw_receipt_contract()
    test_split_stream_target_association()
    test_stderr_only_eilseq_is_mapped_to_frozen_producer()
    test_unresolved_diagnostic_does_not_fabricate_skip_or_certify_rows()
    test_stage_scope_name_matches_pinned_source_contract()
    print('pins_and_nine_rows=PASS')
    print('named_assertion_red_and_incidental_101_rejection=PASS')
    print('resource_census_reaped_observer_exclusion=PASS')
    print('resource_census_unknown_descendant_fails_closed=PASS')
    print('resource_census_interrupted_observer_killed_and_reaped=PASS')
    print('darwin_early_return_named_coverage_and_summary_integrity=PASS')
    print('cleanup_unknown_and_reparented_process=PASS')
    print('cleanup_owned_group_membership=PASS')
    print('distinct_darwin_alias_fixture_and_receipts=PASS')
    print('scope_and_cleanup_contract=PASS')
    print('split_stream_derived_target_order_and_malformed_cases=PASS')
    print('stderr_diagnostic_frozen_producer_association_and_fail_closed=PASS')
    print('strict_source_named_stage_and_scope=PASS')
