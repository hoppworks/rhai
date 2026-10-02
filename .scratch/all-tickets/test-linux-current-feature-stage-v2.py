#!/usr/bin/env python3
"""Pure regression checks for Linux optional MSRV stage identity and early receipts."""
import ast
from pathlib import Path
import sys
import tempfile

HELPER = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name(
    'check-linux-current-feature-compilation-v2.py')


def function_node(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f'missing helper function: {name}')


def test_canonical_same_directory_only(tree: ast.Module) -> None:
    with tempfile.TemporaryDirectory(prefix='rhai-stage-identity-') as temp:
        root = Path(temp)
        actual = root / 'owned-stage'
        actual.mkdir()
        alias = root / 'lexical-alias'
        alias.symlink_to(actual, target_is_directory=True)
        unrelated = root / 'other-stage'
        unrelated.mkdir()
        try:
            function = function_node(tree, 'stage_identity_matches')
        except AssertionError:
            # Exercise the previous guard itself to prove the setup failure.
            main = function_node(tree, 'main')
            legacy = None
            for node in ast.walk(main):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                        and isinstance(node.ops[0], ast.NotEq):
                    text = ast.unparse(node)
                    if text == 'STAGE.resolve() != EXPECTED_STAGE':
                        legacy = node
                        break
            assert legacy is not None, 'old source must expose its exact path guard'
            rejected = eval(compile(ast.Expression(legacy), str(HELPER), 'eval'),
                            {'STAGE': actual, 'EXPECTED_STAGE': alias})
            assert not rejected, 'same directory through the root alias must be accepted'
            return
        namespace = {'Path': Path}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(HELPER), 'exec'), namespace)
        match = namespace['stage_identity_matches']
        assert match(alias, actual), 'canonical same-directory stage alias must be accepted'
        assert match(actual, alias), 'comparison must be symmetric for canonical identity'
        assert not match(unrelated, actual), 'unrelated stage must be rejected'


def test_runtime_receipts_precede_stage_validation(tree: ast.Module) -> None:
    capture = function_node(tree, 'capture_runtime_proof')
    main = function_node(tree, 'main')
    calls = [node.func.id for node in ast.walk(main)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert 'capture_runtime_proof' in calls, 'main must capture runtime proof'
    assert 'validate_stage_inputs' in calls, 'main must validate staged inputs'
    top_level_order = [node.value.func.id for node in main.body
                       if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                       and isinstance(node.value.func, ast.Name)]
    assert top_level_order.index('capture_runtime_proof') < top_level_order.index('validate_stage_inputs'), \
        'runtime/helper/supervisor identity receipts must precede fallible stage validation'
    test_early_receipts_are_durable(capture)
    test_unavailable_required_identity_fails_closed(capture)


def test_early_receipts_are_durable(capture: ast.FunctionDef) -> None:
    import json
    import os
    import tempfile

    with tempfile.TemporaryDirectory(prefix='rhai-early-runtime-proof-') as temp:
        runtime = Path(temp)
        evidence = runtime / 'evidence'
        def identity(pid: int):
            return (pid - 1, pid + 1, 10000 + pid, f'proc-{pid}')
        def record(label, pid, found):
            if found is None:
                row = f'{label}\t{pid}\t<identity-unavailable>\n'
            else:
                ppid, pgid, ticks, command = found
                row = f'{label}\t{pid}\t{ppid}\t{pgid}\t{ticks}\t{command}\n'
            with (evidence / 'process-identities.tsv').open('a', encoding='utf-8') as stream:
                stream.write(row)
        def write_json(path: Path, value: object) -> None:
            path.write_text(json.dumps(value), encoding='utf-8')
        namespace = {
            'Path': Path, 'RUNTIME': runtime, 'EVIDENCE': evidence, 'os': os,
            'record_process_identity': record, 'process_identity': identity, 'write_json': write_json,
        }
        exec(compile(ast.Module(body=[capture], type_ignores=[]), str(HELPER), 'exec'), namespace)
        namespace['capture_runtime_proof']()
        rows = (evidence / 'process-identities.tsv').read_text().splitlines()
        assert rows[0].startswith('label\tpid\tppid')
        assert any(row.startswith('helper\t') and len(row.split('\t')) == 6 for row in rows[1:])
        assert any(row.startswith('scoped-supervisor\t') and len(row.split('\t')) == 6 for row in rows[1:])
        receipt = json.loads((evidence / 'early-runtime-identity.json').read_text())
        assert receipt['runtime'] == str(runtime)
        assert receipt['identity_receipt'] == 'process-identities.tsv'


def test_unavailable_required_identity_fails_closed(capture: ast.FunctionDef) -> None:
    import json
    from types import SimpleNamespace

    for unavailable_pid, expected_label in ((4242, 'helper'), (4243, 'scoped-supervisor')):
        with tempfile.TemporaryDirectory(prefix='rhai-missing-process-proof-') as temp:
            runtime = Path(temp)
            evidence = runtime / 'evidence'
            def identity(pid: int):
                if pid == unavailable_pid:
                    return None
                return (pid - 1, pid + 1, 10000 + pid, f'proc-{pid}')
            def record(label, pid, found):
                if found is None:
                    row = f'{label}\t{pid}\t<identity-unavailable>\n'
                else:
                    ppid, pgid, ticks, command = found
                    row = f'{label}\t{pid}\t{ppid}\t{pgid}\t{ticks}\t{command}\n'
                with (evidence / 'process-identities.tsv').open('a', encoding='utf-8') as stream:
                    stream.write(row)
            fake_os = SimpleNamespace(getpid=lambda: 4242, getppid=lambda: 4243)
            namespace = {
                'Path': Path, 'RUNTIME': runtime, 'EVIDENCE': evidence, 'os': fake_os,
                'record_process_identity': record, 'process_identity': identity,
                'write_json': lambda path, value: path.write_text(json.dumps(value), encoding='utf-8'),
            }
            exec(compile(ast.Module(body=[capture], type_ignores=[]), str(HELPER), 'exec'), namespace)
            try:
                namespace['capture_runtime_proof']()
            except RuntimeError as exc:
                assert str(exc) == 'required helper or scoped supervisor identity unavailable'
            else:
                raise AssertionError('unavailable required process identity must stop setup')
            rows = (evidence / 'process-identities.tsv').read_text().splitlines()
            assert any(row.startswith(f'{expected_label}\t') and '<identity-unavailable>' in row
                       for row in rows[1:])
            receipt = json.loads((evidence / 'early-runtime-identity.json').read_text())
            assert receipt['identity_receipt'] == 'process-identities.tsv'
            assert unavailable_pid == receipt['helper_pid' if expected_label == 'helper'
                                               else 'supervisor_pid']


def main() -> None:
    tree = ast.parse(HELPER.read_text(encoding='utf-8'), filename=str(HELPER))
    test_canonical_same_directory_only(tree)
    test_runtime_receipts_precede_stage_validation(tree)
    print('stage_identity_same_directory=PASS')
    print('unrelated_stage_rejected=PASS')
    print('runtime_receipts_before_stage_validation=PASS')
    print('durable_runtime_helper_supervisor_receipts=PASS')
    print('unavailable_required_identity_fails_closed=PASS')


if __name__ == '__main__':
    try:
        main()
    except AssertionError as exc:
        print(f'REGRESSION_FAIL: {exc}', file=sys.stderr)
        raise
