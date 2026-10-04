#!/usr/bin/env python3
"""Preserve exact measurement originals, validate custody, then permit exact stage retirement."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shlex, shutil, subprocess, tarfile
from pathlib import Path, PurePosixPath

STAGE='/root/rhai-linux-process-performance-8c0ee-20261004'
SCOPE='/root/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004'
PHYSICAL='/var/roothome/rhai-linux-process-performance-8c0ee-20261004'
ROOT=Path(__file__).resolve().parent
DEST=ROOT/'originals'
PREFLIGHT=Path('/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/linux-process-performance-preflight.py')
SLOT_WRAPPER=Path('/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/linux-process-performance-slot-wrapper.py')

INVENTORY=r'''import hashlib,json,pathlib,sys
s=pathlib.Path(sys.argv[1]);scope=pathlib.Path(sys.argv[2])
if not s.is_dir() or s.is_symlink():raise SystemExit('stage unavailable')
f={};d=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink():raise SystemExit('stage symlink '+r)
 if p.is_dir():d.append(r)
 elif p.is_file():f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('unexpected stage object '+r)
print(json.dumps({'stage':str(s),'scope':str(scope),'files':f,'directories':d},sort_keys=True))'''

PROCESS_CHECK=r'''import json,pathlib,shlex,subprocess,sys
import hashlib
s=pathlib.Path(sys.argv[1]);scope=pathlib.Path(sys.argv[2]);physical=pathlib.Path(sys.argv[3]);m=json.loads(sys.argv[4])
stages={pathlib.Path('/root/rhai-linux-process-performance-8c0ee-20261004'),pathlib.Path('/var/roothome/rhai-linux-process-performance-8c0ee-20261004')}
scopes={pathlib.Path('/root/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004'),pathlib.Path('/var/roothome/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004')}
if s not in stages or physical!=pathlib.Path('/var/roothome/rhai-linux-process-performance-8c0ee-20261004') or scope not in scopes or s.is_symlink() or s.resolve()!=physical:raise SystemExit('exact stage identity mismatch')
if scope.exists() or scope.is_symlink():raise SystemExit('private scope/runtime remains')
allocation=json.loads((s/'native-allocation.json').read_text())
if allocation.get('source_revision')!='8c0ee4634355aee4e841b455461a7dd5aac2aa18' or allocation.get('native_launch')!=1 or allocation.get('preflight_source_sha256')!=hashlib.sha256((s/'linux-process-performance-preflight.py').read_bytes()).hexdigest() or allocation.get('slot_wrapper_source_sha256')!=hashlib.sha256((s/'linux-process-performance-slot-wrapper.py').read_bytes()).hexdigest():raise SystemExit('allocation/provenance receipt differs from staged admission files')
receipt=allocation.get('preflight',{})
if receipt.get('ready') is not True or receipt.get('inputs_verified')!=11 or receipt.get('heavy')!=[] or receipt.get('scope_absent') is not True:raise SystemExit('initial admission receipt is not successful')
f={};d=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink():raise SystemExit('stage symlink '+r)
 if p.is_dir():d.append(r)
 elif p.is_file():f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('unexpected stage object '+r)
if f!=m['files'] or d!=m['directories']:raise SystemExit('fresh stage inventory differs from preserved originals')
# Unknown /proc is an error; only absent or a changed start tick proves retired/reused.
def alive(pid,start):
 try:
  raw=pathlib.Path('/proc',str(pid),'stat').read_text();z=raw.rfind(')');prefix=str(pid)+' ('
  if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ':raise ValueError('malformed proc stat')
  x=raw[z+2:].split()
  if len(x)<20 or not x[19].isdigit() or int(x[19])<=0:raise ValueError('malformed proc start ticks')
  return int(x[19])==start
 except (FileNotFoundError,ProcessLookupError):return False
 except (PermissionError,OSError,ValueError,IndexError) as e:raise SystemExit('process identity unknown '+str(pid)+': '+repr(e))
proof=s/'proof-evidence';outer=s/'outer-evidence'
required={'measurement-result.json','source-restoration.json','source-inputs.json','sampled-maxima.json','resource-samples.jsonl','process-identities.tsv','early-runtime-identity.json','commands.json','control-results.json','tool-versions.json','rustc-version.stdout','cargo-version.stdout','measurements.stdout','measurements.stderr','control-pass.stdout','control-pass.stderr'}
if not required.issubset({p.name for p in proof.iterdir()}):raise SystemExit('performance proof originals missing')
if (outer/'outer-status.txt').read_text().strip()!='0' or (outer/'run-scoped.status').read_text().strip()!='0':raise SystemExit('outer/run-scoped status failed')
for name in ('runtime-cleanup.tsv','scope-cleanup.tsv'):
 if 'cleanup_status=0' not in (outer/name).read_text():raise SystemExit('runtime/scope cleanup failed '+name)
early=json.loads((proof/'early-runtime-identity.json').read_text());runtime=pathlib.Path(early['runtime'])
if not runtime.is_absolute() or runtime.parent not in scopes or not runtime.name.startswith('agent-build-') or runtime.exists() or runtime.is_symlink():raise SystemExit('runtime path is not exact absent direct child')
rows=(proof/'process-identities.tsv').read_text().splitlines()
if not rows or rows[0]!='label\tpid\tppid\tpgid\tstart_ticks\tcmdline':raise SystemExit('process identity header mismatch')
seen={};repeat={'command:du':[],'command:ps':[]};groups=set();all_ids=set()
for line in rows[1:]:
 x=line.split('\t',5)
 if len(x)!=6 or not all(v.isdigit() for v in x[1:5]):raise SystemExit('malformed process identity row')
 label,pid,ppid,pgid,start,cmd=x;pid,ppid,pgid,start=map(int,(pid,ppid,pgid,start));key=(pid,start)
 if pid<1 or pgid<1 or start<1 or key in all_ids:raise SystemExit('invalid/duplicate process identity')
 all_ids.add(key)
 if alive(pid,start):raise SystemExit('owned identity remains live '+label)
 row={'pid':pid,'ppid':ppid,'pgid':pgid,'start':start,'cmd':cmd};groups.add(pgid)
 if label in repeat:repeat[label].append(row)
 elif label in seen:raise SystemExit('duplicate singleton label '+label)
 else:seen[label]=row
need={'helper','scoped-supervisor','command:rustup-install','command:rustc-version','command:cargo-version','command:control-pass','command:measurements'}
if set(seen)!=need or not repeat['command:du'] or not repeat['command:ps']:raise SystemExit('missing/unknown identities or sampler instances')
if seen['helper']['ppid']!=seen['scoped-supervisor']['pid']:raise SystemExit('helper/supervisor ancestry mismatch')
if any(v['ppid']!=seen['helper']['pid'] for k,v in seen.items() if k.startswith('command:')):raise SystemExit('command/helper ancestry mismatch')
if any(v['ppid']!=seen['helper']['pid'] for rs in repeat.values() for v in rs):raise SystemExit('sampler/helper ancestry mismatch')
for label,expected in (('command:du',f'/usr/bin/du -sk {runtime}'),('command:ps','/bin/ps -e -o pid=,ppid=,rss=')):
 observed=[v['cmd'] for v in repeat[label] if v['cmd']]
 # Short-lived sampler processes can exit before /proc/cmdline is read. Their
 # exact ledger identity and later absence remain required; every captured
 # argv must match, and at least one captured argv must bind each sampler.
 if any(cmd!=expected for cmd in observed) or expected not in observed:raise SystemExit('sampler argv/runtime mismatch '+label)
if not all(pathlib.Path(x['cmd'].split()[0]).name=='python3' for x in (seen['helper'],seen['scoped-supervisor'])):raise SystemExit('helper or supervisor executable mismatch')
if shlex.split(seen['helper']['cmd'])[1:]!=[str(s/'linux-process-performance-proof.py')]:raise SystemExit('helper argv mismatch')
sup=shlex.split(seen['scoped-supervisor']['cmd'])
if len(sup)!=6 or sup[1]!=str(physical/'runner/tools/run_scoped.py') or sup[2]!='_supervise' or not sup[3].isdigit() or sup[4:]!=['python3',str(s/'linux-process-performance-proof.py')]:raise SystemExit('supervisor argv mismatch')
if set(x for x in groups)!=groups:raise SystemExit('invalid group set')
early=json.loads((proof/'early-runtime-identity.json').read_text())
for label,key in [('helper','helper'),('scoped-supervisor','scoped_supervisor')]:
 x=early.get(key)
 if not isinstance(x,dict) or (x.get('pid'),x.get('ppid'),x.get('pgid'),str(x.get('start_ticks')),x.get('cmdline'))!=(seen[label]['pid'],seen[label]['ppid'],seen[label]['pgid'],str(seen[label]['start']),seen[label]['cmd']):raise SystemExit('early identity differs from complete process ledger '+label)
outer=s/'outer-evidence';launchrows=(outer/'launcher-identities.tsv').read_text().splitlines()
if not launchrows or launchrows[0]!='label\tpid\tppid\tpgid\tstart_ticks\tcmdline':raise SystemExit('launcher identity header mismatch')
launchers={}
for line in launchrows[1:]:
 x=line.split('\t',5)
 if len(x)!=6 or not all(q.isdigit() for q in x[1:5]):raise SystemExit('malformed launcher identity')
 label,pid,ppid,pgid,start,cmd=x;pid,ppid,pgid,start=map(int,(pid,ppid,pgid,start))
 if label in launchers or alive(pid,start):raise SystemExit('launcher identity duplicate/live')
 launchers[label]={'pid':pid,'ppid':ppid,'pgid':pgid,'start':start,'cmd':cmd};groups.add(pgid)
if set(launchers)!={'launcher','run-scoped'} or seen['scoped-supervisor']['ppid']!=launchers['run-scoped']['pid'] or launchers['run-scoped']['ppid']!=launchers['launcher']['pid'] or launchers['launcher']['cmd']!=str(s/'launch.sh'):raise SystemExit('launcher ancestry/argv mismatch')
runner=shlex.split(launchers['run-scoped']['cmd'])
if len(runner)!=7 or pathlib.Path(runner[0]).name!='python3' or runner[1]!=str(s/'runner/tools/run_scoped.py') or runner[2]!='--timeout' or not runner[3].isdigit() or not 0<int(runner[3])<=585 or runner[4:]!=['--','python3',str(s/'linux-process-performance-proof.py')]:raise SystemExit('run-scoped argv mismatch')
# Bind fixture identities from the raw producer outputs. Direct-child groups are
# context only; only the dedicated Managed group is added to owned-group census.
sample_text=(proof/'measurements.stdout').read_text()+'\n'+(proof/'measurements.stderr').read_text()
fixture_ids=[];managed_groups=[]
for line in sample_text.splitlines():
 if line.startswith('PERF_START,') or line.startswith('PERF_RESOURCE,'):
  fields=dict(x.split('=',1) for x in line.split(',')[1:])
  pid,start,pgid=map(int,(fields['pid'],fields['start_ticks'],fields['pgid']))
  if pid<1 or start<1 or pgid<1 or (pid,start) in all_ids:raise SystemExit('invalid or duplicate public fixture identity')
  all_ids.add((pid,start));fixture_ids.append((fields.get('mode',''),pid,start,pgid))
  if alive(pid,start):raise SystemExit('public held fixture identity remains live')
  if fields.get('mode')=='managed':
   if pgid!=pid or (line.startswith('PERF_RESOURCE,') and fields.get('group_members_owned')!='true'):raise SystemExit('managed fixture group is not independently owned')
   groups.add(pgid);managed_groups.append(pgid)
if len(fixture_ids)!=12 or len(managed_groups)!=6 or len(set(managed_groups))!=6:raise SystemExit('public fixture identity receipts are incomplete')
control=(proof/'control-pass.stdout').read_text()+'\n'+(proof/'control-pass.stderr').read_text()
control_identity_count=0
for line in control.splitlines():
 if line.startswith('PERF_CONTROL,kind=resource-count,'):
  fields=dict(x.split('=',1) for x in line.split(',')[1:]);pid,start=int(fields['pid']),int(fields['start_ticks'])
  if (pid,start) in all_ids:raise SystemExit('duplicate resource-control fixture identity')
  if alive(pid,start):raise SystemExit('resource-control fixture identity remains live')
  all_ids.add((pid,start));control_identity_count+=1
if control_identity_count!=1:raise SystemExit('resource-control fixture identity receipt missing or duplicated')
if set(launchers)!={'launcher','run-scoped'} or not groups:raise SystemExit('complete owned group set is empty')
# One fresh census after all helper, command, launcher and Managed fixture
# groups have been collected. A malformed/unknown census fails closed.
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5);members=[]
for line in ps.splitlines():
 z=line.split()
 if len(z)!=2 or not all(q.isdecimal() for q in z):raise SystemExit('malformed process census')
 if int(z[1]) in groups:members.append([int(z[0]),int(z[1])])
if members:raise SystemExit('owned process groups are nonempty '+repr(members))
print(json.dumps({'fresh_stage_inventory':True,'scope_absent':True,'exact_identities_absent_or_reused':len(all_ids),'sampler_instances':sum(map(len,repeat.values())),'public_fixture_identities_absent':len(fixture_ids),'managed_fixture_groups':managed_groups,'owned_groups_empty':True},sort_keys=True))'''

RETIRE=PROCESS_CHECK.rsplit("print(json.dumps",1)[0]+r'''# Repeat the owned-group census and exact byte inventory directly before removal.
import shutil
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5);last=[]
for line in ps.splitlines():
 z=line.split()
 if len(z)!=2 or not all(q.isdecimal() for q in z):raise SystemExit('malformed final process census')
 if int(z[1]) in groups:last.append([int(z[0]),int(z[1])])
if last:raise SystemExit('owned group became nonempty before retirement '+repr(last))
f={};d=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink():raise SystemExit('immediate retirement symlink '+r)
 if p.is_dir():d.append(r)
 elif p.is_file():f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('immediate retirement unexpected object '+r)
if f!=m['files'] or d!=m['directories'] or s.is_symlink() or s.resolve()!=physical or scope.exists() or scope.is_symlink():raise SystemExit('immediate pre-retirement inventory/path mismatch')
shutil.rmtree(s)
if s.exists() or s.is_symlink() or scope.exists() or scope.is_symlink():raise SystemExit('fresh post-retirement absence failed')
print(json.dumps({'exact_stage_removed':True,'scope_absent':True,'fresh_owned_groups_empty':True},sort_keys=True))'''


def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def ssh_json(code: str, manifest: dict|None=None) -> dict:
    argv=[STAGE,SCOPE,PHYSICAL]
    if manifest is not None: argv.append(json.dumps(manifest,sort_keys=True))
    remote='python3 -c '+shlex.quote(code)+' '+' '.join(shlex.quote(x) for x in argv)
    return json.loads(subprocess.check_output(['ssh','workhorse',remote],text=True,timeout=60))
def inventory()->dict:return ssh_json(INVENTORY)

def validate_local(proofdir: Path, root: Path) -> None:
    proofpath=proofdir/'proof-used.py'
    reviewed_proof=ROOT/'linux-process-performance-proof.py'
    expected_proof_hash=digest(reviewed_proof)
    if proofpath.is_symlink() or not proofpath.is_file() or digest(proofpath)!=expected_proof_hash:
        raise ValueError('exported proof consumer differs from reviewed local bytes')
    staged_proof=root/'linux-process-performance-proof.py'
    if staged_proof.is_symlink() or not staged_proof.is_file() or digest(staged_proof)!=expected_proof_hash:
        raise ValueError('staged proof consumer differs from reviewed local bytes')
    spec=importlib.util.spec_from_file_location('frozen_measurement_proof',reviewed_proof)
    if spec is None or spec.loader is None: raise ValueError('missing pinned proof consumer')
    module=importlib.util.module_from_spec(spec)
    import sys
    sys.dont_write_bytecode=True
    spec.loader.exec_module(module)
    staged=root
    expected_inputs={
        'source.tar':module.ARCHIVE,'Cargo.lock.accepted':module.LOCK,
        'check-linux-current-msrv-examples.py':module.BASE_HELPER,
        'archive-build-source.py':module.ARCHIVE_HELPER,
        'linux_process_performance.rs':module.TEST,'measurement-contract.md':module.CONTRACT,
        'linux-process-performance-proof.py':digest(ROOT/'linux-process-performance-proof.py'),
        'launch.sh':digest(ROOT/'launch.sh'),
        'runner/tools/run_scoped.py':'9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d',
        'runner/tools/agentskills/__init__.py':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'runner/tools/agentskills/pyguard.py':'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f',
    }
    manifest={}
    for line in (staged/'input-identities.sha256').read_text().splitlines():
        parts=line.split(None,1)
        if len(parts)!=2 or parts[1] in manifest:raise ValueError('staged input manifest malformed')
        manifest[parts[1]]=parts[0]
    if manifest!=expected_inputs:raise ValueError('staged package input manifest differs from exact reviewed pins')
    for name,expected_hash in expected_inputs.items():
        if digest(staged/name)!=expected_hash:raise ValueError('staged input hash mismatch '+name)
    guard_hash=digest(PREFLIGHT);wrapper_hash=digest(SLOT_WRAPPER)
    for name,expected_hash in (('linux-process-performance-preflight.py',guard_hash),('linux-process-performance-slot-wrapper.py',wrapper_hash)):
        path=staged/name
        if not path.is_file() or path.is_symlink() or digest(path)!=expected_hash:raise ValueError('staged admission source mismatch '+name)
    allocation=json.loads((staged/'native-allocation.json').read_text())
    if allocation.get('source_revision')!=module.REV or allocation.get('native_launch')!=1 or allocation.get('preflight_source_sha256')!=guard_hash or allocation.get('slot_wrapper_source_sha256')!=wrapper_hash:raise ValueError('allocation provenance does not bind reviewed admission files')
    admission=allocation.get('preflight',{})
    if admission.get('ready') is not True or admission.get('inputs_verified')!=11 or admission.get('heavy')!=[] or admission.get('scope_absent') is not True:raise ValueError('initial admission receipt is incomplete or not ready')
    result=json.loads((proofdir/'measurement-result.json').read_text())
    inputs=json.loads((proofdir/'source-inputs.json').read_text())
    restored=json.loads((proofdir/'source-restoration.json').read_text())
    expected={'revision':module.REV,'source_archive_sha256':module.ARCHIVE,'lock_sha256':module.LOCK,'base_helper_sha256':module.BASE_HELPER,'archive_helper_sha256':module.ARCHIVE_HELPER,'measurement_harness_sha256':module.TEST,'contract_sha256':module.CONTRACT,'test_target':'linux_process_performance','features':'testing-environ,sys','production_source_changed':False}
    if inputs!=expected or result.get('source_revision')!=module.REV or result.get('archive_sha256')!=module.ARCHIVE or result.get('lock_sha256')!=module.LOCK or result.get('harness_sha256')!=module.TEST or result.get('features')!='testing-environ,sys' or result.get('acceptance_claim') is not False: raise ValueError('frozen measurement provenance mismatch')
    if digest(proofdir/'linux_process_performance.rs')!=module.TEST or digest(proofdir/'measurement-contract.md')!=module.CONTRACT: raise ValueError('copied source/contract differs from pinned bytes')
    if restored.get('restored_examples_match_recorded_bytes') is not True or restored.get('cargo_lock_sha256')!=module.LOCK: raise ValueError('source/lock restoration failed')
    if restored.get('restored_example_sha256')!={'tests/linux_process_performance.rs':module.TEST}: raise ValueError('restored harness receipt mismatch')
    versions=json.loads((proofdir/'tool-versions.json').read_text())
    rustc_stdout=(proofdir/'rustc-version.stdout').read_text();cargo_stdout=(proofdir/'cargo-version.stdout').read_text()
    if versions!={'toolchain':'1.77.2-x86_64-unknown-linux-gnu','rustc_stdout':rustc_stdout,'cargo_stdout':cargo_stdout} or not rustc_stdout.startswith('rustc 1.77.2 ') or 'host: x86_64-unknown-linux-gnu' not in rustc_stdout or not cargo_stdout.startswith('cargo 1.77.2 '): raise ValueError('private toolchain readback mismatch')
    commands=json.loads((proofdir/'commands.json').read_text())
    if commands!=result.get('commands') or {x.get('name') for x in commands} != {'rustup-install','rustc-version','cargo-version','control-pass','measurements'}: raise ValueError('command ledger is incomplete or differs from result')
    byname={x['name']:x for x in commands}
    runtime=Path(json.loads((proofdir/'early-runtime-identity.json').read_text())['runtime'])
    for name,row in byname.items():
        expected_cwd=runtime if name in ('rustup-install','rustc-version','cargo-version') else runtime/'source'
        if row.get('status')!=0 or row.get('expected_status')!=0 or row.get('cwd')!=str(expected_cwd) or row.get('env_overrides')!={}: raise ValueError('command result/cwd/environment mismatch '+name+' '+repr((row.get('cwd'),str(expected_cwd))))
    toolbin=runtime/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin'
    common=[str(toolbin/'cargo'),'test','--locked','--test','linux_process_performance','--features','testing-environ,sys']
    if byname['control-pass'].get('argv') != common+['measurement_controls_reject_corruption','--','--exact','--nocapture','--test-threads=1'] or byname['measurements'].get('argv') != common+['direct_managed_measurements','--','--exact','--ignored','--nocapture','--test-threads=1']: raise ValueError('test command argv differs from frozen finite recipe')
    if json.loads((proofdir/'control-results.json').read_text())!=result.get('controls'): raise ValueError('independent control-result ledger mismatch')
    rows=module.validate_measurement_rows((proofdir/'measurements.stdout').read_text()+'\n'+(proofdir/'measurements.stderr').read_text())
    module.validate_control_receipts((proofdir/'control-pass.stdout').read_text()+'\n'+(proofdir/'control-pass.stderr').read_text())
    if rows!=result.get('observed_row_counts') or result.get('controls') is None: raise ValueError('measurement/control result receipt mismatch')
    controls=result['controls']
    if [(x.get('name'),x.get('status'),x.get('expected_status')) for x in controls] != [('control-pass',0,0),('measurements',0,0)]: raise ValueError('control/measurement run receipts are incomplete')
    maxima=json.loads((proofdir/'sampled-maxima.json').read_text());samples=[json.loads(x) for x in (proofdir/'resource-samples.jsonl').read_text().splitlines()]
    if not samples or maxima.get('sample_count')!=len(samples) or maxima.get('samples_are_periodic_not_continuous_peak') is not True: raise ValueError('periodic sampler originals missing/mislabeled')
    for name,bound,strict in [('storage_kib',1572864,True),('rss_kib',2097152,True),('descendants',16,False)]:
        values=[x.get(name) for x in samples]
        if any(type(v) is not int or v<0 or (v>=bound if strict else v>bound) for v in values) or maxima.get('maxima',{}).get(name)!=max(values): raise ValueError('sample/maxima corruption or bound exceeded: '+name)
    times=[x.get('monotonic_seconds') for x in samples]
    if any(type(t) not in (float,int) for t in times) or times!=sorted(set(times)) or times[0]<0 or times[-1]>540: raise ValueError('periodic sample clock is malformed or outside helper budget')


def collect(destination: Path) -> None:
    tarpath=destination.with_name(destination.name+'.originals.tar')
    if not destination.parent.is_dir() or destination.parent.is_symlink(): raise FileNotFoundError('originals parent must already exist')
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()): raise FileExistsError('refusing unsafe originals destination')
    if tarpath.is_symlink() or (tarpath.exists() and not tarpath.is_file()): raise FileExistsError('refusing unsafe originals archive')
    destination.mkdir(mode=0o700,exist_ok=True)
    allowed={'stage-originals','independent-readback.json','export-manifest.json','admission-sources','admission-source-hashes.json','fresh-custody-readback.json','retirement-readback.json'}
    if any(item.name not in allowed or item.is_symlink() for item in destination.iterdir()):raise ValueError('unexpected or symlinked entry in resumable originals destination')
    guard_hash,wrapper_hash=digest(PREFLIGHT),digest(SLOT_WRAPPER)
    original=inventory()
    if not tarpath.exists():
        data=subprocess.check_output(['ssh','workhorse','tar','-C',STAGE,'-cf','-','.'],timeout=60)
        with tarpath.open('xb') as out:
            st=os.fstat(out.fileno())
            now=tarpath.lstat()
            if tarpath.is_symlink() or (now.st_dev,now.st_ino)!=(st.st_dev,st.st_ino): raise RuntimeError('exclusive archive path changed')
            out.write(data);out.flush();os.fsync(out.fileno())
    else:
        data=tarpath.read_bytes()
    if not data: raise ValueError('preserved originals archive is empty; refusing a second export')
    tree=destination/'stage-originals'
    if tree.is_symlink() or (tree.exists() and not tree.is_dir()): raise ValueError('unsafe partial originals tree')
    tree.mkdir(mode=0o700,exist_ok=True)
    with tarfile.open(tarpath,'r:') as tf:
        for member in tf.getmembers():
            p=PurePosixPath(member.name)
            parts=tuple(x for x in p.parts if x not in ('','.'))
            if p.is_absolute() or '..' in parts or member.issym() or member.islnk() or not(member.isfile() or member.isdir()): raise ValueError('unsafe archive member '+member.name)
            target=tree.joinpath(*parts)
            if not parts: continue
            if member.isdir():
                target.mkdir(mode=0o700,parents=True,exist_ok=True)
                if target.is_symlink() or not target.is_dir():raise ValueError('unsafe partial archive directory '+member.name)
            else:
                target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                if target.exists() or target.is_symlink():
                    if target.is_symlink() or not target.is_file() or target.read_bytes()!=tf.extractfile(member).read():raise ValueError('partial archive file conflicts '+member.name)
                else:
                    with target.open('xb') as out: shutil.copyfileobj(tf.extractfile(member),out)
    files={};dirs=[]
    for p in sorted(tree.rglob('*')):
        r=p.relative_to(tree).as_posix()
        if p.is_symlink():raise ValueError('local original symlink '+r)
        if p.is_dir():dirs.append(r)
        elif p.is_file():files[r]=digest(p)
        else:raise ValueError('unexpected local original object '+r)
    if files!=original['files'] or dirs!=original['directories']:raise ValueError('archive differs from independent byte inventory')
    def receipt(path: Path, value: dict) -> None:
        content=json.dumps(value,indent=2,sort_keys=True)+'\n'
        if path.is_symlink():raise ValueError('receipt symlink '+path.name)
        if path.exists():
            if path.read_text()!=content:raise ValueError('partial receipt conflicts '+path.name)
        else:
            with path.open('x',encoding='utf-8') as out:out.write(content);out.flush();os.fsync(out.fileno())
    receipt(destination/'independent-readback.json',original)
    receipt(destination/'export-manifest.json',{'stage':STAGE,'scope':SCOPE,'files':files,'directories':dirs,'archive_sha256':hashlib.sha256(data).hexdigest(),'admission_sources':{str(PREFLIGHT):guard_hash,str(SLOT_WRAPPER):wrapper_hash}})
    proofdir=tree/'proof-evidence';validate_local(proofdir,tree)
    allocation=json.loads((tree/'native-allocation.json').read_text())
    admission=allocation.get('preflight',{})
    if allocation.get('source_revision')!='8c0ee4634355aee4e841b455461a7dd5aac2aa18' or allocation.get('native_launch')!=1 or admission.get('ready') is not True or admission.get('inputs_verified')!=11 or admission.get('heavy')!=[]: raise RuntimeError('native allocation receipt is absent or failed guarded admission')
    if allocation.get('preflight_source_sha256')!=guard_hash or allocation.get('slot_wrapper_source_sha256')!=wrapper_hash: raise RuntimeError('current root admission sources differ from recorded guarded allocation')
    admission_dir=destination/'admission-sources';admission_dir.mkdir(mode=0o700,exist_ok=True)
    for source,target in ((PREFLIGHT,admission_dir/'preflight.py'),(SLOT_WRAPPER,admission_dir/'slot-wrapper.py')):
        if target.is_symlink():raise ValueError('admission copy symlink')
        if not target.exists():
            with source.open('rb') as inp,target.open('xb') as out: shutil.copyfileobj(inp,out);out.flush();os.fsync(out.fileno())
        if digest(target)!=digest(source):raise ValueError('partial admission copy differs from source')
    receipt(destination/'admission-source-hashes.json',{'preflight_sha256':guard_hash,'slot_wrapper_sha256':wrapper_hash})
    fresh=inventory()
    if fresh!=original:raise RuntimeError('stage changed during export')
    custody=ssh_json(PROCESS_CHECK,original)
    receipt(destination/'fresh-custody-readback.json',custody)
    latest=inventory()
    if latest!=original:raise RuntimeError('stage changed after custody')
    retired=ssh_json(RETIRE,latest)
    receipt(destination/'retirement-readback.json',retired)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('destination',type=Path,nargs='?',default=DEST);collect(ap.parse_args().destination)
