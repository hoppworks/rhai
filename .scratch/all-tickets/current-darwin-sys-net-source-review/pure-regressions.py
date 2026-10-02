"""Pure injected checks; no Cargo, native APIs, commands, or process fixtures."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / 'snapshot/.scratch/all-tickets'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ, {'AGENT_RUNTIME_DIR': '/tmp/pure-not-created-runtime'}):
        spec.loader.exec_module(module)
    return module

helper = load('helper', SNAPSHOT / 'check-current-darwin-sys-net-behavior.py')
cleanup = load('cleanup', SNAPSHOT / 'readback-current-darwin-sys-net-cleanup.py')

def output(summary, text='test ordinary_test ... ok\n'):
    return '     Running tests/sys_fs.rs (target/debug/deps/sys_fs-abc)\n' + text + summary

summary = 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
skipped = output(summary,
    'running 2 tests\ntest ordinary_test ... ok\n'
    'test test_non_utf8_file_name ... filesystem rejects non-UTF-8 fixture with EILSEQ: Illegal byte sequence (os error 92)\nok\n')
skip_result = helper.positive_test_coverage(skipped, ('sys_fs',))
assert skip_result['coverage_found'] and skip_result['ignored_tests'] == []

one_test_summary = summary.replace('2 passed', '1 passed')
missing_result = helper.positive_test_coverage(output(one_test_summary), ('sys_fs',))
assert missing_result['coverage_found']
repeated_result = helper.positive_test_coverage(output(one_test_summary + one_test_summary), ('sys_fs',))
assert repeated_result['coverage_found']
scoped_fixture = '/Users/hoppworks/.local/share/agent-builds/rhai/' + helper.SESSION_ID + '/agent-build-example/tmp/rhai-sys-test-example'
private_alias = scoped_fixture.replace('/var/', '/private/var/', 1)
assert scoped_fixture == private_alias

# Real absence is distinguishable from a query error, but identity() maps both to None.
with mock.patch.object(cleanup.subprocess, 'run', side_effect=PermissionError('injected ps denial')):
    denied_identity = cleanup.identity(100)
assert denied_identity is None

cases = {}
for case in ('query-denied', 'live-reparented'):
    fixture = Path(tempfile.mkdtemp(prefix=case + '-', dir=ROOT))
    evidence = fixture / 'evidence'
    evidence.mkdir()
    scope = fixture / 'scope'
    scope.mkdir()
    runtime = scope / 'absent-runtime'
    (evidence / 'early-runtime-identity.json').write_text(json.dumps({'runtime': str(runtime)}))
    (evidence / 'process-identities.tsv').write_text(
        'label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n'
        'helper\t100\t200\t200\t123\tpython helper\n'
        'scoped-supervisor\t200\t300\t200\t456\tpython supervisor\n')
    identities = (None, None) if case == 'query-denied' else ((1, 200, '123', 'python helper'), None)
    capture = io.StringIO()
    with mock.patch.object(sys, 'argv', ['readback', '--evidence', str(evidence), '--runtime', str(runtime), '--scope', str(scope)]), \
         mock.patch.object(cleanup, 'identity', side_effect=identities), contextlib.redirect_stdout(capture):
        result = cleanup.main()
    assert result == 0 and 'cleanup_readback=PASS' in capture.getvalue()
    cases[case] = {'exit_status': result, 'stdout': capture.getvalue(), 'injected_identities': identities}

receipt = {
    'reviewed_revision': '2d52bf0b87a684b87222436795dcfc73875a7ce8',
    'native_commands_launched': 0,
    'scope': 'Pure classifier and mocked cleanup checks against immutable extracted snapshot; defects reproduced, not acceptance proof.',
    'actual_eilseq_early_return': {'injected_output': skipped, 'classification': skip_result},
    'missing_named_tests': {'injected_output': output(one_test_summary), 'classification': missing_result},
    'duplicate_summary': {'injected_output': output(one_test_summary + one_test_summary), 'classification': repeated_result},
    'macos_alias_paths_collapse': {'scoped_fixture': scoped_fixture, 'replacement_result': private_alias, 'distinct_aliases': scoped_fixture != private_alias},
    'denied_process_query_returns_none': denied_identity is None,
    'cleanup_cases': cases,
}
(ROOT / 'pure-receipts.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('EILSEQ_EARLY_RETURN_FALSE_ACCEPTANCE=REPRODUCED')
print('MISSING_NAMED_TEST_FALSE_ACCEPTANCE=REPRODUCED')
print('DUPLICATE_SUMMARY_FALSE_ACCEPTANCE=REPRODUCED')
print('MACOS_SYSTEM_PREFIX_ALIAS_SAME_PATH=REPRODUCED')
print('CLEANUP_QUERY_ERROR_FALSE_PASS=REPRODUCED')
print('CLEANUP_LIVE_REPARENTED_FALSE_PASS=REPRODUCED')
