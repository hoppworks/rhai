import os,sys,json,time,hashlib,subprocess,urllib.request,tarfile,traceback,shutil
from pathlib import Path
from datetime import datetime, timezone
E=Path(sys.argv[1]).resolve(); R=Path(os.environ['AGENT_RUNTIME_DIR']).resolve(); REPO=Path('/root/projects/rhai-wayfinder-20261008')
selection=json.loads((E/'selection.json').read_text());commands=[];samples=[]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def record():
 (E/'result.json').write_text(json.dumps({'started_utc':started,'runtime':str(R),'source_revision':selection['revision'],'commands':commands,'samples':samples,'scope':selection['scope']},indent=2)+'\n')
def sample():
 members=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   st=(p/'stat').read_text();parts=st[st.rindex(')')+2:].split()
   if int(parts[2])==os.getpgrp():members.append({'pid':int(p.name),'start':parts[19],'rss_bytes':int(parts[21])*os.sysconf('SC_PAGE_SIZE')})
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 measurement=subprocess.run(['du','-sb',str(R)],capture_output=True,env=dict(os.environ,LC_ALL='C'))
 if measurement.returncode:
  lines=measurement.stderr.decode('utf8',errors='strict').splitlines()
  assert measurement.returncode==1 and lines and all(line.startswith("du: cannot access '") and str(R)+'/' in line and line.endswith("': No such file or directory") for line in lines),('unexpected storage measurement failure',measurement.returncode,lines)
  # Cargo atomically removes transient rmeta/temp files while this owned-only
  # sampler walks them. Preserve the race, numeric total and declared hard bounds.
  with (E/'storage-sampling-races.jsonl').open('a') as f:f.write(json.dumps({'elapsed':round(time.monotonic()-begin,3),'stdout':measurement.stdout.decode(),'stderr':measurement.stderr.decode()})+'\n')
 total=measurement.stdout.decode().splitlines();assert len(total)==1 and total[0].split('\t')[-1]==str(R)
 size=int(total[0].split()[0]);rss=sum(x['rss_bytes'] for x in members)
 item={'elapsed':round(time.monotonic()-begin,3),'storage_bytes':size,'rss_bytes':rss,'processes':members};samples.append(item)
 assert size<8*1024**3,('private storage cap',size)
 assert rss<8*1024**3,('owned RSS cap',rss)
 assert len(members)<=32,('owned process cap',len(members))
 record()
def bounded(argv,tag,timeout,cwd=None,env=None):
 out=E/(tag+'.stdout');err=E/(tag+'.stderr');t=time.monotonic()
 with out.open('wb') as o,err.open('wb') as er:
  p=subprocess.Popen(argv,cwd=cwd,env=env,stdout=o,stderr=er)
  commands.append({'tag':tag,'argv':[str(x) for x in argv],'cwd':str(cwd or REPO),'pid':p.pid,'timeout_seconds':timeout})
  last=0
  while p.poll() is None:
   assert time.monotonic()-t<timeout,('command deadline',tag)
   assert out.stat().st_size<4*1024**2 and err.stat().st_size<4*1024**2,('output cap',tag)
   if time.monotonic()-last>=2:sample();last=time.monotonic()
   time.sleep(.1)
  code=p.wait()
 (E/(tag+'.status')).write_text(str(code)+'\n');commands[-1].update(exit=code,elapsed=round(time.monotonic()-t,3),stdout_sha256=sha(out),stderr_sha256=sha(err));record();return code
started=datetime.now(timezone.utc).isoformat();begin=time.monotonic()
try:
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO).decode().strip()==selection['revision']
 assert sha(Path('/home/Daniel/projects/agent-skills/tools/run_scoped.py'))==selection['runner_sha256']
 assert not any(k.startswith('RHAI_SYS_PROCESS') for k in os.environ)
 downloads=R/'downloads';downloads.mkdir();src=R/'source';src.mkdir()
 (E/'runtime-identity.json').write_text(json.dumps({'path':str(R),'device':R.stat().st_dev,'inode':R.stat().st_ino,'uid':R.stat().st_uid,'limits':selection['private_limits']},indent=2)+'\n')
 def toolchain(version,windows=False):
  tc=R/('toolchain-'+version);tc.mkdir(exist_ok=True)
  items=[('rustc','x86_64-unknown-linux-gnu'),('cargo','x86_64-unknown-linux-gnu'),('rust-std','x86_64-unknown-linux-gnu')]
  if windows:items.append(('rust-std','x86_64-pc-windows-msvc'))
  distribution=[]
  for component,target in items:
   name=component+'-'+version+'-'+target;url='https://static.rust-lang.org/dist/'+name+'.tar.xz'
   with urllib.request.urlopen(url+'.sha256',timeout=30) as response:official=response.read(512)
   want=official.decode().split()[0];assert len(want)==64
   tag=version+'-'+component+'-'+target
   (E/(tag+'.official-sha256')).write_bytes(official)
   old=REPO/'.scratch/rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/rust-1.77.2-official-input'/(name+'.tar.xz')
   archive=downloads/(name+'.tar.xz')
   if old.exists():
    assert sha(old)==want;shutil.copyfile(old,archive)
   else:
    count=0
    with urllib.request.urlopen(url,timeout=60) as response,archive.open('xb') as f:
     while b:=response.read(1048576):
      count+=len(b);assert count<256*1024**2;f.write(b)
   assert sha(archive)==want
   with tarfile.open(archive) as t:t.extractall(downloads,filter='data')
   installer=downloads/name/'install.sh'
   assert bounded(['bash',str(installer),'--help'],'help-'+tag,15,cwd=downloads/name)==0
   h=(E/('help-'+tag+'.stdout')).read_text();assert '--prefix=' in h and '--disable-ldconfig' in h
   assert bounded(['bash',str(installer),'--prefix='+str(tc),'--disable-ldconfig'],'install-'+tag,120,cwd=downloads/name)==0
   distribution.append({'component':component,'version':version,'target':target,'url':url,'sha256':want,'bytes':archive.stat().st_size,'reused_existing_verified_archive':old.exists(),'prefix':str(tc)})
   (E/('portable-'+version+'.json')).write_text(json.dumps(distribution,indent=2)+'\n')
   shutil.rmtree(downloads/name);archive.unlink();sample()
  return tc
 tc=toolchain('1.77.2',False)
 env=dict(os.environ)
 for key in ('RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTFLAGS','RUSTDOCFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTUP_TOOLCHAIN'):env.pop(key,None)
 def buildenv(tc):
  e=dict(env);e.update(RUSTC=str(tc/'bin/rustc'),RUSTDOC=str(tc/'bin/rustdoc'),PATH=str(tc/'bin')+':'+e['PATH'],CARGO_HOME=str(R/'cargo-home'),CARGO_TARGET_DIR=str(R/'target'),CARGO_BUILD_JOBS='2',PYTHONDONTWRITEBYTECODE='1');return e
 cargo=tc/'bin/cargo';ev=buildenv(tc)
 for binary in ('cargo','rustc'):assert bounded([str(tc/'bin'/binary),'--version'],binary+'-1.77-version',15,cwd=REPO,env=ev)==0
 archive=R/'source.tar'
 with archive.open('xb') as f:subprocess.run(['git','archive','--format=tar',selection['revision']],cwd=REPO,stdout=f,check=True,timeout=90)
 (E/'archive-sha256').write_text(sha(archive)+'\n')
 with tarfile.open(archive) as t:t.extractall(src,filter='data')
 archive.unlink()

 (src/'Cargo.lock').write_bytes((E/'Cargo.lock.accepted').read_bytes())
 assert sha(src/'Cargo.lock')==selection['lock_sha256']
 for f,want in selection['source_sha256'].items():assert sha(src/f)==want,('frozen committed source mismatch',f)
 assert sha(src/'src/packages/sys/process/unix.rs')=='55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713'
 assert sha(src/'tests/fixtures/sys_process_shared_child_contract.rs')=='1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217'
 (E/'source-inputs.json').write_text(json.dumps({'revision':selection['revision'],'lock_sha256':sha(src/'Cargo.lock'),'files':selection['source_sha256'],'dirty_or_foreign_source_overlaid':False},indent=2)+'\n')
 for binary in ('cargo','rustc'):
  assert '1.77.2' in (E/(binary+'-1.77-version.stdout')).read_text(),('wrong toolchain',binary)
 (E/'native-environment.json').write_text(json.dumps({'uname':list(os.uname()),'rustc':(E/'rustc-1.77-version.stdout').read_text().strip(),'cargo':(E/'cargo-1.77-version.stdout').read_text().strip(),'features':selection['features'],'cwd':str(src),'uid':os.getuid()},indent=2)+'\n')
 assert bounded([str(cargo),'test','--locked','--features',selection['features'],'--test','sys_process','--no-run','--message-format=json'],'build',480,cwd=src,env=ev)==0,'Compilation failed before product assertions'
 artifacts=[]
 for line in (E/'build.stdout').read_text().splitlines():
  message=json.loads(line)
  if message.get('reason')=='compiler-artifact' and message.get('target',{}).get('name')=='sys_process' and message.get('executable'):artifacts.append(Path(message['executable']))
 assert len(artifacts)==1 and artifacts[0].is_file(),'missing/ambiguous exact test executable'
 exe=artifacts[0];exesha=sha(exe)
 assert bounded([str(exe),'--list'],'test-list',15,cwd=src,env=ev)==0
 inventory=set((E/'test-list.stdout').read_text().splitlines())
 name=selection['test'];assert name+': test' in inventory
 code=bounded([str(exe),name,'--exact','--nocapture','--test-threads=1'],'green',75,cwd=src,env=ev)
 out=(E/'green.stdout').read_text();err=(E/'green.stderr').read_text();combined=out+'\n'+err
 assert code==0 and 'test result: ok. 1 passed; 0 failed;' in out and name in out,(code,'selected parent did not pass')
 assert 'repeated_public_run_calls_keep_fd_count_stable_isolated ... ok' in combined,'actual census child did not pass'
 import re
 matches=re.findall(r'x30_process_run_fd_stability iterations=200 baseline_tasks=(\d+) baseline_fds=(\d+) baseline_cleanup_workers=(\d+) after_tasks=(\d+) after_fds=(\d+) after_cleanup_workers=(\d+)',combined)
 assert len(matches)==1,'Missing or ambiguous independent descriptor readback'
 baseline_tasks,baseline_fds,baseline_cleanup,after_tasks,after_fds,after_cleanup=map(int,matches[0])
 assert baseline_fds==after_fds and baseline_tasks==after_tasks and baseline_cleanup==after_cleanup,'descriptor/task census changed'
 assert sha(src/'Cargo.lock')==selection['lock_sha256']
 (E/'phases.json').write_text(json.dumps({'execution_complete':True,'accepted':False,'test':name,'exit':code,'executable_sha256':exesha,'baseline_tasks':baseline_tasks,'baseline_fds':baseline_fds,'baseline_cleanup_workers':baseline_cleanup,'after_tasks':after_tasks,'after_fds':after_fds,'after_cleanup_workers':after_cleanup,'iterations':200,'reused_RED':'historical/mutant-red.{status,stdout,stderr}; exact oracle/helpers unchanged; independent combined review pending','scope':selection['scope']},indent=2)+'\n')
 sample();(E/'completed.status').write_text('0\n');record()
 print(json.dumps({'test':name,'exit':code,'iterations':200,'elapsed':round(time.monotonic()-begin,3),'review_pending':True}),flush=True)
except BaseException as exc:
 (E/'failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc),'elapsed':round(time.monotonic()-begin,3),'classification':'inspect original command and assertion; no automatic retry or product RED'},indent=2)+'\n');record();traceback.print_exc();raise
