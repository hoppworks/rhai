import subprocess
remote = r'''
import pathlib,os,json,hashlib,shutil,time
stage=pathlib.Path('/root/rhai-linux-sys-process-example-66379d30-20261004')
scope=pathlib.Path('/root/.local/share/agent-builds/rhai/linux-sys-process-example-66379d30-20261004')
pins={
'source.tar':'0ab9ec63c8f4b5d603be0bbcd0f4d582d8ef0a3e08ceb188841ed961828c884b',
'Cargo.lock.accepted':'2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425',
'run-examples.py':'55c2a4a4c177f468757275a2691f73002a984a63b4c7cbba87314813a4b03d69',
'stage.sh':'d80d5f8e353a160a400a0b3f851e65abe9eb314b771d5004524d51c54e0dd415',
'launch.sh':'2381ebb7dd8bb29bedb55f5dbcd9b1d12b732834c00f2fc747d439b0f6902d6d',
'contract.md':'cba45561b10b29689bbd712c7cc8b601647c71fd0c8f99d686f879a27abcbc4a',
'archive-build-source.py':'a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b',
'runner/tools/run_scoped.py':'9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d',
'runner/tools/agentskills/__init__.py':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
'runner/tools/agentskills/pyguard.py':'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f'}
assert stage.is_dir() and not stage.is_symlink()
assert str(stage.resolve())=='/var/roothome/rhai-linux-sys-process-example-66379d30-20261004'
for name,digest in pins.items():
 p=stage/name
 assert p.is_file() and not p.is_symlink(),name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
manifest=(stage/'input-identities.sha256').read_text()
assert manifest==''.join(f'{digest}  {name}\n' for name in ['source.tar','Cargo.lock.accepted','run-examples.py','contract.md','launch.sh','stage.sh','archive-build-source.py','runner/tools/run_scoped.py','runner/tools/agentskills/__init__.py','runner/tools/agentskills/pyguard.py'] for digest in [pins[name]]),'manifest'
assert not scope.exists() and not scope.is_symlink(),'scope'
assert not (stage/'outer-evidence/outer-status.txt').exists(),'already terminal'
assert not (stage/'proof-evidence').exists(),'already run'
rows=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid(): continue
 try:
  args=(p/'cmdline').read_bytes().split(b'\0'); args=[a.decode(errors='replace') for a in args if a]
  comm=(p/'comm').read_text().strip()
  runner=any(pathlib.PurePosixPath(a).name=='run_scoped.py' for a in args[:3])
  if not runner and comm not in ('cargo','rustc','flutter','dart'): continue
  raw=(p/'stat').read_text();f=raw[raw.rfind(')')+2:].split()
  rows.append(dict(pid=int(p.name),start=f[19],pgid=int(f[2]),state=f[0],argv=args[:4]))
 except FileNotFoundError: pass
mem={a.split(':')[0]:a.split(':')[1].strip() for a in pathlib.Path('/proc/meminfo').read_text().splitlines()}
available=int(mem['MemAvailable'].split()[0]);free=shutil.disk_usage(stage).free
ready=not rows and available>=16777216 and free>=17179869184
print(json.dumps(dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),stage=str(stage.resolve()),inputs_verified=10,scope_absent=True,heavy=rows,mem_available_kib=available,disk_free_bytes=free,load=os.getloadavg(),ready=ready),indent=2))
raise SystemExit(0 if ready else 3)
'''
p=subprocess.run(['ssh','-o','BatchMode=yes','workhorse','python3','-'],input=remote,text=True)
raise SystemExit(p.returncode)
