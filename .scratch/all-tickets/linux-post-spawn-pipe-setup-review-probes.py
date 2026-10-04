import ast,contextlib,hashlib,importlib.util,io,json,pathlib,shutil,sys,tarfile,tempfile,time
R=pathlib.Path('/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery');P=R/'.scratch/all-tickets/linux-post-spawn-pipe-setup-523-evidence'
def load(n,f):
 s=importlib.util.spec_from_file_location(n,f);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
c=load('col',P/'collect-originals.py');b=load('base',P/'check-linux-current-msrv-examples.py');p=load('proof',P/'linux-post-spawn-pipe-setup-proof.py');p.BASE=b
T=pathlib.Path(tempfile.mkdtemp(prefix='pipe-review-',dir='/private/tmp'));stage=T/'stage';stage.mkdir();scope=T/'scope';runtime=T/'unrelated-runtime';runtime.mkdir();b.RUNTIME=runtime;b.SOURCE=runtime/'source';b.SOURCE.mkdir();b.STAGE=runtime/'evidence';b.STAGE.mkdir();b.EVIDENCE=stage/'proof-evidence';b.REVISION=p.REV;b.START=time.monotonic();b.export_destination_is_safe=lambda:True
expected=next(ast.literal_eval(n.value) for n in ast.walk(ast.parse(c.CUSTODY)) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected' for t in n.targets))
for n,h in expected.items():
 src=P/n
 if n=='contract.md':src=R/'.scratch/all-tickets/linux-post-spawn-pipe-setup-contract.md'
 if n.startswith('runner/tools/'):src=pathlib.Path('/Users/hoppworks/projects/agent-skills/tools')/n[len('runner/tools/'):]
 dest=stage/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes());assert hashlib.sha256(dest.read_bytes()).hexdigest()==h
(stage/'input-identities.sha256').write_text(''.join(h+'  '+n+'\n' for n,h in expected.items()))
with tarfile.open(P/'source.tar') as tf:
 for m in tf.getmembers():
  if m.isfile() and (m.name.endswith('src/packages/sys/process/unix.rs') or m.name.endswith('Cargo.toml')):
   # source archive paths are directly repository-relative
   n=m.name.removeprefix('./');dest=b.SOURCE/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tf.extractfile(m).read())
# accommodate archive root prefix, if any
sources=list(b.SOURCE.rglob('unix.rs'));test=sources[0];rel=test.relative_to(b.SOURCE).as_posix();assert rel=='src/packages/sys/process/unix.rs',rel
(b.SOURCE/'Cargo.lock').write_bytes((P/'Cargo.lock.accepted').read_bytes());b.ORIGINAL_EXAMPLES={test:test.read_bytes()};b.ORIGINAL_EXAMPLE_HASHES={rel:p.TEST};b.INJECTED_EXAMPLE_HASHES={};b.COMMANDS=[];b.CONTROL_RESULTS=[];b.SAMPLES=[dict(monotonic_seconds=1,storage_kib=100,rss_kib=200,descendants=0),dict(monotonic_seconds=2,storage_kib=100,rss_kib=200,descendants=0)];b.MAXIMA=dict(storage_kib=100,rss_kib=200,descendants=0);b.INTERRUPTED=None
parent=800002
ids=[('helper',800001,parent),('scoped-supervisor',parent,800003)]
ids += [('command:'+n,800010+i,800001) for i,n in enumerate(['rustup-install','rustc-version','cargo-version','wrong-cause-red','wrong-incomplete-report-red','restored-green'])]
for label,pid,ppid in ids:b.record_process_identity(label,pid,dict(ppid=ppid,pgid=800003,start_ticks=100,cmdline='fixture'))
b.write_json(b.STAGE/'early-runtime-identity.json',dict(runtime=str(runtime),helper=dict(pid=800001),scoped_supervisor=dict(pid=800002),identity_errors={},captured_before_stage_validation_or_external_command=True))
def run(name,argv,env,expected_status=0,**kw):
 out='setup-failure child_pid=900001 reap=ESRCH owner_retired=true\nsetup-failure fixture child_pid=900002 reap=ESRCH\n'
 diag=p.CAUSE if name=='wrong-cause-red' else p.REPORT
 err=f"thread '{p.TEST_NAME}' panicked at src/packages/sys/process/unix.rs:42:1:\n{diag}\nnested setup-failure test failed\n" if expected_status else ''
 if not expected_status:out+='test '+p.TEST_NAME+' ... ok\ntest result: ok. 1 passed; 0 failed;\n'
 for ext,content in [('stdout',out),('stderr',err),('status',str(expected_status))]:(b.STAGE/(name+'.'+ext)).write_text(content)
 b.COMMANDS.append(dict(name=name,argv=argv,status=expected_status,expected_status=expected_status));b.write_json(b.STAGE/'commands.json',b.COMMANDS);return expected_status
b.run_command=run
for label,anchor,replacement,diag in [('wrong-cause-red','message == "injected post-spawn pipe configuration failure"','message == "wrong configure pipe message"',p.CAUSE),('wrong-incomplete-report-red','                    && !report.stdout_complete()','                    && report.stdout_complete()',p.REPORT)]:
 original,_=p.mutate_once(test,anchor,replacement,label);p.run_case(label,runtime/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/cargo',{},expected=101,diagnostic=diag);test.write_bytes(original)
p.run_case('restored-green',runtime/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/cargo',{},expected=0)
b.write_json(b.STAGE/'source-inputs.json',dict(revision=p.REV,archive_sha256=p.ARCHIVE,test_source_sha256=p.TEST,cargo_lock_sha256=p.LOCK,test_name=p.TEST_NAME))
b.write_json(b.STAGE/'tool-versions.json',dict(toolchain='1.77.2-x86_64-unknown-linux-gnu'))
p.export();outer=stage/'outer-evidence';outer.mkdir()
for name in ['outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status']:(outer/name).write_text('0\n')
for name in ['runtime-cleanup.tsv','scope-cleanup.tsv']:(outer/name).write_text('cleanup_status=0\n')
(outer/'launcher-identities.tsv').write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\nlauncher\t800004\t1\t800003\t100\tfixture\nrun-scoped\t800003\t800004\t800003\t100\tfixture\n')
code=c.CUSTODY.replace('/root/rhai-linux-post-spawn-pipe-setup-523-20261004',str(stage)).replace('/var/roothome/rhai-linux-post-spawn-pipe-setup-523-20261004',str(stage)).replace('/root/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004',str(scope)).replace('/var/roothome/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004',str(scope))
import subprocess
real=subprocess.check_output;subprocess.check_output=lambda *a,**kw:''
def gate():
 files={x.relative_to(stage).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(stage.rglob('*')) if x.is_file()};dirs=[x.relative_to(stage).as_posix() for x in sorted(stage.rglob('*')) if x.is_dir()];sys.argv=['fixture',str(stage),str(scope),str(stage),json.dumps(dict(files=files,directories=dirs))]
 try:
  with contextlib.redirect_stdout(io.StringIO()) as out:exec(code,{})
  return 'PASS '+out.getvalue().strip()
 except BaseException as e:return type(e).__name__+': '+str(e)
print('full_export_consumer_original='+gate())
code=code.replace('outer=[i for i,x','outer_receipts=[i for i,x').replace('len(outer)!=1 or inner[0]>=outer[0]','len(outer_receipts)!=1 or inner[0]>=outer_receipts[0]')
print('diagnostic_only_outer_shadow_fixed_live_unrelated_runtime='+gate())
# Emit actual repeated sampler labels using the unchanged producer, export exact bytes.
for i in range(2):b.record_process_identity('command:du',800100+i,dict(ppid=800001,pgid=800003,start_ticks=100+i,cmdline='/usr/bin/du -sk '+str(runtime)))
shutil.copy2(b.STAGE/'process-identities.tsv',b.EVIDENCE/'process-identities.tsv')
print('full_consumer_actual_repeated_du='+gate())
subprocess.check_output=real
print('fixture_directory='+str(T))
# Diagnostic-only continuation to test retirement; never delete anything.
ident=b.EVIDENCE/'process-identities.tsv';ident.write_text('\n'.join(ident.read_text().splitlines()[:-2])+'\n')
retirecode=code.rsplit('\nprint(json.dumps',1)[0]+c.RETIRE[c.RETIRE.index('\nimport shutil'):]
called=[];original_rmtree=shutil.rmtree
shutil.rmtree=lambda target:called.append(str(target))
def mutation_census(*args,**kw):
 (stage/'changed-after-inventory.txt').write_text('new unexported content')
 return ''
subprocess.check_output=mutation_census
files={x.relative_to(stage).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(stage.rglob('*')) if x.is_file()};dirs=[x.relative_to(stage).as_posix() for x in sorted(stage.rglob('*')) if x.is_dir()];sys.argv=['fixture',str(stage),str(scope),str(stage),json.dumps(dict(files=files,directories=dirs))]
try:exec(retirecode,{})
except BaseException as e:print('retire_after_last_census_mutation='+repr(called)+' terminal='+repr(e))
shutil.rmtree=original_rmtree
# Intercept transport; show preservation refusal occurs too late for a pre-existing sole tar.
destination=T/'new-originals';sole_tar=T/'new-originals.originals.tar';sole_tar.write_bytes(b'preexisting preserved original')
c.inventory=lambda:dict(files={},directories=[])
subprocess.check_output=lambda *args,**kw:b'not a tar'
try:c.collect(destination)
except BaseException as e:print('preexisting_tar_after_collect='+repr(sole_tar.read_bytes())+' terminal='+type(e).__name__)
subprocess.check_output=real
