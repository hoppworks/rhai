"""Pure split-stream and lexical-root policy recheck; no native queries or APIs."""
from pathlib import Path,PurePosixPath
from unittest import mock
import importlib.util,contextlib,io,json,os,runpy,tempfile
ROOT=Path(__file__).resolve().parent;HERE=ROOT/'snapshot/.scratch/all-tickets';tempfile.tempdir=str(ROOT)
spec=importlib.util.spec_from_file_location('helper',HERE/'check-current-darwin-sys-net-behavior.py');helper=importlib.util.module_from_spec(spec)
with mock.patch.dict(os.environ,{'AGENT_RUNTIME_DIR':'/tmp/pure-not-created-runtime'}):spec.loader.exec_module(helper)
capture=io.StringIO()
with contextlib.redirect_stdout(capture):runpy.run_path(str(HERE/'test-current-darwin-sys-net-behavior.py'),run_name='__main__')
(ROOT/'prepared-source-tests.stdout').write_text(capture.getvalue())
expected={'sys_fs':['filesystem_read','test_non_utf8_file_name'],'net_reads':['net_read']}
stdout=('running 1 test\ntest net_read ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
 'running 2 tests\ntest filesystem_read ... ok\ntest test_non_utf8_file_name ... ok\ntest result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n')
headers='     Running tests/net_reads.rs (target/debug/deps/net_reads-a)\n     Running tests/sys_fs.rs (target/debug/deps/sys_fs-b)\n'
marker='filesystem rejects non-UTF-8 fixture with EILSEQ: Illegal byte sequence (os error 92)\n'
stderr=headers+marker
(ROOT/'eilseq-model.stdout').write_text(stdout);(ROOT/'eilseq-model.stderr').write_text(stderr)
derived=helper.derive_target_order_parser_input(stdout,stderr,('sys_fs','net_reads'),expected)
(ROOT/'eilseq-model.parser-input.txt').write_text(derived['parser_input'])
assert derived['coverage']['coverage_found'] and derived['coverage']['skipped_tests']==[]
assert 'test_non_utf8_file_name' in derived['coverage']['target_results'][0]['completed_named_tests']
full=helper.positive_test_coverage(derived['parser_input'],('sys_fs','net_reads'),expected)
assert not full['coverage_found'] and full['skipped_tests'][0]['test']=='test_non_utf8_file_name'
clean=helper.derive_target_order_parser_input(stdout,headers,('sys_fs','net_reads'),expected);assert clean['coverage']['coverage_found']
negatives={}
for name,badout,baderr in [('missing-header',stdout,headers.splitlines()[0]+'\n'),('duplicate-header',stdout,headers+headers.splitlines()[0]+'\n'),('missing-named-test',stdout.replace('test filesystem_read ... ok\n',''),headers),('incomplete-block',stdout+'running 0 tests\n',headers),('extra-summary',stdout+'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n',headers)]:
 try: helper.derive_target_order_parser_input(badout,baderr,('sys_fs','net_reads'),expected)
 except RuntimeError as exc: negatives[name]=str(exc)
 else: raise AssertionError('bad input accepted: '+name)
# Exact lexical prefix routes corresponding to corrected Rust configuration.
central='/Users/hoppworks/.local/share/agent-builds/rhai/owned/runtime/tmp/rhai-sys-test-owned/real'
var='/var/../../'+central.lstrip('/');private='/private/var/../../'+central.lstrip('/')
def suffix(path,root):
 p,r=PurePosixPath(path).parts,PurePosixPath(root).parts
 assert p[:len(r)]==r
 return p[len(r):]
assert suffix(var+'/a.txt',var)==('a.txt',);assert suffix(private+'/a.txt',private)==('a.txt',)
receipt={'revision':'4c4a81e0551f6e6d5c56112de7febda0101ce27f','native_launches':0,'source_categories':capture.getvalue().splitlines(),'clean_multi_target':clean['coverage'],'meaningful_negatives':negatives,'actual_eprintln_stream_shape_false_acceptance':derived['coverage'],'full_preserved_parser_input_rejects_same_skip':full,'F3_configured_prefix_policy_routes':{'given_root':var,'given_prefix_alias':private,'relative_suffixes':['a.txt','a.txt'],'native_canonicalization_and_engine':'unverified'},'scope_naming':{'helper_required_stage_and_scope':helper.SESSION_ID,'contract_instructed_stage_and_scope':'current-darwin-sys-net-behavior-2f795ece-20261002'}}
assert receipt['scope_naming']['helper_required_stage_and_scope']!=receipt['scope_naming']['contract_instructed_stage_and_scope']
(ROOT/'affected-receipts.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(capture.getvalue(),end='');print('clean_real_separate_multi_target_shape=ACCEPTED');print('malformed_headers_blocks_inventory=REJECTED');print('actual_F19_eprintln_stderr_skip=FALSE_ACCEPTANCE_REPRODUCED');print('full_preserved_parser_input_same_skip=REJECTED');print('F3_configured_and_prefix_alias_lexical_routes=PASS_SOURCE_MODEL');print('stage_scope_contract_helper_mismatch=REPRODUCED')
