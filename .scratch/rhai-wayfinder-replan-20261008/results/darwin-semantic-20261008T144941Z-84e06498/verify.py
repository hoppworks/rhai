import hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

e = Path(sys.argv[1]); i = json.loads((e/'inputs.json').read_text())
runtime = Path(os.environ['AGENT_RUNTIME_DIR']); source = runtime/'source'; source.mkdir()
hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = {'accepted': False, 'rows': [], 'controls': [], 'runtime': str(runtime),
          'runtime_identity': {'device': runtime.stat().st_dev, 'inode': runtime.stat().st_ino},
          'environment': {'os': platform.platform(), 'machine': platform.machine(),
              'rustc': subprocess.check_output(['rustc','+1.77.2','--version'],text=True).strip(),
              'cargo': subprocess.check_output(['cargo','+1.77.2','--version'],text=True).strip()}}
def save(): (e/'result.json').write_text(json.dumps(result,indent=2)+'\n')
def run(tag, argv, timeout=60, control=None):
    env = os.environ.copy()
    for controls in i['controls'].values():
        for c in controls: env.pop(c['env'],None)
    if control: env[control] = '1'
    start = time.monotonic()
    with (e/(tag+'.stdout')).open('wb') as out, (e/(tag+'.stderr')).open('wb') as err:
        completed = subprocess.run(argv,cwd=source,env=env,stdout=out,stderr=err,timeout=timeout)
    record = {'argv': argv, 'cwd': str(source), 'exit': completed.returncode,
              'seconds': time.monotonic()-start, 'control': control}
    (e/(tag+'.command.json')).write_text(json.dumps(record,indent=2)+'\n')
    return completed.returncode
try:
    assert hashfile(Path(i['source_archive'])) == i['source_sha256']
    assert hashfile(e/'owned.patch') == i['owned_patch_sha256']
    assert hashfile(e/'Cargo.lock.accepted') == i['lock_sha256']
    subprocess.run(['tar','-xf',i['source_archive'],'-C',str(source)],check=True)
    (source/'Cargo.lock').write_bytes((e/'Cargo.lock.accepted').read_bytes())
    subprocess.run(['git','apply','--check',str(e/'owned.patch')],cwd=source,check=True)
    subprocess.run(['git','apply',str(e/'owned.patch')],cwd=source,check=True)
    for row in i['rows']:
        name=row['name']; argv=['cargo','+1.77.2','test','--locked','--features','testing-environ,'+row['features']]
        for target in row['targets']: argv += ['--test',target]
        assert run(name+'-build',argv+['--no-run','--message-format=json'],600)==0, 'pre-assertion compile stop: '+name
        executables={}
        for line in (e/(name+'-build.stdout')).read_text().splitlines():
            item=json.loads(line)
            if item.get('reason')=='compiler-artifact' and item.get('executable') and item.get('target',{}).get('name') in row['targets']:
                target=item['target']['name']; assert target not in executables
                executables[target]=Path(item['executable'])
        assert set(executables)==set(row['targets'])
        for target,exe in executables.items():
            tag=name+'-'+target; assert exe.is_file()
            assert run(tag+'-list',[str(exe),'--list'])==0
            names=[line[:-6] for line in (e/(tag+'-list.stdout')).read_text().splitlines() if line.endswith(': test')]
            assert names and len(names)==len(set(names))
            selected=row['targets'][target]
            selected=[n for n in names if n not in i['already_accepted_skip']] if selected is None else selected
            assert selected and len(selected)==len(set(selected)) and set(selected)<=set(names)
            for control in i['controls'].get(name,[]):
                if control['target'] != target: continue
                selector=control['selector']; assert selector in selected
                ctag=tag+'-red'; rc=run(ctag,[str(exe),selector,'--exact','--nocapture','--test-threads=1'],control=control['env'])
                logs=(e/(ctag+'.stdout')).read_text()+'\n'+(e/(ctag+'.stderr')).read_text()
                assert rc==101 and control['assertion'] in logs and '1 failed' in logs and selector in logs, 'wrong assertion RED: '+ctag
                result['controls'].append({'row':name,**control,'exit':rc,'logs':ctag,'executable_sha256':hashfile(exe)});save()
            passed=[]
            for index,selector in enumerate(selected):
                stag=tag+'-green-'+str(index); rc=run(stag,[str(exe),selector,'--exact','--nocapture','--test-threads=1'])
                stdout=(e/(stag+'.stdout')).read_text(); stderr=(e/(stag+'.stderr')).read_text()
                assert rc==0 and '1 passed' in stdout and '0 ignored' in stdout, 'assertion failure: '+stag
                passed.append({'selector':selector,'exit':rc,'logs':stag,'host_unavailable_notice':'EILSEQ' in stderr or 'SKIP' in stderr or 'unsupported' in stderr.lower()})
            result['rows'].append({'name':name,'features':row['features'],'target':target,'selected':passed,'executable_sha256':hashfile(exe),
                                   'source_sha256':hashfile(source/'tests'/(target+'.rs'))});save()
        assert hashfile(source/'Cargo.lock')==i['lock_sha256']
        result['runtime_bytes']=int(subprocess.check_output(['du','-sk',str(runtime)],text=True).split()[0])*1024
        assert result['runtime_bytes']<8*1024**3
        print(name+' GREEN',flush=True)
    result['accepted']=True
except BaseException as error:
    result['failure']=repr(error); raise
finally:
    result['lock_sha256']=hashfile(source/'Cargo.lock') if (source/'Cargo.lock').exists() else None
    save()
