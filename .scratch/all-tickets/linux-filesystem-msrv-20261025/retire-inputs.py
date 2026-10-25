"""Retire only the completed, hash-bound Linux transfer/staging copies."""
from pathlib import Path
import os,subprocess,json,hashlib,shutil,shlex
p=Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text());sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
stage=Path(os.environ['AGENT_RUNTIME_DIR'])/'host';subprocess.run(['scp','-r','workhorse:'+b['host_staging'],str(stage)],check=True)
assert sha(stage/'source.tar')==b['archive_sha256'] and sha(stage/'Cargo.lock')==b['source_lock_sha256']
manifest={}
for f in stage.rglob('*'):
 assert not f.is_symlink()
 if not f.is_file():continue
 name=f.relative_to(stage).as_posix();manifest[name]=sha(f)
 if name in ('source.tar','Cargo.lock'):continue
 if name.startswith('preparation01-'): target=p/'preparation01'/name.replace('preparation01-','',1)
 elif name.startswith('preparation02-'):target=p/'preparation02'/name.replace('preparation02-','',1)
 else:target=p/name
 if target.exists() and sha(target)==sha(f):continue
 target=p/('host-original-'+name) if target.exists() else target
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
(p/'input-retirement-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
code='''from pathlib import Path
import json,hashlib,os
root=Path(ROOT);expected=MANIFEST;scopes=SCOPES
assert all(not Path(x).exists() for x in scopes)
# No surviving command may use this exact completed staging tree.
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
 try:cmd=(proc/'cmdline').read_bytes()
 except (FileNotFoundError,PermissionError,ProcessLookupError):continue
 assert str(root).encode() not in cmd,'Active staging user: '+proc.name
assert root.is_dir() and not root.is_symlink()
actual={}
for f in root.rglob('*'):
 assert not f.is_symlink()
 if f.is_file():actual[f.relative_to(root).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
assert actual==expected
for name in expected:(root/name).unlink()
for d in sorted((x for x in root.rglob('*') if x.is_dir()),key=lambda x:len(x.parts),reverse=True):d.rmdir()
root.rmdir()
print(json.dumps({'host_staging_absent':not root.exists(),'scopes_absent':scopes,'files_retired':len(expected)}))
'''.replace('ROOT',repr(b['host_staging'])).replace('MANIFEST',repr(manifest)).replace('SCOPES',repr(b['prior_session_scopes']+[b['session_scope']]))
r=subprocess.run(['ssh','workhorse','python3 -B -'],input=code.encode(),capture_output=True,check=True)
record=json.loads(r.stdout);local=Path(b['transfer_source_path']);assert local.is_dir() and not local.is_symlink()
assert sorted(x.name for x in local.iterdir())==['Cargo.lock','source.tar']
assert sha(local/'source.tar')==b['archive_sha256'] and sha(local/'Cargo.lock')==b['source_lock_sha256']
for f in local.iterdir():assert f.is_file() and not f.is_symlink();f.unlink()
local.rmdir();record['local_transfer_absent']=not local.exists();record['accepted_evidence_preserved']=True
(p/'input-retirement.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
