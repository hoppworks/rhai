#!/usr/bin/env python3
"""Preserve the unique first-cause run originals, validate every receipt, then retire exact stage."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, pathlib, shlex, subprocess, tarfile
from pathlib import Path, PurePosixPath
STAGE='/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4'
SCOPE='/root/.local/share/agent-builds/rhai/fc-20261007-ack05-7d11e2c4'
PHYSICAL='/var/roothome/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4'
ROOT=Path(__file__).resolve().parent
DEST=ROOT/'originals'
PREFLIGHT=ROOT/'linux-process-first-cause-preflight.py'
SLOT_WRAPPER=ROOT/'linux-process-first-cause-slot-wrapper.py'
MODES=('direct','managed')
KINDS=('baseline-red','overwrite-red','restored-green')
TESTS={
'direct':'packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_direct_child',
'managed':'packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_managed'}
CAUSE='the first committed stdout overflow must remain the public cause'
EXPECTED_MUTANT=None
EXPECTED_ARGV=['/usr/bin/python3','-c',"exec(open(__import__('os').environ['RHAI_FIRST_SCRIPT']).read())"]
EXPECTED_ARGV_JSON=json.dumps(EXPECTED_ARGV,separators=(',',':'))

def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def identity_matches(early:dict,row:dict)->bool:
 try:return tuple(int(early[k]) for k in ('pid','ppid','pgid','start_ticks'))+(early.get('cmdline'),)==tuple(int(row[k]) for k in ('pid','ppid','pgid','start_ticks'))+(row.get('cmdline'),)
 except (TypeError,ValueError,KeyError):return False
def fixture_receipt(raw:str,mode:str,case:str)->str:
 marker=f'first-cause mode={mode} '
 lines=[line for line in raw.splitlines() if marker in line]
 if len(lines)!=1 or sum(line.count(marker) for line in lines)!=1:raise ValueError('fixture receipt missing/duplicated '+case)
 if not lines[0].startswith(f'test {TESTS[mode]} ... {marker}'):raise ValueError('fixture receipt is attached to the wrong selected test '+case)
 return marker+lines[0].split(marker,1)[1]
def selected_test_status(stdout:str,mode:str,expected:str)->bool:
 prefix=f'test {TESTS[mode]} ... '
 lines=stdout.splitlines();matches=[(i,line[len(prefix):]) for i,line in enumerate(lines) if line.startswith(prefix)]
 if len(matches)!=1:return False
 index,suffix=matches[0]
 if suffix==expected:return True
 return suffix.startswith(f'first-cause mode={mode} ') and index+1<len(lines) and lines[index+1]==expected
def bind_fixture_row(row:dict, raw_output:str, expected_case:str)->None:
 if row.get('case')!=expected_case:raise ValueError('fixture case ordering mismatch')
 mode=expected_case.rsplit('-',1)[1]
 raw_line=fixture_receipt(raw_output,mode,expected_case)
 fields=dict(part.split('=',1) for part in raw_line.split()[1:])
 for col,key in (('pid','child_pid'),('start_ticks','child_start_ticks'),('pgid','child_pgid'),('identity_confirmed','identity_confirmed'),('identity_gate_released','identity_gate_released'),('identity_wait','identity_wait'),('stdout_write','stdout_write'),('stdout_committed','stdout_committed'),('stderr_write','stderr_write'),('stderr_overflow','stderr_overflow'),('reap','reap'),('group_closed','group_closed'),('observed_cmdline_hex','child_cmdline_hex')):
  if row.get(col)!=fields.get(key):raise ValueError('fixture ledger differs from raw command receipt '+expected_case+'/'+col)
 if row.get('expected_argv')!=EXPECTED_ARGV_JSON:raise ValueError('fixture expected-argv vector mismatch '+expected_case)
 expected_cmdline=b'\0'.join(value.encode() for value in EXPECTED_ARGV)+b'\0'
 try:observed=bytes.fromhex(row.get('observed_cmdline_hex',''))
 except ValueError as exc:raise ValueError('fixture observed argv is not hexadecimal '+expected_case) from exc
 if observed!=expected_cmdline:raise ValueError('fixture observed argv differs from exact expected vector '+expected_case)
 if fields.get('expected_program')!='/usr/bin/python3' or fields.get('expected_argv_count')!='3':raise ValueError('raw fixture expected program/argv count mismatch '+expected_case)
 for value in ('identity_confirmed=true','identity_gate_released=true','identity_wait=acknowledged','stdout_write=acknowledged','stdout_committed=true','stderr_write=acknowledged','stderr_overflow=observed','reap=ESRCH'):
  if value not in raw_line:raise ValueError('fixture raw receipt lacks readiness/closure '+expected_case)
def validate_resource_receipts(rows:list[dict],maxima:dict)->None:
 if not rows or maxima.get('sample_count')!=len(rows):raise ValueError('resource sample count mismatch')
 calculated={key:max(int(sample[key]) for sample in rows) for key in ('storage_kib','rss_kib','descendants')}
 if maxima.get('maxima')!=calculated or maxima.get('storage_preemptive_stop_kib')!=1572864 or maxima.get('storage_hard_stop_kib')!=2097152 or maxima.get('rss_hard_stop_kib')!=2097152 or maxima.get('descendant_hard_stop')!=16:raise ValueError('resource maxima/caps do not reconcile')
 if calculated['storage_kib']>=1572864 or calculated['rss_kib']>=2097152 or calculated['descendants']>16:raise ValueError('recorded resource sample reached a stop cap')
def validate_mutant_receipt(injected:dict)->None:
 raise RuntimeError('legacy overlap mutation receipts are forbidden in first-cause collection')

def validate_source_phases(phase_rows:list[dict], test_hash:str, patch_hash:str,
                           accepted_patch_hash:str, restored:bool)->None:
 names=['baseline','proposed-fix','stderr-overwrite-mutant','restored-fix',
        'pre-restoration','final-baseline-restored']
 if [row.get('phase') for row in phase_rows]!=names:raise ValueError('source phase order mismatch')
 hashes=[row.get('sha256') for row in phase_rows]
 if hashes[0]!=test_hash or hashes[1]==test_hash or hashes[2] in (hashes[0],hashes[1]) or hashes[3]!=hashes[1] or hashes[4]!=hashes[3] or hashes[5]!=test_hash or restored is not True:
  raise ValueError('baseline/fix/mutant/restoration source hashes do not reconcile')
 if accepted_patch_hash!=patch_hash:raise ValueError('accepted production patch hash mismatch')
def validate_command_inventory(commands:list[dict],runtime:Path)->None:
 expected=[f'{kind}-{mode}' for kind in KINDS for mode in MODES]
 if [c.get('name') for c in commands]!=['rustup-install','rustc-version','cargo-version']+expected:raise ValueError('exact ordered setup plus six controls inventory missing')
 if runtime.parent!=Path(SCOPE):raise ValueError('private runtime is not a direct child of named scope')
 bindir=str(runtime/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin')
 common={'HOME':str(runtime/'home'),'TMPDIR':str(runtime/'tmp'),'TMP':str(runtime/'tmp'),'TEMP':str(runtime/'tmp'),'CARGO_HOME':str(runtime/'cargo-home'),'RUSTUP_HOME':str(runtime/'rustup-home'),'CARGO_TARGET_DIR':str(runtime/'target'),'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_PROFILE_DEV_DEBUG':'0','CARGO_TERM_COLOR':'never','RUST_BACKTRACE':'0'}
 for index,command in enumerate(commands):
  setup=index<3;first=index==0
  expected_env={**common,'PATH':('/usr/bin:/bin:/usr/sbin:/sbin' if first else bindir+':/usr/bin:/bin:/usr/sbin:/sbin')}
  if not first:expected_env['RUSTC']=bindir+'/rustc'
  expected_cwd=str(runtime if setup else runtime/'source')
  if command.get('cwd')!=expected_cwd or command.get('env_overrides')!={} or command.get('effective_env')!=expected_env or command.get('spawned') is not True or not isinstance(command.get('status'),int) or command.get('status')!=command.get('expected_status'):
   raise ValueError('command cwd/effective-env/status/runtime receipt mismatch '+command['name'])
def validate_tool_versions(versions:dict,rustc_raw:str,cargo_raw:str)->None:
 if versions.get('toolchain')!='1.77.2-x86_64-unknown-linux-gnu' or versions.get('rustc_stdout')!=rustc_raw or versions.get('cargo_stdout')!=cargo_raw or not rustc_raw.startswith('rustc 1.77.2 ') or 'host: x86_64-unknown-linux-gnu' not in rustc_raw or not cargo_raw.startswith('cargo 1.77.2 '):raise ValueError('toolchain raw version/host receipt mismatch')
def remote(code:str,manifest:dict|None=None,request:dict|None=None)->dict:
 args=[STAGE,SCOPE,PHYSICAL]
 if manifest is not None:args.append(json.dumps(manifest,sort_keys=True))
 if request is not None:args.append(json.dumps(request,sort_keys=True))
 cmd='python3 -c '+shlex.quote(code)+' '+' '.join(shlex.quote(x) for x in args)
 return json.loads(subprocess.check_output(['ssh','workhorse',cmd],text=True,timeout=60))
INVENTORY=r'''import hashlib,json,pathlib,sys
s=pathlib.Path(sys.argv[1]);scope=pathlib.Path(sys.argv[2]);f={};d=[]
if not s.is_dir() or s.is_symlink():raise SystemExit('stage unavailable')
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink():raise SystemExit('stage symlink '+r)
 if p.is_dir():d.append(r)
 elif p.is_file():f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('unexpected stage object '+r)
print(json.dumps({'stage':str(s),'scope':str(scope),'files':f,'directories':d},sort_keys=True))'''

def validate(tree:Path, inventory:dict)->dict:
 freeze=json.loads((tree/'source-freeze.json').read_text())
 revision=freeze['source_revision'];archive_hash=freeze['files']['source.tar']
 test_hash=freeze['test_source_sha256'];lock_hash=freeze['files']['Cargo.lock.accepted']
 proof=tree/'proof-evidence';outer=tree/'outer-evidence'
 need={'package-result.json','source-inputs.json','source-restoration.json','commands.json','control-results.json','fixture-identities.tsv','process-identities.tsv','early-runtime-identity.json','tool-versions.json','sampled-maxima.json','resource-samples.jsonl','export-budget.json'}
 if not need.issubset({x.name for x in proof.iterdir()}):raise ValueError('first-cause originals incomplete')
 result=json.loads((proof/'package-result.json').read_text());inputs=json.loads((proof/'source-inputs.json').read_text());rest=json.loads((proof/'source-restoration.json').read_text())
 expected_pins={'source_revision':revision,'archive_sha256':archive_hash,'source_sha256':test_hash,'lock_sha256':lock_hash,'acceptance_claim':False,'source_restored':True,'package_status':'complete'}
 if any(result.get(k)!=v for k,v in expected_pins.items()):raise ValueError('source provenance/restoration result mismatch')
 if freeze.get('fixture_adapter_patch_sha256')!=digest(tree/'fixture-adapter.patch'):raise ValueError('test adapter patch provenance mismatch')
 with tarfile.open(tree/'source.tar','r:') as source_archive:
  source_members=[m for m in source_archive.getmembers() if m.name=='src/packages/sys/process/unix.rs']
  if len(source_members)!=1 or not source_members[0].isfile() or hashlib.sha256(source_archive.extractfile(source_members[0]).read()).hexdigest()!=test_hash:
   raise ValueError('frozen source hash does not match adapted archive bytes')
 if inputs.get('source_revision')!=revision or inputs.get('archive_sha256')!=archive_hash or inputs.get('source_sha256')!=test_hash or inputs.get('lock_sha256')!=lock_hash or inputs.get('selected_tests')!=TESTS:raise ValueError('input pins/test names mismatch')
 phase_rows=rest.get('phase_hashes',[])
 if json.loads((proof/'source-phase-hashes.json').read_text())!=phase_rows:raise ValueError('phase hash receipt differs from independent export')
 if rest.get('restored_baseline_matches') is not True:raise ValueError('source phase restoration receipt failed')
 validate_source_phases(phase_rows,test_hash,digest(tree/'preserve-primary-cause.patch'),
                        rest.get('accepted_patch_sha256'),rest.get('restored_baseline_matches'))
 if digest(tree/'source.tar')!=archive_hash or digest(tree/'Cargo.lock.accepted')!=lock_hash:raise ValueError('staged source archive or lock changed')
 # Guard and slot-wrapper are independently reviewed admission inputs, bound outside the circular package manifest.
 allocation=json.loads((tree/'native-allocation.json').read_text());staged=[]
 for line in (tree/'input-identities.sha256').read_text().splitlines():
  bits=line.split(None,1)
  if len(bits)!=2 or bits[1] in {n for n,_ in staged}:raise ValueError('malformed/duplicate staged input pin')
  staged.append((bits[1],bits[0]))
 pins=dict(staged);guard='linux-process-first-cause-preflight.py';wrapper='linux-process-first-cause-slot-wrapper.py'
 gh,wh=digest(tree/guard),digest(tree/wrapper)
 if digest(PREFLIGHT)!=gh or digest(SLOT_WRAPPER)!=wh:raise ValueError('staged admission bytes differ from locally reviewed sources')
 if allocation.get('source_revision')!=revision or allocation.get('native_launch')!=1 or allocation.get('preflight_source_sha256')!=gh or allocation.get('slot_wrapper_source_sha256')!=wh:raise ValueError('allocation provenance does not bind final root guard/wrapper')
 admission=allocation.get('preflight',{})
 if admission.get('ready') is not True or admission.get('heavy')!=[] or admission.get('scope_absent') is not True or admission.get('inputs_verified')!=len(staged):raise ValueError('admission receipt does not verify the full package pin set')
 # Verify every pinned local package input and the exact four per-mode native commands.
 manifest={}
 for line in (tree/'input-identities.sha256').read_text().splitlines():
  h,n=line.split(None,1)
  if n in manifest:raise ValueError('duplicate input manifest path')
  manifest[n]=h
 for n,h in manifest.items():
  path=tree/n
  if path.is_symlink() or not path.is_file() or digest(path)!=h:raise ValueError('staged input identity changed '+n)
 expected_inputs={'archive-build-source.py','source.tar','Cargo.lock.accepted','check-linux-current-msrv-examples.py','source-freeze.json','contract.md','linux-process-first-cause-proof.py','fixture-adapter.patch','preserve-primary-cause.patch','collect-first-cause-originals.py','linux-process-first-cause-fresh-closure.py','recipe-probes.py','launch.sh','runner/tools/run_scoped.py','runner/tools/agentskills/__init__.py','runner/tools/agentskills/pyguard.py'}
 if set(manifest)!=expected_inputs:raise ValueError('staged input pin set is incomplete or has unexpected files')
 if manifest.get('source.tar')!=archive_hash or manifest.get('Cargo.lock.accepted')!=lock_hash:raise ValueError('source/lock absent from guard pin set')
 commands=result.get('commands',[]);names=[c.get('name') for c in commands]
 if json.loads((proof/'commands.json').read_text())!=commands:raise ValueError('independent command ledger differs from package result')
 expected=[f'{k}-{m}' for k in KINDS for m in MODES]
 runtime=Path(json.loads((proof/'early-runtime-identity.json').read_text())['runtime'])
 validate_command_inventory(commands,runtime)
 versions=json.loads((proof/'tool-versions.json').read_text())
 validate_tool_versions(versions,(proof/'rustc-version.stdout').read_text(),(proof/'cargo-version.stdout').read_text())
 for command,stream,needle in ((commands[1],'rustc-version.stdout','host: x86_64-unknown-linux-gnu'),(commands[2],'cargo-version.stdout','cargo 1.77.2 ')):
  raw=(proof/stream).read_text()
  if needle not in raw or raw!=versions['rustc_stdout' if stream.startswith('rustc') else 'cargo_stdout']:raise ValueError('setup raw version output differs from tool-version receipt')
 cargo=str(runtime/'rustup-home/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/cargo')
 for c in commands[-6:]:
  mode=c['name'].rsplit('-',1)[1];kind='-'.join(c['name'].split('-')[:-1]);code=0 if kind=='restored-green' else 101
  argv=[cargo,'test','--locked','--lib','--features','testing-environ,sys',TESTS[mode],'--','--exact','--nocapture','--test-threads=1']
  if c.get('status')!=code or c.get('expected_status')!=code or c.get('argv')!=argv or c.get('cwd')!=str(runtime/'source') or c.get('spawned') is not True:raise ValueError('control status/exact argv/cwd mismatch '+c['name'])
  stdout=(proof/(c['name']+'.stdout')).read_text();stderr=(proof/(c['name']+'.stderr')).read_text()
  r=fixture_receipt(stdout+'\n'+stderr,mode,c['name'])
  for field in ('child_pid=','child_start_ticks=','child_pgid=','identity_confirmed=true','identity_gate_released=true','identity_wait=acknowledged','stdout_write=acknowledged','stdout_committed=true','stderr_write=acknowledged','stderr_overflow=observed','reap=ESRCH'):
   if field not in r:raise ValueError('fixture lacks '+field+' '+c['name'])
  expected_outcome='ok' if kind=='restored-green' else 'FAILED'
  if not selected_test_status(stdout,mode,expected_outcome):raise ValueError('selected test outcome absent '+c['name'])
  if kind!='restored-green' and (CAUSE not in stderr or f"thread '{TESTS[mode]}' panicked at src/packages/sys/process/unix.rs:" not in stderr):raise ValueError('control missed intended cause assertion '+c['name'])
  if kind=='restored-green' and ('stderr_overflow=observed' not in r or 'test result: ok. 1 passed; 0 failed;' not in stdout):raise ValueError('restored GREEN result absent '+c['name'])
 controls=json.loads((proof/'control-results.json').read_text())
 if controls!=result.get('controls'):raise ValueError('independent control ledger differs from package result')
 if [(x.get('name'),x.get('status'),x.get('expected_status')) for x in controls]!=[(n,101,101) for n in expected[:4]]+[(n,0,0) for n in expected[4:]]:raise ValueError('control-results ledger differs from four ordered commands')
 fixture_path=proof/'fixture-identities.tsv'
 if fixture_path.read_text().splitlines()[0]!='case\tpid\tstart_ticks\tpgid\texpected_argv\tobserved_cmdline_hex\tidentity_confirmed\tidentity_gate_released\tidentity_wait\tstdout_write\tstdout_committed\tstderr_write\tstderr_overflow\treap\tgroup_closed':raise ValueError('fixture ledger exact header mismatch')
 fixture=list(csv.DictReader(fixture_path.open(),delimiter='\t'))
 if [x['case'] for x in fixture]!=expected:raise ValueError('fixture identity order/inventory mismatch')
 identities=[];groups=set();seen=set()
 for path,header in ((proof/'process-identities.tsv','label\tpid\tppid\tpgid\tstart_ticks\tcmdline'),(outer/'launcher-identities.tsv','label\tpid\tppid\tpgid\tstart_ticks\tcmdline')):
  lines=path.read_text().splitlines()
  if not lines or lines[0]!=header:raise ValueError('identity ledger header mismatch '+path.name)
  for row in csv.DictReader(path.open(),delimiter='\t'):
   pid,start,pgid=int(row['pid']),int(row['start_ticks']),int(row['pgid'])
   if min(pid,start,pgid)<=0 or (pid,start) in seen:raise ValueError('invalid/duplicate supervised process identity')
   seen.add((pid,start));identities.append((pid,start));groups.add(pgid)
 fixture_by_case={row['case']:row for row in fixture}
 for name in expected:
  kind,mode=name.rsplit('-',1)[0],name.rsplit('-',1)[1];stdout=(proof/(name+'.stdout')).read_text();stderr=(proof/(name+'.stderr')).read_text()
  bind_fixture_row(fixture_by_case[name],stdout+'\n'+stderr,name)
 for row in fixture:
  pid,start,pgid=map(int,(row['pid'],row['start_ticks'],row['pgid']))
  if min(pid,start,pgid)<=0 or (pid,start) in seen:raise ValueError('invalid/duplicate child identity')
  seen.add((pid,start));identities.append((pid,start))
  if row['case'].endswith('-managed'):
   if pid!=pgid:raise ValueError('Managed fixture did not own its process group')
   groups.add(pgid)
 required={'helper','scoped-supervisor','command:rustup-install','command:rustc-version','command:cargo-version'}|{'command:'+n for n in expected}
 identity_lines=(proof/'process-identities.tsv').read_text().splitlines()
 labels=[r.split('\t',1)[0] for r in identity_lines[1:]]
 if not required.issubset(labels):raise ValueError('helper/command process identity group incomplete')
 by_label={}
 for row in csv.DictReader((proof/'process-identities.tsv').open(),delimiter='\t'):
  if not row['pid'].isdecimal() or not row['ppid'].isdecimal() or not row['pgid'].isdecimal() or not row['start_ticks'].isdecimal() or int(row['start_ticks'])<=0:raise ValueError('malformed owned command identity')
  by_label.setdefault(row['label'],[]).append(row)
 for command in commands:
  status_file=proof/(command['name']+'.status')
  if not status_file.is_file() or status_file.read_text().strip()!=str(command.get('status')):raise ValueError('independent command status file mismatch '+command['name'])
  rows=by_label.get('command:'+command['name'],[])
  if len(rows)!=1 or rows[0]['cmdline'] not in (' '.join(command['argv']), ''):raise ValueError('command identity/argv does not match result ledger '+command['name'])
 for label,argv in (('command:du','/usr/bin/du -sk '+str(Path(json.loads((proof/'early-runtime-identity.json').read_text())['runtime']))),('command:ps','/bin/ps -e -o pid=,ppid=,rss=')):
  observed=[row['cmdline'] for row in by_label.get(label,[]) if row['cmdline']]
  if not observed or any(value!=argv for value in observed):raise ValueError('sampler identity missing exact argv '+label)
 early=json.loads((proof/'early-runtime-identity.json').read_text())
 for label,key in (('helper','helper'),('scoped-supervisor','scoped_supervisor')):
  row=by_label[label][0];obj=early.get(key)
  if not isinstance(obj,dict) or not identity_matches(obj,row):raise ValueError('early and full process identity receipts disagree '+label)
 if int(by_label['helper'][0]['ppid'])!=int(by_label['scoped-supervisor'][0]['pid']):raise ValueError('helper/scoped supervisor ancestry is inconsistent')
 resource_rows=[json.loads(line) for line in (proof/'resource-samples.jsonl').read_text().splitlines() if line.strip()]
 maxima=json.loads((proof/'sampled-maxima.json').read_text())
 validate_resource_receipts(resource_rows,maxima)
 budget=json.loads((proof/'export-budget.json').read_text())
 elapsed_start=float(budget.get('elapsed_seconds_at_export_start',-1));elapsed_before_receipt=float(budget.get('elapsed_seconds_before_budget_receipt_copy',999))
 if budget.get('helper_deadline_seconds')!=540 or budget.get('helper_work_deadline_seconds')!=510 or budget.get('deadline_checked_at_entry_between_items_and_after') is not True or budget.get('individual_copy_operations_preemptible') is not False or budget.get('deadline_checked_immediately_before_and_after_budget_receipt_copy') is not True or elapsed_start<0 or elapsed_before_receipt<elapsed_start or elapsed_before_receipt>=540:raise ValueError('export budget receipt invalid')
 if (outer/'outer-status.txt').read_text().strip()!='0' or (outer/'run-scoped.status').read_text().strip()!='0':raise ValueError('outer/scoped execution status failed')
 return {'identities':sorted(identities),'groups':sorted(groups)}

CUSTODY=r'''import hashlib,json,pathlib,subprocess,sys
s=pathlib.Path(sys.argv[1]);scope=pathlib.Path(sys.argv[2]);physical=pathlib.Path(sys.argv[3]);m=json.loads(sys.argv[4]);r=json.loads(sys.argv[5])
if s not in (pathlib.Path('/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4'),physical) or physical!=pathlib.Path('/var/roothome/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4') or not s.is_dir() or s.is_symlink() or s.resolve()!=physical:raise SystemExit('stage identity mismatch')
if scope.exists() or scope.is_symlink():raise SystemExit('private scope remains')
f={};d=[]
for p in sorted(s.rglob('*')):
 q=p.relative_to(s).as_posix()
 if p.is_symlink():raise SystemExit('stage symlink '+q)
 if p.is_dir():d.append(q)
 elif p.is_file():f[q]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('unexpected stage object '+q)
if f!=m['files'] or d!=m['directories']:raise SystemExit('fresh stage differs from originals')
absent=[]
for pid,tick in r['identities']:
 p=pathlib.Path('/proc')/str(pid)/'stat'
 try:raw=p.read_text()
 except FileNotFoundError:absent.append([pid,tick,'absent']);continue
 z=raw.rfind(')');prefix=str(pid)+' ('
 if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ':raise SystemExit('malformed proc stat')
 x=raw[z+2:].split()
 if len(x)<20 or len(x[0])!=1 or x[0] not in 'RSDZTtXxKWPI' or not x[19].isdigit() or int(x[19])<=0:raise SystemExit('malformed proc start ticks')
 if int(x[19])==tick:raise SystemExit('exact supervised process remains '+str(pid))
 absent.append([pid,tick,'reused'])
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5);members=[]
for line in ps.splitlines():
 x=line.split()
 if len(x)!=2 or not all(v.isdecimal() for v in x):raise SystemExit('malformed fresh group census')
 if int(x[1]) in r['groups']:members.append([int(x[0]),int(x[1])])
if members:raise SystemExit('owned groups remain '+repr(members))
print(json.dumps({'scope_absent':True,'exact_identities':absent,'owned_groups_empty':r['groups'],'stage_inventory_unchanged':True},sort_keys=True))'''

RETIRE=r'''import hashlib,json,pathlib,shutil,subprocess,sys
s=pathlib.Path(sys.argv[1]);scope=pathlib.Path(sys.argv[2]);physical=pathlib.Path(sys.argv[3]);m=json.loads(sys.argv[4]);r=json.loads(sys.argv[5])
if s!=pathlib.Path('/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4') or physical!=pathlib.Path('/var/roothome/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4') or not s.is_dir() or s.is_symlink() or s.resolve()!=physical:raise SystemExit('exact stage retirement identity mismatch')
if scope.exists() or scope.is_symlink():raise SystemExit('private scope/runtime remains')
for pid,tick in r['identities']:
 p=pathlib.Path('/proc')/str(pid)/'stat'
 try:raw=p.read_text()
 except FileNotFoundError:continue
 z=raw.rfind(')');prefix=str(pid)+' ('
 if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ':raise SystemExit('malformed proc stat framing')
 f=raw[z+2:].split()
 if len(f)<20 or not f[19].isdigit() or int(f[19])<=0:raise SystemExit('malformed proc start ticks')
 if int(f[19])==tick:raise SystemExit('exact supervised process remains '+str(pid))
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5);members=[]
for line in ps.splitlines():
 f=line.split()
 if len(f)!=2 or not all(x.isdecimal() for x in f):raise SystemExit('malformed retirement process census')
 if int(f[1]) in r['groups']:members.append([int(f[0]),int(f[1])])
if members:raise SystemExit('owned groups remain '+repr(members))
files={};dirs=[]
for p in sorted(s.rglob('*')):
 rel=p.relative_to(s).as_posix()
 if p.is_symlink():raise SystemExit('stage symlink '+rel)
 if p.is_dir():dirs.append(rel)
 elif p.is_file():files[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('unexpected stage object '+rel)
if files!=m['files'] or dirs!=m['directories']:raise SystemExit('stage changed before retirement')
shutil.rmtree(s)
if s.exists() or s.is_symlink() or scope.exists() or scope.is_symlink():raise SystemExit('fresh stage/scope absence failed after retirement')
print(json.dumps({'exact_stage_removed':True,'scope_absent':True,'owned_groups_empty':r['groups'],'exact_identities_checked':len(r['identities'])},sort_keys=True))'''

def collect(destination:Path)->None:
 tarpath=destination.with_name(destination.name+'.originals.tar')
 if not destination.parent.is_dir() or destination.parent.is_symlink():raise ValueError('unsafe originals parent')
 if destination.is_symlink() or tarpath.is_symlink():raise ValueError('unsafe originals target')
 destination.mkdir(mode=0o700,exist_ok=True)
 allowed={'stage-originals','independent-readback.json','export-manifest.json','custody-readback.json','retirement-readback.json','admission-sources','admission-source-hashes.json'}
 if any(x.name not in allowed or x.is_symlink() for x in destination.iterdir()):raise ValueError('unexpected partial originals entries')
 original=remote(INVENTORY)
 if not tarpath.exists():
  data=subprocess.check_output(['ssh','workhorse','tar','-C',STAGE,'-cf','-','.'],timeout=60)
  with tarpath.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 else:data=tarpath.read_bytes()
 if not data:raise ValueError('sole originals archive empty')
 tree=destination/'stage-originals';tree.mkdir(mode=0o700,exist_ok=True)
 with tarfile.open(tarpath,'r:') as tf:
  for m in tf.getmembers():
   p=PurePosixPath(m.name);parts=tuple(x for x in p.parts if x not in ('','.'))
   if p.is_absolute() or '..' in parts or m.issym() or m.islnk() or not(m.isfile() or m.isdir()):raise ValueError('unsafe archive entry '+m.name)
   if not parts:continue
   target=tree.joinpath(*parts)
   if m.isdir():target.mkdir(mode=0o700,parents=True,exist_ok=True)
   else:
    target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);payload=tf.extractfile(m).read()
    if target.exists():
     if target.is_symlink() or target.read_bytes()!=payload:raise ValueError('conflicting partial original '+m.name)
    else:target.write_bytes(payload)
 files={};dirs=[]
 for p in sorted(tree.rglob('*')):
  n=p.relative_to(tree).as_posix()
  if p.is_symlink():raise ValueError('original symlink '+n)
  if p.is_dir():dirs.append(n)
  elif p.is_file():files[n]=digest(p)
 if files!=original['files'] or dirs!=original['directories']:raise ValueError('preserved archive differs from independent live inventory')
 def receipt(name,value):
  target=destination/name;content=json.dumps(value,indent=2,sort_keys=True)+'\n'
  if target.exists():
   if target.read_text()!=content:raise ValueError('conflicting receipt '+name)
  else:
   with target.open('x') as f:f.write(content);f.flush();os.fsync(f.fileno())
 receipt('independent-readback.json',original);receipt('export-manifest.json',{'stage':STAGE,'scope':SCOPE,'files':files,'directories':dirs,'archive_sha256':hashlib.sha256(data).hexdigest()})
 custody_request=validate(tree,original)
 admission=destination/'admission-sources';admission.mkdir(mode=0o700,exist_ok=True)
 for src,name in ((PREFLIGHT,'preflight.py'),(SLOT_WRAPPER,'slot-wrapper.py')):
  target=admission/name
  if target.exists() and digest(target)!=digest(src):raise ValueError('admission source partial copy conflict')
  if not target.exists():target.write_bytes(src.read_bytes())
 receipt('admission-source-hashes.json',{'preflight_sha256':digest(PREFLIGHT),'slot_wrapper_sha256':digest(SLOT_WRAPPER)})
 if remote(INVENTORY)!=original:raise ValueError('stage changed during collection')
 custody=remote(CUSTODY,original,custody_request);receipt('custody-readback.json',custody)
 fixture=list(csv.DictReader((tree/'proof-evidence/fixture-identities.tsv').open(),delimiter='\t'))
 prows=list(csv.DictReader((tree/'proof-evidence/process-identities.tsv').open(),delimiter='\t'))
 lrows=list(csv.DictReader((tree/'outer-evidence/launcher-identities.tsv').open(),delimiter='\t'))
 identities=sorted({(int(x['pid']),int(x['start_ticks'])) for x in prows+lrows+fixture})
 groups=sorted({int(x['pgid']) for x in prows+lrows}|{int(x['pgid']) for x in fixture if x['case'].endswith('-managed')})
 retired=remote(RETIRE,original,{'identities':identities,'groups':groups})
 receipt('retirement-readback.json',retired)
 if retired.get('exact_stage_removed') is not True or retired.get('scope_absent') is not True:raise ValueError('exact retirement receipt incomplete')
 print('first-cause originals preserved, validated and exact stage retired')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('destination',type=Path,nargs='?',default=DEST);collect(p.parse_args().destination)
