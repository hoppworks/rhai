"""Inspect or retire only the exactly preserved pre-test setup-failure stage."""
import argparse, hashlib, json, pathlib, shlex, subprocess, sys
BASE=pathlib.Path(__file__).resolve().parent
DEST=BASE/'linux-drop-false-native1-originals'
REMOTE=r'''
import hashlib,json,pathlib,re,shlex,subprocess,sys
m=json.load(sys.stdin);stage=pathlib.Path('/root/rhai-linux-drop-false-523-20261004');physical=pathlib.Path('/var/roothome/rhai-linux-drop-false-523-20261004');scope=pathlib.Path('/root/.local/share/agent-builds/rhai/linux-drop-false-523-20261004')
assert m['stage']==str(stage) and m['scope']==str(scope)
assert stage.is_dir() and not stage.is_symlink() and stage.resolve()==physical
assert not scope.exists() and not scope.is_symlink()
def inventory():
 files={};dirs=[]
 for p in sorted(stage.rglob('*')):
  assert not p.is_symlink(),str(p)
  rel=p.relative_to(stage).as_posix()
  if p.is_dir():dirs.append(rel)
  elif p.is_file():files[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
  else:raise RuntimeError('nonregular stage entry '+str(p))
 assert files==m['files'] and dirs==m['directories'],'preserved byte inventory mismatch'
 return files,dirs
files,dirs=inventory();proof=stage/'proof-evidence';outer=stage/'outer-evidence'
result=json.loads((proof/'package-result.json').read_text());early=json.loads((proof/'early-runtime-identity.json').read_text())
assert result['status']==1 and result['acceptance_claim'] is False and result['controls']==[]
assert result['source_revision']=='523608648dcae99bc0f6b46eaf2bb91fa4ecc752' and result['source_restored_to_baseline'] is True
assert [(x['name'],x['status']) for x in result['commands']]==[('rustup-install',0),('rustc-version',0),('cargo-version',0)]
assert (outer/'outer-status.txt').read_text().strip()=='1' and (outer/'run-scoped.status').read_text().strip()=='1'
for name in ['pid-readback.status','pid-readback-launcher.status']:assert (outer/name).read_text().strip()=='0'
for name in ['runtime-cleanup.tsv','scope-cleanup.tsv']:assert 'status=0' in (outer/name).read_text()
assert not list(proof.glob('*-green.status')) and not list(proof.glob('*-red.status'))
runtime=pathlib.Path(early['runtime']);assert runtime.is_absolute() and runtime.parent==scope
assert not runtime.exists() and not runtime.is_symlink() and not early['identity_errors']
rows=[];seen=set()
for filename in [outer/'launcher-identities.tsv',proof/'process-identities.tsv']:
 lines=filename.read_text().splitlines();assert lines[0]=='label\tpid\tppid\tpgid\tstart_ticks\tcmdline'
 for line in lines[1:]:
  f=line.split('\t',5);assert len(f)==6 and all(re.fullmatch('[0-9]+',v) for v in f[1:5])
  row=dict(label=f[0],pid=int(f[1]),ppid=int(f[2]),pgid=int(f[3]),start_ticks=int(f[4]),cmdline=f[5]);assert min(row['pid'],row['pgid'],row['start_ticks'])>0
  assert (row['pid'],row['start_ticks']) not in seen;seen.add((row['pid'],row['start_ticks']));rows.append(row)
by={r['label']:r for r in rows if not r['label'].startswith('command:')}
assert set(by)=={'launcher','run-scoped','helper','scoped-supervisor'}
launch,runner,helper,supervisor=[by[k] for k in ['launcher','run-scoped','helper','scoped-supervisor']]
assert runner['ppid']==launch['pid'] and supervisor['ppid']==runner['pid'] and helper['ppid']==supervisor['pid'] and helper['pgid']==supervisor['pid']==supervisor['pgid']
assert shlex.split(launch['cmdline'])==[str(stage/'launch.sh')]
assert shlex.split(runner['cmdline'])==['python3',str(stage/'runner/tools/run_scoped.py'),'--timeout','570','--','python3',str(stage/'linux-drop-false-proof.py')]
assert shlex.split(helper['cmdline'])==['python3',str(stage/'linux-drop-false-proof.py')]
assert shlex.split(supervisor['cmdline'])==['/usr/bin/python3',str(physical/'runner/tools/run_scoped.py'),'_supervise','4','python3',str(stage/'linux-drop-false-proof.py')]
for key,row in [('helper',helper),('scoped_supervisor',supervisor)]:
 assert all(str(row[k])==str(early[key][k]) for k in ['pid','ppid','pgid','start_ticks','cmdline'])
for row in rows:
 if row['label'].startswith('command:'):
  assert row['label'] in {'command:rustup-install','command:rustc-version','command:cargo-version','command:du','command:ps'}
  assert row['ppid']==helper['pid'] and row['pgid']==supervisor['pgid']
groups=sorted({r['pgid'] for r in rows})
def absent():
 for row in rows:
  try:raw=pathlib.Path('/proc',str(row['pid']),'stat').read_text(encoding='ascii')
  except FileNotFoundError:continue
  close=raw.rfind(')');assert raw.startswith(str(row['pid'])+' (') and close>len(str(row['pid'])) and raw[close+1:close+2]==' '
  f=raw[close+2:].split();assert len(f)>=20 and re.fullmatch('[0-9]+',f[19]) and int(f[19])>0
  assert int(f[19])!=row['start_ticks'],'exact owned process remains'
 ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
 for line in ps.splitlines():
  f=line.split();assert len(f)==2 and all(v.isdecimal() for v in f)
  assert int(f[1]) not in groups,'owned group populated'
 for p in [scope,runtime]:assert not p.exists() and not p.is_symlink()
absent();inventory();absent()
removed=False
if sys.argv[1]=='retire':
 for rel in sorted(files,reverse=True):(stage/rel).unlink()
 for rel in sorted(dirs,key=lambda v:(v.count('/'),v),reverse=True):(stage/rel).rmdir()
 stage.rmdir();removed=True
 for p in [stage,physical,scope,runtime]:assert not p.exists() and not p.is_symlink()
 absent()
print(json.dumps(dict(acceptance=False,setup_failure_only=True,identities=rows,groups=groups,runtime=str(runtime),files_verified=len(files),directories_verified=len(dirs),stage_removed=removed,scope_absent=True,runtime_absent=True,groups_empty=True),sort_keys=True))
'''
def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['inspect','retire']);args=parser.parse_args()
 manifest=json.loads((DEST/'independent-readback.json').read_text());export=json.loads((DEST/'export-manifest.json').read_text())
 tree=DEST/'stage-originals';files={};dirs=[]
 for p in sorted(tree.rglob('*')):
  assert not p.is_symlink()
  rel=p.relative_to(tree).as_posix()
  if p.is_file():files[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
  elif p.is_dir():dirs.append(rel)
  else:raise RuntimeError(str(p))
 assert files==manifest['files']==export['files'] and dirs==manifest['directories']==export['directories']
 tar=DEST.with_name(DEST.name+'.stage-originals.tar');stored_tar=pathlib.Path(export['raw_tar_path']);stored_tar=stored_tar if stored_tar.is_absolute() else BASE.parent.parent/stored_tar
 assert stored_tar.resolve()==tar and not stored_tar.is_symlink() and hashlib.sha256(tar.read_bytes()).hexdigest()==export['raw_tar_sha256']
 assert hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()==export['readback_sha256']
 proc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','workhorse','python3','-c',shlex.quote(REMOTE),args.mode],input=json.dumps(manifest),text=True,capture_output=True,check=True,timeout=30)
 receipt=json.loads(proc.stdout);assert receipt['stage_removed']==(args.mode=='retire') and receipt['acceptance'] is False
 (DEST/('failed-run-'+args.mode+'-readback.json')).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(proc.stdout,end='')
if __name__=='__main__':main()
