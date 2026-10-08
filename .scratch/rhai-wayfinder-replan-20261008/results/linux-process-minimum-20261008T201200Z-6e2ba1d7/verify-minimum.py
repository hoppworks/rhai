import os, sys, json, time, hashlib, subprocess, urllib.request, tarfile, traceback
from pathlib import Path
from datetime import datetime, timezone
E=Path(sys.argv[1]).resolve(); R=Path(os.environ['AGENT_RUNTIME_DIR']).resolve(); REPO=Path('/root/projects/rhai-wayfinder-20261008')
selection=json.loads((E/'selection.json').read_text());results=[];commands=[];samples=[]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def record():
 (E/'result.json').write_text(json.dumps({'started_utc':started,'runtime':str(R),'source_revision':selection['revision'],'commands':commands,'GREEN':results,'samples':samples,'scope':'four new Linux1.77.2 baseline selectors only; original RED reused; combined review pending'},indent=2)+'\n')
def sample():
 members=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   st=(p/'stat').read_text();parts=st[st.rindex(')')+2:].split()
   if int(parts[2])==os.getpgrp():members.append({'pid':int(p.name),'start':parts[19],'rss_bytes':int(parts[21])*os.sysconf('SC_PAGE_SIZE')})
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 size=int(subprocess.check_output(['du','-sb',str(R)]).split()[0]);rss=sum(x['rss_bytes'] for x in members)
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
 assert REPO.is_dir() and subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO).decode().strip()==selection['revision']
 assert sha(Path('/home/Daniel/projects/agent-skills/tools/run_scoped.py'))==selection['runner_sha256']
 assert not any(k.startswith('RHAI_SYS_PROCESS') for k in os.environ),'undeclared fixture environment'
 (E/'native-environment.json').write_text(json.dumps({'uname':list(os.uname()),'python':sys.version,'uid':os.getuid(),'runtime_identity':{'device':R.stat().st_dev,'inode':R.stat().st_ino},'limits':{'wall_seconds':1200,'storage_bytes':8*1024**3,'owned_rss_bytes':8*1024**3,'owned_processes':32,'cargo_jobs':2}},indent=2)+'\n')
 downloads=R/'downloads';downloads.mkdir();tc=R/'toolchain';tc.mkdir();src=R/'source';src.mkdir()
 pins={'rustc':'7fa3779e7693825728e99639c9b34b9475bfc0dc4a31f730d1f2fbb6764e183c','cargo':'b57b050ee48123e05021aff43f84da4b10d1d777dd350dd54fbc14448cd3d2d8','rust-std':'23119121fae4b7163b9c2ff5cbaad03d08f80d55da011a025d6b17d27489df7f'}
 distribution=[]
 for component,want in pins.items():
  name=component+'-1.77.2-x86_64-unknown-linux-gnu';url='https://static.rust-lang.org/dist/'+name+'.tar.xz';archive=downloads/(name+'.tar.xz')
  with urllib.request.urlopen(url+'.sha256',timeout=30) as response:official=response.read(512)
  assert official.decode().split()[0]==want
  (E/(component+'.official-sha256')).write_bytes(official)
  count=0
  with urllib.request.urlopen(url,timeout=60) as response,archive.open('xb') as f:
   while b:=response.read(1048576):
    count+=len(b);assert count<256*1024**2;f.write(b)
  assert sha(archive)==want
  with tarfile.open(archive) as t:t.extractall(downloads,filter='data')
  installer=downloads/name/'install.sh';text=installer.read_text();assert '--disable-ldconfig' in text and '--prefix' in text
  assert bounded(['bash',str(installer),'--prefix='+str(tc),'--disable-ldconfig'],'install-'+component,120,cwd=downloads/name)==0
  distribution.append({'component':component,'url':url,'bytes':count,'sha256':want,'private_prefix':str(tc)})
  (E/'portable-toolchain.json').write_text(json.dumps(distribution,indent=2)+'\n')
 env=dict(os.environ)
 for key in ('RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTFLAGS','RUSTDOCFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTUP_TOOLCHAIN'):env.pop(key,None)
 env.update(RUSTC=str(tc/'bin/rustc'),RUSTDOC=str(tc/'bin/rustdoc'),PATH=str(tc/'bin')+':'+env['PATH'],CARGO_HOME=str(R/'cargo-home'),CARGO_TARGET_DIR=str(R/'target'),CARGO_BUILD_JOBS='2',PYTHONDONTWRITEBYTECODE='1')
 cargo=tc/'bin/cargo'
 for binary in ('cargo','rustc'):
  assert bounded([str(tc/'bin'/binary),'--version'],binary+'-version',15,cwd=REPO,env=env)==0
  assert '1.77.2' in (E/(binary+'-version.stdout')).read_text()
 archive=R/'source.tar';
 with archive.open('xb') as f:subprocess.run(['git','archive','--format=tar',selection['revision']],cwd=REPO,stdout=f,check=True,timeout=90)
 archive_sha=sha(archive)
 with tarfile.open(archive) as t:t.extractall(src,filter='data')
 lock=REPO/'.scratch/rhai-wayfinder-replan-20261008/results/f32-process-20261008T162316Z-515571ed/Cargo.lock.accepted';assert sha(lock)==selection['lock_sha256'];(src/'Cargo.lock').write_bytes(lock.read_bytes())
 input_names=['Cargo.toml','build.rs','src/packages/sys/process.rs','src/packages/sys/process/unix.rs','tests/sys_process.rs','tests/fixtures/sys_process_shared_child_contract.rs','tests/sys_support/mod.rs']
 (E/'source-inputs.json').write_text(json.dumps({'revision':selection['revision'],'archive_sha256':archive_sha,'lock_sha256':sha(src/'Cargo.lock'),'files':{n:sha(src/n) for n in input_names},'foreign_fixture_not_overlaid':True},indent=2)+'\n')
 assert sha(src/'tests/fixtures/sys_process_shared_child_contract.rs')=='1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217'
 assert bounded([str(cargo),'test','--locked','--features','testing-environ,sys','--test','sys_process','--no-run','--message-format=json'],'compile',480,cwd=src,env=env)==0
 artifacts=[]
 for line in (E/'compile.stdout').read_text().splitlines():
  try:j=json.loads(line)
  except ValueError:continue
  if j.get('reason')=='compiler-artifact' and j['target']['name']=='sys_process' and j.get('executable'):artifacts.append(Path(j['executable']))
 assert len(artifacts)==1,artifacts;exe=artifacts[0];artifact_sha=sha(exe)
 assert bounded([str(exe),'--list'],'test-list',30,cwd=src,env=env)==0
 inventory=set((E/'test-list.stdout').read_text().splitlines())
 for row in selection['tests']:
  name=row['test'];assert name+': test' in inventory
  code=bounded([str(exe),name,'--exact','--nocapture','--test-threads=1'],'green-'+row['historical_key'],30,cwd=src,env=env)
  stdout=(E/('green-'+row['historical_key']+'.stdout')).read_text()
  assert code==0 and 'test result: ok. 1 passed; 0 failed;' in stdout and name in stdout,(name,code)
  results.append({'test':name,'exit':code,'artifact_sha256':artifact_sha,'test_function_sha256':row['test_function_sha256'],'independent_oracle':'public Engine plus exact child-written record/bytes/absence and direct child ESRCH checked in unchanged test','review_pending':True});record()
 assert sha(src/'Cargo.lock')==selection['lock_sha256']
 sample();(E/'completed.status').write_text('0\n');record()
 print(json.dumps({'GREEN':len(results),'elapsed':round(time.monotonic()-begin,3),'product_code_changed':False,'combined_review_pending':True}),flush=True)
except BaseException as exc:
 (E/'failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc),'elapsed':round(time.monotonic()-begin,3),'GREEN_completed':len(results),'classification':'inspect exact command/status; no automatic product RED or full rerun'},indent=2)+'\n');record();traceback.print_exc();raise
