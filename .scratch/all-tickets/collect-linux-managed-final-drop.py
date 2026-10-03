#!/usr/bin/env python3
"""Read back, validate, export, then retire only the exact final-drop stage."""
from __future__ import annotations
import argparse, hashlib, json, shlex, subprocess, tarfile, tempfile
from pathlib import Path, PurePosixPath

STAGE = '/root/rhai-linux-managed-final-drop-20261003-106f2472-102'
SCOPE = '/root/.local/share/agent-builds/rhai/linux-managed-final-drop-20261003-106f2472-102'
PHYSICAL = '/var/roothome/rhai-linux-managed-final-drop-20261003-106f2472-102'
REV = '61b3739a785503d6a74d769b30c218b82f5dd249'
ARCHIVE = '47361b26246a615e74d6d5d774729acd4380f136ac553723f028ac6605274c24'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TEST = 'd0a8842cc6be749a98ab7786ae66fdeca4a0488ad48aacfc88b24d48bdc660d8'
CONTRACT = '1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41'
PROOF_HASH = 'b94913dd6e7baaf8140c24d1a609086ae0367a62f1c2c30277ccff5393031e99'
STAGE_HASH = '68dcc9ba2e98d5234901701e1e2d5061dbcf14c7ad0faeee869a6fd8ff28b869'
LAUNCH_HASH = 'bc6641e8ccb33fae2fb86468656ef418f0ba893effe0c6f831006fa04b0371ee'
REMOTE_TEMPLATE = r'''import hashlib,importlib.util,json,pathlib,re,subprocess,sys
sys.dont_write_bytecode=True
stage=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); physical=pathlib.Path(sys.argv[3])
if not stage.is_dir() or stage.is_symlink() or stage.resolve()!=physical: raise SystemExit('final-drop stage identity mismatch')
if scope.exists() or scope.is_symlink(): raise SystemExit('final-drop private scope remains')
subprocess.run(['sha256sum','--check','input-identities.sha256'],cwd=stage,check=True,stdout=subprocess.DEVNULL)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if sha(stage/'source.tar')!=SOURCE_ARCHIVE_HASH: raise SystemExit('source archive mismatch')
if sha(stage/'Cargo.lock.accepted')!=LOCK_HASH: raise SystemExit('lock mismatch')
if sha(stage/'contract-source.md')!=CONTRACT_HASH: raise SystemExit('contract mismatch')
for name,digest in [('linux-managed-final-drop-proof.py',PROOF_HASH),('linux-managed-kill-proof.py','4a80d60a826e1db80e174fe0627e01194d46cc54c4d22e55c1c49425637e50d1'),('stage.sh',STAGE_HASH),('launch.sh',LAUNCH_HASH)]:
 if sha(stage/name)!=digest: raise SystemExit(name+' recipe hash mismatch')
contract=(stage/'contract.md').read_text()
for line in ('exact_tests=8','feature_rows=4','positive_exact_invocations=7','negative_controls=1','base_regressions=3','test_exact_invocations=8','toolchain_setup_commands=3','helper_commands_expected=11','outer_timeout_seconds=600','run_scoped_timeout_seconds=585','helper_deadline_seconds=540','export_reserve_seconds=30','cargo_build_jobs=2','max_descendants=16','storage_preemptive_stop_kib=1572864','storage_hard_stop_kib=2097152','rss_hard_stop_kib=2097152'):
 if line not in contract.splitlines(): raise SystemExit('bounded contract mismatch: '+line)
p=stage/'proof-evidence'
expected_closures={'require-member-live-control-fixture-closure.json','native101-kill-regression-row1-fixture-closure.json','final-drop-native101-success-regression-row1-fixture-closure.json','native101-held-regression-row1-held-closure.json',*[f'green-row-{i}-fixture-closure.json' for i in range(1,5)]}
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
proof=load('linux-managed-final-drop-proof.py',PROOF_HASH,'final_drop_proof')
kill=load('linux-managed-kill-proof.py','4a80d60a826e1db80e174fe0627e01194d46cc54c4d22e55c1c49425637e50d1','kill_proof')
old=load('linux-managed-success-proof.py','83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0','accepted_success')
class ComparisonSink:
 STAGE=p
 @staticmethod
 def write_json(path,value):
  if not path.is_file(): raise SystemExit('required original closure missing: '+path.name)
  expected=json.dumps(value,indent=2,sort_keys=True)+'\n'
  if path.read_text(errors='strict')!=expected: raise SystemExit('original closure differs from fresh identity/group readback: '+path.name)
proof.BASE=ComparisonSink; kill.BASE=ComparisonSink
proof.CONTROL='require-member-live-control'; proof.DIAGNOSTIC='managed-final-drop-control require-member-live assertion'
def read(label,suffix): return (p/(label+'.'+suffix)).read_text(errors='strict')
def status(label,wanted):
 if int((p/(label+'.status')).read_text().strip())!=wanted: raise SystemExit(label+': wrong status')
def outer(label,name,failed):
 out=read(label,'stdout'); err=read(label,'stderr'); proof.terminal(out,name,failed)
 if failed and (len(re.findall(r"(?m)^thread '"+re.escape(name)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err))!=1 or err.count(proof.DIAGNOSTIC)!=1): raise SystemExit(label+': intended named panic/assertion missing')
 proof.parse_final_drop(err,label)
 return out,err
status('require-member-live-control',101); outer('require-member-live-control',proof.TEST,True)
for i in range(1,5):
 label=f'green-row-{i}'; status(label,0); outer(label,proof.TEST,False)
for label,name,kind in (('native101-kill-regression-row1',proof.KILL_TEST,'kill'),('native101-success-regression-row1',proof.SUCCESS_TEST,'success'),('native101-held-regression-row1',proof.HELD_TEST,'held')):
 status(label,0); out=read(label,'stdout'); err=read(label,'stderr'); proof.terminal(out,name,False)
 if kind=='kill': kill.boundary(err,label)
 elif kind=='success':
  text=out+err; old.require_success(text); old.identity_closure(text,'final-drop-'+label,ComparisonSink,label)
 else: old.require_held(out+err,ComparisonSink,label)
files={}; dirs=[]
for x in sorted(stage.rglob('*')):
 rel=x.relative_to(stage).as_posix()
 if x.is_symlink(): raise SystemExit('stage symlink: '+rel)
 if x.is_dir(): dirs.append(rel)
 elif x.is_file(): files[rel]=sha(x)
 else: raise SystemExit('unexpected stage entry: '+rel)
print(json.dumps({'stage':str(stage),'scope':str(scope),'statuses':statuses,'owned_process_identities':owned,'launcher_process_identities':launchers,'fixture_closure_files':sorted(expected_closures),'groups':sorted(groups|lgroups),'files':files,'directories':dirs},sort_keys=True))
'''

REMOTE = (REMOTE_TEMPLATE.replace('PROOF_HASH', repr(PROOF_HASH)).replace('STAGE_HASH', repr(STAGE_HASH)).replace('LAUNCH_HASH', repr(LAUNCH_HASH)).replace('SOURCE_ARCHIVE_HASH', repr(ARCHIVE)).replace('LOCK_HASH', repr(LOCK)).replace('CONTRACT_HASH', repr(CONTRACT)).replace('TEST_HASH', repr(TEST)))

def ssh(code: str) -> bytes:
    remote = 'python3 -c ' + shlex.quote(code) + ' ' + shlex.quote(STAGE) + ' ' + shlex.quote(SCOPE) + ' ' + shlex.quote(PHYSICAL)
    return subprocess.run(['ssh', 'workhorse', remote], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout

def collect(destination: Path):
    manifest=json.loads(ssh(REMOTE))
    if destination.exists(): raise FileExistsError(destination)
    with tempfile.NamedTemporaryFile(prefix='managed-final-drop-',suffix='.tar') as f:
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
    except Exception as e: print(f'final-drop collection refused: {e}',file=__import__('sys').stderr); raise SystemExit(1)
