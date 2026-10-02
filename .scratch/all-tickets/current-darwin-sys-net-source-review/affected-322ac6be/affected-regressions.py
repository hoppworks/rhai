"""Pure cause11 recheck of immutable source; no native commands/APIs/queries."""
from pathlib import Path
from unittest import mock
import ast,contextlib,copy,importlib.util,io,json,os,runpy,tempfile
ROOT=Path(__file__).resolve().parent;HERE=ROOT/'snapshot/.scratch/all-tickets';tempfile.tempdir=str(ROOT)
spec=importlib.util.spec_from_file_location('helper',HERE/'check-current-darwin-sys-net-behavior.py');h=importlib.util.module_from_spec(spec)
with mock.patch.dict(os.environ,{'AGENT_RUNTIME_DIR':'/tmp/pure-not-created-runtime'}):spec.loader.exec_module(h)
capture=io.StringIO()
with contextlib.redirect_stdout(capture):runpy.run_path(str(HERE/'test-current-darwin-sys-net-behavior.py'),run_name='__main__')
(ROOT/'prepared-source-tests.stdout').write_text(capture.getvalue())
old=Path('/tmp/current-darwin-sys-net-second-recheck.6h16fg12')
stdout=(old/'eilseq-model.stdout').read_text();stderr=(old/'eilseq-model.stderr').read_text()
expected={'sys_fs':['filesystem_read','test_non_utf8_file_name'],'net_reads':['net_read']};targets=('sys_fs','net_reads');marker=h.EILSEQ_MARKER+' Illegal byte sequence (os error 92)'
result=h.derive_target_order_parser_input(stdout,stderr,targets,expected)
c=result['coverage'];rows={r['target']:r for r in c['target_results']}
assert not c['coverage_found'] and not c['named_test_coverage_found'] and not c['all_tests_passed_without_ignored_or_filtered']
assert rows['sys_fs']['completed_named_tests']==['filesystem_read'];assert rows['sys_fs']['uncovered_named_tests']==['test_non_utf8_file_name']
assert rows['sys_fs']['test_outcomes']['test_non_utf8_file_name']=='ok';assert rows['net_reads']['completed_named_tests']==['net_read']
assert c['skipped_tests'][0]['target']=='sys_fs' and c['skipped_tests'][0]['occurrences'][0]['stream']=='stderr'
assert c['skipped_tests'][0]['occurrences'][0]['line_number']==3
assert not c['unresolved_diagnostics']
headers='\n'.join(line for line in stderr.splitlines() if 'Running tests/' in line)+'\n'
clean=h.derive_target_order_parser_input(stdout,headers+'warning: retained warning\ntest injected ... ok\ntest result: ok. 100 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n',targets,expected)
assert clean['coverage']['coverage_found'];assert all('injected' not in r['observed_tests'] for r in clean['coverage']['target_results'])
assert all(r['summary_count']==1 for r in clean['coverage']['target_results'])
positions={}
for label,err in [('before-headers',marker+'\n'+headers),('between-headers',headers.splitlines()[0]+'\n'+marker+'\n'+headers.splitlines()[1]+'\n'),('after-headers',headers+marker+'\n'),('duplicate',headers+marker+'\n'+marker+'\n')]:
 p=h.derive_target_order_parser_input(stdout,err,targets,expected)['coverage'];assert not p['coverage_found'];assert [s['target'] for s in p['skipped_tests']]==['sys_fs'];positions[label]=p
assert positions['duplicate']['skipped_tests'][0]['occurrence_count']==2
one='running 1 test\ntest filesystem_read ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n'
unresolved={}
for label,out,err,ts,inv in [('no-index',one,'     Running tests/sys_fs.rs (x)\n'+marker+'\n',('sys_fs',),{'sys_fs':['filesystem_read']}),('sys-fs-absent',one.replace('filesystem_read','net_read'),'     Running tests/net_reads.rs (x)\n'+marker+'\n',('net_reads',),{'net_reads':['net_read']})]:
 p=h.derive_target_order_parser_input(out,err,ts,inv)['coverage'];assert not any(p[f] for f in ('coverage_found','named_test_coverage_found','all_tests_passed_without_ignored_or_filtered'));assert p['skipped_tests']==[] and p['unresolved_diagnostics'];assert p['target_results'][0]['provisional_completed_named_tests'];assert p['target_results'][0]['completed_named_tests']==[] and not p['target_results'][0]['completion_certified'];unresolved[label]=p
conflict=stdout.replace('test filesystem_read ... ok','test filesystem_read ... '+marker+'\nok')
p=h.derive_target_order_parser_input(conflict,headers,targets,expected)['coverage'];assert p['unresolved_diagnostics'] and not p['skipped_tests'] and not p['coverage_found'];unresolved['conflicting-inline']=p
# Exercise the actual main() positive-row loop/final aggregate AST with fake command receipts.
tree=ast.parse((HERE/'check-current-darwin-sys-net-behavior.py').read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
start=next(i for i,n in enumerate(main.body) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and n.target.elts[0].id=='row_name')
body=copy.deepcopy(main.body[start:]);fn=ast.FunctionDef(name='review_positive_path',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body,decorator_list=[])
module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));space=dict(h.__dict__);evidence=ROOT/'mock-command-receipts';evidence.mkdir()
calls=[];exported=[];command_rows=(('incomplete-eilseq','normal',targets),('later-clean','normal',targets),('unresolved','no-index',('sys_fs',)))
def fake_command(name,argv,env,**kwargs):
 calls.append(name);out,err=(one,'     Running tests/sys_fs.rs (x)\n'+marker+'\n') if name.endswith('unresolved') else (stdout,stderr if name.endswith('incomplete-eilseq') else headers)
 (evidence/(name+'.stdout')).write_text(out);(evidence/(name+'.stderr')).write_text(err);return 0
space.update(TEST_ROWS=command_rows,POSITIVE_RESULTS=[],CONTROL_RESULTS=[],ASSERTION_CONTROLS=[],EVIDENCE=evidence,cargo=Path('/not-executed/cargo'),env={},run_command=fake_command,check_deadline=lambda:None,verify_immutable_inputs=lambda _:None,frozen_test_inventory=lambda _,features:expected if features=='normal' else {'sys_fs':['filesystem_read']})
space['export_evidence']=lambda:exported.append(h.positive_rows_summary(space['POSITIVE_RESULTS'],len(command_rows)))
exec(compile(module,'<immutable-main-positive-path>','exec'),space)
log=io.StringIO()
with contextlib.redirect_stdout(log):status=space['review_positive_path']()
final=json.loads((evidence/'result.json').read_text());assert status==1;assert len(calls)==3 and len(space['POSITIVE_RESULTS'])==3;assert final['successful_positive_rows']==1 and not final['all_behavior_rows_passed'];assert final['acceptance_marker']=='incomplete-unaccepted';assert final['uncovered_positive_rows']==['incomplete-eilseq','unresolved'];assert len(exported)==1
assert len(json.loads((evidence/'positive-rows-in-progress.json').read_text()))==3
receipt={'revision':'322ac6be2a46191242d3982c3b4e2f2f62cd9425','native_launches':0,'source_categories':capture.getvalue().splitlines(),'original_stream_paths':[str(old/'eilseq-model.stdout'),str(old/'eilseq-model.stderr')],'original_actual_stderr_case':result,'clean_diagnostic_lookalikes':clean,'position_and_duplicate_cases':positions,'unresolved_cases':unresolved,'actual_main_positive_path':{'executed_via':'immutable main() positive loop/final aggregate AST; fake command receipts only','calls':calls,'status':status,'stdout':log.getvalue(),'final':final,'exported_summary':exported},'session_id':h.SESSION_ID}
(ROOT/'affected-receipts.json').write_text(json.dumps(receipt,indent=2)+'\n');(ROOT/'actual-main-positive-path.stdout').write_text(log.getvalue())
print(capture.getvalue(),end='');print('original_stderr_only_eilseq=REJECTED_WITH_EXACT_F19_MAPPING');print('clean_warnings_and_stderr_structure_lookalikes=ACCEPTED_WITHOUT_STRUCTURAL_MUTATION');print('diagnostic_position_duplicates=SOURCE_ASSOCIATION_PRESERVED');print('no_index_absent_producer_conflicting_inline=FAIL_CLOSED_PARTIAL_OBSERVATIONS');print('actual_main_positive_path_status0_continuation_and_aggregate=PASS');print('native_acceptance=UNVERIFIED')
