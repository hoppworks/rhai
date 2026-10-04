#!/usr/bin/env python3
"""Exercise the frozen producer, complete custody consumer and refusal boundaries locally."""
from __future__ import annotations
import ast,contextlib,hashlib,importlib.util,io,json,os,pathlib,shlex,shutil,subprocess,sys,tarfile,tempfile,time
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[3]
PKG=pathlib.Path(__file__).resolve().parent
# Frozen archive and lock inputs are independently pinned by the accepted source contract.
ARCHIVE_SHA='998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b'
TEST_SHA='1b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a'
OVERLAYS={'wrong-cause-red':'7a60d0b4ee7b032e3f5288f493797123989c8004f48f8533c82acb7b79532410','wrong-incomplete-report-red':'2687de283e5dbc5e689421af7ca6501479a27a15048b51c73d4e34bcc838bbba'}
class RetirementReached(RuntimeError):pass

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory_tree(root):
 files={};dirs=[]
 for p in sorted(root.rglob('*')):
  rel=p.relative_to(root).as_posix()
  if p.is_symlink():raise AssertionError('fixture unexpectedly contains symlink '+rel)
  if p.is_dir():dirs.append(rel)
  elif p.is_file():files[rel]=digest(p)
  else:raise AssertionError('fixture unexpected object '+rel)
 return {'stage':str(root),'scope':'','files':files,'directories':dirs}

def make_tar(root):
 buffer=io.BytesIO()
 with tarfile.open(fileobj=buffer,mode='w') as tf:
  for item in sorted(root.iterdir()):tf.add(item,arcname='./'+item.name,recursive=True)
 return buffer.getvalue()

def run():
 assert digest(PKG/'source.tar')==ARCHIVE_SHA
 assert digest(PKG/'Cargo.lock.accepted')=='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
 with tarfile.open(PKG/'source.tar') as tf:
  member=next(m for m in tf.getmembers() if m.name.endswith('src/packages/sys/process/unix.rs'))
  baseline=tf.extractfile(member).read()
 assert hashlib.sha256(baseline).hexdigest()==TEST_SHA
 original_text=baseline.decode()
 overlays=[('message == "injected post-spawn pipe configuration failure"','message == "wrong configure pipe message"'),('                    && !report.stdout_complete()','                    && report.stdout_complete()')]
 for (name,pin),(anchor,replacement) in zip(OVERLAYS.items(),overlays):
  assert original_text.count(anchor)==1
  assert hashlib.sha256(original_text.replace(anchor,replacement,1).encode()).hexdigest()==pin
 proof_source=(PKG/'linux-post-spawn-pipe-setup-proof.py').read_text()
 version_offset=proof_source.index("BASE.run_command('rustc-version'")
 cargo_version_offset=proof_source.index("BASE.run_command('cargo-version'")
 extraction_offset=proof_source.index('BASE.extract_archive(archive_copy)')
 assert version_offset<cargo_version_offset<extraction_offset and "env,cwd=runtime" in proof_source[version_offset:extraction_offset]
 t=pathlib.Path(tempfile.mkdtemp(prefix='pipe-coupled-probes-'))
 os.environ['AGENT_RUNTIME_DIR']=str(t/'import-runtime')
 c=load('pipe_collector_fixture',PKG/'collect-originals.py')
 b=load('pipe_base_fixture',PKG/'check-linux-current-msrv-examples.py')
 p=load('pipe_proof_fixture',PKG/'linux-post-spawn-pipe-setup-proof.py');p.BASE=b
 physical_root=t/'var'/'roothome';physical_root.mkdir(parents=True);logical_root=t/'root';logical_root.symlink_to(physical_root,target_is_directory=True)
 physical_stage=physical_root/'rhai-linux-post-spawn-pipe-setup-523-20261004';physical_stage.mkdir();stage=logical_root/physical_stage.name;scope=logical_root/'.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004';work=t/'producer-work';work.mkdir();source=work/'source'
 assert not stage.is_symlink() and stage.resolve()==physical_stage.resolve()
 # Materialize the exact staged input package and its hash manifest.
 expected=next(ast.literal_eval(node.value) for node in ast.walk(ast.parse(c.CUSTODY)) if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='expected' for target in node.targets))
 for name,pin in expected.items():
  src=PKG/name
  if name=='contract.md':src=ROOT/'.scratch/all-tickets/linux-post-spawn-pipe-setup-contract.md'
  if name.startswith('runner/tools/'):src=pathlib.Path('/Users/hoppworks/projects/agent-skills/tools')/name[len('runner/tools/'):]
  dst=stage/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes());assert digest(dst)==pin,(name,digest(dst),pin)
 (stage/'input-identities.sha256').write_text(''.join(f'{pin}  {name}\n' for name,pin in expected.items()))
 # Extract the accepted source archive with the real base helper extractor.
 b.SOURCE=source;b.STAGE=work/'runtime-evidence';b.STAGE.mkdir();b.RUNTIME=scope/'agent-build-probe0001';b.INPUT_STAGE=stage;b.EXPECTED_STAGE=stage;b.PRESCRIBED_STAGE=stage;b.PRESCRIBED_SCOPE=scope;b.EVIDENCE=stage/'proof-evidence';b.START=time.monotonic();b.REVISION=p.REV
 b.CARGO_HOME=b.RUNTIME/'cargo-home';b.RUSTUP_HOME=b.RUNTIME/'rustup-home';b.TARGET=b.RUNTIME/'target';b.PRIVATE_HOME=b.RUNTIME/'home';b.PRIVATE_TMP=b.RUNTIME/'tmp'
 b.CONTRACT=stage/'contract.md';b.SOURCE_ARCHIVE=stage/'source.tar';b.LOCK_SOURCE=stage/'Cargo.lock.accepted';b.SOURCE_ARCHIVE_SHA256=ARCHIVE_SHA;b.LOCK_SHA256='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425';b.FEATURES='testing-environ,sys'
 # Exercise the actual run_command cwd guard and real child process before source extraction.
 startup_runtime=work/'startup-runtime';startup_runtime.mkdir();b.RUNTIME=startup_runtime;b.STAGE=b.RUNTIME/'startup-evidence';b.STAGE.mkdir();b.START=time.monotonic();b.COMMANDS=[];b.INTERRUPTED=None
 original_sampler=b.sample_resources;b.sample_resources=lambda:None
 try:
  for name,version in [('rustc-version','rustc 1.77.2 host: x86_64-unknown-linux-gnu'),('cargo-version','cargo 1.77.2')]:
   script=f"import os; print({version!r} + ' cwd=' + os.getcwd())"
   assert b.run_command(name,[sys.executable,'-c',script],{},cwd=b.RUNTIME)==0
   assert (b.STAGE/(name+'.stdout')).read_text().strip()==version+' cwd='+str(b.RUNTIME.resolve())
  try:b.run_command('version-before-extract',[sys.executable,'-c','print(\"unreachable\")'],{})
  except RuntimeError as exc:assert 'command working directory does not exist' in str(exc)
  else:raise AssertionError('default source cwd unexpectedly existed before extraction')
  assert not source.exists()
 finally:b.sample_resources=original_sampler
 archive_copy=work/'accepted-source.tar';shutil.copy2(b.SOURCE_ARCHIVE,archive_copy);b.extract_archive(archive_copy)
 test=source/'src/packages/sys/process/unix.rs';assert digest(test)==TEST_SHA
 (source/'Cargo.lock').write_bytes((PKG/'Cargo.lock.accepted').read_bytes())
 b.ORIGINAL_EXAMPLES={test:test.read_bytes()};b.ORIGINAL_EXAMPLE_HASHES={'src/packages/sys/process/unix.rs':TEST_SHA};b.INJECTED_EXAMPLE_HASHES={};b.CARGO_MANIFESTS=b.manifest_hashes();b.COMMANDS=[];b.CONTROL_RESULTS=[];b.IDENTITY_ROWS=[];b.SAMPLES=[dict(monotonic_seconds=1.0,storage_kib=100,rss_kib=200,descendants=0),dict(monotonic_seconds=2.0,storage_kib=100,rss_kib=200,descendants=0)];b.MAXIMA=dict(storage_kib=100,rss_kib=200,descendants=0);b.INTERRUPTED=None
 p.STAGE_PATH=stage;p.SCOPE_PATH=scope;p.REV=p.REV
 # Use complete early identities and the real emitter. Distinct process groups are included in custody readback.
 ids={
  'launcher':dict(pid=990004,ppid=1,pgid=990004,start_ticks=104,cmdline=str(stage/'launch.sh')),
  'run-scoped':dict(pid=990003,ppid=990004,pgid=990004,start_ticks=103,cmdline=f'python3 {stage}/runner/tools/run_scoped.py --timeout 585 -- python3 {stage}/linux-post-spawn-pipe-setup-proof.py'),
  'scoped-supervisor':dict(pid=990002,ppid=990003,pgid=990002,start_ticks=102,cmdline=f'python3 {stage.resolve()}/runner/tools/run_scoped.py _supervise 8 python3 {stage}/linux-post-spawn-pipe-setup-proof.py'),
  'helper':dict(pid=990001,ppid=990002,pgid=990002,start_ticks=101,cmdline=f'python3 {stage}/linux-post-spawn-pipe-setup-proof.py')}
 b.RUNTIME=scope/'agent-build-probe0001';b.STAGE=work/'runtime-evidence';b.STAGE.mkdir(exist_ok=True)
 for label in ('helper','scoped-supervisor'):
  value=ids[label];b.record_process_identity(label,value['pid'],{k:v for k,v in value.items() if k!='pid'})
 # Actual base producer emits a repeated sampler label for every captured instance.
 for label,cmd,first in [('command:du',f'/usr/bin/du -sk {b.RUNTIME}',991000),('command:ps','/bin/ps -e -o pid=,ppid=,rss=',992000)]:
  for offset in range(2):b.record_process_identity(label,first+offset,dict(ppid=990001,pgid=990002,start_ticks=200+offset,cmdline=cmd))
 command_ids={'rustup-install':993001,'rustc-version':993002,'cargo-version':993003,'wrong-cause-red':993004,'wrong-incomplete-report-red':993005,'restored-green':993006}
 core_argv={
  'rustup-install':['/root/.cargo/bin/rustup','toolchain','install','1.77.2-x86_64-unknown-linux-gnu','--profile','minimal','--no-self-update'],
  'rustc-version':[str(b.RUNTIME/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/rustc'),'--version','--verbose'],
  'cargo-version':[str(b.RUNTIME/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/cargo'),'--version','--verbose']}
 test_argv=[str(b.RUNTIME/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/cargo'),'test','--locked','--lib','--features','testing-environ,sys',p.TEST_NAME,'--','--exact','--nocapture','--test-threads=1']
 core_argv.update({n:test_argv for n in ('wrong-cause-red','wrong-incomplete-report-red','restored-green')})
 def fake_command(name,argv,env,*,expected_status=0,cwd=None,**kwargs):
  status=expected_status; b.COMMANDS.append(dict(name=name,argv=argv,expected_status=status,status=status,cwd=str(cwd or source),env_overrides=kwargs.get('env_overrides') or {}))
  b.write_json(b.STAGE/'commands.json',b.COMMANDS)
  ident=dict(ppid=990001,pgid=990002,start_ticks=300+len(b.COMMANDS),cmdline=' '.join(argv))
  b.record_process_identity('command:'+name,command_ids[name],ident)
  return status
 b.run_command=fake_command
 # Make runtime process observations full records, and preserve both launcher records.
 early={'runtime':str(b.RUNTIME),'helper':{'pid':ids['helper']['pid'],**{k:v for k,v in ids['helper'].items() if k!='pid'}},'scoped_supervisor':{'pid':ids['scoped-supervisor']['pid'],**{k:v for k,v in ids['scoped-supervisor'].items() if k!='pid'}},'identity_errors':{},'captured_before_stage_validation_or_external_command':True}
 b.write_json(b.STAGE/'early-runtime-identity.json',early)
 (stage/'outer-evidence').mkdir()
 outer=stage/'outer-evidence'
 (outer/'launcher-identities.tsv').write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n'+'\n'.join(f"{k}\t{v['pid']}\t{v['ppid']}\t{v['pgid']}\t{v['start_ticks']}\t{v['cmdline']}" for k,v in ids.items() if k in ('launcher','run-scoped'))+'\n')
 for name in ('outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status'):(outer/name).write_text('0\n')
 (outer/'runtime-cleanup.tsv').write_text(f'runtime_cleanup_status=0 runtime={b.RUNTIME}\n');(outer/'scope-cleanup.tsv').write_text(f'scope_cleanup_status=0 scope={scope}\n')
 # Call the actual proof consumer functions around an intercepted command runner.
 def run_command_for_case(name,argv,env,*,expected_status=0,**kw):
  status=expected_status;runtime_evidence=b.STAGE
  stdout='setup-failure child_pid=990100 reap=ESRCH owner_retired=true\nsetup-failure fixture child_pid=990101 reap=ESRCH\n'
  if expected_status:
   diagnostic=p.CAUSE if name=='wrong-cause-red' else p.REPORT
   stderr=f"thread '{p.TEST_NAME}' panicked at src/packages/sys/process/unix.rs:42:1:\n{diagnostic}\nnested setup-failure test failed: exit status: 101\n"
  else:
   stderr='';stdout+='test '+p.TEST_NAME+' ... ok\ntest result: ok. 1 passed; 0 failed;\n'
  for ext,value in (('stdout',stdout),('stderr',stderr),('status',str(status))):(runtime_evidence/(name+'.'+ext)).write_text(value)
  b.COMMANDS.append(dict(name=name,argv=argv,status=status,expected_status=status,cwd=str(b.RUNTIME/'source'),env_overrides={}))
  b.write_json(runtime_evidence/'commands.json',b.COMMANDS)
  ident=dict(ppid=990001,pgid=990002,start_ticks=400+len(b.COMMANDS),cmdline=' '.join(argv));b.record_process_identity('command:'+name,command_ids[name],ident)
  return status
 # Toolchain command rows are part of the frozen producer output.
 for name,argv in core_argv.items():
  if name in ('wrong-cause-red','wrong-incomplete-report-red','restored-green'):continue
  command_cwd=b.RUNTIME if name in ('rustup-install','rustc-version','cargo-version') else b.RUNTIME/'source'
  b.COMMANDS.append(dict(name=name,argv=argv,status=0,expected_status=0,cwd=str(command_cwd),env_overrides={}))
  b.record_process_identity('command:'+name,command_ids[name],dict(ppid=990001,pgid=990002,start_ticks=350+len(b.COMMANDS),cmdline=' '.join(argv)))
 b.write_json(b.STAGE/'commands.json',b.COMMANDS);b.run_command=run_command_for_case
 for name,anchor,replacement,diagnostic in [('wrong-cause-red',*overlays[0],p.CAUSE),('wrong-incomplete-report-red',*overlays[1],p.REPORT)]:
  original,_=p.mutate_once(test,anchor,replacement,name);p.run_case(name,pathlib.Path(test_argv[0]),{},expected=101,diagnostic=diagnostic);test.write_bytes(original)
 p.run_case('restored-green',pathlib.Path(test_argv[0]),{},expected=0)
 b.write_json(b.STAGE/'source-inputs.json',dict(revision=p.REV,archive_sha256=ARCHIVE_SHA,test_source_sha256=TEST_SHA,cargo_lock_sha256=b.LOCK_SHA256,test_name=p.TEST_NAME))
 b.write_json(b.STAGE/'tool-versions.json',dict(toolchain='1.77.2-x86_64-unknown-linux-gnu'))
 b.export_destination_is_safe=b.export_destination_is_safe
 p.export()
 assert digest(test)==TEST_SHA and b.CONTROL_RESULTS[-1]['name']=='restored-green'
 # Build the actual complete original export with a harmless local transport stub.
 local_expected=inventory_tree(stage);readback={'stage':str(stage),'scope':str(scope),'files':local_expected['files'],'directories':local_expected['directories']}
 def execute_gate(code,payload):
  local_code=code
  for old,new in [('/root/rhai-linux-post-spawn-pipe-setup-523-20261004',str(stage)),('/var/roothome/rhai-linux-post-spawn-pipe-setup-523-20261004',str(stage.resolve())),('/root/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004',str(scope)),('/var/roothome/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004',str(scope))]:local_code=local_code.replace(old,new)
  argv=['fixture',str(stage),str(scope),str(stage.resolve()),json.dumps(payload,sort_keys=True)]
  original_argv=sys.argv;sys.argv=argv
  original_check=c.subprocess.check_output
  def fake_check(argv,*a,**kw):
   if argv and argv[0]=='/bin/ps':
    hook=process_census_hook
    if hook:hook()
    return ''
   return original_check(argv,*a,**kw)
  c.subprocess.check_output=fake_check
  try:
   if code==c.INVENTORY:return inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
   with contextlib.redirect_stdout(io.StringIO()) as out:
    try:
     debug_env={'__name__':'__main__'};exec(local_code,debug_env)
    except SystemExit:
     raise
   return json.loads(out.getvalue().splitlines()[-1])
  finally:sys.argv=original_argv;c.subprocess.check_output=original_check
 c.STAGE=str(stage);c.SCOPE=str(scope);c.PHYSICAL=str(stage.resolve())
 process_census_hook=None
 c.inventory=lambda:readback
 transport_mutate=False
 def transport(command,**kwargs):
  nonlocal transport_mutate
  if command[:3]==['ssh','workhorse','tar']:
   archived=make_tar(stage)
   if transport_mutate:(stage/'mutated-during-export.txt').write_text('changed after original tar')
   return archived
  return ''
 c.subprocess.check_output=transport
 c.ssh_json=lambda code,payload=None:execute_gate(code,payload)
 destination=t/'accepted-originals'
 called=[];real_rmtree=shutil.rmtree
 def stop_before_delete(path):called.append(path);raise RetirementReached('intercepted at exact deletion call')
 shutil.rmtree=stop_before_delete
 try:
  try:c.collect(destination)
  except RetirementReached:pass
  else:raise AssertionError('safe collector did not stop at intercepted exact retirement boundary')
 finally:shutil.rmtree=real_rmtree
 assert len(called)==1
 assert (destination/'independent-readback.json').is_file() and (destination/'fresh-custody-readback.json').is_file()
 assert (destination.with_name(destination.name+'.originals.tar')).is_file()
 # The retirement command's CUSTODY graph and final snapshot run; intercept only rmtree.
 gate_result=execute_gate(c.CUSTODY,readback);assert gate_result['sampler_instances_validated']==4
 called=[];real_rmtree=shutil.rmtree
 def stop_before_delete(path):called.append(path);raise RetirementReached('intercepted at exact deletion call')
 shutil.rmtree=stop_before_delete
 try:
  try:execute_gate(c.RETIRE,readback)
  except RetirementReached:pass
  else:raise AssertionError('retirement did not reach the exact deletion call after valid gate')
 finally:shutil.rmtree=real_rmtree
 assert len(called)==1 and not stage.is_symlink() and stage.is_dir()
 # A final stage mutation at the process-census boundary must fail before rmtree.
 def mutate_census():(stage/'injected-after-census.txt').write_text('not in exported snapshot')
 called=[];process_census_hook=mutate_census;shutil.rmtree=stop_before_delete
 try:
  try:execute_gate(c.RETIRE,readback)
  except SystemExit as exc:assert 'final retirement inventory differs' in str(exc)
  else:raise AssertionError('final inventory mutation was accepted')
 finally:process_census_hook=None;shutil.rmtree=real_rmtree
 assert not called
 readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 # Full collector refusal cases mutate actual exported artifacts; no retirement call can occur.
 def consumer_refuses(mutator,needle):
  nonlocal readback
  mutator();readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)};ok=False
  observed=''
  try:execute_gate(c.CUSTODY,readback)
  except SystemExit as exc:observed=str(exc);ok=needle in observed
  assert ok,('consumer did not refuse '+needle+'; observed='+observed)
 # Runtime must remain a direct absent child of exact prescribed scope and match exporter.
 original=(stage/'proof-evidence/early-runtime-identity.json').read_bytes()
 runtime_snapshots={name:(stage/'proof-evidence'/name).read_bytes() for name in ('early-runtime-identity.json','export.json','commands.json','package-result.json','process-identities.tsv')}
 def bad_runtime():
  proof=stage/'proof-evidence';obj=json.loads(original);old_runtime=obj['runtime'];new_runtime=str(scope/'nested'/'agent-build-malformed');obj['runtime']=new_runtime;(proof/'early-runtime-identity.json').write_text(json.dumps(obj))
  exported=json.loads((proof/'export.json').read_text());exported['runtime']=new_runtime;(proof/'export.json').write_text(json.dumps(exported))
  cmds=json.loads((proof/'commands.json').read_text())
  for row in cmds:
   row['argv']=[x.replace(old_runtime,new_runtime) if isinstance(x,str) else x for x in row['argv']]
  (proof/'commands.json').write_text(json.dumps(cmds))
  result=json.loads((proof/'package-result.json').read_text())
  for row in result['commands']:
   row['argv']=[x.replace(old_runtime,new_runtime) if isinstance(x,str) else x for x in row['argv']]
  (proof/'package-result.json').write_text(json.dumps(result))
  rows=(proof/'process-identities.tsv').read_text().splitlines();fixed=[rows[0]]
  for line in rows[1:]:
   fields=line.split('\t',5)
   if fields[0].startswith('command:'):fields[5]=fields[5].replace(old_runtime,new_runtime)
   fixed.append('\t'.join(fields))
  (proof/'process-identities.tsv').write_text('\n'.join(fixed)+'\n')
 consumer_refuses(bad_runtime,'runtime is not one absent direct child')
 for name,data in runtime_snapshots.items():(stage/'proof-evidence'/name).write_bytes(data)
 commands_path=stage/'proof-evidence/package-result.json';commands_original=commands_path.read_bytes()
 def bad_version_cwd():
  result=json.loads(commands_original)
  next(row for row in result['commands'] if row['name']=='rustc-version')['cwd']=str(source)
  commands_path.write_text(json.dumps(result))
 consumer_refuses(bad_version_cwd,'command cwd/environment escapes private source/runtime rustc-version')
 commands_path.write_bytes(commands_original);readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 def bad_test_cwd():
  result=json.loads(commands_original)
  next(row for row in result['commands'] if row['name']=='restored-green')['cwd']=str(b.RUNTIME)
  commands_path.write_text(json.dumps(result))
 consumer_refuses(bad_test_cwd,'command cwd/environment escapes private source/runtime restored-green')
 commands_path.write_bytes(commands_original);readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 # Early identity and full TSV must describe the same helper/supervisor PID instance.
 early_path=stage/'proof-evidence/early-runtime-identity.json';early_original=early_path.read_bytes()
 def bad_early_identity():
  obj=json.loads(early_original);obj['helper']['start_ticks']+=1;early_path.write_text(json.dumps(obj))
 consumer_refuses(bad_early_identity,'early helper identity differs')
 early_path.write_bytes(early_original);readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 # Launcher -> run-scoped -> supervisor -> helper parent chain is exact.
 launch_path=stage/'outer-evidence/launcher-identities.tsv';launch_original=launch_path.read_bytes()
 def bad_launcher_parent():
  lines=launch_original.decode().splitlines();fields=lines[2].split('\t');fields[2]='1';lines[2]='\t'.join(fields);launch_path.write_text('\n'.join(lines)+'\n')
 consumer_refuses(bad_launcher_parent,'launcher/helper ancestry mismatch')
 launch_path.write_bytes(launch_original);readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 # Every repeated sampler PID/start instance remains a child of the exact captured helper.
 proc=stage/'proof-evidence/process-identities.tsv';sampler_original=proc.read_bytes()
 def bad_sampler_parent():
  lines=sampler_original.decode().splitlines();changed=[]
  for line in lines:
   fields=line.split('\t',5)
   if fields[0]=='command:du':fields[2]='1'
   changed.append('\t'.join(fields))
  proc.write_text('\n'.join(changed)+'\n')
 consumer_refuses(bad_sampler_parent,'sampler parent identity mismatch')
 proc.write_bytes(sampler_original);readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 # Cargo argv and observed cmdline are bound together to the exact pinned tool invocation.
 orig_commands=(stage/'proof-evidence/commands.json').read_bytes()
 def bad_argv():
  obj=json.loads(orig_commands);obj[-1]['argv'][0]='/tmp/foreign-cargo';(stage/'proof-evidence/commands.json').write_text(json.dumps(obj))
  result=json.loads((stage/'proof-evidence/package-result.json').read_text());result['commands'][-1]['argv'][0]='/tmp/foreign-cargo';(stage/'proof-evidence/package-result.json').write_text(json.dumps(result))
 consumer_refuses(bad_argv,'exact public test contract')
 (stage/'proof-evidence/commands.json').write_bytes(orig_commands)
 (stage/'proof-evidence/package-result.json').write_bytes(runtime_snapshots['package-result.json'])
 # Missing and extra singleton identities fail; distinct sampler instances are all retained.
 proc=stage/'proof-evidence/process-identities.tsv';original_rows=proc.read_text()
 proc.write_text(original_rows+original_rows.splitlines()[-1]+'\n')
 consumer_refuses(lambda:None,'duplicate exact process identity row')
 proc.write_text(original_rows);readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 helper_row=next(x for x in original_rows.splitlines()[1:] if x.startswith('helper\t'))
 parts=helper_row.split('\t');parts[1]='991333';parts[4]='901';proc.write_text(original_rows+'\t'.join(parts)+'\n')
 consumer_refuses(lambda:None,'duplicate singleton process identity label helper')
 proc.write_text(original_rows);readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 # A mutation between initial transport and independent post-export readback must refuse.
 orig_inventory=c.inventory;calls_n=0;transport_mutate=True
 def changing_inventory():
  nonlocal calls_n
  calls_n+=1
  if calls_n==1:return readback
  return inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 c.inventory=changing_inventory
 try:
  c.collect(t/'mutated-stage-export')
 except RuntimeError as exc:assert 'fresh stage inventory changed' in str(exc)
 else:raise AssertionError('mutated stage passed independent collector readback')
 finally:c.inventory=orig_inventory;transport_mutate=False
 readback=inventory_tree(stage)|{'stage':str(stage),'scope':str(scope)}
 # Existing destination/tar files and symlinks are refused before transport, preserving originals.
 for kind in ('tar-file','tar-symlink','destination-file','destination-symlink','destination-directory'):
  dest=t/(kind+'-destination');tarpath=dest.with_name(dest.name+'.originals.tar');sentinel=t/(kind+'-sentinel');sentinel.write_bytes(b'preserved-before-transport')
  if kind=='tar-file':tarpath.write_bytes(b'original tar to preserve')
  elif kind=='tar-symlink':tarpath.symlink_to(sentinel)
  elif kind=='destination-file':dest.write_bytes(b'original destination')
  elif kind=='destination-symlink':dest.symlink_to(sentinel)
  elif kind=='destination-directory':dest.mkdir()
  calls_n=0
  def forbidden_transport(*args,**kwargs):
   nonlocal calls_n
   calls_n+=1;raise AssertionError('transport started before preservation refusal')
  c.subprocess.check_output=forbidden_transport
  try:
   try:c.collect(dest)
   except (FileExistsError,RuntimeError) as exc:assert 'preserve existing' in str(exc) or 'must be an existing real directory' in str(exc)
   else:raise AssertionError('preexisting local original was overwritten')
  finally:c.subprocess.check_output=transport
  assert calls_n==0
  if kind=='tar-file':assert tarpath.read_bytes()==b'original tar to preserve'
  if kind in ('tar-symlink','destination-symlink'):assert (dest if kind=='destination-symlink' else tarpath).is_symlink() and sentinel.read_bytes()==b'preserved-before-transport'
 print('accepted_archive/test/overlay_pins=PASS preextract_scoped_version_cwd=PASS wrong_version_cwd_refused=PASS wrong_test_cwd_refused=PASS actual_run_case_and_exporter=PASS full_CUSTODY=PASS logical_stage_alias_to_physical_supervisor=PASS repeated_sampler_instances=PASS wrong_sampler_parent_refused=PASS exact_ownership_bindings=PASS final_inventory_mutation_refused=PASS exclusive_tar_and_destination_boundaries=PASS retirement_intercepted_before_delete=PASS')
 print('preserved_fixture='+str(t))
if __name__=='__main__':run()
