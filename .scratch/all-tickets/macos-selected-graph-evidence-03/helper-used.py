"""Resolve frozen locked measurement metadata with public index completion only."""
import hashlib, json, os, shutil, subprocess, tarfile, time
from pathlib import Path
REPO=Path('/Users/hoppworks/projects/rhai-all-tickets')
OWNER=Path('/Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai')
EVIDENCE=REPO/'.scratch/all-tickets/macos-selected-graph-evidence-03'
RUNTIME=Path(os.environ['AGENT_RUNTIME_DIR'])
REV='00bed4a0dfeb103ff209ba4c76dac7ae797b7c56'
ARCHIVE_SHA='5414ea195ad00152b1eae36b3f4e10943ba5d9bf323baff6410cca0c5b4d8b98'
LOCK_SHA='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TOOL=Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
DEADLINE=time.monotonic()+75
MAXIMA={'storage_kib':0,'rss_kib':0,'descendants':0}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sample():
    storage=int(subprocess.check_output(['/usr/bin/du','-sk',str(RUNTIME)],timeout=5).split()[0])
    rows={}
    for line in subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,rss='],timeout=5,text=True).splitlines():
        pid,ppid,rss=map(int,line.split()); rows[pid]=(ppid,rss)
    owned={os.getpid()}
    if os.getpid() not in rows: raise RuntimeError('sampler host missing')
    while True:
        more={pid for pid,(ppid,_) in rows.items() if ppid in owned}-owned
        if not more: break
        owned.update(more)
    values={'storage_kib':storage,'rss_kib':sum(rows[p][1] for p in owned),'descendants':len(owned)-1}
    for key,value in values.items(): MAXIMA[key]=max(MAXIMA[key],value)
    print('sample='+json.dumps(values),flush=True)
    if storage>=1572864 or values['rss_kib']>=2097152 or values['descendants']>16:
        raise RuntimeError('sampled resource stop')
def command(name,argv,env):
    with (EVIDENCE/(name+'.stdout')).open('wb') as out, (EVIDENCE/(name+'.stderr')).open('wb') as err:
        child=subprocess.Popen(argv,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
        try:
            while child.poll() is None:
                if time.monotonic()>=DEADLINE: raise TimeoutError('metadata package75s expired')
                sample(); time.sleep(0.1)
            status=child.wait()
        finally:
            if child.poll() is None:
                child.kill(); child.wait(timeout=5)
    (EVIDENCE/(name+'.status')).write_text(str(status)+'\n')
    sample()
    if sha(source/'Cargo.lock')!=LOCK_SHA: raise RuntimeError('locked input changed')
    if status: raise RuntimeError(name+' failed status='+str(status))
    return (EVIDENCE/(name+'.stdout')).read_text()
if EVIDENCE.exists(): raise RuntimeError('preserve existing evidence; no repeat')
EVIDENCE.mkdir(); shutil.copy2(__file__,EVIDENCE/'helper-used.py')
(EVIDENCE/'contract.json').write_text(json.dumps({'revision':REV,'archive_sha256':ARCHIVE_SHA,'lock_sha256':LOCK_SHA,'command':'cargo metadata --locked --format-version 1 --filter-platform aarch64-apple-darwin --features testing-environ,sys','helper_seconds':75,'outer_seconds':100,'sampled_storage_stop_kib':1572864,'sampled_rss_stop_kib':2097152,'descendants':16,'builds_tests_fixtures_measurements':0},indent=2)+'\n')
source=RUNTIME/'source'; source.mkdir(); archive=RUNTIME/'source.tar'
with archive.open('wb') as out:
    subprocess.run(['/usr/bin/git','-C',str(REPO),'archive',REV],stdout=out,check=True,timeout=20)
if sha(archive)!=ARCHIVE_SHA: raise RuntimeError('frozen archive mismatch')
with tarfile.open(archive) as bundle: bundle.extractall(source,filter='data')
archive.unlink()
shutil.copy2(REPO/'.scratch/all-tickets/core-current-msrv-evidence-03/Cargo.lock',source/'Cargo.lock')
if sha(source/'Cargo.lock')!=LOCK_SHA: raise RuntimeError('exact edge-only lock mismatch')
shutil.copy2(source/'Cargo.lock',EVIDENCE/'Cargo.lock')
home=RUNTIME/'cargo-home'; (home/'registry').mkdir(parents=True)
for part in ('cache','index'):
    shutil.copytree(Path('/Users/hoppworks/.cargo/registry')/part,home/'registry'/part)
shutil.copytree(Path('/Users/hoppworks/.cargo/git'),home/'git')
for config in (home/'registry/index').glob('*/config.json'):
    data=json.loads(config.read_text())
    if data.get('dl')!='https://static.crates.io/crates' or data.get('api')!='https://crates.io': raise RuntimeError('unexpected registry endpoints')
for namespace in (home/'registry/index').iterdir():
    if not (namespace/'config.json').is_file(): continue
    cache=home/'registry/cache'/namespace.name; cache.mkdir(exist_ok=True)
    for original in (OWNER/'.scratch/all-tickets/macos-overhead-custody-source-audit/archives').glob('*.crate'):
        shutil.copy2(original,cache/original.name)
private_home=RUNTIME/'home'; private_home.mkdir()
env={'PATH':str(TOOL)+':/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(private_home),'CARGO_HOME':str(home),'CARGO_TARGET_DIR':str(RUNTIME/'target'),'RUSTUP_HOME':str(RUNTIME/'rustup-home'),'TMPDIR':os.environ['TMPDIR'],'TMP':os.environ['TMPDIR'],'TEMP':os.environ['TMPDIR'],'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_TERM_COLOR':'never','RUSTC':str(TOOL/'rustc'),'RUSTDOC':str(TOOL/'rustdoc'),'SDKROOT':'/Library/Developer/CommandLineTools/SDKs/MacOSX27.0.sdk'}
sample()
version=command('rustc-version',[str(TOOL/'rustc'),'--version','--verbose'],env)
if 'rustc 1.93.0 ' not in version: raise RuntimeError('frozen measurement toolchain changed')
command('cargo-version',[str(TOOL/'cargo'),'--version','--verbose'],env)
command('metadata',[str(TOOL/'cargo'),'metadata','--locked','--format-version','1','--filter-platform','aarch64-apple-darwin','--features','testing-environ,sys'],env)
(EVIDENCE/'sampled-maxima.json').write_text(json.dumps(MAXIMA,indent=2)+'\n')
(EVIDENCE/'result.txt').write_text('Metadata only; build/test/confinement/native ABI acceptance remain unproven.\n')
print('selected_graph_metadata=resolved',flush=True)
