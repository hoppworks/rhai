"""One owned Linux minimum-toolchain filesystem acceptance; export before cleanup."""
from pathlib import Path,PurePosixPath
import os,sys,json,hashlib,shutil,subprocess,time,selectors,tarfile,traceback,re
base=Path(__file__).resolve().parent;b=json.loads((base/'binding.json').read_text());out=base/'evidence';out.mkdir();runtime=Path(os.environ['AGENT_RUNTIME_DIR']);source=runtime/'source';source.mkdir();home=runtime/'cargo-home';target=runtime/'target';home.mkdir();target.mkdir();sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(base/'source.tar')==b['archive_sha256'] and sha(base/'Cargo.lock')==b['source_lock_sha256']
assert shutil.disk_usage(runtime).free>10*1024**3,'Insufficient measured capacity for declared estimate'
record={'base':b['base'],'nonce':b['nonce'],'runtime':str(runtime),'source':str(source),'accepted':False,'commands':[],'counts':dict(b.get('prior_consumption',{'cargo_builds':0,'red_tests':0,'green_targets':0})),'counts_scope':'cumulative_package_including_preparation01_and_preparation02','prior_consumption':b.get('prior_consumption',{}),'environment':{},'failure':''}
(original_env,original_cwd)=(dict(os.environ),os.getcwd())
env=dict(os.environ)
for key in ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_TARGET','RUSTDOCFLAGS','RUSTC_BOOTSTRAP','RHAI_AHASH_SEED','RHAI_HASHING_SEED'):env.pop(key,None)
toolchain=Path('/var/roothome/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin')
env.update(CARGO_HOME=str(home),CARGO_TARGET_DIR=str(target),CARGO_BUILD_JOBS='2',CARGO_TERM_COLOR='never',CARGO_NET_OFFLINE='false',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',RUSTC=str(toolchain/'rustc'),RUSTDOC=str(toolchain/'rustdoc'),PATH=str(toolchain)+os.pathsep+env['PATH'],PYTHONDONTWRITEBYTECODE='1')
def command(argv,label,seconds):
 started=time.monotonic();stdout=out/(label+'.stdout');stderr=out/(label+'.stderr');process=None;sel=selectors.DefaultSelector();writers=[];item={'argv':argv,'cwd':str(source),'label':label,'bound_seconds':seconds,'exit':None,'elapsed_seconds':None}
 record['commands'].append(item)
 try:
  process=subprocess.Popen(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  for stream,file in ((process.stdout,stdout),(process.stderr,stderr)):
   writer=file.open('wb');writers.append(writer);os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,{'writer':writer,'bytes':0})
  while sel.get_map():
   if time.monotonic()-started>seconds:raise TimeoutError(label+' exceeded finite command bound')
   for key,_ in sel.select(.1):
    try:data=os.read(key.fileobj.fileno(),65536)
    except BlockingIOError:continue
    if not data:sel.unregister(key.fileobj);key.fileobj.close();continue
    state=key.data;remaining=4*1024**2-state['bytes'];state['writer'].write(data[:remaining]);state['bytes']+=len(data)
    if state['bytes']>4*1024**2:raise RuntimeError(label+' exceeded bounded original log cap')
  item['exit']=process.wait(timeout=max(1,seconds-(time.monotonic()-started)))
 finally:
  if process is not None and process.poll()is None:
   process.kill();process.wait(timeout=10)
  sel.close()
  for writer in writers:writer.close()
  item['elapsed_seconds']=time.monotonic()-started
  (out/'commands.json').write_text(json.dumps(record['commands'],indent=2)+'\n')
 return item,stdout.read_bytes(),stderr.read_bytes()
def build(features,label,targets):
 record['counts']['cargo_builds']+=1
 args=[str(toolchain/'cargo'),'test','--locked','--features',features,'--no-run','--message-format=json']
 for name in targets:args+=['--test',name]
 item,stdout,stderr=command(args,label,450);assert item['exit']==0,(label,stderr[-4000:])
 artifacts={};fresh=[]
 for line in stdout.splitlines():
  if not line:continue
  message=json.loads(line)
  if message.get('reason')=='compiler-artifact':
   if message['target']['name']=='rhai' and 'lib'in message['target']['kind']:fresh.append({'kind':'rhai-lib','fresh':message['fresh'],'filenames':message['filenames']})
   if 'test'in message['target']['kind'] and message.get('executable'):
    path=Path(message['executable']);assert path.is_file()and str(path.resolve()).startswith(str(target.resolve())+os.sep)
    artifacts[message['target']['name']]={'path':str(path),'sha256':sha(path),'fresh':message['fresh']}
 assert set(artifacts)==set(targets),(label,artifacts)
 (out/(label+'-artifacts.json')).write_text(json.dumps({'features':features,'executables':artifacts,'library_artifacts':fresh},indent=2)+'\n')
 return artifacts
try:
 with tarfile.open(base/'source.tar')as archive:
  for member in archive.getmembers():assert not PurePosixPath(member.name).is_absolute()and '..'not in PurePosixPath(member.name).parts and(member.isfile()or member.isdir())
  archive.extractall(source,filter='data')
 shutil.copyfile(base/'Cargo.lock',source/'Cargo.lock')
 for name,h in b['source_pins'].items():assert sha(source/name)==h,name
 record['source_pins']=b['source_pins'];record['lock_sha256']=sha(source/'Cargo.lock')
 # Demonstrate actual byte-name support on the exact fixture filesystem first.
 probe=os.fsencode(runtime/'tmp')+b'/rhai-fs-prerequisite-\xff';os.mkdir(probe);file=probe+b'/bad\xff.txt'
 with open(file,'wb')as stream:stream.write(b'independent-byte-name-truth')
 assert b'bad\xff.txt'in os.listdir(probe)
 with open(file,'rb')as stream:assert stream.read()==b'independent-byte-name-truth'
 os.unlink(file);os.rmdir(probe);record['non_utf8_prerequisite']=True
 for label,args in (('rustc-version',[str(toolchain/'rustc'),'--version','--verbose']),('cargo-version',[str(toolchain/'cargo'),'--version']),('os',['uname','-a']),('capacity',['df','-B1',str(runtime)]),('memory',['free','-b']),('filesystem',['findmnt','-T',str(runtime),'-no','FSTYPE,SOURCE,TARGET'])):
  item,stdout,stderr=command(args,label,15);assert item['exit']==0;record['environment'][label]=stdout.decode(errors='replace')
 assert record['environment']['rustc-version'].startswith('rustc 1.77.2 ') and record['environment']['cargo-version'].startswith('cargo 1.77.2 ')
 # Fresh private registry identity: let locked Cargo fetch its own compatible index/cache.
 gitdb=Path('/var/roothome/.cargo/git/db');private_git=home/'git/db';private_git.mkdir(parents=True)
 copied_git=[]
 for old in sorted(gitdb.iterdir()):
  if old.is_dir() and old.name.startswith(('rustyline-','no-std-compat-')):
   shutil.copytree(old,private_git/old.name);copied_git.append(old.name)
 assert any(n.startswith('rustyline-')for n in copied_git) and any(n.startswith('no-std-compat-')for n in copied_git)
 record['private_git_databases']=copied_git
 record['counts']['metadata_queries']=record['counts'].get('metadata_queries',0)+1
 item,stdout,stderr=command([str(toolchain/'cargo'),'metadata','--locked','--format-version','1','--filter-platform','x86_64-unknown-linux-gnu'],'locked-metadata',120)
 assert item['exit']==0,stderr[-4000:]
 metadata=json.loads(stdout);record['metadata_package_count']=len(metadata['packages'])
 testfile=source/'tests/sys_fs.rs';original=testfile.read_text();mutated=original
 edits=[('test_non_utf8_file_name','assert!(matches!(err, SysError::NotUtf8(..)), "{err}");','assert!(!matches!(err, SysError::NotUtf8(..)), "CONTROL_F19_NOT_UTF8_SENSITIVITY: {err}");','CONTROL_F19_NOT_UTF8_SENSITIVITY'),('test_unrestricted_symlinks_follow_host_semantics','unwrap(), "absolute target");','unwrap(), "WRONG_F22_TARGET", "CONTROL_F22_LINK_SENSITIVITY");','CONTROL_F22_LINK_SENSITIVITY'),('test_unrestricted_symlink_then_parent_uses_host_resolution','unwrap(), "OS-selected target");','unwrap(), "lexical sentinel", "CONTROL_F22_PARENT_SENSITIVITY");','CONTROL_F22_PARENT_SENSITIVITY')]
 for name,old,new,marker in edits:
  start=mutated.index('fn '+name+'()');end=mutated.index('\n}',start)+2;block=mutated[start:end];assert block.count(old)==1,(name,old);mutated=mutated[:start]+block.replace(old,new)+mutated[end:]
 testfile.write_text(mutated);record['mutated_sys_fs_sha256']=sha(testfile);(out/'red-sys_fs.rs').write_text(mutated)
 red=build(b['profile_features'][0],'red-base',['sys_fs'])
 for name,old,new,marker in edits:
  record['counts']['red_tests']+=1;item,stdout,stderr=command([red['sys_fs']['path'],'--exact',name,'--nocapture','--test-threads=1'],'red-'+name,90);text=(stdout+stderr).decode(errors='replace')
  assert item['exit']==101 and marker in text and 'test result: FAILED.'in text and '1 failed'in text and name in text,(name,text[-5000:])
 testfile.write_text(original);assert sha(testfile)==b['source_pins']['tests/sys_fs.rs']
 for index,features in enumerate(b['profile_features']):
  artifacts=build(features,'green-'+str(index),b['targets'])
  for name in b['targets']:
   record['counts']['green_targets']+=1;item,stdout,stderr=command([artifacts[name]['path'],'--nocapture','--test-threads=1'],'green-'+str(index)+'-'+name,90);text=(stdout+stderr).decode(errors='replace')
   assert item['exit']==0 and 'test result: ok.'in text and '; 0 failed;'in text and not re.search(r'test result: ok\. 0 passed;',text),(features,name,text[-5000:])
   if name=='sys_fs':
    assert 'filesystem rejects non-UTF-8 fixture'not in text
    for case in b['controlled_tests']:assert re.search(r'test '+re.escape(case)+r' \.\.\. ok',text),case
 for name,h in b['source_pins'].items():assert sha(source/name)==h,name
 assert not list((runtime/'tmp').iterdir()),'Owned fixture leftovers require exact inspection'
 assert dict(os.environ)==original_env and os.getcwd()==original_cwd,'Controller parent context changed'
 record['accepted']=True;record['fixture_temp_absent']=True;record['parent_context_preserved']=True
except BaseException:
 record['failure']=traceback.format_exc();raise
finally:
 record['remaining_capacity_bytes']=shutil.disk_usage(runtime).free
 (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({'accepted':record['accepted'],'counts':record['counts'],'failure':record['failure'][-1000:]}),flush=True)
