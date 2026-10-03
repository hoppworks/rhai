#!/usr/bin/env python3
"""Hash-gated readback/export and exact stage retirement for run96."""
from __future__ import annotations
import argparse, hashlib, json, shlex, subprocess, sys, tarfile, tempfile
from pathlib import Path, PurePosixPath

STAGE='/root/rhai-linux-managed-success-20261003-7d045f21-96'
SCOPE='/root/.local/share/agent-builds/rhai/linux-managed-success-20261003-7d045f21-96'
PHYSICAL='/var/roothome/rhai-linux-managed-success-20261003-7d045f21-96'
REV='003da06421fbd11c26e0c96ab5013416c0939a1d'
ARCHIVE='f62ea7430f8a92db7210055373f9e96b2d850d3564c4962844c80056b7294d1a'
LOCK='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TEST='e0034cf3a69ccf6107a9dfbc0854c0147ec2d93fdda8acf5ed6b07e683e1dc14'
CONTRACT='1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41'
PROOF='83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0'; STAGE_RECIPE='67e13bdd24c406039cd17d96e3224a0124b1521f522ea86db9819404c0de56cb'; LAUNCH='27e1ee59a936fefaab51172aa0b27d6b877f3eda1e37ca119a2967c6e5f6ff50'
REMOTE=r'''import hashlib,json,pathlib,re,subprocess,sys
stage=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); physical=pathlib.Path(sys.argv[3])
if not stage.is_dir() or stage.is_symlink() or stage.resolve()!=physical: raise SystemExit('run96 stage identity mismatch')
if scope.exists() or scope.is_symlink(): raise SystemExit('run96 private scope remains')
subprocess.run(['sha256sum','--check','input-identities.sha256'],cwd=stage,check=True,stdout=subprocess.DEVNULL)
if hashlib.sha256((stage/'source.tar').read_bytes()).hexdigest()!='f62ea7430f8a92db7210055373f9e96b2d850d3564c4962844c80056b7294d1a': raise SystemExit('source archive mismatch')
if hashlib.sha256((stage/'Cargo.lock.accepted').read_bytes()).hexdigest()!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise SystemExit('lock mismatch')
if hashlib.sha256((stage/'contract-source.md').read_bytes()).hexdigest()!='1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41': raise SystemExit('contract mismatch')
if not (stage/'proof-evidence/source-restoration.json').is_file(): raise SystemExit('restoration receipt missing')
rest=json.loads((stage/'proof-evidence/source-restoration.json').read_text())
if not rest.get('restored') or rest.get('original_sha256',{}).get('tests/sys_process.rs')!='e0034cf3a69ccf6107a9dfbc0854c0147ec2d93fdda8acf5ed6b07e683e1dc14' or rest.get('error') is not None: raise SystemExit('test source restoration not verified')
e=stage/'outer-evidence'; status_names=('outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status')
statuses={n:int((e/n).read_text().strip()) for n in status_names}
if statuses!={'outer-status.txt':0,'run-scoped.status':0,'pid-readback.status':0,'pid-readback-launcher.status':0}: raise SystemExit(f'run96 outer/custody status mismatch: {statuses}')
for n in ('runtime-cleanup.tsv','scope-cleanup.tsv'):
 if 'cleanup_status=0' not in (e/n).read_text(): raise SystemExit(f'exact runtime/scope cleanup missing: {n}')
def read_owned(path,required):
 rows=path.read_text(errors='strict').splitlines(); seen=set(); groups=set(); records=[]
 for line in rows[1:]:
  f=line.split('\t',5)
  if len(f)!=6 or not f[1].isdigit() or not f[2].isdigit() or not f[3].isdigit() or not f[4].isdigit(): raise SystemExit(f'malformed custody row: {line!r}')
  label,pid,ppid,pgid,start,_cmd=f; pid=int(pid); pgid=int(pgid); seen.add(label)
  try:
   raw=pathlib.Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==start
  except FileNotFoundError: alive=False
  except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f'exact custody identity unreadable {label}/{pid}: {ex}')
  if alive: raise SystemExit(f'owned process remains: {label} {pid}/{start}')
  if label in ('helper','scoped-supervisor','launcher','run-scoped'): groups.add(pgid)
  records.append({'label':label,'pid':pid,'start_ticks':start,'ppid':int(ppid),'pgid':pgid,'matching_process_alive':False})
 if not required.issubset(seen): raise SystemExit(f'required custody identities missing: {required-seen}')
 return records,groups
owned,groups=read_owned(stage/'proof-evidence/process-identities.tsv',{'helper','scoped-supervisor'})
launchers,launcher_groups=read_owned(e/'launcher-identities.tsv',{'launcher','run-scoped'})
if not groups: raise SystemExit('helper process groups were not recorded')
ps0=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
left=[[int(x.split()[0]),int(x.split()[1])] for x in ps0.splitlines() if len(x.split())==2 and int(x.split()[1]) in groups|launcher_groups]
if left: raise SystemExit(f'owned helper/launcher process group remains: {left!r}')
p=stage/'proof-evidence'
def read(label,suffix): return (p/(label+'.'+suffix)).read_text(errors='strict')
import importlib.util
helper=stage/'linux-managed-success-proof.py'
if hashlib.sha256(helper.read_bytes()).hexdigest()!='83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0': raise SystemExit('proof helper hash mismatch')
spec=importlib.util.spec_from_file_location('managed_success_proof',helper); proof=importlib.util.module_from_spec(spec); sys.modules[spec.name]=proof; spec.loader.exec_module(proof)
SUCCESS=proof.SUCCESS; HELD=proof.HELD
def segments(stdout,names):
 starts={}
 for name in names:
  found=list(re.finditer(r'(?m)^test '+re.escape(name)+r' \.\.\..*$',stdout))
  if len(found)!=1: raise SystemExit(f'outer exact test prefix missing/duplicated: {name}')
  starts[name]=found[0].start()
 order=sorted((p,n) for n,p in starts.items())
 return {name:stdout[pos:(order[i+1][0] if i+1<len(order) else len(stdout))] for i,(pos,name) in enumerate(order)}
def outer(label,names,passed):
 out=read(label,'stdout'); seg=segments(out,names)
 sums=re.findall(r'(?m)^test result: .*?$',out)
 if not sums: raise SystemExit(f'{label}: outer stdout summary missing')
 last=sums[-1]
 pat=(r'test result: ok\. 2 passed; 0 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s' if passed else r'test result: FAILED\. 0 passed; 1 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s')
 if not re.fullmatch(pat,last): raise SystemExit(f'{label}: outer terminal summary mismatch: {last!r}')
 if not passed:
  failed=out.split('failures:',1)
  names_failed=[x.strip() for x in failed[-1].split('test result:',1)[0].splitlines() if x.strip() and x.strip()!='failures:']
  if names_failed!=[SUCCESS]: raise SystemExit(f'{label}: wrong named outer failure {names_failed!r}')
  err=read(label,'stderr'); expected={'held-mode-red':'managed run must return a successful zero-exit report after exact foreign reaping','require-exit-seven':'managed-success-control require-exit-seven assertion','require-sentinel-absent':'managed-success-control require-sentinel-absent assertion'}[label]
  if len(re.findall(r"(?m)^thread '"+re.escape(SUCCESS)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err))!=1 or err.count(expected)!=1: raise SystemExit(f'{label}: named panic/assertion mismatch')
  text=out+err; early=proof.early_receipt(text,label); got=proof.acquired_for_early(text,early,label)
  rows=proof.acquired_rows(text)
  if len(rows)!=3 or len({x[0] for x in rows})!=3: raise SystemExit(f'{label}: exact one-test PIDFD inventory mismatch')
  if label=='held-mode-red':
   cleanup=re.search(r'managed-scope sentinel_cleanup pid=(\d+) status=Some\(ExitStatus\(unix_wait_status\(\d+\)\)\) esrch=true',text)
   if not cleanup or int(cleanup.group(1))!=early['sentinel'][0]: raise SystemExit('held-mode RED lacks exact sentinel cleanup')
  elif 'managed_prompt_reap_success' not in text or 'sentinel_live_at_return=true' not in text or 'sentinel_reaped_after_return=true' not in text:
   raise SystemExit(f'{label}: wrong-control did not fail after exact success cleanup')
  return last,seg,err
 return last,seg,read(label,'stderr')
def verify_absent(label,identities,group):
 rows=[]
 if len({pid for _,pid,start in identities})!=len(identities): raise SystemExit(f'{label}: duplicate fixture PID')
 for name,pid,start in identities:
  try:
   raw=pathlib.Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==str(start)
  except FileNotFoundError: alive=False
  except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f'{label}: PID/start unreadable {name}: {ex}')
  if alive: raise SystemExit(f'{label}: exact fixture PID/start remains {name}={pid}/{start}')
  rows.append({'label':name,'pid':pid,'start_ticks':start,'matching_identity_alive':False})
 ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
 members=[[int(x.split()[0]),int(x.split()[1])] for x in ps.splitlines() if len(x.split())==2 and int(x.split()[1])==group]
 if members: raise SystemExit(f'{label}: exact fixture group remains populated: {members}')
 return rows
expected_closures=set()
all_fixture_ids=[]; all_fixture_groups=set()
def check_closure(name,expected,group,pidfds):
 path=p/(name+'.json')
 if not path.is_file(): raise SystemExit(f'required closure file missing: {path.name}')
 d=json.loads(path.read_text()); rows=d.get('identities')
 if not isinstance(rows,list) or d.get('group')!=group or d.get('group_members_after_cleanup')!=[]: raise SystemExit(f'{name}: closure group/rows malformed')
 got={(r.get('label'),int(r.get('pid',-1)),int(r.get('start_ticks',-1))) for r in rows if isinstance(r,dict) and r.get('matching_identity_alive') is False}
 if got!=set(expected): raise SystemExit(f'{name}: closure identities mismatch: {got!r}')
 acquired=d.get('pidfd_identities')
 expected_rows=[{'pid':pid,'start_ticks':vals[0],'ppid':vals[1],'pgid':vals[2]} for pid,vals in sorted(pidfds.items())]
 if acquired!=expected_rows: raise SystemExit(f'{name}: PIDFD closure identities mismatch')
 readrows=verify_absent(name,[(lab,pid,start) for lab,pid,start in expected],group)
 all_fixture_ids.extend(readrows); all_fixture_groups.add(group)
 closure_path=name
 expected_closures.add(closure_path+'.json')

def validate_green(label):
 text=read(label,'stdout')+read(label,'stderr'); out=read(label,'stdout')
 cases=segments(out,[SUCCESS,HELD])
 success=cases[SUCCESS]+read(label,'stderr'); held=cases[HELD]+read(label,'stderr')
 sf=proof.require_success(success)
 hids,hgroup,hpidfds=proof.exact_boundary(held)
 acquired=proof.require_acquisition_inventory(text,6,label)
 held_map={int(x['pid']):(int(x['start_ticks']),int(x['ppid']),int(x['pgid'])) for x in hpidfds}
 if acquired!={**sf['pidfds'],**held_map} or set(sf['pidfds']).intersection(held_map): raise SystemExit(f'{label}: two cases do not bind a disjoint complete six-PIDFD inventory')
 if 'sentinel_live_at_return=true' not in success or 'sentinel_reaped_after_return=true' not in success or 'stdout_complete=true stderr_complete=true' not in success: raise SystemExit(f'{label}: success API capture/sentinel boundary incomplete')
 early=proof.early_receipt(success,label)
 s_expected=[(n,*sf[n]) for n in ('host','leader','worker','leaf','sentinel')]+[('reaper',*early['reaper'])]
 check_closure('success-'+label+'-fixture-closure',s_expected,sf['group'],sf['pidfds'])
 h_expected=[(name,pid,int(start)) for name,pid,start in hids]
 check_closure(label+'-held-closure',h_expected,hgroup,{int(x['pid']):(int(x['start_ticks']),int(x['ppid']),int(x['pgid'])) for x in hpidfds})

expected={'held-mode-red':101,'require-exit-seven':101,'require-sentinel-absent':101,'green-row-1':0,'green-row-2':0,'green-row-3':0,'green-row-4':0}
for label,status in expected.items():
 if int((p/(label+'.status')).read_text().strip())!=status: raise SystemExit(f'{label}: expected status {status}')
 names=[SUCCESS,HELD] if label.startswith('green-') else [SUCCESS]
 _,case_segments,err=outer(label,names,passed=label.startswith('green-'))
 if label.startswith('green-'):
  validate_green(label)
 else:
  text=read(label,'stdout')+err; early=proof.early_receipt(text,label); got=proof.acquired_for_early(text,early,label)
  closure_name=label+'-fixture-closure'; ids=[(n,*early[n]) for n in ('reaper','host','leader','worker','leaf','sentinel')]
  check_closure(closure_name,ids,early['group'],got)
  if label!='held-mode-red':
   facts=proof.require_success(text)
   for n in ('host','leader','worker','leaf','sentinel'):
    if facts[n]!=early[n]: raise SystemExit(f'{label}: final success/early {n} identity mismatch')
closure_files={x.name for x in p.glob('*-closure.json')}
if closure_files!=expected_closures: raise SystemExit(f'closure inventory mismatch expected={sorted(expected_closures)} actual={sorted(closure_files)}')
restore=json.loads((p/'source-restoration.json').read_text())
if not restore.get('restored') or restore.get('original_sha256',{}).get('tests/sys_process.rs')!='e0034cf3a69ccf6107a9dfbc0854c0147ec2d93fdda8acf5ed6b07e683e1dc14' or restore.get('error') is not None: raise SystemExit('test source restoration receipt mismatch')
files={}; dirs=[]
for x in sorted(stage.rglob('*')):
 rel=x.relative_to(stage).as_posix()
 if x.is_symlink(): raise SystemExit(f'symlink in stage: {rel}')
 if x.is_dir(): dirs.append(rel)
 elif x.is_file(): files[rel]=hashlib.sha256(x.read_bytes()).hexdigest()
 else: raise SystemExit(f'unexpected stage entry: {rel}')
fixed={'Cargo.lock.accepted':'2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425','contract-source.md':'1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41','linux-managed-success-proof.py':'83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0','stage.sh':'67e13bdd24c406039cd17d96e3224a0124b1521f522ea86db9819404c0de56cb','launch.sh':'27e1ee59a936fefaab51172aa0b27d6b877f3eda1e37ca119a2967c6e5f6ff50'}
for n,h in fixed.items():
 if files.get(n)!=h: raise SystemExit(f'fixed input hash mismatch {n}')
all_groups=groups|launcher_groups|all_fixture_groups
print(json.dumps({'stage':str(stage),'scope':str(scope),'statuses':statuses,'owned_process_identities':owned,'launcher_process_identities':launchers,'fixture_pid_start_identities':all_fixture_ids,'process_groups':sorted(all_groups),'fixture_closure_files':sorted(expected_closures),'files':files,'directories':dirs},sort_keys=True))
'''

def ssh(code: str) -> bytes:
 return subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(code)+' '+shlex.quote(STAGE)+' '+shlex.quote(SCOPE)+' '+shlex.quote(PHYSICAL)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout

def collect(destination:Path):
 manifest=json.loads(ssh(REMOTE));
 if destination.exists(): raise FileExistsError(destination)
 with tempfile.NamedTemporaryFile(prefix='managed-success-',suffix='.tar') as f:
  subprocess.run(['ssh','workhorse','tar','-C',STAGE,'-cf','-', '.'],stdout=f,check=True); f.flush()
  destination.mkdir(mode=0o700,parents=True)
  with tarfile.open(f.name,'r:') as tf:
   for m in tf.getmembers():
    rel=PurePosixPath(m.name)
    if rel.is_absolute() or '..' in rel.parts or m.issym() or m.islnk() or not(m.isfile() or m.isdir()): raise RuntimeError(f'unsafe archive member {m.name}')
   tf.extractall(destination,filter='data')
 actual={}
 for x in destination.rglob('*'):
  if x.is_symlink(): raise RuntimeError(f'export symlink {x}')
  if x.is_file(): actual[x.relative_to(destination).as_posix()]=hashlib.sha256(x.read_bytes()).hexdigest()
 # tar ./ prefixes are normalized by pathlib; require the independently read complete inventory.
 if actual!={k:v for k,v in manifest['files'].items()}: raise RuntimeError('export hashes differ from remote inventory')
 (destination/'independent-readback.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 (destination/'export-manifest.json').write_text(json.dumps({'stage':STAGE,'scope':SCOPE,'files':manifest['files'],'directories':manifest['directories'],'readback_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()},indent=2,sort_keys=True)+'\n')

def validate_local_export(destination:Path, readback:dict, export:dict) -> None:
 if export.get('stage')!=STAGE or export.get('scope')!=SCOPE or export.get('files')!=readback.get('files') or export.get('directories')!=readback.get('directories') or export.get('readback_sha256')!=hashlib.sha256(json.dumps(readback,sort_keys=True).encode()).hexdigest(): raise RuntimeError('local export manifest/readback mismatch; preserve remote stage')
 local_files={}; local_dirs=[]
 for x in sorted(destination.rglob('*')):
  rel=x.relative_to(destination).as_posix()
  if x.is_symlink(): raise RuntimeError(f'local export symlink: {rel}')
  if x.is_dir(): local_dirs.append(rel)
  elif x.is_file() and rel not in ('independent-readback.json','export-manifest.json','remote-cleanup.json'): local_files[rel]=hashlib.sha256(x.read_bytes()).hexdigest()
  elif not x.is_file(): raise RuntimeError(f'unexpected local export object: {rel}')
 if local_files!=readback.get('files') or local_dirs!=readback.get('directories'): raise RuntimeError('local exported bytes/directories changed; preserve remote stage')

def cleanup(destination:Path):
 readback=json.loads((destination/'independent-readback.json').read_text())
 export=json.loads((destination/'export-manifest.json').read_text())
 validate_local_export(destination,readback,export)
 fresh=json.loads(ssh(REMOTE))
 for key in ('files','directories','owned_process_identities','launcher_process_identities','fixture_pid_start_identities','process_groups','statuses'):
  if fresh.get(key)!=readback.get(key): raise RuntimeError(f'fresh stage/custody readback changed ({key}); preserve it')
 payload=json.dumps(fresh,sort_keys=True)
 code=r'''import hashlib,json,pathlib,sys
m=json.loads(sys.argv[1]); s=pathlib.Path(m['stage']); scope=pathlib.Path(m['scope'])
if not s.is_dir() or s.is_symlink() or scope.exists() or scope.is_symlink(): raise SystemExit('stage/scope identity changed')
f={}; d=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink(): raise SystemExit('unexpected symlink '+r)
 if p.is_dir(): d.append(r)
 elif p.is_file(): f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit('unexpected object '+r)
if f!=m['files'] or d!=m['directories']: raise SystemExit('inventory changed')
for r in sorted(f,reverse=True): (s/r).unlink()
for r in sorted(d,key=lambda x:(x.count('/'),x),reverse=True): (s/r).rmdir()
s.rmdir()
if s.exists() or scope.exists(): raise SystemExit('stage/scope remains after exact removal')
print(json.dumps({'stage_absent':not s.exists(),'scope_absent':not scope.exists(),'removed_files':len(f),'removed_directories':len(d)}))'''
 result=subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(code)+' '+shlex.quote(payload)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,text=True)
 cleanup=json.loads(result.stdout)
 if cleanup.get('stage_absent') is not True or cleanup.get('scope_absent') is not True: raise RuntimeError('exact remote cleanup receipt incomplete')
 absence=r'''import json,pathlib,subprocess,sys
m=json.loads(sys.argv[1]); s=pathlib.Path(m['stage']); scope=pathlib.Path(m['scope'])
if s.exists() or s.is_symlink() or scope.exists() or scope.is_symlink(): raise SystemExit('fresh stage/scope absence readback failed')
for row in m['fixture_pid_start_identities']+m['owned_process_identities']+m['launcher_process_identities']:
 pid=int(row['pid']); start=str(row['start_ticks'])
 try:
  raw=pathlib.Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==start
 except FileNotFoundError: alive=False
 except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit('exact identity unreadable '+str(row)+': '+str(ex))
 if alive: raise SystemExit('exact identity remains '+str(row))
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
left=[[int(x.split()[0]),int(x.split()[1])] for x in ps.splitlines() if len(x.split())==2 and int(x.split()[1]) in set(m['process_groups'])]
if left: raise SystemExit('owned process group remains '+repr(left))
print(json.dumps({'stage_absent':True,'scope_absent':True,'identity_count':len(m['fixture_pid_start_identities'])+len(m['owned_process_identities'])+len(m['launcher_process_identities']),'groups_absent':m['process_groups']}))'''
 post=subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(absence)+' '+shlex.quote(json.dumps(readback,sort_keys=True))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,text=True)
 final=json.loads(post.stdout)
 if final.get('stage_absent') is not True or final.get('scope_absent') is not True or set(final.get('groups_absent',[]))!=set(readback['process_groups']): raise RuntimeError('fresh independent cleanup absence receipt incomplete')
 (destination/'remote-cleanup.json').write_text(json.dumps({'cleanup':cleanup,'fresh_absence':final},indent=2,sort_keys=True)+'\n')

def main():
 a=argparse.ArgumentParser(); a.add_argument('mode',choices=('collect','cleanup')); a.add_argument('run',choices=('96',)); a.add_argument('destination',type=Path); x=a.parse_args()
 if x.mode=='collect': collect(x.destination)
 else: cleanup(x.destination)
if __name__=='__main__':
 try: main()
 except Exception as e: print(f'run96 collection refused: {e}',file=sys.stderr); raise SystemExit(1)
