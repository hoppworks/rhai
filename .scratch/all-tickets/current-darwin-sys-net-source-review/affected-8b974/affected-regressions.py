"""Pure affected recheck: no native fixtures, process queries, Cargo, or toolchains."""
from pathlib import Path, PurePosixPath
from unittest import mock
import contextlib, importlib.util, io, json, os, runpy, sys, tempfile
ROOT=Path(__file__).resolve().parent
SNAPSHOT=ROOT/'snapshot'
HERE=SNAPSHOT/'.scratch/all-tickets'
tempfile.tempdir=str(ROOT)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ,{'AGENT_RUNTIME_DIR':'/tmp/pure-not-created-runtime'}):
        spec.loader.exec_module(module)
    return module
helper=load('affected_helper',HERE/'check-current-darwin-sys-net-behavior.py')
cleanup=load('affected_cleanup',HERE/'readback-current-darwin-sys-net-cleanup.py')
receipt={'revision':'8b9740de8e4493c78320293d3a07599672f22484','native_launches':0}
stdout=io.StringIO()
with contextlib.redirect_stdout(stdout):
    runpy.run_path(str(HERE/'test-current-darwin-sys-net-behavior.py'),run_name='__main__')
(ROOT/'prepared-source-tests.stdout').write_text(stdout.getvalue())
receipt['seven_owner_categories']=stdout.getvalue().splitlines()
expected={'sys_fs':['ordinary_test','test_non_utf8_file_name']}
header='     Running tests/sys_fs.rs (target/debug/deps/sys_fs-abc)\n'
summary='test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
body='running 2 tests\ntest ordinary_test ... ok\ntest test_non_utf8_file_name ... ok\n'+summary
skip=body.replace('test test_non_utf8_file_name ... ok','test test_non_utf8_file_name ... filesystem rejects non-UTF-8 fixture with EILSEQ: Illegal byte sequence (os error 92)\nok')
cases={}
for name,text in [('eilseq',header+skip),('missing-name',header+body.replace('test test_non_utf8_file_name ... ok\n','')),('duplicate-summary',header+body+summary),('clean-ordered',header+body)]:
    cases[name]=helper.positive_test_coverage(text,('sys_fs',),expected)
assert not any(cases[x]['coverage_found'] for x in ['eilseq','missing-name','duplicate-summary'])
assert cases['clean-ordered']['coverage_found']
assert cases['eilseq']['target_results'][0]['uncovered_named_tests']==['test_non_utf8_file_name']
receipt['original_F1_cases']=cases
parser_input=body+'\n--- stderr follows stdout; raw files are preserved separately ---\n'+header
(ROOT/'behavior-model.stdout').write_text(body)
(ROOT/'behavior-model.stderr').write_text(header)
(ROOT/'behavior-model.parser-input.txt').write_text(parser_input)
try:
    helper.positive_test_coverage(parser_input,('sys_fs',),expected)
except RuntimeError as exc:
    receipt['F4_separate_stream_order']={'exception':str(exc),'same_data_in_order_accepted':cases['clean-ordered']['coverage_found'],'stdout':'behavior-model.stdout','stderr':'behavior-model.stderr','parser_input':'behavior-model.parser-input.txt'}
else: raise AssertionError('broken separate-stream order was unexpectedly parsed')
with mock.patch.object(cleanup.subprocess,'run',side_effect=PermissionError('injected ps denial')):
    try: cleanup.identity(100)
    except cleanup.CleanupUnknown as exc: receipt['original_F2_query_denial']=str(exc)
    else: raise AssertionError('query error falsely accepted')
# Additional stable PID/start, group-enumeration-error and path-closure checks.
with mock.patch.object(cleanup.subprocess,'run',side_effect=OSError('injected group failure')):
    try: cleanup.process_group_members({100})
    except cleanup.CleanupUnknown as exc: receipt['F2_group_query_failure']=str(exc)
    else: raise AssertionError('group query falsely accepted')
fixture=Path(tempfile.mkdtemp(prefix='closure-',dir=ROOT)); scope=fixture/'scope';scope.mkdir(); evidence=fixture/'evidence';evidence.mkdir();runtime=scope/'absent-runtime'
(evidence/'early-runtime-identity.json').write_text(json.dumps({'runtime':str(runtime)}))
(evidence/'process-identities.tsv').write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\nhelper\t100\t200\t100\t123\tpython helper\nscoped-supervisor\t200\t300\t200\t456\tpython supervisor\n')
argv=['readback','--evidence',str(evidence),'--runtime',str(runtime),'--scope',str(scope)]
with mock.patch.object(sys,'argv',argv),mock.patch.object(cleanup,'identity',side_effect=[(1,999,'123','changed command'),None]):
    try: cleanup.main()
    except SystemExit as exc: receipt['original_F2_reparented_changed_group_command']=str(exc)
    else: raise AssertionError('same PID/start falsely accepted')
(scope/'unexpected').write_text('owned test data')
with mock.patch.object(sys,'argv',argv),mock.patch.object(cleanup,'identity',side_effect=[None,None]),mock.patch.object(cleanup,'process_group_members',return_value=[]):
    try: cleanup.main()
    except SystemExit as exc: receipt['F2_nonempty_scope']=str(exc)
    else: raise AssertionError('nonempty scope falsely accepted')
receipt['inventory']={}
for name,features,targets in helper.TEST_ROWS:
    inv=helper.frozen_test_inventory(SNAPSHOT,features)
    selected={target:inv[target] for target in targets}
    assert all(selected.values())
    receipt['inventory'][name]=selected
assert 'test_root_accepts_macos_system_prefix_aliases' in receipt['inventory']['combined-baseline']['sys_policy']
assert 'test_nested_roots_keep_permissions_through_system_prefix_aliases' in receipt['inventory']['combined-baseline']['sys_policy']
# Pure lexical policy model, using the exact central /Users fixture shape.
base='/Users/hoppworks/.local/share/agent-builds/rhai/owned/runtime/tmp/rhai-sys-test-owned'
root_aliases=[base+'/link',base+'/real']
var='/var/../../'+base.lstrip('/')+'/real/a.txt'
private='/private/var/../../'+base.lstrip('/')+'/real/a.txt'
def matches(path,root):
    p,r=PurePosixPath(path).parts,PurePosixPath(root).parts
    return p[:len(r)]==r
assert var!=private and not any(matches(path,root) for path in (var,private) for root in root_aliases)
receipt['F3_configured_root_policy_mismatch']={'central_fixture':base,'configured_root':base+'/link','canonical_root':base+'/real','absolute_reads':[var,private],'possible_root_aliases':root_aliases,'matches_configured_root':False,'source_dependency':'src/packages/sys/fs.rs:179-200,245-267','scope':'lexical source model only; no OS canonicalization or native Engine executed'}
(ROOT/'affected-receipts.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(stdout.getvalue(),end='')
print('original_F1_injections=REJECTED; clean_ordered_named_output=ACCEPTED')
print('original_F2_query_error_and_stable_identity=REJECTED; group_error_and_nonempty_scope=REJECTED')
print('F4_stdout_then_stderr=RuntimeError_REPRODUCED')
print('F3_central_fixture_alias_paths_do_not_match_configured_root=REPRODUCED')
print('nine_real_feature_rows_inventory=RECORDED; native_acceptance=UNVERIFIED')
