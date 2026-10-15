#!/usr/bin/env python3
import hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
repo=Path('/var/home/Daniel/projects/rhai')
attempt=repo/'.scratch/all-tickets/x36-managed-scope-setup-20261008/attempt-12'
evidence=attempt/'evidence'
scope=Path('/root/.local/share/agent-builds/rhai/x36-unchecked-20261015-02')
runner=Path('/var/home/Daniel/projects/agent-skills/tools/run_scoped.py')
script=attempt/'run-x36-linux-unchecked.sh'
lock_archive=repo/'.scratch/all-tickets/x36-managed-scope-setup-20261008/attempt-06/source-input.tar.gz'
evidence.mkdir(parents=True,exist_ok=True)
assert not scope.exists(), f'owned scope already exists: {scope}'
scope.parent.mkdir(parents=True,exist_ok=True)
scope.mkdir(mode=0o700)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def capture(args):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)
capacity='utc='+capture(['date','-u','+%FT%TZ']).strip()+'\n'
for args in (['uptime'],['df','-B1',str(repo)],['grep','-E','MemAvailable|MemTotal','/proc/meminfo']):
    capacity+=capture(args)
capacity+='active_cargo_rustc_processes:\n'
ps=capture(['ps','-eo','pid,ppid,etime,comm,args'])
capacity+='\n'.join(line for line in ps.splitlines() if ('cargo' in line or 'rustc' in line) and 'grep' not in line)+'\n'
(evidence/'capacity-before.txt').write_text(capacity)
rev=capture(['git','-C',str(repo),'rev-parse','HEAD']).strip()
assert rev=='ffeab7c7958e69ebada7064aa9d0ca31f84edb13', rev
source_hash=hashlib.sha256((repo/'src/packages/sys/process/unix.rs').read_bytes()).hexdigest()
source_patch_hash=hashlib.sha256((attempt/'source-delta.patch').read_bytes()).hexdigest()
files={'Cargo.toml':'cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e','Cargo.lock':'2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425','src/packages/sys/process/unix.rs':source_hash}
obj={'project_revision':rev,'target':'lllm Linux x86_64','features':'testing-environ,sys,unchecked','toolchain':'Rust/Cargo 1.77.2','test':'managed_scope_kernel_setpgid_denial_cleans_created_group','phases':['disable only the test kernel-denial seam; expected public assertion RED 101','restore byte-identical source; targeted GREEN 0'],'files':files,'source_delta_patch_sha256':source_patch_hash,'source_delta':'one cfg gate around Engine::set_max_string_size in the process output test helper; omitted only because API is unavailable under unchecked','lock_source':'attempt-06/source-input.tar.gz; SHA-256 '+sha(lock_archive),'run_scoped_path':str(runner),'run_scoped_sha256':sha(runner),'scope':str(scope),'session_id':scope.name,'timeout_seconds_per_phase':300,'cargo_jobs':1,'estimated_additional_peak_bytes':3221225472,'capacity_evidence':'evidence/capacity-before.txt','preserved_foreign_activity':'Tauron gateway cargo build observed separately; not owned or modified','script_sha256':sha(script)}
(attempt/'inputs.json').write_text(json.dumps(obj,indent=2)+'\n')
env=os.environ.copy()
env['TMPDIR']=str(scope)
env['PYTHONDONTWRITEBYTECODE']='1'
with (evidence/'run-scoped.log').open('w') as out:
    result=subprocess.run([sys.executable,str(runner),'--','bash',str(script),str(scope)],cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT)
(evidence/'run-scoped-status.txt').write_text(f'runner_status={result.returncode}\n')
log=(evidence/'run-scoped.log').read_text(errors='replace')
print(log[-8000:])
if result.returncode:
    raise SystemExit(result.returncode)
runtime_match=re.search(r'^runtime=(.+)$',(evidence/'environment.txt').read_text(),re.M)
assert runtime_match, 'runtime path missing from evidence'
runtime=Path(runtime_match.group(1))
assert not runtime.exists(), f'private runtime remains: {runtime}'
readback=subprocess.run([sys.executable,str(attempt/'postrun-readback.py'),str(evidence)],cwd=repo,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
assert readback.returncode==0,readback.stdout
(evidence/'external-readback.txt').write_text(readback.stdout)
assert not any(scope.iterdir()),f'scope is not empty: {list(scope.iterdir())}'
scope.rmdir()
cleanup='runner_status=0\nruntime_absent=true\nsession_scope_removed=true\nscope='+str(scope)+'\nruntime='+str(runtime)+'\n'+readback.stdout
(evidence/'cleanup-readback.txt').write_text(cleanup)
manifest=evidence/'evidence-export.sha256'
if manifest.exists(): manifest.unlink()
rows=[]
for p in sorted(evidence.iterdir()):
    if p.is_file() and p.name!='evidence-export.sha256':
        rows.append(f'{sha(p)}  {p.name}')
manifest.write_text('\n'.join(rows)+'\n')
print('FINAL RESULTS')
for name in ('statuses.csv','result.txt','cleanup-readback.txt'):
    print('--- '+name)
    print((evidence/name).read_text())
print('manifest_sha256='+sha(manifest))
