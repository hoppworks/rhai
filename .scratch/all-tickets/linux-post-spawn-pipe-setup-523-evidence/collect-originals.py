#!/usr/bin/env python3
"""Export a pipe-setup proof stage unchanged, then validate fresh custody without retiring it."""
from __future__ import annotations
import argparse,hashlib,json,os,shlex,subprocess,tarfile
from pathlib import Path,PurePosixPath
STAGE='/root/rhai-linux-post-spawn-pipe-setup-523-20261004'
SCOPE='/root/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004'
PHYSICAL='/var/roothome/rhai-linux-post-spawn-pipe-setup-523-20261004'
DEST=Path(__file__).resolve().parent/'originals'
ARCHIVE='998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b'
LOCK='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TEST='1b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a'
TEST_NAME='packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child'
INNER='setup-failure child_pid='
OUTER='setup-failure fixture child_pid='
CAUSE='primary cause must remain configure-pipe Io'
REPORT='setup failure must not fabricate EOF or timeout completion'

INVENTORY=r'''import hashlib,json,pathlib,sys
s=pathlib.Path(sys.argv[1])
if not s.is_dir() or s.is_symlink(): raise SystemExit('stage unavailable for exact readback')
f={};d=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink(): raise SystemExit('stage symlink '+r)
 if p.is_dir(): d.append(r)
 elif p.is_file(): f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit('unexpected stage entry '+r)
print(json.dumps({'stage':str(s),'scope':sys.argv[2],'files':f,'directories':d},sort_keys=True))'''

CUSTODY=r'''import hashlib,json,math,pathlib,re,shlex,subprocess,sys
m=json.loads(sys.argv[4]);s=pathlib.Path(sys.argv[1]);scope=pathlib.Path(sys.argv[2]);physical=pathlib.Path(sys.argv[3])
stages={pathlib.Path('/root/rhai-linux-post-spawn-pipe-setup-523-20261004'),pathlib.Path('/var/roothome/rhai-linux-post-spawn-pipe-setup-523-20261004')}
scopes={pathlib.Path('/root/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004'),pathlib.Path('/var/roothome/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004')}
if s not in stages or physical!=pathlib.Path('/var/roothome/rhai-linux-post-spawn-pipe-setup-523-20261004') or scope not in scopes or not s.is_dir() or s.is_symlink() or s.resolve()!=physical: raise SystemExit('exact stage identity mismatch')
if scope.exists() or scope.is_symlink(): raise SystemExit('private scope/runtime remains')
files={};dirs=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink(): raise SystemExit('stage symlink '+r)
 if p.is_dir():dirs.append(r)
 elif p.is_file():files[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('unexpected stage object '+r)
if files!=m.get('files') or dirs!=m.get('directories'):raise SystemExit('fresh stage inventory differs from independent original readback')
expected={'source.tar':'998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b','Cargo.lock.accepted':'2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425','check-linux-current-msrv-examples.py':'c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9','archive-build-source.py':'a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b','contract.md':'ff4c5ed27bbdb55ef2ad66c28cddc31a1e624726cb7ec3f98078bc49cfc81b9d','linux-post-spawn-pipe-setup-proof.py':'236b6d8279274ca6b8d21174469ec632aad298df36191bd85ee49c15510a2a83','launch.sh':'9f67bf3211d609f88684de4f3b2af8de36f3a9f6fdb73124c2011be26f409b3e','runner/tools/run_scoped.py':'9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d','runner/tools/agentskills/__init__.py':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855','runner/tools/agentskills/pyguard.py':'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f'}
for n,h in expected.items():
 if files.get(n)!=h:raise SystemExit('frozen input mismatch '+n)
manifest={}
for line in (s/'input-identities.sha256').read_text().splitlines():
 f=line.split(None,1)
 if len(f)!=2 or f[1] in manifest:raise SystemExit('malformed staged input identity manifest')
 manifest[f[1]]=f[0]
if manifest!=expected:raise SystemExit('staged input identity manifest differs from exact package pins')
proof=s/'proof-evidence';outer=s/'outer-evidence'
required={'package-result.json','source-restoration.json','source-inputs.json','tool-versions.json','commands.json','control-results.json','early-runtime-identity.json','process-identities.tsv','sampled-maxima.json','resource-samples.jsonl'}
if not required.issubset({x.name for x in proof.iterdir()}):raise SystemExit('required proof emitter outputs missing')
result=json.loads((proof/'package-result.json').read_text());rest=json.loads((proof/'source-restoration.json').read_text());inputs=json.loads((proof/'source-inputs.json').read_text())
if result.get('source_revision')!='523608648dcae99bc0f6b46eaf2bb91fa4ecc752' or result.get('source_archive_sha256')!='998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b' or result.get('test_source_sha256')!='1b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a' or result.get('compatible_lock_sha256')!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425' or result.get('acceptance_claim') is not False:raise SystemExit('package frozen provenance mismatch')
if rest.get('restored_examples_match_original_bytes') is not True or rest.get('original_example_sha256')!={'src/packages/sys/process/unix.rs':'1b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a'} or rest.get('cargo_lock_sha256_after_execution')!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425':raise SystemExit('exact baseline source/lock restoration failed')
if rest.get('injected_example_sha256')!={'wrong-cause-red':'7a60d0b4ee7b032e3f5288f493797123989c8004f48f8533c82acb7b79532410','wrong-incomplete-report-red':'2687de283e5dbc5e689421af7ca6501479a27a15048b51c73d4e34bcc838bbba'}:raise SystemExit('source overlays differ from the two reviewed single-expression controls')
if inputs.get('revision')!=result['source_revision'] or inputs.get('archive_sha256')!=result['source_archive_sha256'] or inputs.get('test_source_sha256')!=result['test_source_sha256'] or inputs.get('cargo_lock_sha256')!=result['compatible_lock_sha256'] or inputs.get('test_name')!='packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child':raise SystemExit('emitted source input binding mismatch')
expected_controls=[('wrong-cause-red',101,101),('wrong-incomplete-report-red',101,101),('restored-green',0,0)]
controls=result.get('controls',[])
if [(x.get('name'),x.get('status'),x.get('expected_status')) for x in controls]!=expected_controls:raise SystemExit('three test invocation results are incomplete or misordered')
commands={x.get('name'):x for x in result.get('commands',[]) if isinstance(x,dict)}
if not set(n for n,_,_ in expected_controls).issubset(commands):raise SystemExit('Cargo command record missing')
if any(commands[n].get('status')!=st or commands[n].get('expected_status')!=st for n,st,_ in expected_controls):raise SystemExit('Cargo status does not match proof result')
expected_argv=['test','--locked','--lib','--features','testing-environ,sys','packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child','--','--exact','--nocapture','--test-threads=1']
for label in ('wrong-cause-red','wrong-incomplete-report-red','restored-green'):
 if commands[label].get('argv',[])[1:]!=expected_argv or not commands[label].get('argv',[None])[0].startswith(str(pathlib.Path(json.loads((proof/'early-runtime-identity.json').read_text())['runtime']))):raise SystemExit('Cargo invocation differs from the exact public test contract '+label)
 if (proof/(label+'.status')).read_text().strip()!=str(commands[label]['status']):raise SystemExit('individual command status file mismatch '+label)
# Require both child-reaping receipts and the exact intended panic for each control.
for label,diagnostic in (('wrong-cause-red','primary cause must remain configure-pipe Io'),('wrong-incomplete-report-red','setup failure must not fabricate EOF or timeout completion'),('restored-green',None)):
 out=(proof/(label+'.stdout')).read_text();err=(proof/(label+'.stderr')).read_text(); lines=out.splitlines()
 inner=[i for i,x in enumerate(lines) if x.startswith('setup-failure child_pid=') and 'reap=ESRCH owner_retired=true' in x]
 outer_receipts=[i for i,x in enumerate(lines) if x.startswith('setup-failure fixture child_pid=') and 'reap=ESRCH' in x]
 if len(inner)!=1 or len(outer_receipts)!=1 or inner[0]>=outer_receipts[0]:raise SystemExit('ordered post-reap receipts missing '+label)
 if diagnostic and (diagnostic not in err or 'nested setup-failure test failed' not in err or "thread 'packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child' panicked at src/packages/sys/process/unix.rs:" not in err):raise SystemExit('control failed outside intended inner assertion/outer reap wrapper '+label)
 if not diagnostic and ('test result: ok. 1 passed; 0 failed;' not in out or 'test packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child ... ok' not in out):raise SystemExit('restored GREEN lacks named public test result')
# The sample schema is exact and bounded; reject missing/unknown records.
rows=[json.loads(x) for x in (proof/'resource-samples.jsonl').read_text().splitlines() if x]
if not rows:raise SystemExit('no periodic resource samples')
previous=-1.0
for row in rows:
 if set(row)!={'monotonic_seconds','storage_kib','rss_kib','descendants'}:raise SystemExit('resource sample schema mismatch')
 t=row['monotonic_seconds']
 if type(t) not in (int,float) or not math.isfinite(t) or t<=previous or t>540:raise SystemExit('resource sample clock invalid')
 if any(type(row[k]) is not int or row[k]<0 for k in ('storage_kib','rss_kib','descendants')):raise SystemExit('resource counters invalid')
 if row['storage_kib']>=1572864 or row['rss_kib']>=2097152 or row['descendants']>16:raise SystemExit('resource sample exceeded declared bound')
 previous=t
for name in ('outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status'):
 if (outer/name).read_text().strip()!='0':raise SystemExit('outer custody status failed '+name)
for name in ('runtime-cleanup.tsv','scope-cleanup.tsv'):
 if 'cleanup_status=0' not in (outer/name).read_text():raise SystemExit('outer cleanup status failed '+name)
# Unknown proc is a refusal; exact PID/start matches and any owned-group member are failures.
def alive(pid,start):
 try:
  raw=pathlib.Path('/proc',str(pid),'stat').read_text(encoding='ascii');z=raw.rfind(')');prefix=str(pid)+' ('
  if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ':raise ValueError('malformed stat framing')
  f=raw[z+2:].split()
  if len(f)<20 or len(f[0])!=1 or f[0] not in 'RSDZTtXxKWPI' or not f[19].isdigit() or int(f[19])<=0:raise ValueError('malformed stat fields')
  return int(f[19])==start
 except (FileNotFoundError,ProcessLookupError):return False
 except (PermissionError,OSError,IndexError,ValueError) as e:raise SystemExit('process identity unknown '+str(pid)+': '+str(e))
early=json.loads((proof/'early-runtime-identity.json').read_text())
runtime=pathlib.Path(early.get('runtime',''))
if not runtime.is_absolute() or runtime.parent not in scopes or not runtime.name.startswith('agent-build-') or runtime.name=='agent-build-' or runtime.is_symlink() or runtime.exists():raise SystemExit('runtime is not one absent direct child of the prescribed scope')
export_record=json.loads((proof/'export.json').read_text())
if export_record.get('runtime')!=str(runtime) or export_record.get('destination')!=str(proof):raise SystemExit('runtime/export destination provenance mismatch')
if early.get('identity_errors')!={} or early.get('captured_before_stage_validation_or_external_command') is not True:raise SystemExit('early runtime identity is incomplete or late')
identfile=proof/'process-identities.tsv';rows=identfile.read_text().splitlines()
if not rows or rows[0]!='label\tpid\tppid\tpgid\tstart_ticks\tcmdline':raise SystemExit('process identity header mismatch')
seen={};sampled={};groups=set();all_ids=set()
for line in rows[1:]:
 f=line.split('\t',5)
 if len(f)!=6 or not f[1].isdigit() or not f[2].isdigit() or not f[3].isdigit() or not f[4].isdigit():raise SystemExit('malformed process identity row '+repr(line))
 label,pid,ppid,pgid,start,cmd=f;pid=int(pid);ppid=int(ppid);pgid=int(pgid);start=int(start)
 if pid<=0 or pgid<=0 or start<=0:raise SystemExit('invalid process identity row')
 key=(pid,start)
 if key in all_ids:raise SystemExit('duplicate exact process identity row '+repr(key))
 all_ids.add(key)
 if alive(pid,start):raise SystemExit('exact owned process remains '+label)
 row={'pid':pid,'ppid':ppid,'pgid':pgid,'start':start,'cmd':cmd}
 if label in ('command:du','command:ps'):
  sampled.setdefault(label,[]).append(row)
 elif label in seen:raise SystemExit('duplicate singleton process identity label '+label)
 else:seen[label]=row
 groups.add(pgid)
required={'helper','scoped-supervisor','command:rustup-install','command:rustc-version','command:cargo-version','command:wrong-cause-red','command:wrong-incomplete-report-red','command:restored-green'}
if not required.issubset(seen):raise SystemExit('required process identities missing '+repr(required-set(seen)))
if set(seen)-required:raise SystemExit('unknown singleton process identity labels '+repr(set(seen)-required))
if set(sampled)-{'command:du','command:ps'}:raise SystemExit('unknown repeated sampler identity label')
if not sampled.get('command:du') or not sampled.get('command:ps'):raise SystemExit('resource sampler process identities missing')
if seen['helper']['ppid']!=seen['scoped-supervisor']['pid']:raise SystemExit('helper/supervisor parent mismatch')
if any(v['ppid']!=seen['helper']['pid'] for k,v in seen.items() if k.startswith('command:')):raise SystemExit('command parent identity mismatch')
def early_match(label,obj):
 if not isinstance(obj,dict) or set(obj)!={'pid','ppid','pgid','start_ticks','cmdline'}:raise SystemExit('early '+label+' object malformed')
 row=seen[label]
 if (obj['pid'],obj['ppid'],obj['pgid'],str(obj['start_ticks']),obj['cmdline'])!=(row['pid'],row['ppid'],row['pgid'],str(row['start']),row['cmd']):raise SystemExit('early '+label+' identity differs from full sampled row')
early_match('helper',early.get('helper'));early_match('scoped-supervisor',early.get('scoped_supervisor'))
def python_argv(words):return len(words)>0 and pathlib.Path(words[0]).name=='python3'
helper_words=shlex.split(seen['helper']['cmd'])
if not python_argv(helper_words) or helper_words[1:]!=[str(s/'linux-post-spawn-pipe-setup-proof.py')]:raise SystemExit('helper executable/argv is not owned by exact staged proof')
supervisor_words=shlex.split(seen['scoped-supervisor']['cmd'])
if not python_argv(supervisor_words) or len(supervisor_words)!=6 or supervisor_words[1:]!=[str(physical/'runner/tools/run_scoped.py'),'_supervise',supervisor_words[3],'python3',str(s/'linux-post-spawn-pipe-setup-proof.py')] or not supervisor_words[3].isdigit():raise SystemExit('scoped-supervisor executable/argv is not owned by exact resolved runner and staged helper')
if any(x['cmd']!=f'/usr/bin/du -sk {runtime}' for x in sampled['command:du']):raise SystemExit('du sampler argv/runtime ownership mismatch')
if any(x['cmd']!='/bin/ps -e -o pid=,ppid=,rss=' for x in sampled['command:ps']):raise SystemExit('ps sampler argv mismatch')
if any(x['ppid']!=seen['helper']['pid'] for instances in sampled.values() for x in instances):raise SystemExit('sampler parent identity mismatch')
commands_by_name={x.get('name'):x for x in result.get('commands',[]) if isinstance(x,dict)}
if set(commands_by_name)!={'rustup-install','rustc-version','cargo-version','wrong-cause-red','wrong-incomplete-report-red','restored-green'}:raise SystemExit('command records do not contain exact bounded run set')
for name,row in commands_by_name.items():
 argv=row.get('argv');pidrow=seen.get('command:'+name)
 if not isinstance(argv,list) or not argv or not pidrow or shlex.split(pidrow['cmd'])!=argv:raise SystemExit('command argv does not match its exact recorded process identity '+str(name))
 expected_cwd=runtime if name in ('rustup-install','rustc-version','cargo-version') else runtime/'source'
 if row.get('cwd')!=str(expected_cwd) or row.get('env_overrides')!={}:raise SystemExit('command cwd/environment escapes private source/runtime '+str(name))
expected_runtime_bin=runtime/'rustup-home'/'toolchains'/'1.77.2-x86_64-unknown-linux-gnu'/'bin'
expected_commands={
 'rustup-install':['/root/.cargo/bin/rustup','toolchain','install','1.77.2-x86_64-unknown-linux-gnu','--profile','minimal','--no-self-update'],
 'rustc-version':[str(expected_runtime_bin/'rustc'),'--version','--verbose'],
 'cargo-version':[str(expected_runtime_bin/'cargo'),'--version','--verbose'],
 'wrong-cause-red':[str(expected_runtime_bin/'cargo'),'test','--locked','--lib','--features','testing-environ,sys','packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child','--','--exact','--nocapture','--test-threads=1'],
 'wrong-incomplete-report-red':[str(expected_runtime_bin/'cargo'),'test','--locked','--lib','--features','testing-environ,sys','packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child','--','--exact','--nocapture','--test-threads=1'],
 'restored-green':[str(expected_runtime_bin/'cargo'),'test','--locked','--lib','--features','testing-environ,sys','packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child','--','--exact','--nocapture','--test-threads=1']}
if any(commands_by_name[n].get('argv')!=argv for n,argv in expected_commands.items()):raise SystemExit('one or more command argv differ from the exact approved package invocation')
launch=outer/'launcher-identities.tsv';lrows=launch.read_text().splitlines()
if not lrows or lrows[0]!='label\tpid\tppid\tpgid\tstart_ticks\tcmdline':raise SystemExit('launcher identity header mismatch')
launchers={}
for line in lrows[1:]:
 f=line.split('\t',5)
 if len(f)!=6 or not f[1].isdigit() or not f[2].isdigit() or not f[3].isdigit() or not f[4].isdigit():raise SystemExit('malformed launcher identity')
 label,pid,ppid,pgid,start,cmd=f;pid=int(pid);ppid=int(ppid);pgid=int(pgid);start=int(start)
 if label in launchers or alive(pid,start):raise SystemExit('launcher identity duplicate or still live')
 launchers[label]={'pid':pid,'ppid':ppid,'pgid':pgid,'start':start,'cmd':cmd};groups.add(pgid)
if set(launchers)!={'launcher','run-scoped'} or seen['scoped-supervisor']['ppid']!=launchers['run-scoped']['pid'] or launchers['run-scoped']['ppid']!=launchers['launcher']['pid']:raise SystemExit('launcher/helper ancestry mismatch')
if launchers['launcher']['cmd']!=str(s/'launch.sh'):raise SystemExit('launcher argv does not name exact staged launcher')
run_words=shlex.split(launchers['run-scoped']['cmd'])
if not python_argv(run_words) or len(run_words)!=7 or run_words[1]!=str(s/'runner/tools/run_scoped.py') or run_words[2]!='--timeout' or not run_words[3].isdigit() or not 0<int(run_words[3])<=585 or run_words[4:]!=['--','python3',str(s/'linux-post-spawn-pipe-setup-proof.py')]:raise SystemExit('run-scoped argv is not exact staged runner/helper command')
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5);live=[]
for line in ps.splitlines():
 f=line.split()
 if len(f)!=2 or not all(x.isdecimal() for x in f):raise SystemExit('malformed process group census')
 if int(f[1]) in groups:live.append([int(f[0]),int(f[1])])
if not groups or live:raise SystemExit('owned process groups remain or group set is empty '+repr(live))
print(json.dumps({'stage_inventory_exact':True,'scope_absent':True,'process_identities_absent_or_reused':len(all_ids)+len(launchers),'sampler_instances_validated':sum(map(len,sampled.values())),'owned_groups_empty':True,'cargo_rows_validated':3,'post_reap_controls_validated':2,'restored_green_validated':True},sort_keys=True))'''

RETIRE=CUSTODY.rsplit('\nprint(json.dumps',1)[0] + r'''
import shutil
final_files={};final_dirs=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink():raise SystemExit('final retirement inventory found symlink '+r)
 if p.is_dir():final_dirs.append(r)
 elif p.is_file():final_files[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('final retirement inventory found unexpected object '+r)
if final_files!=m.get('files') or final_dirs!=m.get('directories'):raise SystemExit('final retirement inventory differs from exported original readback')
if s.is_symlink() or not s.is_dir() or s.resolve()!=physical or scope.exists() or scope.is_symlink():raise SystemExit('final retirement path/scope identity changed')
shutil.rmtree(s)
if s.exists() or s.is_symlink() or scope.exists() or scope.is_symlink(): raise SystemExit('exact stage/scope absence readback failed')
print(json.dumps({'exact_stage_removed':True,'scope_absent':True},sort_keys=True))'''


def ssh_json(code: str,payload: dict|None=None) -> dict:
    args=[STAGE,SCOPE,PHYSICAL]
    if payload is not None:args.append(json.dumps(payload,sort_keys=True))
    command='python3 -c '+shlex.quote(code)+' '+' '.join(shlex.quote(x) for x in args)
    out=subprocess.check_output(['ssh','workhorse',command],text=True,timeout=30)
    return json.loads(out)

def inventory() -> dict:return ssh_json(INVENTORY)

def collect(destination: Path) -> None:
    tar_path=destination.with_name(destination.name+'.originals.tar')
    if destination.exists() or destination.is_symlink():raise FileExistsError('preserve existing export '+str(destination))
    if tar_path.exists() or tar_path.is_symlink():raise FileExistsError('preserve existing original tar '+str(tar_path))
    if not destination.parent.is_dir() or destination.parent.is_symlink():raise FileNotFoundError('export parent must be an existing real directory '+str(destination.parent))
    # Reserve the sole tar exclusively before any remote inventory/transport.
    with tar_path.open('xb') as reserved_tar:
        reserved_stat=os.fstat(reserved_tar.fileno())
        readback=inventory()
        remote_tar=subprocess.check_output(['ssh','workhorse','tar','-C',STAGE,'-cf','-','.'],timeout=60)
        try:current_tar=tar_path.lstat()
        except FileNotFoundError:raise RuntimeError('exclusive original tar path disappeared during transport')
        if tar_path.is_symlink() or not tar_path.is_file() or (current_tar.st_dev,current_tar.st_ino)!=(reserved_stat.st_dev,reserved_stat.st_ino):raise RuntimeError('exclusive original tar path was replaced during transport')
        reserved_tar.write(remote_tar);reserved_tar.flush();os.fsync(reserved_tar.fileno())
    digest=hashlib.sha256(remote_tar).hexdigest();tree=destination/'stage-originals';tree.mkdir(parents=True)
    with tarfile.open(tar_path,'r:') as tf:
        for m in tf.getmembers():
            p=PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or m.issym() or m.islnk() or not (m.isfile() or m.isdir()):raise RuntimeError('unsafe original archive member '+m.name)
        tf.extractall(tree,filter='data')
    files={};dirs=[]
    for p in sorted(tree.rglob('*')):
        rel=p.relative_to(tree).as_posix()
        if p.is_symlink():raise RuntimeError('local original symlink '+rel)
        if p.is_dir():dirs.append(rel)
        elif p.is_file():files[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
        else:raise RuntimeError('unexpected local original object '+rel)
    if files!=readback['files'] or dirs!=readback['directories']:raise RuntimeError('archive does not match independent byte inventory')
    (destination/'independent-readback.json').write_text(json.dumps(readback,indent=2,sort_keys=True)+'\n')
    (destination/'export-manifest.json').write_text(json.dumps({'stage':STAGE,'scope':SCOPE,'files':files,'directories':dirs,'readback_sha256':hashlib.sha256(json.dumps(readback,sort_keys=True).encode()).hexdigest(),'archive_path':str(tar_path),'archive_sha256':digest},indent=2,sort_keys=True)+'\n')
    fresh=ssh_json(INVENTORY)
    if fresh!=readback:raise RuntimeError('fresh stage inventory changed during export; preserve originals')
    receipt=ssh_json(CUSTODY,readback)
    (destination/'fresh-custody-readback.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    # Persist all original bytes and custody evidence before the exact retirement.
    latest=inventory()
    if latest!=readback:raise RuntimeError('stage changed after custody; preserve originals')
    retired=ssh_json(RETIRE,latest)
    (destination/'retirement-readback.json').write_text(json.dumps(retired,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('destination',type=Path,nargs='?',default=DEST);args=ap.parse_args();collect(args.destination)
