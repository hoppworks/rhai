import hashlib,json,os,platform,re,subprocess,sys,time
from pathlib import Path
e=Path(sys.argv[1]);i=json.loads((e/'inputs.json').read_text());runtime=Path(os.environ['AGENT_RUNTIME_DIR']);s=runtime/'source';s.mkdir();result={'rows':[],'accepted':False,'runtime':str(runtime),'environment':{'os':platform.platform(),'machine':platform.machine(),'rustc':subprocess.check_output(['rustc','+1.77.2','--version'],text=True).strip(),'cargo':subprocess.check_output(['cargo','+1.77.2','--version'],text=True).strip()},'scope_bound_seconds':1200}
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(tag,argv,seconds=300):
    start=time.monotonic()
    with (e/(tag+'.stdout')).open('wb') as out,(e/(tag+'.stderr')).open('wb') as err:
        r=subprocess.run(argv,cwd=s,stdout=out,stderr=err,timeout=seconds)
    record={'argv':argv,'cwd':str(s),'exit':r.returncode,'seconds':time.monotonic()-start};(e/(tag+'.command.json')).write_text(json.dumps(record,indent=2)+'\n');print(tag,'exit',r.returncode,flush=True);return r.returncode
def compile(tag,features):
    rc=cmd(tag,['cargo','+1.77.2','test','--locked','--features','testing-environ,'+features,'--test','sys_process','--no-run','--message-format=json'],600)
    assert rc==0,'compilation stopped before assertion: '+tag
    xs=[x for x in map(json.loads,(e/(tag+'.stdout')).read_text().splitlines()) if x.get('reason')=='compiler-artifact' and x.get('target',{}).get('name')=='sys_process' and x.get('executable')]
    assert len(xs)==1
    exe=Path(xs[0]['executable']);assert exe.is_file();assert cmd(tag+'-list',[str(exe),'--list'])==0
    assert i['selector']+': test' in (e/(tag+'-list.stdout')).read_text()
    return exe
try:
    assert h(Path(i['source_archive']))==i['source_sha256'] and h(e/'owned.patch')==i['owned_patch_sha256'] and h(e/'Cargo.lock.accepted')==i['lock_sha256']
    subprocess.run(['tar','-xf',i['source_archive'],'-C',str(s)],check=True);(s/'Cargo.lock').write_bytes((e/'Cargo.lock.accepted').read_bytes());subprocess.run(['git','apply','--check',str(e/'owned.patch')],cwd=s,check=True);subprocess.run(['git','apply',str(e/'owned.patch')],cwd=s,check=True)
    f=s/'tests/sys_process.rs';original=f.read_text();assert h(f)==i['test_source_sha256']
    # Function-specific control: exactly one exit oracle, never global assertion replacement.
    start=original.index('fn '+i['selector']+'()');end=original.index('/// The scalar text API',start);body=original[start:end];old='assert_eq!(report.exit_code(), Some(0), "normally completed child exit is preserved");';assert body.count(old)==1
    red=original[:start]+body.replace(old,old.replace('Some(0)','Some(1)'))+original[end:]
    for number,features in enumerate(i['profiles']):
        profile=['standard','sync','no-float','sync-no-float'][number]
        for phase,text in [('red',red),('green',original)]:
            f.write_text(text);exe=compile(profile+'-'+phase+'-build',features);tag=profile+'-'+phase
            rc=cmd(tag,[str(exe),i['selector'],'--exact','--nocapture','--test-threads=1'],30);out=(e/(tag+'.stdout')).read_text();err=(e/(tag+'.stderr')).read_text();combined=out+'\n'+err
            if phase=='red':
                assert rc==101 and 'normally completed child exit is preserved' in err and re.search(r'left:\s*Some\(0\).*right:\s*Some\(1\)',err,re.S) and ('    '+i['selector']) in combined and '1 failed' in combined,'wrong RED: '+tag
            else:
                assert rc==0 and '1 passed' in combined and 'primary_limit=false' in err and 'primary_limit=true' in err and 'child_reaped=true' in err,'wrong GREEN: '+tag
                assert h(f)==i['test_source_sha256']
            result['rows'].append({'profile':features,'phase':phase,'exit':rc,'executable_sha256':h(exe),'test_source_sha256':h(f),'log':tag});(e/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        assert h(s/'Cargo.lock')==i['lock_sha256']
        size=int(subprocess.check_output(['du','-sk',str(runtime)],text=True).split()[0])*1024;assert size<8*1024**3
    result['accepted']=True
except BaseException as error:
    result['failure']=repr(error);raise
finally:
    if 'original' in globals(): f.write_text(original);result['restored_test_sha256']=h(f)
    result['runtime_identity']={'device':runtime.stat().st_dev,'inode':runtime.stat().st_ino}
    (e/'result.json').write_text(json.dumps(result,indent=2)+'\n')
