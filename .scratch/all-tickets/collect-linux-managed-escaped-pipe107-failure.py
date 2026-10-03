#!/usr/bin/env python3
"""Preserve failed native107 originals with fresh custody checks; never acceptance."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, shlex, subprocess, sys, tarfile, tempfile
from pathlib import Path, PurePosixPath

STAGE='/root/rhai-linux-managed-escaped-pipe-20261003-52360864-107'
SCOPE='/root/.local/share/agent-builds/rhai/linux-managed-escaped-pipe-20261003-52360864-107'
PHYSICAL='/var/roothome/rhai-linux-managed-escaped-pipe-20261003-52360864-107'
REV='523608648dcae99bc0f6b46eaf2bb91fa4ecc752'
ARCHIVE='998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b'
LOCK='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TEST='5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb'
CONTRACT='0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68'
PROOF='81141bf9aac013f2230337ef0cbff1d5c5638c52a1e2f947a8c67fbd9066c7e5'; STAGE_RECIPE='b6150e4ba02b5ebd3575a98449051641c83d3d8612388884d76423a8da95ab8b'; LAUNCH='798d9c94323f5646d6d0f3e535e1b4fff8b922ac8a83be16e17a01b5e29dbbe4'; OLD_PROOF='83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0'

REMOTE="import hashlib,json,pathlib,subprocess,sys\nstage=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); physical=pathlib.Path(sys.argv[3])\nif not stage.is_dir() or stage.is_symlink() or stage.resolve()!=physical: raise SystemExit('managed-deadline stage identity mismatch')\nif scope.exists() or scope.is_symlink(): raise SystemExit('managed-deadline private scope remains')\nsubprocess.run(['sha256sum','--check','input-identities.sha256'],cwd=stage,check=True,stdout=subprocess.DEVNULL)\ndef sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()\nif sha(stage/'source.tar')!='998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b': raise SystemExit('source archive mismatch')\nif sha(stage/'Cargo.lock.accepted')!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise SystemExit('lock mismatch')\nif sha(stage/'contract-source.md')!='0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68': raise SystemExit('contract mismatch')\nfor name,digest in [('linux-managed-escaped-pipe-proof.py','81141bf9aac013f2230337ef0cbff1d5c5638c52a1e2f947a8c67fbd9066c7e5'),('stage.sh','b6150e4ba02b5ebd3575a98449051641c83d3d8612388884d76423a8da95ab8b'),('launch.sh','798d9c94323f5646d6d0f3e535e1b4fff8b922ac8a83be16e17a01b5e29dbbe4')]:\n if sha(stage/name)!=digest: raise SystemExit(name+' recipe hash mismatch')\ncontract=(stage/'contract.md').read_text()\nfor line in ('exact_tests=8','feature_rows=4','positive_exact_invocations=7','negative_controls=1','base_regressions=3','test_exact_invocations=8','toolchain_setup_commands=3','helper_commands_expected=11','outer_timeout_seconds=600','run_scoped_timeout_seconds=585','helper_deadline_seconds=540','export_reserve_seconds=30','cargo_build_jobs=2','max_descendants=16','storage_preemptive_stop_kib=1572864','storage_hard_stop_kib=2097152','rss_hard_stop_kib=2097152'):\n if line not in contract.splitlines(): raise SystemExit('bounded contract mismatch: '+line)\np=stage/'proof-evidence'\nrest=json.loads((p/'source-restoration.json').read_text())\nif not rest.get('restored') or rest.get('original_sha256',{}).get('tests/sys_process.rs')!='5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb' or rest.get('error') is not None: raise SystemExit('frozen test source restoration mismatch')\ne=stage/'outer-evidence'; names=('outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status')\nstatuses={n:int((e/n).read_text().strip()) for n in names}\nif statuses!={'outer-status.txt':1,'run-scoped.status':1,'pid-readback.status':0,'pid-readback-launcher.status':0}: raise SystemExit(f'failed-run/custody statuses mismatch: {statuses}')\nfor n in ('runtime-cleanup.tsv','scope-cleanup.tsv'):\n if 'cleanup_status=0' not in (e/n).read_text(): raise SystemExit(f'exact runner/scope cleanup missing: {n}')\ndef read_owned(path,required):\n rows=path.read_text(errors='strict').splitlines(); seen=set(); groups=set(); records=[]\n for line in rows[1:]:\n  f=line.split('\\t',5)\n  if len(f)!=6 or not all(x.isdigit() for x in f[1:5]): raise SystemExit(f'malformed custody row: {line!r}')\n  label,pid,ppid,pgid,start,_cmd=f; pid=int(pid); pgid=int(pgid); seen.add(label)\n  try:\n   raw=pathlib.Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==start\n  except FileNotFoundError: alive=False\n  except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f'exact custody identity unreadable: {label}/{pid}: {ex}')\n  if alive: raise SystemExit(f'owned process remains: {label}={pid}/{start}')\n  if label in ('helper','scoped-supervisor','launcher','run-scoped'): groups.add(pgid)\n  records.append({'label':label,'pid':pid,'start_ticks':start,'ppid':int(ppid),'pgid':pgid,'matching_process_alive':False})\n if not required.issubset(seen): raise SystemExit(f'required custody rows missing: {required-seen}')\n return records,groups\nowned,groups=read_owned(p/'process-identities.tsv',{'helper','scoped-supervisor'})\nlaunchers,lgroups=read_owned(e/'launcher-identities.tsv',{'launcher','run-scoped'})\nif not groups: raise SystemExit('helper process groups missing')\nps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)\nleft=[[int(x.split()[0]),int(x.split()[1])] for x in ps.splitlines() if len(x.split())==2 and int(x.split()[1]) in groups|lgroups]\nif left: raise SystemExit(f'owned helper/launcher process group remains: {left!r}')\nlabel='require-escaped-holder-control'\nif int((p/(label+'.status')).read_text())!=101: raise SystemExit('original control status mismatch')\nout=(p/(label+'.stdout')).read_text();err=(p/(label+'.stderr')).read_text()\nimport re\nname='managed_run_deadline_cancels_escaped_pipe_holder_under_fixture_reaper'\nif len(re.findall(r'(?m)^test '+re.escape(name)+r' \\.\\.\\..*$',out))!=1: raise SystemExit('unique actual control prefix missing')\nsummaries=re.findall(r'(?m)^test result: .*?$',out)\nif not summaries or not re.fullmatch(r'test result: FAILED\\. 0 passed; 1 failed; 0 ignored; 0 measured; \\d+ filtered out; finished in \\d+(?:\\.\\d+)?s',summaries[-1]): raise SystemExit('actual final control summary mismatch')\nparts=out.split('failures:',1)\nnames=[x.strip() for x in parts[-1].split('test result:',1)[0].splitlines() if x.strip() and x.strip()!='failures:']\nif names!=[name]: raise SystemExit('actual final control failure list mismatch')\nif 'managed-escaped-pipe-control require-timeout-report assertion' not in err: raise SystemExit('named post-cleanup panic missing')\nfailure=(p/'failure.txt').read_text()\nif 'exact leader/holder PIDFD identity mismatch: {}' not in failure: raise SystemExit('actual parser infrastructure failure missing')\nif list(p.glob('*-closure.json')): raise SystemExit('unexpected original closure artifacts')\nimport re\nboundaries=re.findall(r'(?m)^managed_deadline_escaped_pipe_boundary ([^\\n]*)$',err)\nif len(boundaries)!=1: raise SystemExit('unique original boundary missing')\nfld=dict(re.findall(r'([a-z_]+)=([^\\s]+)',boundaries[0]))\nfixture=[]\nfor name in ('host','reaper','leader','holder','sentinel'):\n pid=int(fld[name]); start=str(int(fld[name+'_start']))\n try:\n  raw=pathlib.Path('/proc',str(pid),'stat').read_text();fields=raw[raw.rfind(')')+2:].split();alive=fields[19]==start\n except FileNotFoundError:alive=False\n except (PermissionError,OSError,IndexError,ValueError) as ex:raise SystemExit('fixture identity unreadable '+name+': '+str(ex))\n if alive:raise SystemExit('exact fixture identity remains '+name)\n fixture.append({'label':name,'pid':pid,'start_ticks':start,'matching_process_alive':False})\nfixture_groups={int(fld['managed_group']),int(fld['sentinel_group'])}\nif any(len(x.split())==2 and int(x.split()[1]) in fixture_groups for x in ps.splitlines()):raise SystemExit('fixture groups remain')\ngroups.update(fixture_groups)\nfiles={}; dirs=[]\nfor x in sorted(stage.rglob('*')):\n rel=x.relative_to(stage).as_posix()\n if x.is_symlink(): raise SystemExit('stage symlink '+rel)\n if x.is_dir(): dirs.append(rel)\n elif x.is_file(): files[rel]=sha(x)\n else: raise SystemExit('unexpected stage object '+rel)\nprint(json.dumps({'classification':'parser infrastructure failure after intended control execution; NOT acceptance','stage':str(stage),'scope':str(scope),'statuses':statuses,'fixture_process_identities':fixture,'owned_process_identities':owned,'launcher_process_identities':launchers,'groups':sorted(groups|lgroups),'files':files,'directories':dirs},sort_keys=True))\n"

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
 for key in ('files','directories','owned_process_identities','launcher_process_identities','fixture_closure_files','fixture_process_identities','groups','statuses'):
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
for row in m['owned_process_identities']+m['launcher_process_identities']+m['fixture_process_identities']:
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
 except Exception as e: print(f'managed-deadline raw-failure export refused: {e}',file=sys.stderr); raise SystemExit(1)
