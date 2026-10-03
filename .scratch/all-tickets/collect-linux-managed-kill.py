#!/usr/bin/env python3
"""Read back, export, validate, then retire only the exact managed-kill stage."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, shlex, subprocess, sys, tarfile, tempfile
from pathlib import Path, PurePosixPath

STAGE='/root/rhai-linux-managed-kill-20261003-a17f40a7-97'
SCOPE='/root/.local/share/agent-builds/rhai/linux-managed-kill-20261003-a17f40a7-97'
PHYSICAL='/var/roothome/rhai-linux-managed-kill-20261003-a17f40a7-97'
REV='d70e2c409c82b09ab205e2fc12b08a7c6b94acec'
ARCHIVE='4510841b868ad57cbff61129b2f6244c21b3915588d36caf760a54d653e9e43d'
LOCK='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TEST='9c6ca59e753ebae483a3f2bed6cf5ffd076e80a7c6ef1be76dc87e49c5ea00da'
CONTRACT='1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41'
PROOF='929e0509ba74c41fc294f03d99e6a8e157cc5a63a8fbcfc00b45d43b7f74f13b'; STAGE_RECIPE='6fe4319a1bd3b57c1e47a23cc97b837843566da6a867a40e88582ba7d2a52554'; LAUNCH='d7f90e31bb593171a5b7739463495f104497ecad65b17388c8bf4c06c5731be5'; OLD_PROOF='83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0'

REMOTE=r'''import hashlib,json,pathlib,subprocess,sys
stage=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); physical=pathlib.Path(sys.argv[3])
if not stage.is_dir() or stage.is_symlink() or stage.resolve()!=physical: raise SystemExit('managed-kill stage identity mismatch')
if scope.exists() or scope.is_symlink(): raise SystemExit('managed-kill private scope remains')
subprocess.run(['sha256sum','--check','input-identities.sha256'],cwd=stage,check=True,stdout=subprocess.DEVNULL)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if sha(stage/'source.tar')!='4510841b868ad57cbff61129b2f6244c21b3915588d36caf760a54d653e9e43d': raise SystemExit('source archive mismatch')
if sha(stage/'Cargo.lock.accepted')!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise SystemExit('lock mismatch')
if sha(stage/'contract-source.md')!='1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41': raise SystemExit('contract mismatch')
for name,digest in [('linux-managed-kill-proof.py','929e0509ba74c41fc294f03d99e6a8e157cc5a63a8fbcfc00b45d43b7f74f13b'),('stage.sh','6fe4319a1bd3b57c1e47a23cc97b837843566da6a867a40e88582ba7d2a52554'),('launch.sh','d7f90e31bb593171a5b7739463495f104497ecad65b17388c8bf4c06c5731be5')]:
 if sha(stage/name)!=digest: raise SystemExit(name+' recipe hash mismatch')
contract=(stage/'contract.md').read_text()
for line in ('exact_tests=8','feature_rows=4','positive_exact_invocations=6','negative_controls=2','test_exact_invocations=8','toolchain_setup_commands=3','helper_commands_expected=11','outer_timeout_seconds=600','run_scoped_timeout_seconds=585','helper_deadline_seconds=540','export_reserve_seconds=30','cargo_build_jobs=2','max_descendants=16','storage_preemptive_stop_kib=1572864','storage_hard_stop_kib=2097152','rss_hard_stop_kib=2097152'):
 if line not in contract.splitlines(): raise SystemExit('bounded contract mismatch: '+line)
p=stage/'proof-evidence'
rest=json.loads((p/'source-restoration.json').read_text())
if not rest.get('restored') or rest.get('original_sha256',{}).get('tests/sys_process.rs')!='9c6ca59e753ebae483a3f2bed6cf5ffd076e80a7c6ef1be76dc87e49c5ea00da' or rest.get('error') is not None: raise SystemExit('frozen test source restoration mismatch')
e=stage/'outer-evidence'; names=('outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status')
statuses={n:int((e/n).read_text().strip()) for n in names}
if statuses!={n:0 for n in names}: raise SystemExit(f'outer/custody statuses mismatch: {statuses}')
for n in ('runtime-cleanup.tsv','scope-cleanup.tsv'):
 if 'cleanup_status=0' not in (e/n).read_text(): raise SystemExit(f'exact runner/scope cleanup missing: {n}')
def read_owned(path,required):
 rows=path.read_text(errors='strict').splitlines(); seen=set(); groups=set(); records=[]
 for line in rows[1:]:
  f=line.split('\t',5)
  if len(f)!=6 or not all(x.isdigit() for x in f[1:5]): raise SystemExit(f'malformed custody row: {line!r}')
  label,pid,ppid,pgid,start,_cmd=f; pid=int(pid); pgid=int(pgid); seen.add(label)
  try:
   raw=pathlib.Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==start
  except FileNotFoundError: alive=False
  except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f'exact custody identity unreadable: {label}/{pid}: {ex}')
  if alive: raise SystemExit(f'owned process remains: {label}={pid}/{start}')
  if label in ('helper','scoped-supervisor','launcher','run-scoped'): groups.add(pgid)
  records.append({'label':label,'pid':pid,'start_ticks':start,'ppid':int(ppid),'pgid':pgid,'matching_process_alive':False})
 if not required.issubset(seen): raise SystemExit(f'required custody rows missing: {required-seen}')
 return records,groups
owned,groups=read_owned(p/'process-identities.tsv',{'helper','scoped-supervisor'})
launchers,lgroups=read_owned(e/'launcher-identities.tsv',{'launcher','run-scoped'})
if not groups: raise SystemExit('helper process groups missing')
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
left=[[int(x.split()[0]),int(x.split()[1])] for x in ps.splitlines() if len(x.split())==2 and int(x.split()[1]) in groups|lgroups]
if left: raise SystemExit(f'owned helper/launcher process group remains: {left!r}')
import importlib.util
def load(path,name,expected):
 if sha(path)!=expected: raise SystemExit(f'{path.name} hash mismatch')
 spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
proof=load(stage/'linux-managed-kill-proof.py','kill_proof','929e0509ba74c41fc294f03d99e6a8e157cc5a63a8fbcfc00b45d43b7f74f13b')
old=load(stage/'linux-managed-success-proof.py','accepted96_proof','83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0')
class Sink:
 STAGE=p
 @staticmethod
 def write_json(path,value): path.write_text(json.dumps(value,sort_keys=True)+'\n')
proof.BASE=Sink
def read(label,suffix): return (p/(label+'.'+suffix)).read_text(errors='strict')
def outer(label,name,failed):
 out=read(label,'stdout'); err=read(label,'stderr')
 proof.terminal(out,name,failed)
 if failed:
  diag=proof.CONTROLS['require-success-control' if label=='require-success-control' else 'require-sentinel-absent-control']
  proof.verify_panic(out,err,label,diag)
 else: proof.boundary(err,label)
 return out,err
expected={'require-success-control':101,'require-sentinel-absent-control':101,'native96-success-row1':0,'native96-held-row1':0,'green-row-1':0,'green-row-2':0,'green-row-3':0,'green-row-4':0}
for label,status in expected.items():
 if int((p/(label+'.status')).read_text().strip())!=status: raise SystemExit(f'{label}: status != {status}')
 if label.startswith('require-'):
  out,err=outer(label,proof.TEST,True)
  diagnostic=proof.CONTROLS['require-success-control' if label=='require-success-control' else 'require-sentinel-absent-control']
  if len(re.findall(r"(?m)^thread '"+re.escape(proof.TEST)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err))!=1 or err.count(diagnostic)!=1: raise SystemExit(f'{label}: named panic/assertion missing')
 elif label.startswith('green-'):
  out,err=outer(label,proof.TEST,False)
 else:
  name=old.SUCCESS if 'success' in label else old.HELD
  out=read(label,'stdout'); err=read(label,'stderr'); proof.terminal(out,name,False)
  if name==old.SUCCESS: old.require_success(out+err)
  else: old.require_held(out+err,proof.BASE,label)

def check_closure(name,expected_ids,groups,pidfds):
 path=p/(name+'.json')
 if not path.is_file(): raise SystemExit(f'required closure file missing: {path.name}')
 d=json.loads(path.read_text()); rows=d.get('identities')
 if not isinstance(rows,list) or d.get('group_members_after_cleanup')!=[]: raise SystemExit(f'{name}: malformed closure rows/group')
 got={(r.get('label'),int(r.get('pid',-1)),int(r.get('start_ticks',-1))) for r in rows if isinstance(r,dict) and r.get('matching_identity_alive') is False}
 if got!=set(expected_ids): raise SystemExit(f'{name}: exact identity set mismatch {got!r}')
 actual_groups=d.get('groups',[d.get('group')])
 if set(actual_groups)!=set(groups): raise SystemExit(f'{name}: process groups mismatch')
 acquired=d.get('pidfd_identities')
 if acquired!=[{'pid':pid,'start_ticks':v[0],'ppid':v[1],'pgid':v[2]} for pid,v in sorted(pidfds.items())]: raise SystemExit(f'{name}: exact PIDFD inventory mismatch')
def kill_expected(label):
 c=proof.boundary(read(label,'stderr'),label); f=c['facts']
 ids={(n,*v) for n,v in c['identities'].items()}
 # closure JSON uses these labels and PID/start pairs exactly.
 check_closure(label+'-fixture-closure',ids,{f['group'],f['sentinel_group']},c['pidfds'])
for label in ('require-success-control','require-sentinel-absent-control','green-row-1','green-row-2','green-row-3','green-row-4'): kill_expected(label)
# Retained native96 cases are independently parsed and their strict closure artifacts are required.
success_text=read('native96-success-row1','stdout')+read('native96-success-row1','stderr'); s=old.require_success(success_text); se=old.early_receipt(success_text,'native96-success-row1')
success_ids={(n,*s[n]) for n in ('host','leader','worker','leaf','sentinel')}|{('reaper',*se['reaper'])}
check_closure('kill-package-native96-success-row1-fixture-closure',success_ids,{s['group']},s['pidfds'])
held_text=read('native96-held-row1','stdout')+read('native96-held-row1','stderr'); hids,hgroup,hrows=old.exact_boundary(held_text)
held_ids={(n,pid,int(start)) for n,pid,start in hids}; hpidfds={int(x['pid']):(int(x['start_ticks']),int(x['ppid']),int(x['pgid'])) for x in hrows}
check_closure('native96-held-row1-held-closure',held_ids,{hgroup},hpidfds)
expected_closures={'require-success-control-fixture-closure.json','require-sentinel-absent-control-fixture-closure.json',*[f'green-row-{i}-fixture-closure.json' for i in range(1,5)],'kill-package-native96-success-row1-fixture-closure.json','native96-held-row1-held-closure.json'}
actual={x.name for x in p.glob('*-closure.json')}
if actual!=expected_closures: raise SystemExit(f'required closure inventory mismatch expected={sorted(expected_closures)} actual={sorted(actual)}')
files={}; dirs=[]
for x in sorted(stage.rglob('*')):
 rel=x.relative_to(stage).as_posix()
 if x.is_symlink(): raise SystemExit(f'stage symlink: {rel}')
 if x.is_dir(): dirs.append(rel)
 elif x.is_file(): files[rel]=sha(x)
 else: raise SystemExit(f'unexpected stage entry: {rel}')
print(json.dumps({'stage':str(stage),'scope':str(scope),'statuses':statuses,'owned_process_identities':owned,'launcher_process_identities':launchers,'fixture_closure_files':sorted(expected_closures),'groups':sorted(groups|lgroups),'files':files,'directories':dirs},sort_keys=True))
'''

def ssh(code: str) -> bytes:
 return subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(code)+' '+shlex.quote(STAGE)+' '+shlex.quote(SCOPE)+' '+shlex.quote(PHYSICAL)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout

def collect(destination:Path):
 manifest=json.loads(ssh(REMOTE))
 if destination.exists(): raise FileExistsError(destination)
 with tempfile.NamedTemporaryFile(prefix='managed-kill-',suffix='.tar') as f:
  subprocess.run(['ssh','workhorse','tar','-C',STAGE,'-cf','-','.'],stdout=f,check=True); f.flush()
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
 if actual!=manifest['files']: raise RuntimeError('local export hashes differ from independent remote inventory')
 (destination/'independent-readback.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 (destination/'export-manifest.json').write_text(json.dumps({'stage':STAGE,'scope':SCOPE,'files':manifest['files'],'directories':manifest['directories'],'readback_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()},indent=2,sort_keys=True)+'\n')

def validate_local(destination,readback,export):
 if export.get('stage')!=STAGE or export.get('scope')!=SCOPE or export.get('files')!=readback.get('files') or export.get('directories')!=readback.get('directories') or export.get('readback_sha256')!=hashlib.sha256(json.dumps(readback,sort_keys=True).encode()).hexdigest(): raise RuntimeError('local export/readback manifest mismatch; preserve remote stage')
 files={}; dirs=[]
 for x in sorted(destination.rglob('*')):
  rel=x.relative_to(destination).as_posix()
  if x.is_symlink(): raise RuntimeError(f'local export symlink {rel}')
  if x.is_dir(): dirs.append(rel)
  elif x.is_file() and rel not in ('independent-readback.json','export-manifest.json','remote-cleanup.json'): files[rel]=hashlib.sha256(x.read_bytes()).hexdigest()
  elif not x.is_file(): raise RuntimeError(f'unexpected export object {rel}')
 if files!=readback['files'] or dirs!=readback['directories']: raise RuntimeError('local exported bytes/directories changed; preserve remote stage')

def cleanup(destination):
 readback=json.loads((destination/'independent-readback.json').read_text()); export=json.loads((destination/'export-manifest.json').read_text()); validate_local(destination,readback,export)
 fresh=json.loads(ssh(REMOTE))
 for key in ('files','directories','owned_process_identities','launcher_process_identities','fixture_closure_files','groups','statuses'):
  if fresh.get(key)!=readback.get(key): raise RuntimeError(f'fresh remote inventory/custody changed ({key}); preserve stage')
 payload=json.dumps(fresh,sort_keys=True)
 code=r'''import hashlib,json,pathlib,sys
m=json.loads(sys.argv[1]); s=pathlib.Path(m['stage']); scope=pathlib.Path(m['scope'])
if not s.is_dir() or s.is_symlink() or scope.exists() or scope.is_symlink(): raise SystemExit('stage/scope identity changed')
f={}; d=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink(): raise SystemExit('stage symlink '+r)
 if p.is_dir(): d.append(r)
 elif p.is_file(): f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit('unexpected object '+r)
if f!=m['files'] or d!=m['directories']: raise SystemExit('stage inventory changed')
for r in sorted(f,reverse=True): (s/r).unlink()
for r in sorted(d,key=lambda x:(x.count('/'),x),reverse=True): (s/r).rmdir()
s.rmdir()
if s.exists() or scope.exists(): raise SystemExit('stage/scope remains')
print(json.dumps({'stage_absent':not s.exists(),'scope_absent':not scope.exists(),'removed_files':len(f),'removed_directories':len(d)}))'''
 result=subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(code)+' '+shlex.quote(payload)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,text=True); receipt=json.loads(result.stdout)
 if receipt.get('stage_absent') is not True or receipt.get('scope_absent') is not True: raise RuntimeError('exact stage cleanup receipt incomplete')
 absence=r'''import json,pathlib,subprocess,sys
m=json.loads(sys.argv[1]); s=pathlib.Path(m['stage']); scope=pathlib.Path(m['scope'])
if s.exists() or s.is_symlink() or scope.exists() or scope.is_symlink(): raise SystemExit('fresh stage/scope absence failed')
for row in m['owned_process_identities']+m['launcher_process_identities']:
 pid=int(row['pid']); start=str(row['start_ticks'])
 try:
  raw=pathlib.Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==start
 except FileNotFoundError: alive=False
 except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit('identity unreadable '+repr(row)+': '+str(ex))
 if alive: raise SystemExit('owned identity remains '+repr(row))
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
left=[[int(x.split()[0]),int(x.split()[1])] for x in ps.splitlines() if len(x.split())==2 and int(x.split()[1]) in set(m['groups'])]
if left: raise SystemExit('owned process group remains '+repr(left))
print(json.dumps({'stage_absent':True,'scope_absent':True,'process_groups_absent':m['groups']}))'''
 final=json.loads(subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(absence)+' '+shlex.quote(json.dumps(readback,sort_keys=True))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,text=True).stdout)
 if final.get('stage_absent') is not True or final.get('scope_absent') is not True: raise RuntimeError('fresh post-cleanup absence receipt incomplete')
 (destination/'remote-cleanup.json').write_text(json.dumps({'cleanup':receipt,'fresh_absence':final},indent=2,sort_keys=True)+'\n')

def main():
 a=argparse.ArgumentParser(); a.add_argument('mode',choices=('collect','cleanup')); a.add_argument('destination',type=Path); x=a.parse_args()
 if x.mode=='collect': collect(x.destination)
 else: cleanup(x.destination)
if __name__=='__main__':
 try: main()
 except Exception as e: print(f'managed-kill collection refused: {e}',file=sys.stderr); raise SystemExit(1)
