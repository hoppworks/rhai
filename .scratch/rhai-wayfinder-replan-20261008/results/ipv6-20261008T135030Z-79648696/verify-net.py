import hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
e=Path(sys.argv[1]);i=json.loads((e/'inputs.json').read_text());runtime=Path(os.environ['AGENT_RUNTIME_DIR']);s=runtime/'source';s.mkdir();tool=os.environ.get('RHAI_CARGO');cargo=[tool] if tool else ['cargo','+1.77.2'];rust=[os.environ['RUSTC']] if tool else ['rustc','+1.77.2']
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r={'accepted':False,'rows':[],'runtime':str(runtime),'runtime_identity':{'device':runtime.stat().st_dev,'inode':runtime.stat().st_ino},'environment':{'os':platform.platform(),'machine':platform.machine(),'rustc':subprocess.check_output(rust+['--version'],text=True).strip(),'cargo':subprocess.check_output(cargo+['--version'],text=True).strip()}}
def cmd(tag,argv,seconds=300):
 start=time.monotonic()
 with (e/(tag+'.stdout')).open('wb') as out,(e/(tag+'.stderr')).open('wb') as err:
  result=subprocess.run(argv,cwd=s,stdout=out,stderr=err,timeout=seconds)
 record={'argv':argv,'cwd':str(s),'exit':result.returncode,'seconds':time.monotonic()-start};(e/(tag+'.command.json')).write_text(json.dumps(record,indent=2)+'\n');print(tag,result.returncode,flush=True);return result.returncode
def compile(tag,features):
 rc=cmd(tag,cargo+['test','--locked','--features','testing-environ,'+features,'--test','net_connect','--test','net_listen','--no-run','--message-format=json'],600);assert rc==0,'compile stopped before product assertion: '+tag
 artifacts={}
 for x in map(json.loads,(e/(tag+'.stdout')).read_text().splitlines()):
  if x.get('reason')=='compiler-artifact' and x.get('executable') and x.get('target',{}).get('name') in ['net_connect','net_listen']:
   name=x['target']['name'];assert name not in artifacts;artifacts[name]=Path(x['executable'])
 assert set(artifacts)=={'net_connect','net_listen'}
 for t in i['tests']:
  exe=artifacts[t['target']];assert exe.is_file();assert cmd(tag+'-'+t['target']+'-list',[str(exe),'--list'])==0
  assert (e/(tag+'-'+t['target']+'-list.stdout')).read_text().splitlines().count(t['selector']+': test')==1
 return artifacts
originals={}
try:
 assert h(Path(i['source_archive']))==i['source_sha256'] and h(e/'owned.patch')==i['owned_patch_sha256'] and h(e/'Cargo.lock.accepted')==i['lock_sha256']
 subprocess.run(['tar','-xf',i['source_archive'],'-C',str(s)],check=True);(s/'Cargo.lock').write_bytes((e/'Cargo.lock.accepted').read_bytes());subprocess.run(['git','apply','--check',str(e/'owned.patch')],cwd=s,check=True);subprocess.run(['git','apply',str(e/'owned.patch')],cwd=s,check=True)
 reds={}
 for t in i['tests']:
  f=s/t['file'];original=f.read_text();assert h(f)==t['source_sha256'];originals[t['file']]=original
  start=original.index('fn '+t['selector']+'()');end=original.find('\n#[test]',start);end=len(original) if end<0 else end;body=original[start:end];assert body.count(t['old'])==1
  reds[t['file']]=original[:start]+body.replace(t['old'],t['red'])+original[end:]
 for n,features in enumerate(i['profiles']):
  for phase,texts in [('red',reds),('green',originals)]:
   for file,content in texts.items():(s/file).write_text(content)
   tag='profile'+str(n)+'-'+phase;artifacts=compile(tag+'-build',features)
   for t in i['tests']:
    selected=tag+'-'+t['target'];exe=artifacts[t['target']];rc=cmd(selected,[str(exe),t['selector'],'--exact','--nocapture','--test-threads=1'],15);out=(e/(selected+'.stdout')).read_text();err=(e/(selected+'.stderr')).read_text();combined=out+'\n'+err
    if phase=='red':assert rc==101 and t['assertion'] in err and ('    '+t['selector']) in combined and '1 failed' in combined,'wrong assertion RED: '+selected
    else:assert rc==0 and '1 passed' in combined and t['readback'] in err and 'exact_bytes=true' in err and 'eof=true' in err and h(s/t['file'])==t['source_sha256'],'wrong GREEN: '+selected
    r['rows'].append({'profile':features,'phase':phase,'target':t['target'],'selector':t['selector'],'exit':rc,'executable_sha256':h(exe),'test_source_sha256':h(s/t['file']),'log':selected});(e/'result.json').write_text(json.dumps(r,indent=2)+'\n')
  assert h(s/'Cargo.lock')==i['lock_sha256'];r['runtime_bytes']=int(subprocess.check_output(['du','-sk',str(runtime)],text=True).split()[0])*1024;assert r['runtime_bytes']<8*1024**3
 r['accepted']=True
except BaseException as error:r['failure']=repr(error);raise
finally:
 for file,content in originals.items():(s/file).write_text(content)
 r['restored_sources']={file:h(s/file) for file in originals};(e/'result.json').write_text(json.dumps(r,indent=2)+'\n')
