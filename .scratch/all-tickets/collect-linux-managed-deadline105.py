#!/usr/bin/env python3
"""Read back, validate, export, then retire only the exact deadline stage."""
from __future__ import annotations
import argparse, hashlib, json, shlex, subprocess, tarfile, tempfile
from pathlib import Path, PurePosixPath

STAGE = '/root/rhai-linux-managed-deadline-20261003-bcecd9eb-105'
SCOPE = '/root/.local/share/agent-builds/rhai/linux-managed-deadline-20261003-bcecd9eb-105'
PHYSICAL = '/var/roothome/rhai-linux-managed-deadline-20261003-bcecd9eb-105'
REV = '31a61e752d0ffb747be827475278e3fc5d9dbe30'
ARCHIVE = 'aa3916aeb2cfb842cb2572032e398fc1c3f43f3811e6c60abc3e73d51dba4796'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TEST = '8d6af23f45ac24ce640ca624800b3e40daff9e10941047a786ce5f7bd233f02b'
CONTRACT = '0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68'
PROOF_HASH = '44cb3867771c93af50fb50dbbf496fcf35fc645dfdfd7d59d248d9a663783f55'
STAGE_HASH = '8e42a15807c51daf735203cf3f718fe0b3d8e5d6bf8d90594f8ed74c840cb42f'
LAUNCH_HASH = 'd0ce048cdf6fa0bb162e08e33d99dd7f16103c69ad17328a02daaa5e6ee4739d'
KILL_PROOF_HASH = '4a80d60a826e1db80e174fe0627e01194d46cc54c4d22e55c1c49425637e50d1'
FINAL_DROP_PROOF_HASH = 'b94913dd6e7baaf8140c24d1a609086ae0367a62f1c2c30277ccff5393031e99'
REMOTE_TEMPLATE = r'''import hashlib,importlib.util,json,pathlib,re,subprocess,sys
sys.dont_write_bytecode=True
stage=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); physical=pathlib.Path(sys.argv[3])
if not stage.is_dir() or stage.is_symlink() or stage.resolve()!=physical: raise SystemExit('deadline stage identity mismatch')
if scope.exists() or scope.is_symlink(): raise SystemExit('deadline private scope remains')
subprocess.run(['sha256sum','--check','input-identities.sha256'],cwd=stage,check=True,stdout=subprocess.DEVNULL)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if sha(stage/'source.tar')!=SOURCE_ARCHIVE_HASH: raise SystemExit('source archive mismatch')
if sha(stage/'Cargo.lock.accepted')!=LOCK_HASH: raise SystemExit('lock mismatch')
if sha(stage/'contract-source.md')!=CONTRACT_HASH: raise SystemExit('contract mismatch')
for name,digest in [('linux-managed-deadline105-proof.py',PROOF_HASH),('stage.sh',STAGE_HASH),('launch.sh',LAUNCH_HASH),('linux-managed-kill-proof.py',KILL_HASH_REMOTE),('linux-managed-final-drop-proof.py',FINAL_DROP_HASH_REMOTE)]:
 if sha(stage/name)!=digest: raise SystemExit(name+' recipe hash mismatch')
contract=(stage/'contract.md').read_text()
for line in ('exact_tests=9','feature_rows=4','positive_exact_invocations=8','negative_controls=1','base_regressions=4','test_exact_invocations=9','toolchain_setup_commands=3','helper_commands_expected=12','outer_timeout_seconds=600','run_scoped_timeout_seconds=585','helper_deadline_seconds=540','export_reserve_seconds=30','cargo_build_jobs=2','max_descendants=16','storage_preemptive_stop_kib=1572864','storage_hard_stop_kib=2097152','rss_hard_stop_kib=2097152'):
 if line not in contract.splitlines(): raise SystemExit('bounded contract mismatch: '+line)
p=stage/'proof-evidence'
expected_closures={'require-timeout-control-fixture-closure.json','deadline-base-prompt-regression-row1-fixture-closure.json','deadline-base-held-regression-row1-held-closure.json','base-kill-regression-row1-fixture-closure.json','base-final-drop-regression-row1-fixture-closure.json',*[f'green-row-{i}-fixture-closure.json' for i in range(1,5)]}
actual_closures={x.name for x in p.glob('*-closure.json')}
if actual_closures!=expected_closures: raise SystemExit(f'required original closure inventory mismatch expected={sorted(expected_closures)} actual={sorted(actual_closures)}')
rest=json.loads((p/'source-restoration.json').read_text())
if not rest.get('restored') or rest.get('original_sha256',{}).get('tests/sys_process.rs')!=TEST_HASH or rest.get('error') is not None: raise SystemExit('frozen test source restoration mismatch')
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
def load(name,expected,module_name):
 path=stage/name
 if sha(path)!=expected: raise SystemExit(name+' hash mismatch')
 spec=importlib.util.spec_from_file_location(module_name,path); mod=importlib.util.module_from_spec(spec); sys.modules[module_name]=mod; spec.loader.exec_module(mod); return mod
proof=load('linux-managed-deadline105-proof.py',PROOF_HASH,'deadline_proof')
old=load('linux-managed-success-proof.py','83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0','accepted_success')
kill=load('linux-managed-kill-proof.py',KILL_HASH_REMOTE,'accepted_kill')
final_drop=load('linux-managed-final-drop-proof.py',FINAL_DROP_HASH_REMOTE,'accepted_final_drop')
class ComparisonSink:
 STAGE=p
 @staticmethod
 def write_json(path,value):
  if not path.is_file(): raise SystemExit('required original closure missing: '+path.name)
  expected=json.dumps(value,indent=2,sort_keys=True)+'\n'
  if path.read_text(errors='strict')!=expected: raise SystemExit('original closure differs from fresh identity/group readback: '+path.name)
proof.BASE=ComparisonSink
kill.BASE=ComparisonSink; final_drop.BASE=ComparisonSink
proof.CONTROL='require-timeout-control'; proof.DIAGNOSTIC='managed-deadline-control require-timeout assertion'
def read(label,suffix): return (p/(label+'.'+suffix)).read_text(errors='strict')
def status(label,wanted):
 if int((p/(label+'.status')).read_text().strip())!=wanted: raise SystemExit(label+': wrong status')
def outer(label,name,failed):
 out=read(label,'stdout'); err=read(label,'stderr'); proof.terminal(out,name,failed)
 if failed and (len(re.findall(r"(?m)^thread '"+re.escape(name)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err))!=1 or err.count(proof.DIAGNOSTIC)!=1): raise SystemExit(label+': intended named panic/assertion missing')
 proof.parse_deadline(err,label)
 return out,err
status('require-timeout-control',101); outer('require-timeout-control',proof.TEST,True)
for i in range(1,5):
 label=f'green-row-{i}'; status(label,0); outer(label,proof.TEST,False)
for label,name,kind in (('base-prompt-regression-row1',proof.SUCCESS_TEST,'success'),('base-held-regression-row1',proof.HELD_TEST,'held'),('base-kill-regression-row1',proof.KILL_TEST,'kill'),('base-final-drop-regression-row1',proof.FINAL_DROP_TEST,'final-drop')):
 status(label,0); out=read(label,'stdout'); err=read(label,'stderr'); proof.terminal(out,name,False)
 if kind=='success':
  text=out+err; old.require_success(text); old.identity_closure(text,'deadline-'+label,ComparisonSink,label)
 elif kind=='held': old.require_held(out+err,ComparisonSink,'deadline-'+label)
 elif kind=='kill': kill.boundary(err,label)
 elif kind=='final-drop': final_drop.parse_final_drop(err,label)
files={}; dirs=[]
for x in sorted(stage.rglob('*')):
 rel=x.relative_to(stage).as_posix()
 if x.is_symlink(): raise SystemExit('stage symlink: '+rel)
 if x.is_dir(): dirs.append(rel)
 elif x.is_file(): files[rel]=sha(x)
 else: raise SystemExit('unexpected stage entry: '+rel)
print(json.dumps({'stage':str(stage),'scope':str(scope),'statuses':statuses,'owned_process_identities':owned,'launcher_process_identities':launchers,'fixture_closure_files':sorted(expected_closures),'groups':sorted(groups|lgroups),'files':files,'directories':dirs},sort_keys=True))
'''

REMOTE = (REMOTE_TEMPLATE.replace('PROOF_HASH', repr(PROOF_HASH)).replace('KILL_HASH_REMOTE', repr(KILL_PROOF_HASH)).replace('FINAL_DROP_HASH_REMOTE', repr(FINAL_DROP_PROOF_HASH)).replace('STAGE_HASH', repr(STAGE_HASH)).replace('LAUNCH_HASH', repr(LAUNCH_HASH)).replace('SOURCE_ARCHIVE_HASH', repr(ARCHIVE)).replace('LOCK_HASH', repr(LOCK)).replace('CONTRACT_HASH', repr(CONTRACT)).replace('TEST_HASH', repr(TEST)))

def ssh(code: str) -> bytes:
    remote = 'python3 -c ' + shlex.quote(code) + ' ' + shlex.quote(STAGE) + ' ' + shlex.quote(SCOPE) + ' ' + shlex.quote(PHYSICAL)
    return subprocess.run(['ssh', 'workhorse', remote], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout

def collect(destination: Path):
    manifest=json.loads(ssh(REMOTE))
    if destination.exists(): raise FileExistsError(destination)
    with tempfile.NamedTemporaryFile(prefix='managed-deadline-',suffix='.tar') as f:
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
    code=r'''import json,pathlib,sys
m=json.loads(sys.argv[1]); s=pathlib.Path(m['stage']); scope=pathlib.Path(m['scope'])
if not s.is_dir() or s.is_symlink() or scope.exists() or scope.is_symlink(): raise SystemExit('stage/scope identity changed')
import hashlib
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
    code='python3 -c '+shlex.quote(code)+' '+shlex.quote(payload)
    receipt=json.loads(subprocess.run(['ssh','workhorse',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,text=True).stdout)
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
    except Exception as e: print(f'deadline collection refused: {e}',file=__import__('sys').stderr); raise SystemExit(1)
