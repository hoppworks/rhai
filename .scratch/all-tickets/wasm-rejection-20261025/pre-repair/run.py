"""One bounded compile-time unsupported-WASM rejection acceptance; export before cleanup."""
from pathlib import Path,PurePosixPath
import os,sys,json,hashlib,shutil,subprocess,time,selectors,tarfile,traceback,re
base=Path(__file__).resolve().parent;b=json.loads((base/'binding.json').read_text());out=base/'evidence';out.mkdir();runtime=Path(os.environ['AGENT_RUNTIME_DIR']);source=runtime/'source';source.mkdir();home=runtime/'cargo-home';target=runtime/'target';home.mkdir();target.mkdir();sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(base/'source.tar')==b['archive_sha256'] and sha(base/'Cargo.lock')==b['source_lock_sha256']
assert shutil.disk_usage(runtime).free>b['additional_storage_bytes_estimate'],'Insufficient measured capacity for declared estimate'
record={'base':b['base'],'nonce':b['nonce'],'runtime':str(runtime),'source':str(source),'accepted':False,'commands':[],'counts':{'cargo_checks':0,'metadata_queries':0,'matcher_controls':0},'counts_scope':'one_bounded_invocation_no_prior_attempts','prior_consumption':b.get('prior_consumption',{}),'environment':{},'failure':''}
(original_env,original_cwd)=(dict(os.environ),os.getcwd())
env=dict(os.environ)
for key in ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_TARGET','RUSTDOCFLAGS','RUSTC_BOOTSTRAP','RHAI_AHASH_SEED','RHAI_HASHING_SEED'):env.pop(key,None)
toolchain=Path(b['toolchain'])
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
def matches(item,stdout,expected):
 diagnostics=[];foreign_errors=[]
 for line in stdout.splitlines():
  if not line:continue
  message=json.loads(line)
  if message.get('reason')=='compiler-message' and message['message']['level']=='error':
   if message.get('target',{}).get('name')=='rhai':diagnostics.append(message['message']['message'])
   else:foreign_errors.append(message['message']['message'])
 return item['exit']==101 and not foreign_errors and sorted(diagnostics)==sorted(expected),diagnostics
try:
 with tarfile.open(base/'source.tar')as archive:
  for member in archive.getmembers():assert not PurePosixPath(member.name).is_absolute()and '..'not in PurePosixPath(member.name).parts and(member.isfile()or member.isdir())
  archive.extractall(source,filter='data')
 shutil.copyfile(base/'Cargo.lock',source/'Cargo.lock')
 for name,h in b['source_pins'].items():assert sha(source/name)==h,name
 record['source_pins']=b['source_pins'];record['lock_sha256']=sha(source/'Cargo.lock')
 for label,args in (('rustc-version',[str(toolchain/'rustc'),'--version','--verbose']),('cargo-version',[str(toolchain/'cargo'),'--version']),('target-cfg',[str(toolchain/'rustc'),'--print','cfg','--target',b['target']]),('target-libdir',[str(toolchain/'rustc'),'--print','target-libdir','--target',b['target']]),('os',['uname','-a']),('capacity',['df','-B1',str(runtime)]),('memory',['free','-b'])):
  item,stdout,stderr=command(args,label,15);assert item['exit']==0;record['environment'][label]=stdout.decode(errors='replace')
 assert record['environment']['rustc-version'].startswith('rustc '+b['expected_rust_version']+' ')
 assert 'target_family="wasm"'in record['environment']['target-cfg']
 libdir=Path(record['environment']['target-libdir'].strip());stdlib=list(libdir.glob('libstd-*.rlib'));assert len(stdlib)==1
 record['tool_hashes']={str(f):sha(f)for f in (toolchain/'rustc',toolchain/'cargo',stdlib[0])}
 gitdb=Path('/var/roothome/.cargo/git/db');private_git=home/'git/db';private_git.mkdir(parents=True);copied=[]
 for old in sorted(gitdb.iterdir()):
  if old.is_dir()and old.name.startswith(('rustyline-','no-std-compat-')):shutil.copytree(old,private_git/old.name);copied.append(old.name)
 assert any(n.startswith('rustyline-')for n in copied)and any(n.startswith('no-std-compat-')for n in copied)
 record['private_git_databases']=copied;record['counts']['metadata_queries']+=1
 item,stdout,stderr=command([str(toolchain/'cargo'),'metadata','--locked','--format-version','1','--filter-platform',b['target']],'locked-metadata',120);assert item['exit']==0,stderr[-4000:]
 record['metadata_package_count']=len(json.loads(stdout)['packages']);record['rows']=[]
 for index,features in enumerate(b['negative_features']):
  record['counts']['cargo_checks']+=1
  item,stdout,stderr=command([str(toolchain/'cargo'),'check','--locked','--lib','--no-default-features','--features',features,'--target',b['target'],'--message-format=json'],'wasm-'+str(index),120)
  expected=['the `'+name+'` feature is not available on WASM targets'for name in features.split(',')]
  passed,diagnostics=matches(item,stdout,expected)
  # Wrong expected public compiler contract must be rejected against the same original trace.
  wrong,_=matches(item,stdout,['WRONG_WASM_EXPECTATION: package is supported on WASM'])
  extra=json.dumps({'reason':'compiler-message','target':{'name':'rhai'},'message':{'level':'error','message':'UNRELATED_COMPILER_ERROR_CONTROL'}}).encode()+b'\n'
  accepts_extra,_=matches(item,stdout+extra,expected)
  record['counts']['matcher_controls']+=2
  assert not accepts_extra,'Matcher accepted unrelated extra compiler failure'
  assert not wrong,'Matcher accepted deliberately wrong expected diagnostic'
  assert passed,(features,item,diagnostics,stderr[-4000:])
  record['rows'].append({'features':features,'target':b['target'],'exit':item['exit'],'intentional_diagnostics':expected,'actual_project_errors':diagnostics,'wrong_expectation_red':not wrong,'extra_error_rejected':not accepts_extra,'restored_expectation_green':passed,'elapsed_seconds':item['elapsed_seconds']})
 for name,h in b['source_pins'].items():assert sha(source/name)==h,name
 assert sha(source/'Cargo.lock')==b['source_lock_sha256']
 assert dict(os.environ)==original_env and os.getcwd()==original_cwd
 record['parent_context_preserved']=True;record['source_lock_unchanged']=True;record['accepted']=True
except BaseException:
 record['failure']=traceback.format_exc();raise
finally:
 record['remaining_capacity_bytes']=shutil.disk_usage(runtime).free
 (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({'accepted':record['accepted'],'counts':record['counts'],'failure':record['failure'][-1000:]}),flush=True)
