#!/usr/bin/env python3
"""Deterministic source/package probes; performs no SSH, build, launch or allocation."""
import ast,hashlib,json,pathlib,tarfile,types,os
import importlib.util,tempfile
import csv,shutil
import time
P=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
f=json.loads((P/'source-freeze.json').read_text())
assert f['source_revision']=='9dc92b16dad173eaffbde521310d1e2480e7be9c'
assert f['test_source_sha256']=='6b088870e6f4ed758c88e6fdc7e50475cae7cda90ba10dae58e45718a2ba3a98'
assert f['files']['source.tar']=='2b46a48f0978de3f7c1a7958678d3474232a0b2246ac8ff8f85e9e931345c039'
assert sha(P/'source.tar')==f['files']['source.tar']
assert sha(P/'Cargo.lock.accepted')==f['files']['Cargo.lock.accepted']
with tarfile.open(P/'source.tar') as t:
 b=t.extractfile(next(m for m in t.getmembers() if m.name.endswith('src/packages/sys/process/unix.rs'))).read()
assert hashlib.sha256(b).hexdigest()==f['test_source_sha256']
proof=(P/'linux-process-overlap-proof.py').read_text();ast.parse(proof)
assert 'BASE.run_command(label, argv, env, expected_status=expected)' in proof
assert "'--exact'" in proof and 'packages::sys::process::unix::tests::readable_output_overflow_wins_when_deadline_expires_direct_child' in proof and 'packages::sys::process::unix::tests::readable_output_overflow_wins_when_deadline_expires_managed' in proof
assert proof.index("for mode in ('direct', 'managed'):\n            run_case(mode, 'timeout-first'") < proof.index("for mode in ('direct', 'managed'):\n            run_case(mode, 'restored'")
spec=importlib.util.spec_from_file_location('overlap_recipe_probe',P/'linux-process-overlap-proof.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tarfile.open(P/'source.tar') as t:
 source=next(m for m in t.getmembers() if m.name.endswith('src/packages/sys/process/unix.rs'))
 baseline=t.extractfile(source).read()
with tempfile.TemporaryDirectory() as td:
 mutant_source=pathlib.Path(td)/'unix.rs';mutant_source.write_bytes(baseline)
 mutant=module.move_timeout_before_read(mutant_source)[1]
assert hashlib.sha256(mutant).hexdigest()=='53ce5a454661ffd08e6f3d0a9bbac15c8ccd8f1ea397c042b777a066be756b23'
assert 'overflow must win over the simultaneously expired deadline' in proof
assert 'poll=stdout-readable' in proof and 'child_write=acknowledged' in proof and 'owner=closed' in proof
assert 'changed.index(START)' in proof and 'changed.index(READ)' in proof
for n in ('collect-originals.py','linux-process-overlap-fresh-closure.py'):ast.parse((P/n).read_text())
collector=(P/'collect-originals.py').read_text()
assert 'stage-originals' in collector and "open('xb')" in collector and 'independent live inventory' in collector
assert "['/bin/ps','-e','-o','pid=,pgid=']" in collector
assert 'shutil.rmtree(s)' in collector and 'shutil.rmtree(scope)' not in collector
launch=(P/'launch.sh').read_text();stage=(P/'stage.sh').read_text()
assert '/root/rhai-linux-process-overlap-d79-20261004-1259' in launch and '/root/.local/share/agent-builds/rhai/linux-process-overlap-d79-20261004-1259' in launch
assert '600' in launch and '585' in launch and '30' in launch
assert 'source-freeze.json' in stage and 'linux-process-overlap-proof.py' in stage
assert 'linux-process-overlap-preflight.py' in stage and 'linux-process-overlap-slot-wrapper.py' in stage
assert 'input-identities.sha256' in stage and 'native-allocation.json' not in stage
assert 'inputs_verified' in collector and 'preflight_source_sha256' in collector and 'slot_wrapper_source_sha256' in collector
assert '53ce5a454661ffd08e6f3d0a9bbac15c8ccd8f1ea397c042b777a066be756b23' in proof or hashlib.sha256(mutant).hexdigest()=='53ce5a454661ffd08e6f3d0a9bbac15c8ccd8f1ea397c042b777a066be756b23'
spec=importlib.util.spec_from_file_location('overlap_actual_collector',P/'collect-originals.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
# Exercise the actual collector predicates with valid inputs, then falsify one bound at a time.
early={'pid':44,'ppid':12,'pgid':44,'start_ticks':987,'cmdline':'cargo test'}
row={'pid':'44','ppid':'12','pgid':'44','start_ticks':'987','cmdline':'cargo test'}
assert collector.identity_matches(early,row)
assert not collector.identity_matches({**early,'pid':45},row)
case='timeout-first-managed'
raw='overlap-fixture mode=managed child_pid=44 child_start_ticks=987 child_pgid=44 child_write=acknowledged deadline=expired poll=stdout-readable overflow_observed=false reap=ESRCH owner=closed'
fixture={'case':case,'pid':'44','start_ticks':'987','pgid':'44','write':'acknowledged','deadline':'expired','poll':'stdout-readable','overflow':'false','reap':'ESRCH','owner':'closed','expected_command':'/bin/sleep 30'}
collector.bind_fixture_row(fixture,raw,case)
for change in ({'pgid':'45'},{'poll':'sleep-only'},{'owner':'open'},{'expected_command':'/bin/sleep 30 observed'}):
    try:collector.bind_fixture_row({**fixture,**change},raw,case)
    except ValueError:pass
    else:raise AssertionError('altered fixture identity/readiness/closure was accepted: '+repr(change))
collector.validate_mutant_receipt({'timeout-first-ordering':'53ce5a454661ffd08e6f3d0a9bbac15c8ccd8f1ea397c042b777a066be756b23'})
for bad in ({'timeout-first-ordering':'0'*64},{},None):
    try:collector.validate_mutant_receipt(bad)
    except ValueError:pass
    else:raise AssertionError('altered mutant hash was accepted')
samples=[{'storage_kib':101,'rss_kib':202,'descendants':3},{'storage_kib':103,'rss_kib':200,'descendants':4}]
maxima={'maxima':{'storage_kib':103,'rss_kib':202,'descendants':4},'sample_count':2,'storage_preemptive_stop_kib':1572864,'storage_hard_stop_kib':2097152,'rss_hard_stop_kib':2097152,'descendant_hard_stop':16}
collector.validate_resource_receipts(samples,maxima)
for bad in ({**maxima,'sample_count':1},{**maxima,'maxima':{**maxima['maxima'],'rss_kib':999}},{**maxima,'descendant_hard_stop':17}):
    try:collector.validate_resource_receipts(samples,bad)
    except ValueError:pass
    else:raise AssertionError('altered resource receipt/cap was accepted')
runtime=pathlib.Path(collector.SCOPE)/'private-run'
bindir=str(runtime/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin')
common={'HOME':str(runtime/'home'),'TMPDIR':str(runtime/'tmp'),'TMP':str(runtime/'tmp'),'TEMP':str(runtime/'tmp'),'CARGO_HOME':str(runtime/'cargo-home'),'RUSTUP_HOME':str(runtime/'rustup-home'),'CARGO_TARGET_DIR':str(runtime/'target'),'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_PROFILE_DEV_DEBUG':'0','CARGO_TERM_COLOR':'never','RUST_BACKTRACE':'0'}
names=['rustup-install','rustc-version','cargo-version','timeout-first-direct','timeout-first-managed','restored-direct','restored-managed']
commands=[]
for index,n in enumerate(names):
    env={**common,'PATH':('/usr/bin:/bin:/usr/sbin:/sbin' if index==0 else bindir+':/usr/bin:/bin:/usr/sbin:/sbin')}
    if index:env['RUSTC']=bindir+'/rustc'
    commands.append({'name':n,'cwd':str(runtime if index<3 else runtime/'source'),'env_overrides':{},'effective_env':env,'spawned':True,'status':0,'expected_status':0})
collector.validate_command_inventory(commands,runtime)
for bad_runtime in (pathlib.Path('/tmp/unowned-runtime'),runtime/'nested'):
    try:collector.validate_command_inventory(commands,bad_runtime)
    except ValueError:pass
    else:raise AssertionError('arbitrary runtime identity was accepted')
try:collector.validate_command_inventory([{**commands[0],'cwd':'/tmp'}]+commands[1:],runtime)
except ValueError:pass
else:raise AssertionError('altered setup cwd was accepted')
wrong_tmp_commands=[dict(c) for c in commands]
wrong_tmp_commands[3]={**commands[3],'effective_env':{**commands[3]['effective_env'],'TMPDIR':collector.SCOPE,'TMP':collector.SCOPE,'TEMP':collector.SCOPE}}
try:collector.validate_command_inventory(wrong_tmp_commands,runtime)
except ValueError:pass
else:raise AssertionError('outer scope temp path was accepted instead of runner runtime/tmp')
versions={'toolchain':'1.77.2-x86_64-unknown-linux-gnu','rustc_stdout':'rustc 1.77.2 (x)\nhost: x86_64-unknown-linux-gnu\n','cargo_stdout':'cargo 1.77.2 (x)\n'}
collector.validate_tool_versions(versions,versions['rustc_stdout'],versions['cargo_stdout'])
try:collector.validate_tool_versions({**versions,'toolchain':'other'},versions['rustc_stdout'],versions['cargo_stdout'])
except ValueError:pass
else:raise AssertionError('altered tool version was accepted')
def full_collector_receipt_probe():
  with tempfile.TemporaryDirectory() as temp:
    tree=pathlib.Path(temp)/'stage';proof=tree/'proof-evidence';outer=tree/'outer-evidence';proof.mkdir(parents=True);outer.mkdir()
    runtime=pathlib.Path(collector.SCOPE)/'probe-runtime';bindir=runtime/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin';cargo=bindir/'cargo'
    expected_names=['timeout-first-direct','timeout-first-managed','restored-direct','restored-managed']
    commands=[];controls=[];fixture_rows=[];identity_rows=[]
    full_env_base={'HOME':str(runtime/'home'),'TMPDIR':str(runtime/'tmp'),'TMP':str(runtime/'tmp'),'TEMP':str(runtime/'tmp'),'CARGO_HOME':str(runtime/'cargo-home'),'RUSTUP_HOME':str(runtime/'rustup-home'),'CARGO_TARGET_DIR':str(runtime/'target'),'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_PROFILE_DEV_DEBUG':'0','CARGO_TERM_COLOR':'never','RUST_BACKTRACE':'0','PATH':'/usr/bin:/bin:/usr/sbin:/sbin'}
    for index,name in enumerate(['rustup-install','rustc-version','cargo-version']+expected_names):
      setup=index<3;first=index==0;env={**full_env_base,'PATH':('/usr/bin:/bin:/usr/sbin:/sbin' if first else str(bindir)+':/usr/bin:/bin:/usr/sbin:/sbin')}
      if not first:env['RUSTC']=str(bindir/'rustc')
      mode=name.rsplit('-',1)[-1];kind=name.rsplit('-',1)[0] if not setup else name
      argv=([str(pathlib.Path('/root/.cargo/bin/rustup')),'toolchain','install'] if name=='rustup-install' else
            [str(bindir/'rustc'),'--version','--verbose'] if name=='rustc-version' else
            [str(cargo),'--version','--verbose'] if name=='cargo-version' else
            [str(cargo),'test','--locked','--lib','--features','testing-environ,sys',collector.TESTS[mode],'--','--exact','--nocapture','--test-threads=1'])
      status=101 if name.startswith('timeout-first-') else 0
      cmd={'name':name,'argv':argv,'expected_status':status,'status':status,'spawned':True,'cwd':str(runtime if setup else runtime/'source'),'env_overrides':{},'effective_env':env,'stdout':name+'.stdout','stderr':name+'.stderr'}
      commands.append(cmd);(proof/(name+'.status')).write_text(str(status)+'\n')
      pid=500+index;identity_rows.append(('command:'+name,pid,400,400,3000+pid,' '.join(argv)))
      if setup:
        (proof/(name+'.stdout')).write_text('');(proof/(name+'.stderr')).write_text('')
      if not setup:
        mode=name.rsplit('-',1)[1]
        child_pid=700+index;pgid=child_pid
        overflow='false' if name.startswith('timeout-first-') else 'true'
        raw=f'overlap-fixture mode={mode} child_pid={child_pid} child_start_ticks={5000+child_pid} child_pgid={pgid} child_write=acknowledged deadline=expired poll=stdout-readable overflow_observed={overflow} reap=ESRCH owner=closed'
        output=f'{raw}\n'
        error=(f"{collector.CAUSE}\nthread '{collector.TESTS[mode]}' panicked at src/packages/sys/process/unix.rs:1\n" if status else '')
        if not status:output+=f'test {collector.TESTS[mode]} ... ok\ntest result: ok. 1 passed; 0 failed;\n'
        (proof/(name+'.stdout')).write_text(output);(proof/(name+'.stderr')).write_text(error)
        fixture_rows.append([name,str(child_pid),str(5000+child_pid),str(pgid),'acknowledged','expired','stdout-readable',overflow,'ESRCH','closed','/bin/sleep 30'])
        controls.append({'name':name,'status':status,'expected_status':status})
    (proof/'fixture-identities.tsv').write_text('case\tpid\tstart_ticks\tpgid\twrite\tdeadline\tpoll\toverflow\treap\towner\texpected_command\n'+'\n'.join('\t'.join(r) for r in fixture_rows)+'\n')
    process_rows=[('helper',400,399,400,2000,'python3 overlap-proof.py'),('scoped-supervisor',399,1,399,1999,'python3 run_scoped.py')]+identity_rows+[('command:du',900,400,400,3900,'/usr/bin/du -sk '+str(runtime)),('command:ps',901,400,400,3901,'/bin/ps -e -o pid=,ppid=,rss=')]
    (proof/'process-identities.tsv').write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n'+'\n'.join('\t'.join(map(str,r)) for r in process_rows)+'\n')
    early={'runtime':str(runtime),'helper':{'pid':400,'ppid':399,'pgid':400,'start_ticks':2000,'cmdline':'python3 overlap-proof.py'},'scoped_supervisor':{'pid':399,'ppid':1,'pgid':399,'start_ticks':1999,'cmdline':'python3 run_scoped.py'}}
    (proof/'early-runtime-identity.json').write_text(json.dumps(early))
    (outer/'launcher-identities.tsv').write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\nlauncher\t310\t1\t310\t1100\tbash launch.sh\n')
    rustc='rustc 1.77.2 (test)\nhost: x86_64-unknown-linux-gnu\n';cargo_out='cargo 1.77.2 (test)\n'
    (proof/'tool-versions.json').write_text(json.dumps({'toolchain':'1.77.2-x86_64-unknown-linux-gnu','rustc_stdout':rustc,'cargo_stdout':cargo_out}))
    (proof/'rustc-version.stdout').write_text(rustc);(proof/'cargo-version.stdout').write_text(cargo_out)
    (proof/'resource-samples.jsonl').write_text('{"storage_kib":101,"rss_kib":202,"descendants":3}\n')
    (proof/'sampled-maxima.json').write_text(json.dumps({'maxima':{'storage_kib':101,'rss_kib':202,'descendants':3},'sample_count':1,'storage_preemptive_stop_kib':1572864,'storage_hard_stop_kib':2097152,'rss_hard_stop_kib':2097152,'descendant_hard_stop':16}))
    (proof/'export-budget.json').write_text(json.dumps({'elapsed_seconds_at_export_start':10,'elapsed_seconds_before_budget_receipt_copy':11,'helper_deadline_seconds':540,'helper_work_deadline_seconds':510,'deadline_checked_at_entry_between_items_and_after':True,'deadline_checked_immediately_before_and_after_budget_receipt_copy':True,'individual_copy_operations_preemptible':False}))
    (proof/'commands.json').write_text(json.dumps(commands));(proof/'control-results.json').write_text(json.dumps(controls))
    pins={'source_revision':collector.REV,'source_archive_sha256':collector.ARCHIVE,'source_sha256':collector.TEST,'base_helper_sha256':'unused','lock_sha256':collector.LOCK}
    (proof/'source-inputs.json').write_text(json.dumps({**pins,'test_names':collector.TESTS}))
    (proof/'source-restoration.json').write_text(json.dumps({'restored_examples_match_original_bytes':True,'original_example_sha256':{'src/packages/sys/process/unix.rs':collector.TEST},'injected_example_sha256':{'timeout-first-ordering':collector.EXPECTED_MUTANT},'cargo_lock_sha256_after_execution':collector.LOCK}))
    (proof/'package-result.json').write_text(json.dumps({**pins,'acceptance_claim':False,'source_restored_to_baseline':True,'commands':commands,'controls':controls}))
    (outer/'outer-status.txt').write_text('0\n');(outer/'run-scoped.status').write_text('0\n')
    for name in ('archive-build-source.py','source.tar','Cargo.lock.accepted','check-linux-current-msrv-examples.py','source-freeze.json','contract.md','linux-process-overlap-proof.py','collect-originals.py','linux-process-overlap-fresh-closure.py','recipe-probes.py','launch.sh'):
      shutil.copy2(P/name,tree/name)
    (tree/'runner/tools/agentskills').mkdir(parents=True)
    runner_root=pathlib.Path('/Users/hoppworks/projects/agent-skills/tools')
    for source,relative in ((runner_root/'run_scoped.py','runner/tools/run_scoped.py'),(runner_root/'agentskills/__init__.py','runner/tools/agentskills/__init__.py'),(runner_root/'agentskills/pyguard.py','runner/tools/agentskills/pyguard.py')):shutil.copy2(source,tree/relative)
    for source,name in ((collector.PREFLIGHT,'linux-process-overlap-preflight.py'),(collector.SLOT_WRAPPER,'linux-process-overlap-slot-wrapper.py')):shutil.copy2(source,tree/name)
    manifest_names=['archive-build-source.py','source.tar','Cargo.lock.accepted','check-linux-current-msrv-examples.py','source-freeze.json','contract.md','linux-process-overlap-proof.py','collect-originals.py','linux-process-overlap-fresh-closure.py','recipe-probes.py','launch.sh','runner/tools/run_scoped.py','runner/tools/agentskills/__init__.py','runner/tools/agentskills/pyguard.py']
    (tree/'input-identities.sha256').write_text(''.join(collector.digest(tree/n)+'  '+n+'\n' for n in manifest_names))
    (tree/'native-allocation.json').write_text(json.dumps({'source_revision':collector.REV,'native_launch':1,'preflight_source_sha256':collector.digest(tree/'linux-process-overlap-preflight.py'),'slot_wrapper_source_sha256':collector.digest(tree/'linux-process-overlap-slot-wrapper.py'),'preflight':{'ready':True,'heavy':[],'scope_absent':True,'inputs_verified':len(manifest_names)}}))
    result=collector.validate(tree,{'files':{},'directories':[]})
    assert result['identities'] and result['groups']
    saved_commands=json.loads((proof/'commands.json').read_text())
    wrong_tmp=[dict(c) for c in saved_commands]
    wrong_tmp[3]={**saved_commands[3],'effective_env':{**saved_commands[3]['effective_env'],'TMPDIR':collector.SCOPE,'TMP':collector.SCOPE,'TEMP':collector.SCOPE}}
    (proof/'commands.json').write_text(json.dumps(wrong_tmp))
    try:collector.validate(tree,{'files':{},'directories':[]})
    except ValueError:pass
    else:raise AssertionError('full collector accepted outer scope temp path')
    (proof/'commands.json').write_text(json.dumps(saved_commands))
    # A changed raw receipt must make the complete collector reject its own otherwise-valid corpus.
    (proof/'timeout-first-direct.stdout').write_text((proof/'timeout-first-direct.stdout').read_text().replace('child_pgid=703','child_pgid=999'))
    try:collector.validate(tree,{'files':{},'directories':[]})
    except ValueError:pass
    else:raise AssertionError('full collector accepted altered fixture receipt')
full_collector_receipt_probe()
# Execute the real closure transport function with a fake runner: no SSH is started.
closure_spec=importlib.util.spec_from_file_location('overlap_closure_probe',P/'linux-process-overlap-fresh-closure.py')
closure=importlib.util.module_from_spec(closure_spec);closure_spec.loader.exec_module(closure)
called={}
def fake_run(argv,**kwargs):
    called.update(argv=argv,kwargs=kwargs)
    return types.SimpleNamespace(stdout='{"scope_absent":true}\n')
assert closure.invoke_closure({'identities':[]},fake_run)=={'scope_absent':True}
assert called['kwargs'].get('capture_output') is True and called['kwargs'].get('text') is True and called['kwargs'].get('check') is True and called['kwargs'].get('input')=='{"identities": []}'
assert called['argv'][0]=='ssh' and 'capture_output' not in called['kwargs'].get('kwargs',{})
# Execute the real producer export path with a deterministic clock/deadline spy.
def export_base(root,fail_on=None):
    stage=root/'stage';evidence=root/'proof-evidence';source=root/'source';stage.mkdir();source.mkdir();(stage/'evidence-item').write_text('owned proof bytes')
    calls=[]
    def deadline(*,during_export=False):
        calls.append(during_export)
        if fail_on is not None and len(calls)==fail_on:raise TimeoutError('probe deadline')
    return types.SimpleNamespace(STAGE=stage,EVIDENCE=evidence,SOURCE=source,START=time.monotonic()-1,
        ORIGINAL_EXAMPLES={},ORIGINAL_EXAMPLE_HASHES={},INJECTED_EXAMPLE_HASHES={},SAMPLES=[],
        MAXIMA={'storage_kib':1,'rss_kib':2,'descendants':0},COMMANDS=[],CONTROL_RESULTS=[],
        REVISION='9dc92b16dad173eaffbde521310d1e2480e7be9c',LOCK_SHA256=collector.LOCK,
        FEATURES='testing-environ,sys',HELPER_EXIT_STATUS=1,restore_example_sources=lambda:None,
        manifest_hashes=lambda:{},export_destination_is_safe=lambda:True,
        write_json=lambda path,value:path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n'),
        check_deadline=deadline),calls
with tempfile.TemporaryDirectory() as td:
    module.BASE,deadline_calls=export_base(pathlib.Path(td));module.export()
    budget=json.loads((pathlib.Path(td)/'proof-evidence/export-budget.json').read_text())
    assert budget['deadline_checked_at_entry_between_items_and_after'] is True and budget['individual_copy_operations_preemptible'] is False
    assert len(deadline_calls)>=4 and all(deadline_calls)
with tempfile.TemporaryDirectory() as td:
    module.BASE,_=export_base(pathlib.Path(td),fail_on=3)
    try:module.export()
    except TimeoutError:pass
    else:raise AssertionError('producer export ignored between-item deadline failure')
# Exercise the producer's real proc parser with deterministic procfs-like records.
base_spec=importlib.util.spec_from_file_location('overlap_base_probe',P/'check-linux-current-msrv-examples.py')
base=importlib.util.module_from_spec(base_spec)
_runtime_env=os.environ.get('AGENT_RUNTIME_DIR');os.environ['AGENT_RUNTIME_DIR']='/tmp/process-overlap-probe-runtime'
try:base_spec.loader.exec_module(base)
finally:
    if _runtime_env is None:os.environ.pop('AGENT_RUNTIME_DIR',None)
    else:os.environ['AGENT_RUNTIME_DIR']=_runtime_env
real_path=base.Path
class FakeProcPath:
    def __init__(self,value):self.value=str(value)
    def __truediv__(self,other):return FakeProcPath(self.value+'/'+str(other))
    def read_text(self,**kwargs):
        if self.value.endswith('/stat'):return proc_record[0]
        raise FileNotFoundError(self.value)
    def read_bytes(self):
        if self.value.endswith('/cmdline'):return b'fixture\0arg\0'
        raise FileNotFoundError(self.value)
def stat_record(pid=17,state='S',start='321',nfields=20):
    fields=[state,'12','13']+['0']*max(0,nfields-3)
    if nfields>=20:fields[19]=start
    return f'{pid} (fixture ) with paren) '+' '.join(fields)
for proc_record in ((stat_record(),),):
    base.Path=FakeProcPath
    identity=base.process_identity(17)
    assert identity=={'pid':17,'ppid':12,'pgid':13,'start_ticks':321,'cmdline':'fixture arg'}
for proc_record in ((stat_record(pid=18),),(stat_record(state='?'),),(stat_record(start='0'),),(stat_record(nfields=19),)):
    try:base.process_identity(17)
    except RuntimeError:pass
    else:raise AssertionError('malformed producer proc stat was accepted')
base.Path=real_path
print('actual-function overlap probes passed: full valid collector receipt, altered child-group rejection, export deadline/copy path, strict proc identity, mutant/runtime/tmp-path/version/cap rejection, and closure subprocess.run invocation; no SSH/build/native run performed')
