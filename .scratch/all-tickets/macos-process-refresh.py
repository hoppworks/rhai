import hashlib, os, platform, re, shutil, subprocess, sys, time
from pathlib import Path
REPO=Path('/Users/hoppworks/projects/rhai-managed-unix-scope-close')
SOURCE_REF='e5b55460ff8f94dba5d35564ced640e6ac8ea3ee'
ARCHIVE_SHA='70b7404b1dd40c6371d5638d1e5492fe8ff6b73c03ddfd86ba7bfc68af65793c'
RUNTIME=Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
BASE=Path(os.environ['RHAI_RESUME_LOG_BASE']).absolute()
EVIDENCE=Path('/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/macos-process-refresh-evidence')
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
    if RUNTIME.is_symlink() or not RUNTIME.is_dir(): raise RuntimeError('unowned runtime path')
    if BASE.parent!=EVIDENCE or BASE.is_symlink(): raise RuntimeError('log base outside evidence directory')
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    print('phase=owner_suite_and_full_sys_process_resume',flush=True)
    print('scope=immutable_managed_scope_macos_development_refresh_not_release',flush=True)
    print(f'runtime_path={RUNTIME}',flush=True)
    print(f'python={sys.version.replace(chr(10)," ")} platform={platform.platform()}',flush=True)
    print(f'harness_pid={os.getpid()} supervisor_pid={os.getppid()} inherited_pgid={os.getpgid(0)}',flush=True)
    for name,p in [('cargo',CARGO),('rustc',RUSTC),('rustdoc',RUSTDOC)]:
        v=subprocess.check_output([str(p),'--version','--verbose'] if name=='rustc' else [str(p),'--version'],text=True,timeout=10).strip().replace('\n',' | ')
        print(f'{name}_path={p} {name}_version={v}',flush=True)
    hashes={n:hashlib.sha256(subprocess.check_output(['git','-C',str(REPO),'show',f'{SOURCE_REF}:{n}'],timeout=10)).hexdigest() for n in OVERLAYS}
    print('repo_head='+subprocess.check_output(['git','-C',str(REPO),'rev-parse',SOURCE_REF],text=True).strip(),flush=True)
    print('original_overlay_hashes='+repr(hashes),flush=True)
    wrapper=Path('/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/run-macos-process-refresh.sh')
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
    deadline=time.monotonic()+540
    # Native75 already proved this control. Only unit-test enum path and diagnostic formatting changed.
    accepted_control=EVIDENCE/'macos-process-refresh.LOytvN.cargo.wrong-expectation.log'
    if sha(accepted_control)!='0cd30945ba91709ea75e3a13f23a5f02db23a5314141f989e3716cd0fc0bf8ab': raise RuntimeError('accepted native75 control receipt changed')
    accepted_output=accepted_control.read_text()
    if not re.search(r'left:\s*0\s+right:\s*42',accepted_output) or '1 failed' not in accepted_output:
        raise RuntimeError('accepted native75 control lacks exact API assertion')
    print(f'reused_native75_exit_control={accepted_control} sha256={sha(accepted_control)} production_unchanged_test_only_changes=true',flush=True)
    unix_path=source/'src/packages/sys/process/unix.rs'
    unix_original=unix_path.read_text()
    branch_start=unix_original.index('                Err(error) if error.raw_os_error() == Some(libc::EPERM) => {', unix_original.index('fn supervise('))
    branch_end=unix_original.index('                Err(error) => {', branch_start)
    # Remove provisional retry while retaining the real Engine regression and fault seam.
    # Falling through to the adjacent generic error arm reproduces immediate commitment.
    broken_unix=unix_original[:branch_start]+unix_original[branch_end:]
    regression='packages::sys::process::unix::tests::managed_run_retries_provisional_group_eperm_within_one_observation_window'
    regression_log=BASE.with_name(BASE.name+'.provisional-eperm-control.log')
    try:
        unix_path.write_text(broken_unix)
        cmd=[str(CARGO),'test','--locked','--lib','--features','testing-environ,sys',regression,'--','--exact','--nocapture','--test-threads=1']
        status,out=run(cmd,regression_log,deadline,env,source)
        if status!=101 or 'a later exact ESRCH observation closes the scope' not in out or '1 failed' not in out:
            raise RuntimeError('provisional EPERM control did not reach intended real Engine recovery assertion')
        print('provisional_eperm_control_status=101 intended_one_shot_recovery_failure=true',flush=True)
    finally:
        unix_path.write_text(unix_original)
        restored={n:sha(source/n) for n in OVERLAYS}
        if restored!=hashes: raise RuntimeError('provisional EPERM control restoration mismatch')
        print('provisional_control_restored_private_overlay_hashes='+repr(restored),flush=True)
    owner=BASE.with_name(BASE.name+'.owner.log')
    cmd=[str(CARGO),'test','--locked','--lib','--features','testing-environ,sys','packages::sys::process::unix::tests::','--','--nocapture','--test-threads=1']
    status,out=run(cmd,owner,deadline,env,source)
    summaries=re.findall(r'(?m)^test result: ok\. (\d+) passed; 0 failed;',out)
    receipt=re.search(r'(?m)^(?:test packages::sys::process::unix::tests::public_kill_on_drop_false_final_lease_retires_owner_and_worker \.\.\. )?false-policy-owner-retired pid=(\d+) slot_retired=true worker_done=true reap=ESRCH stdout=retained-output stdout_complete=true stderr_complete=true exit=Code\(0\)$',out)
    if status!=0 or not summaries or int(summaries[-1])!=21 or not receipt: raise RuntimeError('owner suite did not pass its retained-owner receipt')
    owner_count=int(summaries[-1])
    print(f'owner_suite status={status} tests={owner_count} receipt_pid={receipt.group(1)}',flush=True)
    suite=BASE.with_name(BASE.name+'.sys_process.log')
    cmd=[str(CARGO),'test','--locked','--test','sys_process','--features','testing-environ,sys','--','--nocapture','--test-threads=1']
    status,out=run(cmd,suite,deadline,env,source)
    summaries=re.findall(r'(?m)^test result: ok\. (\d+) passed; 0 failed;',out)
    if status!=0 or not summaries or int(summaries[-1])!=29: raise RuntimeError('full sys_process suite failed or unexpected outer count')
    final={n:sha(source/n) for n in OVERLAYS}
    if final!=hashes: raise RuntimeError('final private manifest differs from frozen overlays')
    print('final_private_overlay_hashes='+repr(final),flush=True)
    for label,p in [('owner',owner),('sys_process',suite)]: print(f'{label}_log={p} bytes={p.stat().st_size} sha256={sha(p)}',flush=True)
    print(f'owner_suite_tests={owner_count}',flush=True)
    print(f'full_sys_process_tests={summaries[-1]}',flush=True)
    print('resumed_check_status=passed',flush=True)
main()
