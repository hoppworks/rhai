import hashlib, os, platform, re, shutil, subprocess, sys, time
from pathlib import Path
REPO=Path('/Users/hoppworks/projects/rhai-all-tickets')
SOURCE_REF='00bed4a0dfeb103ff209ba4c76dac7ae797b7c56'
ARCHIVE_SHA='5414ea195ad00152b1eae36b3f4e10943ba5d9bf323baff6410cca0c5b4d8b98'
RUNTIME=Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
BASE=Path(os.environ['RHAI_OVERHEAD_LOG_BASE']).absolute()
EVIDENCE=Path('/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/macos-process-overhead-evidence')
TOOL=Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO,RUSTC,RUSTDOC=(TOOL/n for n in ('cargo','rustc','rustdoc'))
LOCK_SHA='8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
OVERLAYS=['Cargo.toml','src/packages/sys/config.rs','src/packages/sys/mod.rs','src/packages/sys/process.rs','src/packages/sys/process/unix.rs','tests/sys_process.rs']
LIMIT=1_572_864

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sample(deadline):
    for n in (1,2):
        left=deadline-time.monotonic()
        if left<=0: raise TimeoutError('aggregate Cargo deadline expired during storage sample')
        try: r=subprocess.run(['du','-sk',str(RUNTIME)],capture_output=True,text=True,timeout=min(5,left))
        except subprocess.TimeoutExpired as e:
            print(f'storage_sample_attempt={n} status=timeout stdout={e.stdout!r} stderr={e.stderr!r}',flush=True)
            if n==2: raise
            time.sleep(min(.05,max(0,deadline-time.monotonic()))); continue
        print(f'storage_sample_attempt={n} status={r.returncode} stdout={r.stdout.strip()!r} stderr={r.stderr.strip()!r}',flush=True)
        if r.returncode:
            if n==2: raise RuntimeError('two failed storage samples')
            time.sleep(min(.05,max(0,deadline-time.monotonic()))); continue
        f=r.stdout.strip().split(maxsplit=1)
        if len(f)!=2 or not f[0].isdigit() or f[1]!=str(RUNTIME): raise RuntimeError('invalid storage sample')
        k=int(f[0]); print(f'storage_sample_kib={k}',flush=True)
        if k>=LIMIT: raise RuntimeError(f'sampled storage reached {LIMIT} KiB')
        return k
    raise RuntimeError('no valid storage measurement')
def emit(path,complete):
    b=path.read_bytes() if path.exists() else b''
    print(f'cargo_output_begin path={path} complete={str(complete).lower()} bytes={len(b)} sha256={hashlib.sha256(b).hexdigest()}',flush=True)
    print(b.decode(errors='replace'),flush=True); print('cargo_output_end',flush=True)
def run(argv,path,deadline,env,source):
    print('cargo_argv='+repr(argv),flush=True); print('cargo_cwd='+str(source),flush=True); print('cargo_log='+str(path),flush=True)
    command_start=time.monotonic()
    with path.open('wb') as f:
        p=subprocess.Popen(argv,cwd=source,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=False)
        print(f'cargo_pid={p.pid} cargo_pgid={os.getpgid(p.pid)}',flush=True)
        try:
            while p.poll() is None:
                if time.monotonic()>=deadline: raise TimeoutError('aggregate Cargo watchdog expired')
                sample(deadline); time.sleep(1)
            status=p.returncode; print(f'cargo_status={status} cargo_elapsed_seconds={time.monotonic()-command_start:.3f}',flush=True); emit(path,True); sample(deadline)
        except BaseException:
            rc=p.poll()
            if rc is not None: print(f'cargo_status={rc}',flush=True)
            emit(path,rc is not None); raise
    return status,path.read_text(errors='replace')

def main():
    package_deadline=time.monotonic()+580
    if RUNTIME.is_symlink() or not RUNTIME.is_dir(): raise RuntimeError('unowned runtime path')
    if BASE.parent!=EVIDENCE or BASE.is_symlink(): raise RuntimeError('log base outside evidence directory')
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    print('phase=process_scope_overhead_measurement',flush=True)
    print('scope=immutable_POSIX_overhead_development_not_release',flush=True)
    print(f'runtime_path={RUNTIME}',flush=True)
    print(f'python={sys.version.replace(chr(10)," ")} platform={platform.platform()}',flush=True)
    print(f'harness_pid={os.getpid()} supervisor_pid={os.getppid()} inherited_pgid={os.getpgid(0)}',flush=True)
    for name,p in [('cargo',CARGO),('rustc',RUSTC),('rustdoc',RUSTDOC)]:
        v=subprocess.check_output([str(p),'--version','--verbose'] if name=='rustc' else [str(p),'--version'],text=True,timeout=10).strip().replace('\n',' | ')
        print(f'{name}_path={p} {name}_version={v}',flush=True)
    hashes={n:hashlib.sha256(subprocess.check_output(['git','-C',str(REPO),'show',f'{SOURCE_REF}:{n}'],timeout=10)).hexdigest() for n in OVERLAYS}
    print('repo_head='+subprocess.check_output(['git','-C',str(REPO),'rev-parse',SOURCE_REF],text=True,timeout=10).strip(),flush=True)
    print('original_overlay_hashes='+repr(hashes),flush=True)
    wrapper=Path('/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/run-macos-process-overhead.sh')
    scoped=Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
    print(f'harness_sha256={sha(Path(__file__))}',flush=True)
    print(f'wrapper_sha256={sha(wrapper)}',flush=True)
    print(f'run_scoped_sha256={sha(scoped)}',flush=True)
    source=RUNTIME/'source'; source.mkdir()
    archive=RUNTIME/'baseline.tar'
    with archive.open('wb') as f:
        p=subprocess.Popen(['git','-C',str(REPO),'archive',SOURCE_REF],stdout=f,stderr=subprocess.PIPE,start_new_session=False)
        d=time.monotonic()+90
        while p.poll() is None:
            if time.monotonic()>=d: raise TimeoutError('baseline archive exceeded90s')
            sample(d); time.sleep(.5)
        err=p.stderr.read().decode(errors='replace')
        if p.returncode: raise RuntimeError(f'git archive status={p.returncode}: {err}')
    if sha(archive)!=ARCHIVE_SHA: raise RuntimeError('immutable archive hash mismatch')
    print(f'archive_sha256={sha(archive)} source_ref={SOURCE_REF}',flush=True)
    if subprocess.run(['tar','-xf',str(archive),'-C',str(source)],timeout=90).returncode: raise RuntimeError('archive extraction failed')
    archive.unlink()
    private={n:sha(source/n) for n in OVERLAYS}
    if private!=hashes: raise RuntimeError('private source manifest differs from frozen source')
    print('private_overlay_hashes='+repr(private),flush=True)
    lock=REPO/'.scratch/managed-unix-scope-close/Cargo.lock.baseline'
    if sha(lock)!=LOCK_SHA: raise RuntimeError('accepted lock hash mismatch')
    plock=source/'Cargo.lock'; shutil.copy2(lock,plock); txt=plock.read_text()
    marker='name = "rhai"\nversion = "1.26.1"\ndependencies = [\n'
    if txt.count(marker)!=1: raise RuntimeError('unexpected accepted lock entry')
    a=txt.index(marker); b=txt.index('\n]',a); section=txt[a:b]
    if ' "libc",\n' not in section:
        i=section.index(' "libm",\n'); section=section[:i]+' "libc",\n'+section[i:]; plock.write_text(txt[:a]+section+txt[b:])
    if sha(plock)!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise RuntimeError('private edge-only lock hash mismatch')
    print(f'accepted_lock_sha256={sha(lock)} private_lock_sha256={sha(plock)}',flush=True)
    env=dict(os.environ)
    for k in ('RUSTUP_TOOLCHAIN','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTC_WRAPPER'): env.pop(k,None)
    env.update({'PATH':f'{TOOL}:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin','CARGO_HOME':str(RUNTIME/'cargo-home'),'RUSTUP_HOME':str(RUNTIME/'rustup-home'),'CARGO_TARGET_DIR':str(RUNTIME/'target'),'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_PROFILE_DEV_DEBUG':'0','CARGO_PROFILE_TEST_DEBUG':'0','RUSTC':str(RUSTC),'RUSTDOC':str(RUSTDOC),'TMPDIR':str(RUNTIME/'tmp'),'TMP':str(RUNTIME/'tmp'),'TEMP':str(RUNTIME/'tmp')})
    (RUNTIME/'cargo-home').mkdir(); (RUNTIME/'rustup-home').mkdir()
    measurement_dir=BASE.with_name(BASE.name+'.samples')
    driver=source/'.scratch/managed-unix-scope-close/measure-process-overhead.py'
    measurement_log=BASE.with_name(BASE.name+'.measurement-driver.log')
    cmd=[sys.executable,str(driver),'--source-dir',str(source),'--evidence-dir',str(measurement_dir),'--source-revision',SOURCE_REF,'--source-archive-sha256',ARCHIVE_SHA]
    status,out=run(cmd,measurement_log,package_deadline,env,source)
    if status!=0: raise RuntimeError('measurement driver failed; no retry')
    import json
    summary=json.loads((measurement_dir/'summary.json').read_text())
    if summary['samples_total']!=120 or summary['warmups']!=0: raise RuntimeError('unexpected measurement count')
    final={n:sha(source/n) for n in OVERLAYS}
    if final!=hashes: raise RuntimeError('final source manifest differs from frozen inputs')
    if sha(plock)!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise RuntimeError('private lock changed')
    print('final_private_overlay_hashes='+repr(final),flush=True)
    print(f'measurement_evidence={measurement_dir} samples=120 warmups=0',flush=True)
    print('measurement_check_status=passed',flush=True)
main()
