import os, shutil, subprocess, time
from pathlib import Path
root=Path.cwd()
evidence=root/'.scratch/unsupported-feature-proof'
runtime=Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
src=runtime/'source'; home=runtime/'cargo-home'; target=runtime/'target'; tmp=runtime/'tmp'
shutil.copytree(root,src,ignore=shutil.ignore_patterns('.git','.scratch','target','build'))
shutil.copy2(evidence/'scoped-Cargo.lock',src/'Cargo.lock')
home.mkdir(exist_ok=True); tmp.mkdir(exist_ok=True)
env=os.environ.copy(); env.update(CARGO_HOME=str(home),CARGO_TARGET_DIR=str(target),CARGO_BUILD_JOBS='2',CARGO_PROFILE_DEV_DEBUG='0',CARGO_INCREMENTAL='0',TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp))
logpath=evidence/'logs/sys-no_std-attempt3.log'
logpath.parent.mkdir(parents=True,exist_ok=True)
(evidence/'runtime-path-attempt3.txt').write_text(str(runtime)+'\n')
limit=1536*1024*1024; peak=0; samples=[]; start=time.monotonic()
def usage():
 total=0
 for base,dirs,files in os.walk(runtime):
  for name in dirs+files:
   try:
    st=(Path(base)/name).lstat(); total+=getattr(st,'st_blocks',(st.st_size+511)//512)*512
   except FileNotFoundError: pass
 return total
with logpath.open('w') as log:
 cmd=['cargo','check','--locked','--no-default-features','--features','sys,no_std']
 log.write('$ '+' '.join(cmd)+'\n'); log.flush()
 proc=subprocess.Popen(cmd,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT,text=True)
 while proc.poll() is None:
  size=usage(); peak=max(peak,size); samples.append(f'{time.monotonic()-start:.3f}\t{size}\n')
  if size>=limit:
   proc.terminate()
   try: proc.wait(timeout=1)
   except subprocess.TimeoutExpired: proc.kill(); proc.wait()
   raise SystemExit('stopped at 1.5 GiB preemptive cap')
  time.sleep(1)
 status=proc.wait()
text=logpath.read_text(errors='replace')
needle='error: the `sys` feature requires `std`; it cannot be combined with `no_std`'
count=text.splitlines().count(needle)
(evidence/'attempt3-resource-samples.tsv').write_text('elapsed_seconds\tbytes\n'+''.join(samples))
(evidence/'attempt3-metrics.txt').write_text(f'status={status}\nexpected_diagnostic_count={count}\npeak_sampled_runtime_bytes={peak}\npreemptive_limit_bytes={limit}\nelapsed_seconds={time.monotonic()-start:.3f}\nruntime_path={runtime}\n')
if status==0 or count!=1: raise SystemExit(f'expected status != 0 and exactly one intended diagnostic; got status={status}, count={count}')
