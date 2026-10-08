import hashlib,json,os,platform,subprocess,sys,time,re
from pathlib import Path
e=Path(sys.argv[1]);i=json.loads((e/'inputs.json').read_text());runtime=Path(os.environ['AGENT_RUNTIME_DIR']);s=runtime/'source';s.mkdir();h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r={'accepted':False,'rows':[],'runtime':str(runtime),'runtime_identity':{'device':runtime.stat().st_dev,'inode':runtime.stat().st_ino},'environment':{'os':platform.platform(),'machine':platform.machine()}}
def save():(e/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def cmd(tag,argv,bound=60):
 start=time.monotonic()
 with (e/(tag+'.stdout')).open('wb') as out,(e/(tag+'.stderr')).open('wb') as err:p=subprocess.run(argv,cwd=s,stdout=out,stderr=err,timeout=bound)
 (e/(tag+'.command.json')).write_text(json.dumps({'argv':argv,'cwd':str(s),'exit':p.returncode,'seconds':time.monotonic()-start},indent=2)+'\n');return p.returncode
def build(tag,version,features,targets):
 argv=['cargo','+'+version,'test','--locked','--features','testing-environ,'+features]
 for target in targets:argv+=['--test',target]
 assert cmd(tag,argv+['--no-run','--message-format=json'],600)==0,'pre-assertion compiler failure '+tag
 artifacts={}
 for line in (e/(tag+'.stdout')).read_text().splitlines():
  x=json.loads(line)
  if x.get('reason')=='compiler-artifact' and x.get('executable') and x.get('target',{}).get('name') in targets:artifacts[x['target']['name']]=Path(x['executable'])
 assert set(artifacts)==set(targets)
 return artifacts
def selected(tag,exe,selector,red=False):
 rc=cmd(tag,[str(exe),selector,'--exact','--nocapture','--test-threads=1'],90);out=(e/(tag+'.stdout')).read_text()+'\n'+(e/(tag+'.stderr')).read_text()
 if red:assert rc==101 and 'timed_out' in out and '1 failed' in out and 'run_io_contract_empty_output' in out
 else:assert rc==0 and '1 passed' in out and '0 ignored' in out, 'selected assertion failed '+tag
 return {'selector':selector,'exit':rc,'log':tag,'executable_sha256':h(exe)}
try:
 assert h(Path(i['archive']))==i['archive_sha256'] and h(e/'owned.patch')==i['patch_sha256'] and h(e/'Cargo.lock.accepted')==i['lock_sha256']
 subprocess.run(['tar','-xf',i['archive'],'-C',str(s)],check=True);(s/'Cargo.lock').write_bytes((e/'Cargo.lock.accepted').read_bytes());subprocess.run(['git','apply','--check',str(e/'owned.patch')],cwd=s,check=True);subprocess.run(['git','apply',str(e/'owned.patch')],cwd=s,check=True)
 r['bound_sources']={p:h(s/p) for p in ['tests/sys_process.rs','tests/sys_process_report.rs','tests/fixtures/sys_process_shared_child_contract.rs','src/packages/sys/process/unix.rs','Cargo.toml','build.rs']}
 f=s/'tests/sys_process.rs';original=f.read_text();start=original.index('fn run_io_contract_empty_output()');end=original.index('\n#[test]',start);body=original[start:end];old='assert!(!result["timed_out"].as_bool().unwrap());';assert body.count(old)==1
 f.write_text(original[:start]+body.replace(old,'assert!(result["timed_out"].as_bool().unwrap());')+original[end:]);exe=build('x20-control-build','1.77.2','sys',['sys_process'])['sys_process'];assert cmd('x20-control-list',[str(exe),'--list'])==0;assert (e/'x20-control-list.stdout').read_text().splitlines().count('run_io_contract_empty_output: test')==1
 r['control']=selected('x20-control',exe,'run_io_contract_empty_output',True);f.write_text(original);assert h(f)==r['bound_sources']['tests/sys_process.rs'];save()
 for n,row in enumerate(i['rows']):
  tag='row'+str(n);r['environment'][row['toolchain']]=subprocess.check_output(['rustc','+'+row['toolchain'],'--version'],text=True).strip();artifacts=build(tag+'-build',row['toolchain'],row['features'],row['targets']);record={'name':row['name'],'features':row['features'],'toolchain':row['toolchain'],'results':[]};r['rows'].append(record)
  for target,selection in row['targets'].items():
   exe=artifacts[target];assert cmd(tag+'-'+target+'-list',[str(exe),'--list'])==0;listing=(e/(tag+'-'+target+'-list.stdout')).read_text().splitlines();names=[line[:-6] for line in listing if line.endswith(': test')];assert len(set(names))==len(names)
   if selection=='all':selection=names
   if selection=='baseline':selection=[name for name in names if name not in i['baseline_skip'] and not re.search(i['baseline_skip_regex'],name)]
   assert selection
   for index,name in enumerate(selection):
    assert names.count(name)==1;record['results'].append(dict(target=target,**selected(tag+'-'+target+'-'+str(index),exe,name)));save()
  assert h(s/'Cargo.lock')==i['lock_sha256'];r['runtime_bytes']=int(subprocess.check_output(['du','-sk',str(runtime)],text=True).split()[0])*1024;assert r['runtime_bytes']<8*1024**3;print(row['name'],len(record['results']),flush=True)
 r['accepted']=True
except BaseException as error:r['failure']=repr(error);raise
finally:save()
