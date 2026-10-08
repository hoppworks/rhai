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
 (src/'Cargo.lock').write_bytes((E/'Cargo.lock.windows-wip').read_bytes())
 def overlay(hashes):
  for f in selection['owned_files']:
   assert sha(REPO/f)==hashes[f],('source changed',f)
   (src/f).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/f,src/f)
  assert sha(src/'src/packages/sys/process/unix.rs')=='55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713'
  assert sha(src/'tests/fixtures/sys_process_shared_child_contract.rs')=='1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217'
  assert sha(src/'Cargo.lock')==selection['new_lock_sha256']
 hashes=selection['sha256'];overlay(hashes)
 result={'rows':[], 'accepted':False, 'runtime':str(R)}
 evidence=E;source=src;digest=sha
 import errno,re
 def command(tag,argv,env=None,timeout=1000):
  code=bounded(argv,tag,timeout,cwd=src,env=env)
  (E/(tag+'.command.json')).write_text(json.dumps(commands[-1],indent=2)+'\n')
  return code
 def example_phase(profile, executable, expected):
     tag = profile + ('-red' if expected == 8 else '-green')
     env = dict(os.environ, RHAI_SYS_PROCESS_EXAMPLE_EXPECTED_EXIT=str(expected))
     rc = command(tag, [str(executable)], env=env, timeout=30)
     out = (evidence / (tag + '.stdout')).read_text()
     err = (evidence / (tag + '.stderr')).read_text()
     if 'bounded cleanup did not observe a terminal child result' in err:
         raise RuntimeError(tag + ': example reported incomplete cleanup')
     required = [
         'Host read back run child record: "run child wrote its record\\n"',
         'Host read back spawned child record: "spawn child observed release\\n"',
         'Spawn wait was pending, then both cloned handles returned the same result.',
     ]
     if not all(marker in out for marker in required):
         raise RuntimeError(tag + ': missing independent host readback or pending/clone assertion')
     pids = re.findall(r'Host read back spawned child record: .*\(pid (\d+)\)', out)
     if len(pids) != 1:
         raise RuntimeError(tag + ': expected one observed spawn fixture PID')
     pid = int(pids[0])
     try:
         os.kill(pid, 0)
     except OSError as error:
         if error.errno != errno.ESRCH:
             raise
     else:
         raise RuntimeError(tag + ': spawned PID still present after terminal waits')
     if expected == 8:
         if rc != 101 or 'RED control changes only the expected exit' not in err or not re.search(r'left:\s*7\s+right:\s*8', err):
             raise RuntimeError(tag + ': not the intended wrong-exit assertion RED')
     elif rc != 0:
         raise RuntimeError(tag + ': restored expectation did not pass')
     row = {'profile': profile, 'expected_exit': expected, 'exit': rc, 'spawn_pid': pid,
            'spawn_post_exit_probe': 'ESRCH', 'binary_sha256': digest(executable),
            'example_sha256': digest(source / 'examples/sys_process.rs')}
     result['rows'].append(row)
     (evidence / 'phases.json').write_text(json.dumps(result, indent=2) + '\n')

 (E/'native-environment.json').write_text(json.dumps({'os':subprocess.check_output(['uname','-srv'],text=True).strip(),'architecture':subprocess.check_output(['uname','-m'],text=True).strip(),'rustc':(E/'rustc-1.77-version.stdout').read_text().strip(),'cargo':(E/'cargo-1.77-version.stdout').read_text().strip(),'features':['sys,no_float','sys,sync,only_i32,no_float'],'lock_sha256':sha(src/'Cargo.lock'),'cwd':str(src),'runtime':str(R)},indent=2)+'\n')
 for profile,features in [('no-float','sys,no_float'),('sync-i32-no-float','sys,sync,only_i32,no_float')]:
  tag=profile+'-build'
  assert command(tag,[str(cargo),'build','--locked','--features',features,'--example','sys_process','--message-format=json'],env=ev,timeout=480)==0,'build failed before native assertions'
  artifacts=[]
  for line in (E/(tag+'.stdout')).read_text().splitlines():
   message=json.loads(line)
   if message.get('reason')=='compiler-artifact' and message.get('target',{}).get('name')=='sys_process' and 'example' in message.get('target',{}).get('kind',[]) and message.get('executable'):artifacts.append(Path(message['executable']))
  assert len(artifacts)==1 and artifacts[0].is_file(),'ambiguous/missing native example executable'
  example_phase(profile,artifacts[0],8)
  example_phase(profile,artifacts[0],7)
  assert sha(src/'Cargo.lock')==selection['new_lock_sha256']
  assert sha(src/'examples/sys_process.rs')==hashes['examples/sys_process.rs']
 result['accepted']=False;result['execution_complete']=True;result['scope']='Native Linux minimum integer example rows; independent combined review still required'
 (E/'phases.json').write_text(json.dumps(result,indent=2)+'\n')
 sample();(E/'completed.status').write_text('0\n');record();print(json.dumps({'native_linux_rows':result['rows'],'elapsed':round(time.monotonic()-begin,3),'review_pending':True}),flush=True)
except BaseException as exc:
 (E/'failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc),'elapsed':round(time.monotonic()-begin,3),'classification':'inspect original command/assertion before classifying; no automatic retry'},indent=2)+'\n');record();traceback.print_exc();raise
