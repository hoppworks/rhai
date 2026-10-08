import hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
e=Path(sys.argv[1]); i=json.loads((e/'inputs.json').read_text()); runtime=Path(os.environ['AGENT_RUNTIME_DIR']); source=runtime/'source'; source.mkdir(); h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
os.environ.update(CARGO_HOME=str(runtime/'cargo-home'),CARGO_TARGET_DIR=str(runtime/'target'),CARGO_BUILD_JOBS='2',PYTHONDONTWRITEBYTECODE='1')
for key in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER']:os.environ.pop(key,None)
if 'toolchain_dir' in i:
 t=Path(i['toolchain_dir']);cargo=[str(t/'cargo')];rustc=[str(t/'rustc')];os.environ.update(RUSTC=str(t/'rustc'),RUSTDOC=str(t/'rustdoc'))
else:cargo=['cargo','+'+i['toolchain']];rustc=['rustc','+'+i['toolchain']]
r={'execution_passed':False,'runtime':str(runtime),'runtime_identity':{'device':runtime.stat().st_dev,'inode':runtime.stat().st_ino},'environment':{'os':platform.platform(),'machine':platform.machine()},'runs':[]}
def save():(e/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def cmd(tag,argv,timeout=60):
 started=time.monotonic()
 with (e/(tag+'.stdout')).open('wb') as out,(e/(tag+'.stderr')).open('wb') as err:p=subprocess.run(argv,cwd=source,stdout=out,stderr=err,timeout=timeout)
 row={'argv':argv,'cwd':str(source),'exit':p.returncode,'seconds':time.monotonic()-started};(e/(tag+'.command.json')).write_text(json.dumps(row,indent=2)+'\n');return row
try:
 assert h(Path(i['archive']))==i['archive_sha256'] and h(e/'Cargo.lock.accepted')==i['lock_sha256'] and h(e/'owned.patch')==i['patch_sha256']
 subprocess.run(['tar','-xf',i['archive'],'-C',str(source)],check=True);(source/'Cargo.lock').write_bytes((e/'Cargo.lock.accepted').read_bytes());subprocess.run(['git','apply','--check',str(e/'owned.patch')],cwd=source,check=True);subprocess.run(['git','apply',str(e/'owned.patch')],cwd=source,check=True)
 r['environment']['rustc']=subprocess.check_output(rustc+['--version'],text=True).strip();r['environment']['cargo']=subprocess.check_output(cargo+['--version'],text=True).strip();assert r['environment']['rustc'].startswith('rustc 1.77.2 ')
 for label in ['red','green']:
  overlay=e/('sys_process.'+label+'.rs');assert h(overlay)==i[label+'_sha256'];(source/'tests/sys_process.rs').write_bytes(overlay.read_bytes())
  build=cmd(label+'-build',cargo+['test','--locked','--features',i['features'],'--test','sys_process','--no-run','--message-format=json'],600);assert build['exit']==0,'pre-assertion compilation failure'
  exe=None
  for line in (e/(label+'-build.stdout')).read_text().splitlines():
   item=json.loads(line)
   if item.get('reason')=='compiler-artifact' and item.get('executable') and item['target']['name']=='sys_process':exe=Path(item['executable'])
  assert exe is not None and exe.is_file();assert cmd(label+'-list',[str(exe),'--list'])['exit']==0
  assert (e/(label+'-list.stdout')).read_text().splitlines().count(i['selector']+': test')==1,'missing/ambiguous exact selector'
  test=cmd(label,[str(exe),i['selector'],'--exact','--nocapture','--test-threads=1'],30);text=(e/(label+'.stdout')).read_text()+'\n'+(e/(label+'.stderr')).read_text()
  if label=='red':assert test['exit']==101 and '1 failed' in text and 'finite fractional f32 timeout preserves normal completion' in text and 'left: 0' in text and 'right: 9' in text,'control did not reach exact assertion'
  else:assert test['exit']==0 and '1 passed' in text and '0 ignored' in text and 'invalid_durations_no_child=5' in text and 'children_reaped=true' in text,'real public contract failed'
  assert h(source/'Cargo.lock')==i['lock_sha256'];r['runs'].append(dict(label=label,executable_sha256=h(exe),source_sha256=h(overlay),**test));save();print(label,test['exit'],flush=True)
 r['bound_sources']={str(p):h(source/p) for p in map(Path,['src/packages/sys/process/unix.rs','src/packages/sys/process.rs','src/packages/sys/config.rs','src/packages/sys/mod.rs','tests/sys_process.rs','tests/fixtures/sys_process_shared_child_contract.rs','Cargo.toml','Cargo.lock','build.rs'])};r['runtime_bytes']=int(subprocess.check_output(['du','-sk',str(runtime)],text=True).split()[0])*1024;assert r['runtime_bytes']<8*1024**3;r['execution_passed']=True
except BaseException as error:r['failure']=repr(error);raise
finally:save()
