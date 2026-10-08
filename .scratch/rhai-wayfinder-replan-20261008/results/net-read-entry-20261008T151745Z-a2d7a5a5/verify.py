import hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
e=Path(sys.argv[1]); i=json.loads((e/'inputs.json').read_text()); runtime=Path(os.environ['AGENT_RUNTIME_DIR']); source=runtime/'source';source.mkdir()
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r={'accepted':False,'rows':[],'runtime':str(runtime),'runtime_identity':{'device':runtime.stat().st_dev,'inode':runtime.stat().st_ino},'environment':{'os':platform.platform(),'machine':platform.machine(),'rustc':subprocess.check_output(['rustc','+1.77.2','--version'],text=True).strip(),'cargo':subprocess.check_output(['cargo','+1.77.2','--version'],text=True).strip()}}
def save(): (e/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(tag,argv,timeout=60):
    start=time.monotonic()
    with (e/(tag+'.stdout')).open('wb') as out,(e/(tag+'.stderr')).open('wb') as err:
        completed=subprocess.run(argv,cwd=source,stdout=out,stderr=err,timeout=timeout)
    (e/(tag+'.command.json')).write_text(json.dumps({'argv':argv,'cwd':str(source),'exit':completed.returncode,'seconds':time.monotonic()-start},indent=2)+'\n')
    return completed.returncode
def selected(tag,features,red):
    assert run(tag+'-build',['cargo','+1.77.2','test','--locked','--features','testing-environ,'+features,'--test','net_reads','--no-run','--message-format=json'],600)==0,'pre-assertion compilation stop'
    artifacts=[]
    for line in (e/(tag+'-build.stdout')).read_text().splitlines():
        item=json.loads(line)
        if item.get('reason')=='compiler-artifact' and item.get('executable') and item.get('target',{}).get('name')=='net_reads':artifacts.append(Path(item['executable']))
    assert len(artifacts)==1;exe=artifacts[0]
    assert run(tag+'-list',[str(exe),'--list'])==0
    assert (e/(tag+'-list.stdout')).read_text().splitlines().count(i['selector']+': test')==1
    rc=run(tag,[str(exe),i['selector'],'--exact','--nocapture','--test-threads=1'],15)
    output=(e/(tag+'.stdout')).read_text()+'\n'+(e/(tag+'.stderr')).read_text()
    if red: assert rc==101 and 'read readiness must come from WouldBlock inside the actual public read operation' in output and 'thread_started' in output and 'read_wait' in output and '1 failed' in output
    else:
        assert rc==0 and '1 passed' in output and 'public_read_wait_observed=true; read_result_pending=true; peer_open_without_bytes=true' in output
        assert 'public_read_cancelled=true; reader_joined=true; quota_reused=true; peer_eof=true; peer_joined=true' in output
    r['rows'].append({'phase':'red' if red else 'green','features':features,'exit':rc,'log':tag,'executable_sha256':h(exe),'test_sha256':h(source/'tests/net_reads.rs'),'stream_sha256':h(source/'src/packages/net/stream.rs')});save();print(tag,rc,flush=True)
try:
    assert h(Path(i['archive']))==i['archive_sha256'] and h(e/'red.patch')==i['red_patch_sha256'] and h(e/'Cargo.lock.accepted')==i['lock_sha256']
    subprocess.run(['tar','-xf',i['archive'],'-C',str(source)],check=True);(source/'Cargo.lock').write_bytes((e/'Cargo.lock.accepted').read_bytes())
    subprocess.run(['git','apply','--check',str(e/'red.patch')],cwd=source,check=True);subprocess.run(['git','apply',str(e/'red.patch')],cwd=source,check=True)
    assert h(source/'tests/net_reads.rs')==i['test_red_sha256'];selected('test-first-red',i['profiles'][0],True)
    (e/'red-complete.json').write_text(json.dumps(r,indent=2)+'\n')
    deadline=time.monotonic()+600
    while not (e/'green-inputs.json').is_file():
        assert time.monotonic()<deadline,'no implementation within finite RED scope';time.sleep(.1)
    green=json.loads((e/'green-inputs.json').read_text());assert set(green)=={'tests/net_reads.rs','src/packages/net/stream.rs'}
    for path,record in green.items():
        f=e/record['file'];assert h(f)==record['sha256'];(source/path).write_bytes(f.read_bytes())
    for index,features in enumerate(i['profiles']):selected('green-'+str(index),features,False)
    assert h(source/'Cargo.lock')==i['lock_sha256'];r['accepted']=True
except BaseException as error:r['failure']=repr(error);raise
finally:save()
