import hashlib, os, platform, re, shutil, signal, subprocess, sys, time
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
MAX_DESCENDANTS=16
MAX_RSS_KIB=2*1024*1024

class Interrupted(BaseException):
    def __init__(self, signum): self.signum=signum

def _interrupt(signum, _frame): raise Interrupted(signum)

def parse_ps_snapshot(output):
    """Parse `ps -axo pid=,ppid=,pgid=,rss=,state=,lstart=` output."""
    rows={}
    for line in output.splitlines():
        fields=line.strip().split(None,5)
        if len(fields)!=6: raise RuntimeError('malformed process snapshot row')
        pid,ppid,pgid,rss,state,start=fields
        if not all(v.isdigit() for v in (pid,ppid,pgid,rss)) or not start:
            raise RuntimeError('invalid process snapshot identity or RSS')
        ident={'pid':int(pid),'ppid':int(ppid),'pgid':int(pgid),'rss_kib':int(rss),
               'state':state,'start':start}
        if ident['pid'] in rows: raise RuntimeError('duplicate PID in process snapshot')
        rows[ident['pid']]=ident
    return rows

def descendants(rows, root_pid):
    found=set(); parents={pid:row['ppid'] for pid,row in rows.items()}
    changed=True
    while changed:
        changed=False
        for pid,parent in parents.items():
            if pid!=root_pid and pid not in found and (parent==root_pid or parent in found):
                found.add(pid); changed=True
    return [rows[pid] for pid in sorted(found)]

def enforce_process_sample(live, rss_kib):
    count=max(0,len(live)-1)  # The first row is Cargo; cap its descendants separately.
    if count>MAX_DESCENDANTS: raise RuntimeError(f'sampled process descendants exceeded {MAX_DESCENDANTS}')
    if rss_kib>=MAX_RSS_KIB: raise RuntimeError(f'sampled process RSS reached {MAX_RSS_KIB} KiB')

def process_snapshot(root_pid, deadline):
    left=deadline-time.monotonic()
    if left<=0: raise TimeoutError('aggregate Cargo deadline expired during process sample')
    result=subprocess.run(['ps','-axo','pid=,ppid=,pgid=,rss=,state=,lstart='],
                          capture_output=True,text=True,timeout=min(5,left),check=False)
    if result.returncode: raise RuntimeError(f'process snapshot failed status={result.returncode}: {result.stderr.strip()}')
    rows=parse_ps_snapshot(result.stdout)
    if root_pid not in rows: return [],0
    live=descendants(rows,root_pid)
    # The direct Cargo process is itself part of the bounded process tree.
    live=[rows[root_pid],*live]
    return live,sum(row['rss_kib'] for row in live)

def persist_ledger(rows, complete=False, state='monitoring'):
    path=RUNTIME/'owned-process-ledger.json'
    data={'sampling':'one-second ps snapshots; not continuous enforcement',
          'identities':rows,'observed_identity_readback_complete':complete,
          'custody_state':state}
    temporary=path.with_suffix('.tmp')
    temporary.write_text(__import__('json').dumps(data,sort_keys=True)+'\n')
    os.replace(temporary,path)

def live_ledger_identities(ledger, deadline):
    if not ledger: return []
    left=deadline-time.monotonic()
    if left<=0: raise TimeoutError('aggregate measurement deadline expired before final identity readback')
    result=subprocess.run(['ps','-axo','pid=,ppid=,pgid=,rss=,state=,lstart='],
                          capture_output=True,text=True,timeout=min(5,left),check=False)
    if result.returncode: raise RuntimeError('final process identity readback failed')
    current=parse_ps_snapshot(result.stdout)
    by_key={(row['pid'],row['start']):row for row in current.values()}
    return [by_key[(row['pid'],row['start'])] for row in ledger
            if (row['pid'],row['start']) in by_key]

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
    print(f'measurement_driver_output_begin path={path} complete={str(complete).lower()} bytes={len(b)} sha256={hashlib.sha256(b).hexdigest()}',flush=True)
    print(b.decode(errors='replace'),flush=True); print('measurement_driver_output_end',flush=True)
def cancel_and_reap(p):
    if p.poll() is not None:
        return p.wait(timeout=2)
    p.terminate()  # Exact direct-child handle: Popen wait/reap establishes custody.
    try: return p.wait(timeout=2)
    except subprocess.TimeoutExpired:
        p.kill()
        try: return p.wait(timeout=2)
        except subprocess.TimeoutExpired as exc: raise RuntimeError('exact Cargo child remains unreaped after bounded KILL wait') from exc

def run(argv,path,deadline,env,source):
    print('measurement_driver_argv='+repr(argv),flush=True); print('measurement_driver_cwd='+str(source),flush=True); print('measurement_driver_log='+str(path),flush=True)
    command_start=time.monotonic()
    with path.open('wb') as f:
        if not callable(getattr(signal,'pthread_sigmask',None)):
            raise RuntimeError('cannot safely block interruption across exact Cargo child registration')
        old_handlers={sig:signal.signal(sig,_interrupt) for sig in (signal.SIGTERM,signal.SIGINT)}
        blocked=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT})
        persist_ledger([],state='spawn-in-progress')
        try:
            p=subprocess.Popen(argv,cwd=source,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=False)
        except BaseException:
            for sig,handler in old_handlers.items(): signal.signal(sig,handler)
            signal.pthread_sigmask(signal.SIG_SETMASK,blocked)
            raise
        ledger=[]
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK,blocked)
            print(f'measurement_driver_pid={p.pid} measurement_driver_pgid={os.getpgid(p.pid)}',flush=True)
            persist_ledger(ledger,state='monitoring')
            last_sample_started=None
            while p.poll() is None:
                if time.monotonic()>=deadline: raise TimeoutError('aggregate Cargo watchdog expired')
                sample_started=time.monotonic()
                sample(deadline)
                observed,rss=process_snapshot(p.pid,deadline)
                for row in observed:
                    if not any((x['pid'],x['start'])==(row['pid'],row['start']) for x in ledger): ledger.append(row)
                persist_ledger(ledger)
                descendants_now=len(observed)
                interval='first' if last_sample_started is None else f'{sample_started-last_sample_started:.3f}'
                last_sample_started=sample_started
                print(f'measurement_tree_descendants={max(0,descendants_now-1)} measurement_tree_rss_kib={rss} limit_descendants={MAX_DESCENDANTS} limit_rss_kib={MAX_RSS_KIB} sample_interval_seconds={interval} continuous_enforcement=false',flush=True)
                enforce_process_sample(observed,rss)
                time.sleep(max(0,sample_started+1-time.monotonic()))
            status=p.returncode; print(f'measurement_driver_status={status} measurement_driver_elapsed_seconds={time.monotonic()-command_start:.3f}',flush=True); emit(path,True); sample(deadline)
        except BaseException as exc:
            for sig in (signal.SIGTERM,signal.SIGINT): signal.signal(sig,signal.SIG_IGN)
            rc=cancel_and_reap(p)
            print(f'measurement_driver_cancelled_reaped=true measurement_driver_status={rc} cause={type(exc).__name__}; descendant_custody_not_implied=true',flush=True)
            emit(path,rc is not None); raise
        finally:
            for sig,handler in old_handlers.items(): signal.signal(sig,handler)
            signal.pthread_sigmask(signal.SIG_SETMASK,blocked)
    live=live_ledger_identities(ledger,deadline)
    print(f'final_owned_identity_readback_live={len(live)}',flush=True)
    if live:
        print('incomplete_cleanup_live_identities='+repr(live),flush=True)
        raise RuntimeError('recorded process descendants remain live; runtime must be retained')
    persist_ledger(ledger,complete=True,state='readback-complete')
    return status,path.read_text(errors='replace')

def main():
    # Setup commands below are external children too. Any interrupted setup is
    # deliberately incomplete so the adapter retains the runtime for review.
    persist_ledger([],state='setup-in-progress')
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
    adapter=Path('/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/run-macos-process-overhead-scoped.py')
    scoped=Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
    print(f'harness_sha256={sha(Path(__file__))}',flush=True)
    print(f'wrapper_sha256={sha(wrapper)}',flush=True)
    print(f'custody_adapter_sha256={sha(adapter)}',flush=True)
    print(f'shared_runner_reference_sha256={sha(scoped)}',flush=True)
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
if __name__ == '__main__':
    main()
