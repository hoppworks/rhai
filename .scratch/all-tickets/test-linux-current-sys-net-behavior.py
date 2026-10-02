#!/usr/bin/env python3
"""Pure checks for the prepared Linux sys/net behavior package."""
from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HELPER = HERE / 'check-linux-current-sys-net-behavior.py'
CONTRACT = HERE / 'linux-current-sys-net-behavior-contract.md'
PREP_EVIDENCE = HERE / 'linux-current-sys-net-behavior-prep-evidence'
STAGE_SCRIPT = HERE / 'stage-linux-current-sys-net-behavior.sh'
LAUNCH_SCRIPT = HERE / 'launch-linux-current-sys-net-behavior.sh'


def constants(tree: ast.Module) -> dict[str, object]:
    return {node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body if isinstance(node, ast.Assign)
            and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)}


def test_frozen_pins_and_finite_rows(source: str, tree: ast.Module) -> None:
    values = constants(tree)
    assert values['SOURCE_REVISION'] == '1ca21e32eed2aa40287ba7e1282000add1dd49c7'
    assert values['SOURCE_ARCHIVE_SHA256'] == '8251e0429d51ffd330e7eac596a1513d836e43e549ca761852cafc642a2a8155'
    assert values['LOCK_SHA256'] == '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
    assert values['TOOLCHAIN'] == '1.77.2-x86_64-unknown-linux-gnu'
    assert values['HELPER_DEADLINE_SECONDS'] == 540
    assert values['WORK_DEADLINE_SECONDS'] == 510
    assert values['EXPORT_RESERVE_SECONDS'] == 30
    assert values['PREEMPTIVE_STORAGE_KIB'] == 1_572_864
    assert values['HARD_STORAGE_KIB'] == 2 * 1024 * 1024
    assert values['HARD_RSS_KIB'] == 2 * 1024 * 1024
    assert values['MAX_DESCENDANTS'] == 16
    assert values['CARGO_JOBS'] == '2'
    assert 'testing-environ,sys,net' in source
    assert "Path('/root/rhai-linux-current-sys-net-behavior-1ca21e32-20261002-followup1')" in source
    assert "Path('/root/.local/share/agent-builds/rhai/linux-current-sys-net-behavior-1ca21e32-20261002-followup1')" in source
    assert 'testing-environ,net,no_object' in source
    assert 'testing-environ,sys,net,no_index' in source
    assert 'testing-environ,sys,net,metadata,serde' in source
    assert 'sys_process' not in source


def test_real_engine_targets_and_controls(source: str, contract: str) -> None:
    for token in (
        "'sys_env', 'sys_fs', 'sys_policy'", "'net_connect', 'net_listen'",
        "'net_reads', 'net_writes', 'combined_sys_net'",
        "'net_no_object',)", "'sys_policy', 'net_metadata'", '--test-threads=1',
        'RHAI_NET_NO_OBJECT_WRONG_PEER_EXPECTATION',
        'RHAI_NET_WRONG_WRITE_EXPECTATION', 'RHAI_COMBINED_WRONG_EXPECTATION',
        'classify_assertion_control', 'named_test_failed',
        'exactly_one_test_ran_and_failed',
        'stderr=subprocess.STDOUT if merge_streams else stderr', 'merge_streams=True',
        "'test', '--locked'", 'all-controls-and-positive-runs-passed',
    ):
        assert token in source, f'missing package detail {token!r}'
    assert 'sys_process' not in source
    lower = contract.lower()
    for token in ('real engine', 'filesystem', 'environment', 'tcp', 'independent',
                  'wrong expectation', 'status 101', 'rust 1.77.2', 'linux x86_64',
                  'invocation 85', 'sys_process', 'invocation 85 is allocated',
                  'runtime acceptance remains open'):
        assert token in lower, f'missing contract detail {token!r}'
    assert 'cargo check' not in source



def test_rows_and_controls_match_frozen_test_sources(tree: ast.Module, source: str) -> None:
    assignments = {node.targets[0].id: node.value for node in tree.body
                   if isinstance(node, ast.Assign) and len(node.targets) == 1
                   and isinstance(node.targets[0], ast.Name)}
    rows = ast.literal_eval(assignments['TEST_ROWS'])
    assert [row[0] for row in rows] == [
        'combined-baseline', 'combined-no-index', 'net-no-object',
        'combined-metadata-serde']
    assert rows[0][1] == 'testing-environ,sys,net'
    assert rows[1][1] == 'testing-environ,sys,net,no_index'
    assert rows[2][1] == 'testing-environ,net,no_object'
    assert rows[3][1] == 'testing-environ,sys,net,metadata,serde'
    controls = ast.literal_eval(assignments['ASSERTION_CONTROLS'])
    assert len(controls) == 5
    source_expectations = {
        'RHAI_FILE_READ_WRONG_EXPECTATION': ('wrong expectation', '"abc"'),
        'RHAI_NET_WRONG_READ_EXPECTATION': ('wrong peer payload', '[0x61, 0xff, 0x62]'),
        'RHAI_NET_WRONG_WRITE_EXPECTATION': ('[0, 254, b\'A\']',),
        'RHAI_COMBINED_WRONG_EXPECTATION': ('incorrect filesystem expectation',
                                            'fresh host readback must match'),
        'RHAI_NET_NO_OBJECT_WRONG_PEER_EXPECTATION': ('b"pang"',
                                                       'deliberately wrong independent peer expectation'),
    }
    for _name, _features, target, test_name, env_name, required_context in controls:
        test_source = (ROOT / 'tests' / f'{target}.rs').read_text(encoding='utf-8')
        assert f'fn {test_name}(' in test_source
        assert env_name in test_source
        for needle in source_expectations[env_name]:
            assert needle in test_source
        assert required_context
        assert f"'{target}'" in ast.get_source_segment(source, assignments['ASSERTION_CONTROLS'])


def test_control_classifier_rejects_incidental_101_and_accepts_intended_red() -> None:
    spec = importlib.util.spec_from_file_location('linux_sys_net_classifier_test', HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    controls = ast.literal_eval(next(node.value for node in ast.parse(HELPER.read_text()).body
                                     if isinstance(node, ast.Assign)
                                     and getattr(node.targets[0], 'id', None) == 'ASSERTION_CONTROLS'))

    def test_output(target: str, test_name: str, context: tuple[str, ...]) -> str:
        details = '\n'.join(f' {line}' for line in context)
        assertion = ('' if target == 'combined_sys_net'
                     else 'assertion `left == right` failed')
        return (f'running 1 test\ntest {test_name} ...\n'
                f'thread {test_name!r} panicked at tests/{target}.rs:1:1:\n'
                f'{assertion}\n{details}\n'
                f'test {test_name} ... FAILED\n\nfailures:\n    {test_name}\n'
                'test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; '
                '8 filtered out; finished in 0.00s\n')

    for _name, _features, target, test_name, _env_name, context in controls:
        output = test_output(target, test_name, context)
        assert module.classify_assertion_control(101, output, target, test_name, context)['diagnostic_found']
    test_name = 'script_write_blob_preserves_exact_bytes'
    target = 'net_writes'
    context = ('left: [0, 255, 65]', 'right: [0, 254, 65]')
    intended = test_output(target, test_name, context)
    incidental_outputs = (
        'error[E0432]: unresolved import\n 254\n',
        'running 0 tests\ntest result: FAILED. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n',
        test_output(target, test_name, ('left: [0, 3, 65]', 'right: [0, 4, 65]')),
        intended.replace('right: [0, 254, 65]', 'right: [0, 253, 65]'),
        intended.replace('assertion `left == right` failed', 'unrelated panic'),
    )
    for output in incidental_outputs:
        assert not module.classify_assertion_control(101, output, target, test_name, context)['diagnostic_found']
        assert not module.classify_assertion_control(0, intended, target, test_name, context)['diagnostic_found']

    # These are byte-for-byte excerpts from the historical outputs whose
    # optional numeric thread suffix triggered the review finding.
    for fixture, target, test_name, context in (
        ('net-writes-rust-thread-pid.log', 'net_writes',
         'script_write_blob_preserves_exact_bytes',
         ('left: [0, 255, 65]', 'right: [0, 254, 65]')),
        ('net-no-object-rust-thread-pid.log', 'net_no_object',
         'registered_stream_functions_work_without_dot_syntax',
         ('deliberately wrong independent peer expectation',
          'left: [112, 105, 110, 103]', 'right: [112, 97, 110, 103]')),
    ):
        historical = (PREP_EVIDENCE / 'original-output-fixtures' / fixture).read_text()
        assert module.classify_assertion_control(
            101, historical, target, test_name, context)['diagnostic_found']

    combined_test = 'sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors'
    combined_context = ('fresh host readback must match independent expected bytes',
                        'actual="filesystem-payload"',
                        'expected="incorrect filesystem expectation"')
    combined_base = PREP_EVIDENCE / 'original-output-fixtures' / 'combined-host-wrong-readback'
    combined_stdout = (combined_base.with_suffix('.stdout')).read_text()
    combined_stderr = (combined_base.with_suffix('.stderr')).read_text()
    combined_status = int(combined_base.with_suffix('.status').read_text())
    combined_output = combined_stdout + combined_stderr
    assert combined_status == 101
    assert module.classify_assertion_control(
        combined_status, combined_output, 'combined_sys_net', combined_test,
        combined_context)['diagnostic_found']
    assert not module.classify_assertion_control(
        combined_status, combined_output.replace(
            'fresh host readback must match independent expected bytes', 'unrelated failure'),
        'combined_sys_net', combined_test, combined_context)['diagnostic_found']
    assert not module.classify_assertion_control(
        combined_status, combined_output.replace('expected="incorrect filesystem expectation"',
                                                  'expected="other value"'),
        'combined_sys_net', combined_test, combined_context)['diagnostic_found']


def test_positive_coverage_requires_every_target_and_no_skips() -> None:
    spec = importlib.util.spec_from_file_location('linux_sys_net_coverage_test', HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    targets = ('sys_env', 'sys_fs')
    complete = (
        '     Running tests/sys_env.rs (target/debug/deps/sys_env-abc)\n'
        'running 2 tests\ntest a ... ok\ntest b ... ok\n'
        'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
        '     Running tests/sys_fs.rs (target/debug/deps/sys_fs-def)\n'
        'running 3 tests\ntest a ... ok\ntest b ... ok\ntest c ... ok\n'
        'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
    )
    assert module.positive_test_coverage(complete, targets)['coverage_found']
    # Cargo emits `Running` on stderr and libtest summaries on stdout. The
    # positive command must merge both descriptors into one chronological log.
    separated_stderr = (
        '     Running tests/sys_env.rs (target/debug/deps/sys_env-abc)\n'
        '     Running tests/sys_fs.rs (target/debug/deps/sys_fs-def)\n')
    separated_stdout = (
        'running 2 tests\ntest a ... ok\ntest b ... ok\n'
        'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
        'running 3 tests\ntest a ... ok\ntest b ... ok\ntest c ... ok\n'
        'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    actual_merged_order = (
        separated_stderr.splitlines()[0] + '\n' + separated_stdout.split('running 3 tests')[0]
        + separated_stderr.splitlines()[1] + '\nrunning 3 tests' + separated_stdout.split('running 3 tests', 1)[1])
    assert module.positive_test_coverage(actual_merged_order, targets)['coverage_found']
    reverse_order = complete.replace(
        '     Running tests/sys_env.rs (target/debug/deps/sys_env-abc)\n'
        'running 2 tests\ntest a ... ok\ntest b ... ok\n'
        'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
        '     Running tests/sys_fs.rs (target/debug/deps/sys_fs-def)\n'
        'running 3 tests\ntest a ... ok\ntest b ... ok\ntest c ... ok\n'
        'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n',
        '     Running tests/sys_fs.rs (target/debug/deps/sys_fs-def)\n'
        'running 3 tests\ntest a ... ok\ntest b ... ok\ntest c ... ok\n'
        'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
        '     Running tests/sys_env.rs (target/debug/deps/sys_env-abc)\n'
        'running 2 tests\ntest a ... ok\ntest b ... ok\n'
        'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    assert module.positive_test_coverage(reverse_order, targets)['coverage_found']
    duplicate = complete.replace('     Running tests/sys_fs.rs',
                                 '     Running tests/sys_env.rs (duplicate)\n'
                                 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
                                 '     Running tests/sys_fs.rs')
    assert not module.positive_test_coverage(duplicate, targets)['coverage_found']
    nested_fixture = complete.replace(
        'test a ... ok\ntest b ... ok\n'
        'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n',
        'test a ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; '
        'finished in 0.00s\ntest b ... ok\n'
        'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
    assert module.positive_test_coverage(nested_fixture, targets)['coverage_found']
    skipped = complete.replace('3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;',
                              '2 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out;')
    assert not module.positive_test_coverage(skipped, targets)['coverage_found']
    missing = complete.replace(
        '     Running tests/sys_fs.rs (target/debug/deps/sys_fs-def)\n'
        'running 3 tests\ntest a ... ok\ntest b ... ok\ntest c ... ok\n'
        'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n', '')
    assert not module.positive_test_coverage(missing, targets)['coverage_found']


def test_identity_capture_fails_before_external_work_and_export_deadline_is_hard() -> None:
    with tempfile.TemporaryDirectory(prefix='linux-sys-net-pure-') as temp:
        base = Path(temp)
        runtime = base / 'linux-current-sys-net-behavior-1ca21e32-20261002-followup1' / 'agent-build-test'
        runtime.mkdir(parents=True)
        stage = base / 'stage'
        stage.mkdir()
        env = {'AGENT_RUNTIME_DIR': str(runtime), 'PROOF_STAGE': str(stage),
               'INTERRUPT_REQUEST': str(stage / 'outer-evidence' / 'interrupt.request')}
        with mock.patch.dict(os.environ, env, clear=False):
            spec = importlib.util.spec_from_file_location('linux_sys_net_helper_test', HELPER)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.RUNTIME = runtime
            module.EVIDENCE = runtime / 'evidence'
            module.process_identity = lambda _pid: None
            with mock.patch.object(module.subprocess, 'Popen', side_effect=AssertionError('external command started')):
                try:
                    module.capture_runtime_proof()
                except RuntimeError as error:
                    assert 'identity unavailable' in str(error)
                else:
                    raise AssertionError('missing process custody identity did not fail closed')
            identities = (module.EVIDENCE / 'process-identities.tsv').read_text(encoding='utf-8')
            assert identities.count('<identity-unavailable>') >= 2
            early = (module.EVIDENCE / 'early-runtime-identity.json').read_text(encoding='utf-8')
            assert 'captured_before_stage_validation_or_external_command' in early
            module.INTERRUPTED = signal.SIGTERM
            with mock.patch.object(module.time, 'monotonic', return_value=module.START + 1):
                module.check_deadline(during_export=True)
            with mock.patch.object(module.time, 'monotonic', return_value=module.DEADLINE + 1):
                try:
                    module.check_deadline(during_export=True)
                except TimeoutError:
                    pass
                else:
                    raise AssertionError('expired helper deadline permitted export')


def test_wrapper_has_bounded_custody_and_does_not_signal_by_pid() -> None:
    stage = STAGE_SCRIPT.read_text(encoding='utf-8')
    launcher = LAUNCH_SCRIPT.read_text(encoding='utf-8')
    assert 'git -C "$repo" archive' in stage and 'ssh workhorse' in stage and 'scp ' in stage
    assert 'python3 "$runner" --timeout 600 --' in launcher
    assert 'interrupt.request' in launcher and 'rmdir "$scope"' in launcher
    assert 'kill ' not in launcher
    assert 'IFS= read -r runner_raw < "/proc/$runner_pid/stat"' in launcher
    assert 'sleep 0.1' in launcher
    assert 'fail closed' in launcher and 'preserving scope' in launcher
    assert 'proof-evidence/process-identities.tsv' in launcher
    assert '/root/.local/share/agent-builds/rhai/linux-current-sys-net-behavior-1ca21e32-20261002-followup1' in launcher
    for path in (STAGE_SCRIPT, LAUNCH_SCRIPT):
        subprocess.run(['/bin/bash', '-n', str(path)], check=True, timeout=5)
    blocks = []
    lines = launcher.splitlines()
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
    source = HELPER.read_text(encoding='utf-8')
    contract = CONTRACT.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(HELPER))
    test_frozen_pins_and_finite_rows(source, tree)
    test_real_engine_targets_and_controls(source, contract)
    test_rows_and_controls_match_frozen_test_sources(tree, source)
    test_control_classifier_rejects_incidental_101_and_accepts_intended_red()
    test_positive_coverage_requires_every_target_and_no_skips()
    test_identity_capture_fails_before_external_work_and_export_deadline_is_hard()
    test_wrapper_has_bounded_custody_and_does_not_signal_by_pid()
    print('frozen_source_lock_toolchain_and_finite_rows=PASS')
    print('real_engine_os_targets_and_named_controls=PASS')
    print('rows_and_assertion_controls_match_frozen_test_sources=PASS')
    print('controls_require_named_test_and_exact_wrong_assertion=PASS')
    print('positive_rows_require_complete_non_skipped_target_coverage=PASS')
    print('unavailable_identity_fails_before_external_work=PASS')
    print('interrupted_export_allowed_only_within_original_deadline=PASS')
    print('wrapper_bounded_custody_no_pid_signal_bash_and_heredoc_syntax=PASS')


if __name__ == '__main__':
    main()
