#!/usr/bin/env python3
"""Pure checks for the frozen Linux examples preparation package."""
import ast
import importlib.util
import os
from pathlib import Path
import signal
import sys
import tempfile
from unittest import mock

HERE = Path(__file__).resolve().parent
HELPER = HERE / 'check-linux-current-msrv-examples.py'
CONTRACT = HERE / 'linux-current-msrv-examples-proof.md'
STAGE_SCRIPT = HERE / 'stage-linux-current-msrv-examples.sh'
LAUNCH_SCRIPT = HERE / 'launch-linux-current-msrv-examples.sh'


def test_pinned_source_and_toolchain(source: str, tree: ast.Module) -> None:
    constants = {node.targets[0].id: ast.literal_eval(node.value)
                 for node in tree.body if isinstance(node, ast.Assign)
                 and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                 and isinstance(node.value, ast.Constant)}
    assert constants['REVISION'] == '1ca21e32eed2aa40287ba7e1282000add1dd49c7'
    assert constants['SOURCE_ARCHIVE_SHA256'] == \
        '8251e0429d51ffd330e7eac596a1513d836e43e549ca761852cafc642a2a8155'
    assert constants['LOCK_SHA256'] == \
        '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
    assert constants['TOOLCHAIN'] == '1.77.2-x86_64-unknown-linux-gnu'
    assert "Path('/root/rhai-linux-current-msrv-examples-1ca21e32-20261002')" in source
    assert "Path('/root/.local/share/agent-builds/rhai/linux-current-msrv-examples-1ca21e32-20261002')" in source
    assert 'host: x86_64-unknown-linux-gnu' in source
    assert '/Users/hoppworks/' not in source


def test_real_examples_and_named_controls(source: str, contract: str) -> None:
    for expected in (
        "'examples/sys.rs'", "'examples/net.rs'", "'cargo-build-examples'",
        "'sys-red'", "'sys-green'", "'net-red'", "'net-green'",
        'RHAI_EXAMPLE_SYS_EXPECTED_HOST', 'RHAI_EXAMPLE_NET_EXPECTED_PEER',
        'host file independent readback', 'independent peer received the script bytes',
        'host file now contains "Rhaiting data"',
        'Peer received ping; script received pong.',
        'all_controls_and_positive_runs_passed',
    ):
        assert expected in source, f'missing executable acceptance detail {expected!r}'
    lower_contract = contract.lower()
    for expected in ('engine', 'independent peer thread', 'sys-red', 'net-red',
                     'exit 101', 'status 0', 'no mock', 'invocation 85'):
        assert expected in lower_contract, f'missing contract detail {expected!r}'
    assert 'cargo test' not in source
    assert 'test --' not in source


def test_early_identity_failure_and_interrupt_export(helper: Path) -> None:
    with tempfile.TemporaryDirectory(prefix='linux-examples-pure-') as temp:
        runtime = Path(temp) / 'agent-build-private'
        runtime.mkdir()
        previous_runtime = os.environ.get('AGENT_RUNTIME_DIR')
        os.environ['AGENT_RUNTIME_DIR'] = str(runtime)
        try:
            spec = importlib.util.spec_from_file_location('linux_examples_helper_test', helper)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.RUNTIME = runtime
            module.STAGE = runtime / 'evidence'
            module.process_identity = lambda _pid: None
            with mock.patch.object(module.subprocess, 'Popen', side_effect=AssertionError('external command started')):
                try:
                    module.capture_runtime_proof()
                except RuntimeError as error:
                    assert 'identity unavailable' in str(error)
                else:
                    raise AssertionError('unavailable process identity did not fail closed')
            identities = (module.STAGE / 'process-identities.tsv').read_text(encoding='utf-8')
            assert 'helper\t' in identities and '<identity-unavailable>' in identities
            assert 'scoped-supervisor\t' in identities
            receipt = (module.STAGE / 'early-runtime-identity.json').read_text(encoding='utf-8')
            assert 'captured_before_stage_validation_or_external_command' in receipt

            module.INTERRUPTED = signal.SIGTERM
            with mock.patch.object(module.time, 'monotonic', return_value=module.START + 1):
                module.check_deadline(during_export=True)
            with mock.patch.object(module.time, 'monotonic', return_value=module.DEADLINE + 1):
                try:
                    module.check_deadline(during_export=True)
                except TimeoutError:
                    pass
                else:
                    raise AssertionError('expired helper deadline allowed evidence export')
        finally:
            if previous_runtime is None:
                os.environ.pop('AGENT_RUNTIME_DIR', None)
            else:
                os.environ['AGENT_RUNTIME_DIR'] = previous_runtime


def test_early_main_order_and_bounds(tree: ast.Module, source: str) -> None:
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    names = [node.func.id for node in ast.walk(functions['main'])
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert names.index('capture_runtime_proof') < names.index('validate_stage_inputs')
    assert 'record_process_identity' in source and 'process-identities.tsv' in source
    assert 'INTERRUPT_REQUEST.is_file()' in source
    assert 'DEADLINE = START + 540' in source
    assert 'WORK_DEADLINE = DEADLINE - 30' in source
    assert 'PREEMPTIVE_STORAGE_KIB = 1_572_864' in source
    assert 'HARD_STORAGE_KIB = 2 * 1024 * 1024' in source
    assert 'HARD_RSS_KIB = 2 * 1024 * 1024' in source
    assert 'MAX_DESCENDANTS = 16' in source
    assert "'CARGO_BUILD_JOBS': '2'" in source
    assert "'CARGO_INCREMENTAL': '0'" in source
    assert "'CARGO_PROFILE_DEV_DEBUG': '0'" in source
    assert 'export_destination_is_safe()' in source
    assert 'EXPECTED_STAGE.resolve() != PRESCRIBED_STAGE.resolve()' in source
    assert 'RUNTIME.parent.resolve() != PRESCRIBED_SCOPE.resolve()' in source


def test_wrappers_are_prepared_not_invoked() -> None:
    stage = STAGE_SCRIPT.read_text(encoding='utf-8')
    launcher = LAUNCH_SCRIPT.read_text(encoding='utf-8')
    assert 'ssh workhorse' in stage and 'scp ' in stage
    assert 'test ! -e' in stage and 'git -C "$repo" archive' in stage
    assert 'python3 "$runner" --timeout 600' in launcher
    assert 'stage/proof-evidence/process-identities.tsv' in launcher
    assert 'interrupt.request' in launcher
    assert 'rmdir "$scope"' in launcher
    assert 'kill ' not in launcher
    assert 'runner_raw=$(</proc/"$runner_pid"/stat 2>/dev/null)' not in launcher
    assert 'IFS= read -r runner_raw < "/proc/$runner_pid/stat"' in launcher
    assert 'if [[ ! "$runner_start" =~ ^[0-9]+$ ]]; then' in launcher
    assert 'runner PID identity changed while waiting; fail closed' in launcher
    assert 'runner proc identity is unreadable; failing closed and preserving scope' in launcher
    assert 'if (( launcher_interrupted )); then\n      sleep 0.1\n      continue' in launcher
    assert 'read -t 0.1 -r _ < /dev/null' not in launcher
    assert 'sleep 0.1' in launcher


def main() -> None:
    source = HELPER.read_text(encoding='utf-8')
    contract = CONTRACT.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(HELPER))
    test_pinned_source_and_toolchain(source, tree)
    test_real_examples_and_named_controls(source, contract)
    test_early_identity_failure_and_interrupt_export(HELPER)
    test_early_main_order_and_bounds(tree, source)
    test_wrappers_are_prepared_not_invoked()
    print('frozen_source_lock_toolchain=PASS')
    print('real_engine_examples_and_named_controls=PASS')
    print('missing_identity_durable_failure_and_no_command=PASS')
    print('interruption_exports_within_deadline_and_rejects_expiry=PASS')
    print('custody_deadlines_resource_limits_and_wrapper_scope=PASS')


if __name__ == '__main__':
    main()
