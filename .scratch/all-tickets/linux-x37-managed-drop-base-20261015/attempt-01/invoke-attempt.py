#!/usr/bin/env python3
import hashlib,json,os,re,subprocess,sys
from pathlib import Path
repo=Path('/var/home/Daniel/projects/rhai')
attempt=repo/'.scratch/all-tickets/linux-x37-managed-drop-base-20261015/attempt-01'
evidence=attempt/'evidence'
scope=Path('/root/.local/share/agent-builds/rhai/x37-base-20261015-01')
runner=Path('/var/home/Daniel/projects/agent-skills/tools/run_scoped.py')
script=attempt/'run-x37-linux-base.sh'
lock=repo/'.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock'
evidence.mkdir(parents=True,exist_ok=True)
assert not scope.exists(),str(scope)
scope.parent.mkdir(parents=True,exist_ok=True)
scope.mkdir(mode=0o700)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def out(args): return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)
capacity='utc='+out(['date','-u','+%FT%TZ']).strip()+'\n'
for args in (['uptime'],['df','-B1',str(repo)],['grep','-E','MemAvailable|MemTotal','/proc/meminfo']):
    capacity+=out(args)
capacity+='active cargo/rustc processes:\n'
ps=out(['ps','-eo','pid,ppid,etime,comm,args'])
capacity+='\n'.join(line for line in ps.splitlines() if ('cargo' in line or 'rustc' in line) and 'grep' not in line)+'\n'
(evidence/'capacity-before.txt').write_text(capacity)
rev=out(['git','-C',str(repo),'rev-parse','HEAD']).strip()
assert rev=='d304d1ad325275873b04b096cb9f519634125e00',rev
files={'Cargo.toml':sha(repo/'Cargo.toml'),'Cargo.lock':sha(lock),'src/packages/sys/process/unix.rs':sha(repo/'src/packages/sys/process/unix.rs'),'tests/sys_process.rs':sha(repo/'tests/sys_process.rs')}
obj={'project_revision':rev,'target':'lllm Linux x86_64/Bazzite 44','features':'testing-environ,sys','profile':'default','toolchain':'Rust/Cargo 1.77.2','test':'managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not','mutation':'invert only final sentinel-live assertion','expected_red':'101 at the inverted sentinel assertion after all managed members are absent and sentinel is independently observed live','restored_green':'1/1 with nonfinal live, final leader/worker/leaf absent, sentinel live then reaped','files':files,'lock_source':str(lock),'run_scoped_path':str(runner),'run_scoped_sha256':sha(runner),'scope':str(scope),'session_id':scope.name,'timeout_seconds_per_phase':300,'cargo_jobs':1,'estimated_additional_peak_bytes':3221225472,'capacity_evidence':'evidence/capacity-before.txt','script_sha256':sha(script)}
(attempt/'inputs.json').write_text(json.dumps(obj,indent=2)+'\n')
env=os.environ.copy()
env.update(TMPDIR=str(scope),PYTHONDONTWRITEBYTECODE='1')
with (evidence/'run-scoped.log').open('w') as log:
    result=subprocess.run([sys.executable,str(runner),'--','bash',str(script),str(scope)],cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT)
(evidence/'run-scoped-status.txt').write_text(f'runner_status={result.returncode}\n')
log=(evidence/'run-scoped.log').read_text(errors='replace')
print(log[-6000:])
if result.returncode:
    raise SystemExit(result.returncode)
runtime_match=re.search(r'^runtime=(.+)$',(evidence/'environment.txt').read_text(),re.M)
assert runtime_match
runtime=Path(runtime_match.group(1))
assert not runtime.exists(),str(runtime)
readback=subprocess.run([sys.executable,str(attempt/'postrun-readback.py'),str(evidence/'green.log')],cwd=repo,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
assert readback.returncode==0,readback.stdout
(evidence/'external-readback.txt').write_text(readback.stdout)
assert not any(scope.iterdir()),list(scope.iterdir())
scope.rmdir()
(evidence/'cleanup-readback.txt').write_text('runner_status=0\nruntime_absent=true\nsession_scope_removed=true\nscope='+str(scope)+'\nruntime='+str(runtime)+'\n'+readback.stdout)
rows=[]
for p in sorted(evidence.iterdir()):
    if p.is_file() and p.name!='evidence-export.sha256':
        rows.append(f'{sha(p)}  {p.name}')
(evidence/'evidence-export.sha256').write_text('\n'.join(rows)+'\n')
print('FINAL')
for name in ('statuses.csv','result.txt','cleanup-readback.txt'):
    print('--- '+name)
    print((evidence/name).read_text())
print('manifest_sha256='+sha(evidence/'evidence-export.sha256'))
