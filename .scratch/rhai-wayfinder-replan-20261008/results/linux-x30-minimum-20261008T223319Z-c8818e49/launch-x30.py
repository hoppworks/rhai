
from pathlib import Path
import subprocess,os,json,time,hashlib,shutil
E=Path(__file__).resolve().parent
selection=json.loads((E/'selection.json').read_text())
plan=json.loads((E/'scope-plan.json').read_text())
repo=Path('/root/projects/rhai-wayfinder-20261008').resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
runner=Path('/home/Daniel/projects/agent-skills/tools/run_scoped.py')
helper=E/'verify-x30.py'
review=repo/'.scratch/rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/custody-review.md'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==selection['revision']
assert sha(runner)==selection['runner_sha256']
assert sha(helper)==plan['helper_sha256']
assert sha(E/'Cargo.lock.accepted')==selection['lock_sha256']
for name,want in selection['historical_files'].items():assert sha(E/name)==want,name
assert 'linux-x30-minimum-20261008T223319Z-c8818e49' in review.read_text(),'independent prepared entry review missing'
assert not (E/'launcher.json').exists(),'one prepared invocation only; no automatic replay'
def proc_rows():
 rows=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   raw=(p/'stat').read_text();parts=raw[raw.rindex(')')+2:].split()
   cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   rows.append({'pid':int(p.name),'ppid':int(parts[1]),'pgid':int(parts[2]),'start':parts[19],'comm':raw[raw.index('(')+1:raw.rindex(')')],'cmd':cmd})
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 return rows
heavy=[r for r in proc_rows() if r['pid']!=os.getpid() and (r['comm'] in ['cargo','rustc','rustdoc','cc1','cc1plus','clang','clang++'] or (r['comm'].startswith('python') and '/tools/run_scoped.py' in r['cmd']))]
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
capacity={'mem_available_bytes':mem,'disk_available_bytes':shutil.disk_usage(repo).free,'cpu_count':os.cpu_count(),'load':list(os.getloadavg()),'heavy_processes':heavy}
assert not heavy and mem>=16*1024**3 and capacity['disk_available_bytes']>=16*1024**3,('native capacity unavailable',capacity)
scope=Path(plan['scope'])
assert scope.parent.is_dir() and not scope.exists() and not scope.is_symlink()
scope.mkdir(mode=0o700);identity=scope.stat()
argv=['python3','-B',str(runner),'--timeout','1200','--','python3','-B',str(helper),str(E)]
env=dict(os.environ,TMPDIR=str(scope.resolve()),PYTHONDONTWRITEBYTECODE='1')
started=time.monotonic()
with (E/'runner.stdout').open('xb') as stdout,(E/'runner.stderr').open('xb') as stderr:
 p=subprocess.Popen(argv,cwd=repo,env=env,stdout=stdout,stderr=stderr)
 stat=None
 try:
  stat=(Path('/proc')/str(p.pid)/'stat').read_text()
  data={'pid':p.pid,'start_stat':stat,'cwd':str(repo),'scope':str(scope),'scope_device':identity.st_dev,'scope_inode':identity.st_ino,'scope_uid':identity.st_uid,'argv':argv,'runner_sha256':sha(runner),'helper_sha256':sha(helper),'review_sha256':sha(review),'capacity':capacity,'outer_pid':os.getpid()}
  (E/'launcher.json').write_text(json.dumps(data,indent=2)+'\n')
 except BaseException as exc:
  (E/'launcher-bookkeeping-error.json').write_text(json.dumps({'error':repr(exc),'runner_started':True,'action':'wait for this existing finite invocation; do not relaunch'},indent=2)+'\n')
 finally:
  code=p.wait(timeout=1260)
 (E/'runner.status').write_text(str(code)+'\n')
elapsed=round(time.monotonic()-started,3)
runtime_data=json.loads((E/'runtime-identity.json').read_text()) if (E/'runtime-identity.json').exists() else None
runtime_absent=runtime_data is not None and not Path(runtime_data['path']).exists()
identities=[{'pid':p.pid,'start':stat[stat.rindex(')')+2:].split()[19]}] if stat is not None else []
if (E/'result.json').exists():
 for sample in json.loads((E/'result.json').read_text())['samples']:
  identities.extend({'pid':r['pid'],'start':r['start']} for r in sample['processes'])
unique={(r['pid'],r['start']) for r in identities}
live=proc_rows();remaining=[r for r in live if (r['pid'],r['start']) in unique]
same=scope.stat().st_dev==identity.st_dev and scope.stat().st_ino==identity.st_ino and scope.stat().st_uid==identity.st_uid
empty=not list(scope.iterdir())
retired=False
if code is not None and stat is not None and runtime_absent and same and empty and not remaining:
 scope.rmdir();retired=True
(E/'cleanup.json').write_text(json.dumps({'runner_exit':code,'runner_identity_captured':stat is not None,'outer_elapsed_seconds':elapsed,'runtime':runtime_data,'runtime_absent':runtime_absent,'scope':str(scope),'scope_identity_matches':same,'scope_empty':empty,'scope_retired':retired,'scope_absent':not scope.exists(),'observed_identities':len(unique),'remaining_owned_identities':remaining,'foreign_resources_changed':False},indent=2)+'\n')
print(json.dumps({'runner_exit':code,'outer_elapsed_seconds':elapsed,'runtime_absent':runtime_absent,'scope_retired':retired}),flush=True)
assert code==0 and retired,'Inspect exported originals; no automatic rerun'
