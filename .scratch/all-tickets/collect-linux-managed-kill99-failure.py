#!/usr/bin/env python3
"""Preserve failed native99 originals with fresh custody checks; never acceptance."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, shlex, subprocess, sys, tarfile, tempfile
from pathlib import Path, PurePosixPath

STAGE='/root/rhai-linux-managed-kill-20261003-a17f40a7-99'
SCOPE='/root/.local/share/agent-builds/rhai/linux-managed-kill-20261003-a17f40a7-99'
PHYSICAL='/var/roothome/rhai-linux-managed-kill-20261003-a17f40a7-99'
REV='90a6ddea70a7d25f2554845cc5f1b3d9e62e7e07'
ARCHIVE='450bf2f8dd3325e49e8a2e5e2e937903aee39e7a5381a0677b08bda3d977e9b9'
LOCK='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TEST='90b9216c4517384228418e57c2b6ec91ed779b590e68ff6b288b81760a6b537d'
CONTRACT='1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41'
PROOF='7cf8f2a1784193c206f63ffa35cb0d2c72e9add46bdf22457fe9526acb3735a1'; STAGE_RECIPE='dec96c3450f7119439424fb8fbb917c2a956dc64d93b9e2207ace2d7f9a13b52'; LAUNCH='b3c04620840cdb412ca52982d5c0e47e0cf7318bc28e2cc6605621f52ff0eb61'; OLD_PROOF='83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0'

REMOTE="import hashlib,json,pathlib,subprocess,sys\nstage=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); physical=pathlib.Path(sys.argv[3])\nif not stage.is_dir() or stage.is_symlink() or stage.resolve()!=physical: raise SystemExit('managed-kill stage identity mismatch')\nif scope.exists() or scope.is_symlink(): raise SystemExit('managed-kill private scope remains')\nsubprocess.run(['sha256sum','--check','input-identities.sha256'],cwd=stage,check=True,stdout=subprocess.DEVNULL)\ndef sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()\nif sha(stage/'source.tar')!='450bf2f8dd3325e49e8a2e5e2e937903aee39e7a5381a0677b08bda3d977e9b9': raise SystemExit('source archive mismatch')\nif sha(stage/'Cargo.lock.accepted')!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise SystemExit('lock mismatch')\nif sha(stage/'contract-source.md')!='1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41': raise SystemExit('contract mismatch')\nfor name,digest in [('linux-managed-kill-proof.py','7cf8f2a1784193c206f63ffa35cb0d2c72e9add46bdf22457fe9526acb3735a1'),('stage.sh','dec96c3450f7119439424fb8fbb917c2a956dc64d93b9e2207ace2d7f9a13b52'),('launch.sh','b3c04620840cdb412ca52982d5c0e47e0cf7318bc28e2cc6605621f52ff0eb61')]:\n if sha(stage/name)!=digest: raise SystemExit(name+' recipe hash mismatch')\ncontract=(stage/'contract.md').read_text()\nfor line in ('exact_tests=8','feature_rows=4','positive_exact_invocations=6','negative_controls=2','test_exact_invocations=8','toolchain_setup_commands=3','helper_commands_expected=11','outer_timeout_seconds=600','run_scoped_timeout_seconds=585','helper_deadline_seconds=540','export_reserve_seconds=30','cargo_build_jobs=2','max_descendants=16','storage_preemptive_stop_kib=1572864','storage_hard_stop_kib=2097152','rss_hard_stop_kib=2097152'):\n if line not in contract.splitlines(): raise SystemExit('bounded contract mismatch: '+line)\np=stage/'proof-evidence'\nrest=json.loads((p/'source-restoration.json').read_text())\nif not rest.get('restored') or rest.get('original_sha256',{}).get('tests/sys_process.rs')!='90b9216c4517384228418e57c2b6ec91ed779b590e68ff6b288b81760a6b537d' or rest.get('error') is not None: raise SystemExit('frozen test source restoration mismatch')\ne=stage/'outer-evidence'; names=('outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status')\nstatuses={n:int((e/n).read_text().strip()) for n in names}\nif statuses!={'outer-status.txt':1,'run-scoped.status':1,'pid-readback.status':0,'pid-readback-launcher.status':0}: raise SystemExit(f'failed-run/custody statuses mismatch: {statuses}')\nfor n in ('runtime-cleanup.tsv','scope-cleanup.tsv'):\n if 'cleanup_status=0' not in (e/n).read_text(): raise SystemExit(f'exact runner/scope cleanup missing: {n}')\ndef read_owned(path,required):\n rows=path.read_text(errors='strict').splitlines(); seen=set(); groups=set(); records=[]\n for line in rows[1:]:\n  f=line.split('\\t',5)\n  if len(f)!=6 or not all(x.isdigit() for x in f[1:5]): raise SystemExit(f'malformed custody row: {line!r}')\n  label,pid,ppid,pgid,start,_cmd=f; pid=int(pid); pgid=int(pgid); seen.add(label)\n  try:\n   raw=pathlib.Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==start\n  except FileNotFoundError: alive=False\n  except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f'exact custody identity unreadable: {label}/{pid}: {ex}')\n  if alive: raise SystemExit(f'owned process remains: {label}={pid}/{start}')\n  if label in ('helper','scoped-supervisor','launcher','run-scoped'): groups.add(pgid)\n  records.append({'label':label,'pid':pid,'start_ticks':start,'ppid':int(ppid),'pgid':pgid,'matching_process_alive':False})\n if not required.issubset(seen): raise SystemExit(f'required custody rows missing: {required-seen}')\n return records,groups\nowned,groups=read_owned(p/'process-identities.tsv',{'helper','scoped-supervisor'})\nlaunchers,lgroups=read_owned(e/'launcher-identities.tsv',{'launcher','run-scoped'})\nif not groups: raise SystemExit('helper process groups missing')\nps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)\nleft=[[int(x.split()[0]),int(x.split()[1])] for x in ps.splitlines() if len(x.split())==2 and int(x.split()[1]) in groups|lgroups]\nif left: raise SystemExit(f'owned helper/launcher process group remains: {left!r}')\nlabel='require-success-control'\nif int((p/(label+'.status')).read_text())!=101: raise SystemExit('control status mismatch')\nfailure=(p/'failure.txt').read_text(); err=(p/(label+'.stderr')).read_text()\nif 'boundary invariant false' not in failure or 'reaper_ok=false' not in err or 'managed-child-kill-control require-success assertion' not in err: raise SystemExit('expected reaper exit verification failure missing')\nimport re\nlines=re.findall(r'^managed_child_kill_live (.+)$',err,re.M)\nif len(lines)!=1: raise SystemExit('exact live fixture receipt missing/duplicated')\nfacts=dict(re.findall(r'(\\w+)=(\\d+)',lines[0]))\nfor label in ('reaper','host','leader','worker','leaf','sentinel'):\n pid=int(facts[label]); start=facts[label+'_start']\n try:\n  raw=pathlib.Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==start\n except FileNotFoundError: alive=False\n except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit('fixture identity unreadable '+str(ex))\n if alive: raise SystemExit('fixture identity remains '+label)\n owned.append({'label':'fixture-'+label,'pid':pid,'start_ticks':start,'matching_process_alive':False})\ngroups.update((int(facts['group']),int(facts['sentinel_pgid'])))\nps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)\nleft=[[int(x.split()[0]),int(x.split()[1])] for x in ps.splitlines() if len(x.split())==2 and int(x.split()[1]) in groups|lgroups]\nif left: raise SystemExit('fixture/helper group remains '+repr(left))\nif list(p.glob('*-closure.json')): raise SystemExit('unexpected fixture closures; classify manually')\nfiles={}; dirs=[]\nfor x in sorted(stage.rglob('*')):\n rel=x.relative_to(stage).as_posix()\n if x.is_symlink(): raise SystemExit('stage symlink '+rel)\n if x.is_dir(): dirs.append(rel)\n elif x.is_file(): files[rel]=sha(x)\n else: raise SystemExit('unexpected stage object '+rel)\nprint(json.dumps({'classification':'actual control reached; reaper exit status unverified; NOT acceptance','stage':str(stage),'scope':str(scope),'statuses':statuses,'owned_process_identities':owned,'launcher_process_identities':launchers,'groups':sorted(groups|lgroups),'files':files,'directories':dirs},sort_keys=True))\n"

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
 except Exception as e: print(f'managed-kill raw-failure export refused: {e}',file=sys.stderr); raise SystemExit(1)
