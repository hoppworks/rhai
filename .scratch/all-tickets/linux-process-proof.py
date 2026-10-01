#!/usr/bin/env python3
"""Source-only prepared Linux process proof driver; executed only on stage host."""
import hashlib, os, pathlib, shutil, subprocess, sys, tarfile, time, re

STAGE=pathlib.Path(os.environ['PROOF_STAGE']); E=STAGE/'evidence'
R=pathlib.Path(os.environ['AGENT_RUNTIME_DIR']); SRC=R/'source'; TARGET=R/'target'
LOCK_BASE=STAGE/'Cargo.lock.baseline'
LOCK_SHA='8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
LOCK_EDGE='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
ARCHIVE_SHA='030bc9630b1348ff1dd540985e3032d2840c4dfb3a462499254758a8d6c8ad91'
RUST=pathlib.Path('/root/.rustup/toolchains/1.93.0-x86_64-unknown-linux-gnu/bin')
OUTER=time.monotonic()+600; CARGO=time.monotonic()+540; HARD=2*1024*1024; STOP=1572864
E.mkdir(parents=True,exist_ok=True)
emit('PRIVATE_RUNTIME '+str(R))
def emit(s): print(s,flush=True)
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
if sha(LOCK_BASE)!=LOCK_SHA: raise SystemExit('baseline lock hash mismatch')
archive=STAGE/'source.tar'
if sha(archive)!=ARCHIVE_SHA: raise SystemExit('source archive hash mismatch')
with tarfile.open(archive) as t: t.extractall(SRC, filter='data')
shutil.copy2(LOCK_BASE,SRC/'Cargo.lock')
if not (SRC/'Cargo.toml').exists(): raise SystemExit('workspace archive incomplete')
manifest=(SRC/'Cargo.toml').read_text()
manifest=manifest.replace('[workspace]', '[workspace]', 1)
root_manifest=SRC/'Cargo.toml'
if 'libc = { version = "=0.2.189", optional = true }' not in root_manifest.read_text():
    raise SystemExit('frozen production manifest lacks exact optional libc dependency')
lock=SRC/'Cargo.lock'; s=lock.read_text(); start=s.index('name = "rhai"\n'); end=s.index('[[package]]',start); block=s[start:end]
if ' "libc",\n' not in block:
    if ' "libm",\n' not in block: raise SystemExit('expected rhai lock dependency insertion anchor missing')
    block=block.replace(' "libm",\n',' "libc",\n "libm",\n',1); s=s[:start]+block+s[end:]; lock.write_text(s)
if sha(SRC/'Cargo.lock')!=LOCK_EDGE: raise SystemExit('private edge-only lock SHA mismatch')
env=os.environ.copy(); env.update(CARGO_HOME=str(R/'cargo-home'),RUSTUP_HOME=str(R/'rustup-home'),CARGO_TARGET_DIR=str(TARGET),TMPDIR=str(R/'tmp'),CARGO_BUILD_JOBS='2',RUSTC=str(RUST/'rustc'),RUSTDOC=str(RUST/'rustdoc'),PATH=str(RUST)+':'+env['PATH'])
for p in (R/'cargo-home',R/'rustup-home',R/'tmp',TARGET): p.mkdir(parents=True,exist_ok=True)
cargo=RUST/'cargo'
if not all(x.is_file() for x in (cargo,RUST/'rustc',RUST/'rustdoc')): raise SystemExit('direct Rust 1.93 toolchain incomplete')
def run(label,args,expect=0):
    if time.monotonic()>min(OUTER,CARGO): raise TimeoutError('600s outer or 540s aggregate Cargo monotonic deadline')
    start=time.monotonic(); p=subprocess.Popen([str(cargo),*args],cwd=SRC,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=False)
    try: output,_=p.communicate(timeout=max(1,min(OUTER,CARGO)-time.monotonic()))
    except subprocess.TimeoutExpired: raise TimeoutError(f'{label} exceeded aggregate Cargo/outer monotonic deadline')
    (E/(label+'.log')).write_text(output); (E/(label+'.status')).write_text(str(p.returncode)+'\n')
    emit(f'{label} status={p.returncode} elapsed={time.monotonic()-start:.2f}s')
    if p.returncode!=expect: raise RuntimeError(f'{label} expected {expect}, got {p.returncode}')
    size=int(subprocess.check_output(['du','-sk',str(R)],text=True).split()[0]); emit(f'PRIVATE_RUNTIME sampled_storage_kib={size}')
    if size>=STOP or size>=HARD: raise RuntimeError(f'sampled storage ceiling reached: {size} KiB')
    return p.returncode,output
BASE=['test','--locked','--no-fail-fast','--features','testing-environ,sys']
test='direct_spawn_kill_on_drop_false_preserves_child_and_capture'
impl=SRC/'src/packages/sys/process/unix.rs'; original=impl.read_bytes(); source_sha=hashlib.sha256(original).hexdigest()
old=b'if !state.terminal && state.kill_on_drop {'; new=b'if !state.terminal {'
if original.count(old)!=1: raise SystemExit('expected one exact false-policy drop guard')
try:
    impl.write_bytes(original.replace(old,new,1))
    label='known-broken-direct-control'
    status,log=run(label,BASE+['--test','sys_process',test,'--','--exact','--nocapture','--test-threads=1'],expect=101)
    started=re.search(r'direct_drop_fixture_started root=(\S+) test_pid=(\d+) child_pid=(\d+)',log)
    observed=re.search(r'direct_drop_after_final_client_drop pid=(\d+) alive=false challenge_ack=false completion_exists=false',log)
    cleanup=re.search(r'direct_drop_fixture_cleanup root=(\S+) pid=(\d+) esrch=true',log)
    required=(f'test {test} ...' in log and 'test result: FAILED. 0 passed; 1 failed;' in log and
      'kill_on_drop(false) must preserve the child after final handle drop' in log and started and observed and cleanup and
      observed.group(1)==started.group(3) and cleanup.group(1)==started.group(1) and cleanup.group(2)==started.group(3) and
      int(started.group(2))!=int(started.group(3)) and not pathlib.Path(started.group(1)).is_symlink() and
      pathlib.Path(started.group(1)).parent==R/'tmp' and
      re.fullmatch(r'rhai-sys-test-'+started.group(2)+r'-'+test+r'-\d+',pathlib.Path(started.group(1)).name) and
      not pathlib.Path(started.group(1)).exists())
    if not required: raise RuntimeError('known-broken control lacked named survival assertion/fixture cleanup receipts')
finally:
    impl.write_bytes(original)
if hashlib.sha256(impl.read_bytes()).hexdigest()!=source_sha: raise RuntimeError('production source restoration hash mismatch')
emit(f'control_source_restored_sha256={source_sha}')
for name in ('direct_spawn_kill_on_drop_false_preserves_child_and_capture','managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit'):
    _,log=run('restored-'+name,BASE+['--test','sys_process',name,'--','--exact','--nocapture','--test-threads=1'])
    if f'test result: ok. 1 passed; 0 failed;' not in log: raise RuntimeError(f'{name} did not pass exactly once')
    if name.startswith('managed_') and not re.search(r'managed_false_drop_after_leader_exit .*leader_esrch=true .*worker_esrch=true .*leaf_esrch=true .*sentinel_live=true',log):
        raise RuntimeError('managed fixture failed exact member/sentinel cleanup receipt')
_,log=run('unix-owner',BASE+['--lib','packages::sys::process::unix::tests::','--','--nocapture','--test-threads=1'])
if 'test result: FAILED.' in log or not re.search(r'test result: ok\. \d+ passed; 0 failed;',log): raise RuntimeError('Unix owner suite summary failed/missing')
_,log=run('full-sys-process',BASE+['--test','sys_process','--','--test-threads=1'])
if 'test result: FAILED.' in log or not re.search(r'test result: ok\. \d+ passed; 0 failed;',log): raise RuntimeError('public sys_process suite summary failed/missing')
emit('SOURCE_ONLY_PACKAGE_COMPLETE')
