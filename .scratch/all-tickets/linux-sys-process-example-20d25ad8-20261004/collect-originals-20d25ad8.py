#!/usr/bin/env python3
"""Preserve original sys-process stage bytes, then independently assess custody."""
from __future__ import annotations
import argparse, hashlib, json, re, shlex, subprocess, tarfile
from pathlib import Path, PurePosixPath

# This collector belongs only to the original failed 66379d30 invocation.
STAGE='/root/rhai-linux-sys-process-example-20d25ad8-20261004'
PHYSICAL='/var/roothome/rhai-linux-sys-process-example-20d25ad8-20261004'
SCOPE='/root/.local/share/agent-builds/rhai/linux-sys-process-example-20d25ad8-20261004'
HOST='workhorse'
INPUTS={
 'source.tar':'e7a9a118bd29c05e8a70e284196837594fc97811f3d80688d17f55167008be93',
 'Cargo.lock.accepted':'2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425',
 'run-examples.py':'e89c91496d8543c418149573c3b0f7a6fe41e04a02adf470cdb4811cf43fff4e',
 'contract.md':'8279084c6a1c8c85105fdc565810ecfe22233db4c17f2a84005564dc5a528b71',
 'launch.sh':'896d7aec52f3da44b01f1d692078c24d5ee4d869a4eb6510c7069a2458c1f045',
 'stage.sh':'321ea96b3f6ccc30cfeb2fc4dbee52d68061dfac0cef58ec17e94905fe43c0a3',
 'archive-build-source.py':'a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b',
 'runner/tools/run_scoped.py':'9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d',
 'runner/tools/agentskills/__init__.py':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
 'runner/tools/agentskills/pyguard.py':'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f',
}
INPUT_ORDER=tuple(INPUTS)
INPUT_MANIFEST=''.join(f'{INPUTS[name]}  {name}\n' for name in INPUT_ORDER)

# Raw inventory never queries /proc, ps, runtime, or the private scope. A custody
# failure therefore cannot prevent acquisition of otherwise readable originals.
REMOTE_INVENTORY=r'''import hashlib,json,pathlib,sys
s=pathlib.Path(sys.argv[1]); physical=pathlib.Path(sys.argv[2]); scope=pathlib.Path(sys.argv[3]); expected=json.loads(sys.argv[4]); expected_manifest=sys.argv[5]
if s.is_symlink() or not s.is_dir() or s.resolve()!=physical: raise SystemExit('exact stage identity mismatch')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
files={}; dirs=[]; links=[]; errors=[]
for x in sorted(s.rglob('*')):
 r=x.relative_to(s).as_posix()
 try:
  if x.is_symlink(): links.append({'path':r,'target':str(x.readlink())})
  elif x.is_dir(): dirs.append(r)
  elif x.is_file(): files[r]=sha(x)
  else: errors.append('unsupported object: '+r)
 except (OSError,PermissionError) as e: errors.append('inventory read failed '+r+': '+repr(e))
manifest_path=s/'input-identities.sha256'; raw=None; manifest_ok=False; manifest_error=None
try:
 if manifest_path.is_symlink() or not manifest_path.is_file(): raise OSError('manifest is not a regular file')
 raw=manifest_path.read_text(errors='strict')
 manifest_ok=(raw==expected_manifest)
except (OSError,UnicodeError) as e: manifest_error=repr(e)
input_actual={name:files.get(name) for name in expected}
input_ok=manifest_ok and input_actual==expected and not errors and not links
print(json.dumps({'stage':str(s),'physical':str(physical),'files':files,'directories':dirs,'links':links,'inventory_errors':errors,'input_manifest_sha256':hashlib.sha256(raw.encode()).hexdigest() if raw is not None else None,'input_manifest_exact':manifest_ok,'input_manifest_error':manifest_error,'input_actual':input_actual,'input_expected':expected,'input_binding_verified':input_ok},sort_keys=True))'''

# Custody is a separate read-only call. Errors are returned as unknown observations
# and never abort or roll back the raw originals already copied by collect().
REMOTE_CUSTODY=r'''import json,pathlib,re,subprocess,sys
s=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); errors=[]
HEADER='label\tpid\tppid\tpgid\tstart_ticks\tcmdline'
def parse(path,allowed,required):
 if not path.is_file(): errors.append('missing identity file '+str(path)); return []
 try: lines=path.read_text(errors='strict').splitlines()
 except (OSError,UnicodeError) as e: errors.append('cannot read '+str(path)+': '+repr(e)); return []
 if not lines or lines[0]!=HEADER: errors.append('identity header mismatch '+str(path)); return []
 rows=[]
 for line in lines[1:]:
  f=line.split('\t',5)
  command=allowed=={'helper','scoped-supervisor'} and f[0].startswith('command:') and bool(f[0][8:])
  if len(f)!=6 or (f[0] not in allowed and not command) or not all(x.isdigit() and int(x)>0 for x in f[1:5]) or (not f[5] and not command):
   errors.append('malformed identity row '+repr(line)); continue
  rows.append({'label':f[0],'pid':int(f[1]),'ppid':int(f[2]),'pgid':int(f[3]),'start_ticks':int(f[4]),'cmdline':f[5]})
 labels=[r['label'] for r in rows]
 owner_labels=required
 if any(labels.count(label)!=1 for label in owner_labels): errors.append('required identity multiplicity '+str(path))
 for label in required:
  if labels.count(label)!=1: errors.append('required identity count '+label+'='+str(labels.count(label)))
 if len({r['pid'] for r in rows})!=len(rows): errors.append('duplicate identity PID '+str(path))
 return rows
proc=parse(s/'proof-evidence'/'process-identities.tsv',{'helper','scoped-supervisor'}, {'helper','scoped-supervisor'})
# The helper also emits one command:<name> identity for each spawned command.
# Read and validate these with the same exact TSV parser while retaining the two required owners.

launch=parse(s/'outer-evidence'/'launcher-identities.tsv',{'launcher','run-scoped'}, {'launcher','run-scoped'})
byproc={label:next((r for r in proc if r['label']==label),None) for label in ('helper','scoped-supervisor')}; bylaunch={label:next((r for r in launch if r['label']==label),None) for label in ('launcher','run-scoped')}
if len({r['pid'] for r in proc+launch})!=len(proc+launch): errors.append('duplicate identity PID across files')
if byproc.get('helper') is not None and byproc.get('scoped-supervisor') is not None:
 for row in proc:
  if row['label'].startswith('command:') and row['ppid']!=byproc['helper']['pid']: errors.append('command parent does not match helper PID '+row['label'])
 if bylaunch.get('run-scoped') is not None and byproc['scoped-supervisor']['ppid']!=bylaunch['run-scoped']['pid']: errors.append('supervisor parent does not match run-scoped PID')
 if byproc['helper']['ppid']!=byproc['scoped-supervisor']['pid']: errors.append('helper parent does not match scoped-supervisor PID')
if bylaunch.get('launcher') is not None and bylaunch.get('run-scoped') is not None and bylaunch['run-scoped']['ppid']!=bylaunch['launcher']['pid']: errors.append('run-scoped parent does not match launcher PID')
roots=('/root/rhai-linux-sys-process-example-20d25ad8-20261004','/var/roothome/rhai-linux-sys-process-example-20d25ad8-20261004')
provenance={'helper':tuple(root+'/run-examples.py' for root in roots),'scoped-supervisor':tuple(root+'/runner/tools/run_scoped.py' for root in roots),'launcher':tuple(root+'/launch.sh' for root in roots),'run-scoped':tuple(root+'/runner/tools/run_scoped.py' for root in roots)}
for label,row in [('helper',byproc.get('helper')),('scoped-supervisor',byproc.get('scoped-supervisor')),('launcher',bylaunch.get('launcher')),('run-scoped',bylaunch.get('run-scoped'))]:
 if row and not any(path in row['cmdline'] for path in provenance[label]): errors.append(label+' command provenance mismatch')
observations=[]; groups=sorted({r['pgid'] for r in proc+launch})
for row in proc+launch:
 try:
  raw=pathlib.Path('/proc',str(row['pid']),'stat').read_text(); prefix=str(row['pid'])+' ('; close=raw.rfind(')')
  if not raw.startswith(prefix) or close<=len(prefix) or raw[close+1:close+2]!=' ': raise ValueError('malformed proc stat PID/comm framing')
  fields=raw[close+2:].split()
  if len(fields)<=19 or len(fields[0])!=1 or fields[0] not in 'RSDZTtXxKWPI' or not all(re.fullmatch(r'-?\d+',x) for x in fields[1:20]) or int(fields[19])<=0: raise ValueError('invalid proc stat state/start fields')
  state='live' if int(fields[19])==row['start_ticks'] else 'pid-reused-original-absent'
 except FileNotFoundError: state='absent'
 except (PermissionError,OSError,IndexError,ValueError) as e: state='unknown'; errors.append('PID/start readback unknown '+repr(row)+': '+repr(e))
 if state=='live': errors.append('recorded PID/start remains live '+repr(row))
 observations.append({'label':row['label'],'pid':row['pid'],'start_ticks':row['start_ticks'],'pgid':row['pgid'],'state':state})
group_census=None
try:
 text=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
 census=[]
 for line in text.splitlines():
  f=line.split()
  if len(f)!=2 or not all(x.isdigit() for x in f) or int(f[0])<=0 or int(f[1])<0: raise ValueError('malformed ps group census row '+repr(line))
  if int(f[1]) in groups: census.append([int(f[0]),int(f[1])])
 group_census=census
 if census: errors.append('recorded process groups remain '+repr(census))
except (subprocess.SubprocessError,OSError,ValueError) as e: errors.append('group census unknown: '+repr(e))
# Require a single direct runtime child, and matching helper and launcher records.
runtime_values=[]; outer=s/'outer-evidence'/'outer.log'
try:
 text=outer.read_text(errors='strict')
 runtime_values=re.findall(r'(?m)^PRIVATE_RUNTIME (\S+)$',text)
except (OSError,UnicodeError) as e: errors.append('runtime provenance unreadable: '+repr(e))
runtime=runtime_values[-1] if len(runtime_values)==1 else None
if len(runtime_values)!=1: errors.append('expected exactly one PRIVATE_RUNTIME record')
expected_prefix=str(scope)+'/agent-build-'
if runtime:
 name=runtime[len(expected_prefix):] if runtime.startswith(expected_prefix) else ''
 if not name or '/' in name or name in ('.','..') or not re.fullmatch(r'[A-Za-z0-9._-]+',name): errors.append('runtime is not one direct named scope child')
 runtime_path=pathlib.Path(runtime)
 runtime_state='symlink' if runtime_path.is_symlink() else ('present' if runtime_path.exists() else 'absent')
 if runtime_state!='absent': errors.append('recorded private runtime is present or symlinked')
else: runtime_state='unknown'
# Final scope observation is explicit and lstat-aware.
scope_state='symlink' if scope.is_symlink() else ('present' if scope.exists() else 'absent')
if scope_state!='absent': errors.append('private scope is not absent: '+scope_state)
receipt={'process_identities':proc,'launcher_identities':launch,'pid_start_observations':observations,'groups':groups,'group_census':group_census,'groups_absent':group_census==[],'runtime':runtime,'runtime_state':runtime_state,'runtime_absent':runtime_state=='absent','scope_state':scope_state,'scope_absent':scope_state=='absent','errors':errors,'custody_ready':not errors and bool(groups) and group_census==[] and scope_state=='absent'}
print(json.dumps(receipt,sort_keys=True))'''


def file_hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def inventory(root: Path):
    files,dirs={},[]
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root).as_posix()
        if p.is_symlink(): raise RuntimeError('symlink in extracted originals: '+rel)
        if p.is_dir(): dirs.append(rel)
        elif p.is_file(): files[rel]=file_hash(p)
        else: raise RuntimeError('unexpected extracted object: '+rel)
    return files,dirs

def ssh_code(code: str, *args: str, timeout: int=30) -> bytes:
    remote='python3 -c '+shlex.quote(code)+' '+' '.join(shlex.quote(a) for a in args)
    return subprocess.run(['ssh',HOST,remote],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=timeout).stdout

def get_inventory():
    return json.loads(ssh_code(REMOTE_INVENTORY,STAGE,PHYSICAL,SCOPE,json.dumps(INPUTS,sort_keys=True),INPUT_MANIFEST))

def get_custody():
    return json.loads(ssh_code(REMOTE_CUSTODY,STAGE,SCOPE,timeout=15))

def validate_input_binding(row: dict) -> bool:
    return (row.get('input_manifest_exact') is True and row.get('input_binding_verified') is True
            and row.get('input_expected')==INPUTS and row.get('input_actual')==INPUTS
            and row.get('inventory_errors')==[] and row.get('links')==[]
            and row.get('files',{}).get('input-identities.sha256')==hashlib.sha256(INPUT_MANIFEST.encode()).hexdigest())

def validate_custody_receipt(row: dict) -> bool:
    if not isinstance(row,dict): return False
    if row.get('custody_ready') is not True or row.get('errors')!=[]: return False
    if row.get('scope_state')!='absent' or row.get('scope_absent') is not True or row.get('groups_absent') is not True: return False
    if not isinstance(row.get('group_census'),list) or row.get('group_census')!=[] or not row.get('groups') or not isinstance(row.get('groups'),list) or any(type(x) is not int or x<=0 for x in row.get('groups',[])): return False
    if not row.get('runtime') or row.get('runtime_absent') is not True: return False
    required_proc={'helper','scoped-supervisor'}; required_launch={'launcher','run-scoped'}
    proc=row.get('process_identities',[]); launch=row.get('launcher_identities',[])
    if not isinstance(proc,list) or not isinstance(launch,list): return False
    if any(not isinstance(x,dict) for x in proc+launch): return False
    if any(not isinstance(x.get('label'),str) for x in proc+launch): return False
    if any(sum(1 for x in proc if x.get('label')==label)!=1 for label in required_proc): return False
    if any(x.get('label') not in required_proc and not (isinstance(x.get('label'),str) and x['label'].startswith('command:') and x['label'][8:]) for x in proc): return False
    if len(launch)!=2 or {x.get('label') for x in launch}!=required_launch: return False
    identities=row['process_identities']+row['launcher_identities']
    if any(not isinstance(x,dict) or not all(type(x.get(k)) is int and x[k]>0 for k in ('pid','ppid','pgid','start_ticks')) or not isinstance(x.get('cmdline'),str) for x in identities): return False
    if any(not x['cmdline'] for x in identities if x.get('label') in required_proc|required_launch): return False
    labels=[x.get('label') for x in identities]
    if len({x['pid'] for x in identities})!=len(identities): return False
    owners={x['label']:x for x in identities if x['label'] in required_proc|required_launch}
    if set(owners)!=required_proc|required_launch: return False
    if owners['run-scoped']['ppid']!=owners['launcher']['pid'] or owners['scoped-supervisor']['ppid']!=owners['run-scoped']['pid'] or owners['helper']['ppid']!=owners['scoped-supervisor']['pid']: return False
    if any(x['ppid']!=owners['helper']['pid'] for x in proc if x['label'].startswith('command:')): return False
    roots=('/root/rhai-linux-sys-process-example-20d25ad8-20261004','/var/roothome/rhai-linux-sys-process-example-20d25ad8-20261004')
    provenance={'helper':tuple(root+'/run-examples.py' for root in roots),'scoped-supervisor':tuple(root+'/runner/tools/run_scoped.py' for root in roots),'launcher':tuple(root+'/launch.sh' for root in roots),'run-scoped':tuple(root+'/runner/tools/run_scoped.py' for root in roots)}
    if any(not any(path in owners[label]['cmdline'] for path in provenance[label]) for label in provenance): return False
    runtime=row.get('runtime'); prefix=SCOPE+'/agent-build-'
    if not isinstance(runtime,str) or not runtime.startswith(prefix): return False
    runtime_name=runtime[len(prefix):]
    if not runtime_name or '/' in runtime_name or runtime_name in ('.','..') or not re.fullmatch(r'[A-Za-z0-9._-]+',runtime_name): return False
    if row.get('runtime_state')!='absent': return False
    if row.get('groups')!=sorted({x['pgid'] for x in identities}): return False
    obs=row.get('pid_start_observations',[])
    if not isinstance(obs,list) or any(not isinstance(x,dict) or not isinstance(x.get('label'),str) or any(type(x.get(k)) is not int or x[k]<=0 for k in ('pid','start_ticks','pgid')) for x in obs): return False
    expected={(x['label'],x['pid'],x['start_ticks'],x['pgid']) for x in identities}
    actual={(x.get('label'),x.get('pid'),x.get('start_ticks'),x.get('pgid')) for x in obs}
    if len(obs)!=len(identities) or actual!=expected or any(x.get('state') not in ('absent','pid-reused-original-absent') for x in obs): return False
    return True

def safe_extract(archive: Path, destination: Path):
    with tarfile.open(archive,'r:') as tf:
        for m in tf.getmembers():
            p=PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or m.issym() or m.islnk() or not(m.isfile() or m.isdir()):
                raise RuntimeError('unsafe archive member '+repr(m.name))
        destination.mkdir(mode=0o700)
        tf.extractall(destination)

def validate_retirement_receipt(receipt: dict, custody: dict) -> bool:
    if not isinstance(receipt,dict) or not isinstance(custody,dict): return False
    expected={(x['label'],x['pid'],x['start_ticks'],x['pgid']) for x in custody['process_identities']+custody['launcher_identities']}
    observations=receipt.get('final_pid_start_observations',[])
    if not isinstance(observations,list): return False
    if any(not isinstance(x,dict) or not isinstance(x.get('label'),str) or any(type(x.get(k)) is not int or x[k]<=0 for k in ('pid','start_ticks','pgid')) or x.get('state') not in ('absent','pid-reused-original-absent') for x in observations): return False
    actual={(x.get('label'),x.get('pid'),x.get('start_ticks'),x.get('pgid')) for x in observations if isinstance(x,dict)}
    return (all(receipt.get(k) is True for k in ('stage_absent','scope_absent','runtime_absent','custody_rechecked'))
            and receipt.get('final_groups')==custody['groups'] and receipt.get('final_group_census')==[]
            and isinstance(observations,list) and len(observations)==len(expected) and actual==expected
            and all(isinstance(x,dict) and x.get('state') in ('absent','pid-reused-original-absent') for x in observations))

def collect(dest: Path):
    if dest.exists() or dest.is_symlink(): raise FileExistsError(dest)
    dest.mkdir(mode=0o700,parents=True)
    status=dest/'collection-status.json'
    status.write_text(json.dumps({'originals_verified':False,'input_binding_verified':False,'custody_readback':'not-run','acceptance':False},indent=2,sort_keys=True)+'\n')
    archive=dest/'stage-originals.tar.partial'
    first=None; verified=False; fresh=None; local_files={}; local_dirs=[]
    try:
        first=get_inventory()
        with archive.open('xb') as out:
            subprocess.run(['ssh',HOST,'tar','-C',STAGE,'-cf','-','.'],stdout=out,stderr=subprocess.PIPE,check=True,timeout=120)
        raw_tar_hash=file_hash(archive)
        extraction_error=None
        try:
            safe_extract(archive,dest/'stage-originals')
            local_files,local_dirs=inventory(dest/'stage-originals')
            verified=(local_files==first.get('files') and local_dirs==first.get('directories') and not first.get('links') and not first.get('inventory_errors'))
            if not verified: extraction_error='local extracted originals differ from independent initial inventory'
        except (OSError,tarfile.TarError,RuntimeError,ValueError) as e: extraction_error=repr(e)
        # Establish byte-preservation and input-binding records before any custody call.
        first_record={'inventory':first,'raw_tar_sha256':raw_tar_hash,'local_files':local_files,'local_directories':local_dirs,'extraction_error':extraction_error,'originals_verified':verified,'input_binding_verified':validate_input_binding(first)}
        (dest/'original-preservation.json').write_text(json.dumps(first_record,indent=2,sort_keys=True)+'\n')
        archive.rename(dest/'stage-originals.tar')
        try:
            fresh=get_inventory()
            if any(fresh.get(k)!=first.get(k) for k in ('files','directories','links','inventory_errors','input_manifest_sha256','input_manifest_exact','input_actual','input_expected','input_binding_verified')):
                raise RuntimeError('fresh stage inventory/input binding changed')
            (dest/'fresh-inventory.json').write_text(json.dumps(fresh,indent=2,sort_keys=True)+'\n')
        except BaseException as e:
            (dest/'fresh-inventory.error').write_text(repr(e)+'\n')
        # Custody assessment is deliberately last and isolated; failure leaves originals intact.
        try:
            custody=get_custody(); custody['receipt_validated']=validate_custody_receipt(custody)
            (dest/'custody-readback.json').write_text(json.dumps(custody,indent=2,sort_keys=True)+'\n')
        except BaseException as e:
            (dest/'custody-readback.error').write_text(repr(e)+'\n')
        status.write_text(json.dumps({'originals_verified':verified,'input_binding_verified':validate_input_binding(first),'custody_readback':'complete' if (dest/'custody-readback.json').exists() else 'unknown','acceptance':False},indent=2,sort_keys=True)+'\n')
    except BaseException as e:
        (dest/'collection-error.txt').write_text(repr(e)+'\n')
        raise

def retire(dest: Path):
    status=json.loads((dest/'collection-status.json').read_text())
    original=json.loads((dest/'original-preservation.json').read_text())
    read=json.loads((dest/'fresh-inventory.json').read_text())
    custody_path=dest/'custody-readback-refresh.json'
    if not custody_path.is_file(): custody_path=dest/'custody-readback.json'
    custody=json.loads(custody_path.read_text())
    if status.get('originals_verified') is not True or original.get('originals_verified') is not True: raise RuntimeError('original byte preservation is incomplete; keep stage')
    if (status.get('input_binding_verified') is not True or not validate_input_binding(original['inventory'])
            or not validate_input_binding(read['inventory'] if 'inventory' in read else read)):
        raise RuntimeError('immutable input manifest/source binding failed; keep stage')
    if not validate_custody_receipt(custody) or custody.get('receipt_validated') is not True: raise RuntimeError('fresh custody is incomplete; keep stage')
    root=dest/'stage-originals'; files,dirs=inventory(root)
    if files!=original['inventory']['files'] or dirs!=original['inventory']['directories'] or file_hash(dest/'stage-originals.tar')!=original['raw_tar_sha256']: raise RuntimeError('preserved original bytes changed; keep stage')
    fresh=get_inventory(); fresh_custody=get_custody()
    if any(fresh.get(k)!=read.get(k) for k in ('files','directories','links','inventory_errors','input_manifest_sha256','input_manifest_exact','input_actual','input_expected','input_binding_verified')): raise RuntimeError('fresh immutable stage inventory changed; keep stage')
    if not validate_input_binding(fresh): raise RuntimeError('fresh ten-input binding failed; keep stage')
    if not validate_custody_receipt(fresh_custody) or fresh_custody!= {k:v for k,v in custody.items() if k!='receipt_validated'}: raise RuntimeError('fresh identity/runtime/group receipt changed; keep stage')
    payload=json.dumps(fresh,sort_keys=True); cust=json.dumps(fresh_custody,sort_keys=True)
    deletion=r'''import hashlib,json,pathlib,re,subprocess,sys
m=json.loads(sys.argv[1]); c=json.loads(sys.argv[2]); s=pathlib.Path(sys.argv[3]); physical=pathlib.Path(sys.argv[4]); scope=pathlib.Path(sys.argv[5])
if s.is_symlink() or not s.is_dir() or s.resolve()!=physical: raise SystemExit('exact stage path changed')
if scope.exists() or scope.is_symlink(): raise SystemExit('scope is present')
if c.get('custody_ready') is not True or c.get('scope_absent') is not True or c.get('scope_state')!='absent' or c.get('group_census')!=[] or c.get('runtime_absent') is not True: raise SystemExit('custody receipt is incomplete')
for row in c['process_identities']+c['launcher_identities']:
 if not all(isinstance(row.get(k),int) and row[k]>0 for k in ('pid','pgid','start_ticks')): raise SystemExit('invalid recorded identity')
 try:
  raw=pathlib.Path('/proc',str(row['pid']),'stat').read_text(); prefix=str(row['pid'])+' ('; close=raw.rfind(')')
  if not raw.startswith(prefix) or close<=len(prefix) or raw[close+1:close+2]!=' ': raise ValueError('malformed stat PID/comm framing')
  fields=raw[close+2:].split()
  if len(fields)<=19 or len(fields[0])!=1 or fields[0] not in 'RSDZTtXxKWPI' or not all(re.fullmatch(r'-?\d+',x) for x in fields[1:20]) or int(fields[19])<=0: raise ValueError('invalid stat state/start fields')
  if int(fields[19])==row['start_ticks']: raise SystemExit('recorded PID/start still live')
 except FileNotFoundError: pass
 except (PermissionError,OSError,IndexError,ValueError) as e: raise SystemExit('PID/start unknown: '+repr(e))
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5); groups=set(c['groups']); census=[]
for line in ps.splitlines():
 f=line.split()
 if len(f)!=2 or not all(x.isdigit() for x in f) or int(f[0])<=0 or int(f[1])<0: raise SystemExit('malformed group census')
 if int(f[1]) in groups: census.append([int(f[0]),int(f[1])])
if census: raise SystemExit('group members remain: '+repr(census))
runtime=c.get('runtime'); prefix=str(scope)+'/agent-build-'
if not runtime or not runtime.startswith(prefix): raise SystemExit('runtime provenance invalid')
name=runtime[len(prefix):]
if not name or '/' in name or name in ('.','..') or not re.fullmatch(r'[A-Za-z0-9._-]+',name): raise SystemExit('runtime path grammar invalid')
r=pathlib.Path(runtime)
if r.is_symlink() or r.exists(): raise SystemExit('runtime is present or symlinked')
if s.resolve()!=pathlib.Path(m['physical']): raise SystemExit('physical path mismatch')
files={}; dirs=[]; links=[]
for p in sorted(s.rglob('*')):
 rel=p.relative_to(s).as_posix()
 if p.is_symlink(): links.append(rel)
 elif p.is_dir(): dirs.append(rel)
 elif p.is_file():
  h=hashlib.sha256()
  with p.open('rb') as q:
   for b in iter(lambda:q.read(1048576),b''): h.update(b)
  files[rel]=h.hexdigest()
 else: raise SystemExit('unexpected stage object '+rel)
if files!=m['files'] or dirs!=m['directories'] or links!=m['links'] or m['inventory_errors']: raise SystemExit('stage inventory changed')
expected=json.loads(sys.argv[6]); order=json.loads(sys.argv[7]); manifest=''.join(expected[k]+'  '+k+'\n' for k in order)
if (s/'input-identities.sha256').read_text()!=manifest: raise SystemExit('input manifest changed')
for k,v in expected.items():
 if files.get(k)!=v: raise SystemExit('input mismatch '+k)
for rel in sorted(files,reverse=True): (s/rel).unlink()
for rel in sorted(dirs,key=lambda x:(x.count('/'),x),reverse=True): (s/rel).rmdir()
s.rmdir()
if s.exists() or s.is_symlink() or scope.exists() or scope.is_symlink() or r.exists() or r.is_symlink(): raise SystemExit('stage/scope/runtime absence failed')
# Final observation receipt is emitted only after exact deletion and absence readback.
ps2=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5); census2=[]
for line in ps2.splitlines():
 f=line.split()
 if len(f)!=2 or not all(x.isdigit() for x in f) or int(f[0])<=0 or int(f[1])<0: raise SystemExit('malformed final group census')
 if int(f[1]) in groups: census2.append([int(f[0]),int(f[1])])
if census2: raise SystemExit('final owned group remains')
final_obs=[]
for row in c['process_identities']+c['launcher_identities']:
 try:
  raw=pathlib.Path('/proc',str(row['pid']),'stat').read_text(); prefix=str(row['pid'])+' ('; close=raw.rfind(')')
  if not raw.startswith(prefix) or close<=len(prefix) or raw[close+1:close+2]!=' ': raise ValueError('malformed final stat PID/comm framing')
  fields=raw[close+2:].split()
  if len(fields)<=19 or len(fields[0])!=1 or fields[0] not in 'RSDZTtXxKWPI' or not all(re.fullmatch(r'-?\d+',x) for x in fields[1:20]) or int(fields[19])<=0: raise ValueError('invalid final stat state/start fields')
  state='live' if int(fields[19])==row['start_ticks'] else 'pid-reused-original-absent'
 except FileNotFoundError: state='absent'
 except (PermissionError,OSError,IndexError,ValueError) as e: raise SystemExit('final PID/start unknown: '+repr(e))
 if state=='live': raise SystemExit('recorded PID/start became live before final receipt')
 final_obs.append({'label':row['label'],'pid':row['pid'],'start_ticks':row['start_ticks'],'pgid':row['pgid'],'state':state})
print(json.dumps({'stage_absent':not s.exists() and not s.is_symlink(),'scope_absent':not scope.exists() and not scope.is_symlink(),'runtime_absent':not r.exists() and not r.is_symlink(),'final_pid_start_observations':final_obs,'final_groups':sorted(groups),'final_group_census':census2,'custody_rechecked':True,'removed_files':len(files),'removed_directories':len(dirs)},sort_keys=True))'''
    remote='python3 -c '+shlex.quote(deletion)+' '+shlex.quote(payload)+' '+shlex.quote(cust)+' '+shlex.quote(STAGE)+' '+shlex.quote(PHYSICAL)+' '+shlex.quote(SCOPE)+' '+shlex.quote(json.dumps(INPUTS,sort_keys=True))+' '+shlex.quote(json.dumps(INPUT_ORDER))
    result=subprocess.run(['ssh',HOST,remote],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30)
    receipt=json.loads(result.stdout)
    if not validate_retirement_receipt(receipt,fresh_custody):
        raise RuntimeError('final absence/identity/group receipt incomplete')
    (dest/'retirement-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

def custody_readback(dest: Path):
    """Write a new named readback after verifying the preserved original bytes."""
    if (dest/'custody-readback-refresh.json').exists(): raise FileExistsError(dest/'custody-readback-refresh.json')
    original=json.loads((dest/'original-preservation.json').read_text())
    if original.get('originals_verified') is not True or not validate_input_binding(original['inventory']):
        raise RuntimeError('preserved originals/input binding are not verified; keep stage')
    files,dirs=inventory(dest/'stage-originals')
    if files!=original['inventory']['files'] or dirs!=original['inventory']['directories'] or file_hash(dest/'stage-originals.tar')!=original['raw_tar_sha256']:
        raise RuntimeError('preserved original bytes changed; keep stage')
    fresh=get_inventory()
    if not validate_input_binding(fresh) or any(fresh.get(k)!=original['inventory'].get(k) for k in ('files','directories','links','inventory_errors','input_manifest_sha256','input_manifest_exact','input_actual','input_expected','input_binding_verified')):
        raise RuntimeError('fresh immutable stage inventory differs; keep stage')
    custody=get_custody(); custody['receipt_validated']=validate_custody_receipt(custody)
    (dest/'custody-readback-refresh.json').write_text(json.dumps(custody,indent=2,sort_keys=True)+'\n')

def main():
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=('collect','custody-readback','retire')); p.add_argument('destination',type=Path); a=p.parse_args()
    if a.mode=='collect': collect(a.destination)
    elif a.mode=='custody-readback': custody_readback(a.destination)
    else: retire(a.destination)
if __name__=='__main__': main()
