#!/usr/bin/env python3
"""Bounded Rust 1.77.2 Linux managed Child.kill proof."""
from __future__ import annotations
import hashlib, importlib.util, json, os, platform, re, shutil, signal, stat, subprocess, sys, time, traceback
from pathlib import Path

REV = 'c69524f15666d66b7dc3fa8d4750e84ddc946535'
ARCHIVE = 'e16cd6482d1e3e1ff4b9056e3198b6ad6e8733657c66c87fd2e59fc35e023fe8'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
BASE_SHA = '59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06'
TEST_SHA = 'a29511c1b9c61b51f68022527e4fe2a9914d0a8d7589c32ab0938a4729023293'
CONTRACT_SHA = '1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41'
OLD_PROOF_SHA = '83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0'
ROWS = ('testing-environ,sys', 'testing-environ,sys,sync,metadata', 'testing-environ,sys,f32_float', 'testing-environ,sys,unchecked')
TEST = 'managed_child_kill_reports_group_closed_under_fixture_reaper'
SUCCESS = 'managed_run_succeeds_after_fixture_reaper_reaps_descendants'
HELD = 'managed_run_reports_while_fixture_reaper_holds_stopped_zombies'
CONTROLS = {
 'require-success-control': 'managed-child-kill-control require-success assertion',
 'require-sentinel-absent-control': 'managed-child-kill-control require-sentinel-absent assertion',
}
STAGE_PATH = Path('/root/rhai-linux-managed-kill-20261003-a17f40a7-100')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/linux-managed-kill-20261003-a17f40a7-100')
BASE = None
OLD = None

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(stage, name, expected, module_name):
 p=stage/name
 if sha(p)!=expected: raise RuntimeError(f'{name} hash mismatch')
 spec=importlib.util.spec_from_file_location(module_name,p); mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def overlay(original, control):
 text=original.decode()
 if control=='require-success-control':
  anchor='    assert!(killed_report, "public Child.kill report must record the killed child as unsuccessful");'
  replacement=f'    assert!(!killed_report, "{CONTROLS[control]}");'
 elif control=='require-sentinel-absent-control':
  anchor='    assert!(sentinel_live, "public Child.kill must preserve the unrelated sentinel at API return");'
  replacement=f'    assert!(!sentinel_live, "{CONTROLS[control]}");'
 else: raise RuntimeError(f'unknown control {control}')
 if text.count(anchor)!=1: raise RuntimeError('post-cleanup report assertion anchor is not unique')
 return text.replace(anchor,replacement,1).encode()

DU_TRANSIENT_MAX_ATTEMPTS = 4


def transient_du_missing_paths(stderr: str, runtime: Path) -> list[str] | None:
 """Accept only GNU du ENOENT diagnostics for vanished files below this runtime."""
 lines = stderr.splitlines()
 if not lines or any(not line for line in lines):
  return None
 root_absolute = Path(os.path.abspath(runtime))
 root = root_absolute.resolve(strict=True)
 missing = []
 pattern = re.compile(r"^du: cannot access '([^'\r\n]+)': No such file or directory$")
 for line in lines:
  match = pattern.fullmatch(line)
  if match is None:
   return None
  candidate = Path(match.group(1))
  if not candidate.is_absolute():
   return None
  try:
   relative = candidate.relative_to(root_absolute)
  except ValueError:
   return None
  if not relative.parts or any(part in ('', '.', '..') for part in relative.parts):
   return None
  current = root
  disappeared = False
  for index, part in enumerate(relative.parts):
   current = current / part
   try:
    info = current.lstat()
   except FileNotFoundError:
    disappeared = True
    break
   except (PermissionError, OSError) as exc:
    raise RuntimeError(f'cannot verify transient du ENOENT path {candidate}: {exc}') from exc
   if stat.S_ISLNK(info.st_mode):
    return None
   if index < len(relative.parts) - 1 and not stat.S_ISDIR(info.st_mode):
    return None
  if not disappeared:
   return None
  missing.append(str(candidate))
 return missing


def install_bounded_du_retry(base) -> None:
 """Replace only this proof's sampler; keep complete du/ps measurements and limits."""
 def capture(name: str, argv: list[str]) -> tuple[str, str, int]:
  child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, close_fds=True)
  try:
   base.record_process_identity(f'command:{name}', child.pid, base.process_identity(child.pid))
   stdout, stderr = child.communicate(timeout=5)
  except subprocess.TimeoutExpired:
   base.stop_child(child)
   raise TimeoutError(f'{name} sampling command exceeded five seconds')
  except BaseException:
   base.stop_child(child)
   raise
  return stdout, stderr, child.returncode

 def process_usage() -> tuple[int, int]:
  base.check_deadline()
  ps_output, stderr, status = capture('ps', ['/bin/ps', '-e', '-o', 'pid=,ppid=,rss='])
  base.check_deadline()
  if status != 0:
   raise RuntimeError(f'ps sampling command failed: {stderr[-500:]}')
  rows: dict[int, tuple[int, int]] = {}
  for line in ps_output.splitlines():
   fields = line.split()
   if len(fields) != 3:
    raise RuntimeError(f'malformed ps resource row: {line!r}')
   pid, ppid, rss = map(int, fields)
   if pid in rows:
    raise RuntimeError(f'duplicate PID in resource sample: {pid}')
   rows[pid] = (ppid, rss)
  root_pid = os.getpid()
  if root_pid not in rows:
   raise RuntimeError('helper PID absent from resource sample')
  owned = {root_pid}
  while True:
   children = {pid for pid, (ppid, _rss) in rows.items() if ppid in owned} - owned
   if not children:
    break
   owned.update(children)
  return sum(rows[pid][1] for pid in owned), len(owned) - 1

 def enforce_live_limits(rss: int, descendants: int) -> None:
  base.MAXIMA['rss_kib'] = max(base.MAXIMA['rss_kib'], rss)
  base.MAXIMA['descendants'] = max(base.MAXIMA['descendants'], descendants)
  if rss >= base.HARD_RSS_KIB:
   raise RuntimeError('sampled helper RSS reached 2 GiB hard stop')
  if descendants > base.MAX_DESCENDANTS:
   raise RuntimeError('sampled helper descendants exceeded 16')

 def sample_resources() -> None:
  base.check_deadline()
  du_argv = ['/usr/bin/du', '-sk', str(base.RUNTIME)]
  for attempt in range(1, DU_TRANSIENT_MAX_ATTEMPTS + 1):
   base.check_deadline()
   stdout, stderr, status = capture('du', du_argv)
   if status == 0:
    storage = int(stdout.split()[0])
    break
   vanished = transient_du_missing_paths(stderr, base.RUNTIME) if status == 1 else None
   if vanished is None:
    raise RuntimeError(f'du sampling command failed status={status}: {stderr[-500:]}')
   # Keep live limits and the helper deadline active between complete storage
   # measurements; retrying du never creates a window without RSS/child checks.
   rss, descendants = process_usage()
   enforce_live_limits(rss, descendants)
   if attempt == DU_TRANSIENT_MAX_ATTEMPTS:
    raise RuntimeError(f'du still saw transient ENOENT after {attempt} complete measurements: {vanished!r}')
   event = {'monotonic_seconds': round(time.monotonic() - base.START, 3),
            'attempt': attempt, 'vanished_paths': vanished,
            'rss_kib': rss, 'descendants': descendants,
            'next_action': 'rerun complete du measurement; no paths excluded'}
   retry_path = base.STAGE / 'du-transient-retries.jsonl'
   with retry_path.open('a', encoding='utf-8') as stream:
    stream.write(json.dumps(event, sort_keys=True) + '\n')
    stream.flush()
   print('du_transient_retry=' + json.dumps(event, sort_keys=True), flush=True)
  rss, descendants = process_usage()
  current = {'monotonic_seconds': round(time.monotonic() - base.START, 3),
             'storage_kib': storage, 'rss_kib': rss, 'descendants': descendants}
  base.SAMPLES.append(current)
  base.MAXIMA['storage_kib'] = max(base.MAXIMA['storage_kib'], storage)
  base.MAXIMA['rss_kib'] = max(base.MAXIMA['rss_kib'], rss)
  base.MAXIMA['descendants'] = max(base.MAXIMA['descendants'], descendants)
  print('sample=' + json.dumps(current, sort_keys=True), flush=True)
  if storage >= base.PREEMPTIVE_STORAGE_KIB:
   raise RuntimeError('sampled private storage reached 1.5 GiB preemptive stop')
  if storage >= base.HARD_STORAGE_KIB:
   raise RuntimeError('sampled private storage/RSS reached 2 GiB hard stop')
  enforce_live_limits(rss, descendants)
 base.sample_resources = sample_resources


def cargo_cmd(cargo,features): return [str(cargo),'test','--locked','--features',features,'--test','sys_process','--','--exact','--nocapture','--test-threads=1']
def streams(label): return BASE.read_text(BASE.STAGE/f'{label}.stdout'),BASE.read_text(BASE.STAGE/f'{label}.stderr')

def terminal(out, name, failed):
 if len(re.findall(r'(?m)^test '+re.escape(name)+r' \.\.\..*$',out))!=1: raise RuntimeError(f'{name}: exact outer name missing/duplicated')
 summaries=re.findall(r'(?m)^test result: .*?$',out)
 pat=(r'test result: FAILED\. 0 passed; 1 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s' if failed else r'test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s')
 if not summaries or not re.fullmatch(pat,summaries[-1]): raise RuntimeError(f'{name}: wrong final outer summary')
 if failed:
  block=out.split('failures:',1)
  names=[x.strip() for x in block[-1].split('test result:',1)[0].splitlines() if x.strip() and x.strip()!='failures:']
  if names != [name]: raise RuntimeError(f'{name}: wrong outer failure list {names!r}')
 return summaries[-1]

def early(text):
 pat=(r'managed_child_kill_live reaper=(\d+) reaper_start=(\d+) host=(\d+) host_start=(\d+) '
      r'leader=(\d+) leader_start=(\d+) worker=(\d+) worker_start=(\d+) leaf=(\d+) leaf_start=(\d+) '
      r'group=(\d+) sentinel=(\d+) sentinel_start=(\d+) sentinel_pgid=(\d+)')
 found=list(re.finditer(pat,text))
 if len(found)!=1: raise RuntimeError('exact early live PID/start/group receipt missing or duplicated')
 v=list(map(int,found[0].groups())); r,rs,h,hs,l,ls,w,ws,f,fs,g,s,ss,sg=v
 if len({r,h,l,w,f,s})!=6 or g!=l or sg!=s: raise RuntimeError('early live identity/group ownership conflict')
 return {'reaper':(r,rs),'host':(h,hs),'leader':(l,ls),'worker':(w,ws),'leaf':(f,fs),'sentinel':(s,ss),'group':g,'sentinel_group':sg}

def acquired(text, facts):
 rows=[tuple(map(int,m)) for m in re.findall(r'managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)',text)]
 h=facts['host'][0]; l=facts['leader'][0]; w=facts['worker'][0]; g=facts['group']
 expected={l:(facts['leader'][1],h,g),w:(facts['worker'][1],l,g),facts['leaf'][0]:(facts['leaf'][1],w,g)}
 got=[row for row in rows if row[0] in expected]
 if len(got)!=3 or len({x[0] for x in got})!=3: raise RuntimeError(f'exact three PIDFD rows missing/duplicated: {got!r}')
 result={pid:(start,ppid,pgid) for pid,start,ppid,pgid in got}
 if result!=expected: raise RuntimeError(f'PIDFD start/parent/group identities mismatch: {result!r}')
 return result

def boundary(text, label):
 facts=early(text); pidfds=acquired(text,facts)
 pattern=re.compile(r'(?m)^managed_child_kill_boundary host_live_at_return=(?P<host_live>true|false) reaper_live_at_return=(?P<reaper_live>true|false) '
  r'leader=(?P<leader>\d+) leader_start=(?P<leader_start>\d+) leader_absent=(?P<leader_absent>true|false) worker=(?P<worker>\d+) worker_start=(?P<worker_start>\d+) worker_absent=(?P<worker_absent>true|false) '
  r'leaf=(?P<leaf>\d+) leaf_start=(?P<leaf_start>\d+) leaf_absent=(?P<leaf_absent>true|false) group=(?P<group>\d+) exact_descendants_reaped=(?P<exact_reaped>true|false) '
  r'sentinel=(?P<sentinel>\d+) sentinel_start=(?P<sentinel_start>\d+) sentinel_pgid=(?P<sentinel_pgid>\d+) sentinel_live_at_return=(?P<sentinel_live>true|false) sentinel_reaped_after_return=(?P<sentinel_reaped>true|false) '
  r'api_bound=(?P<api_bound>true|false) report_returned=(?P<report_returned>true|false) killed_report=(?P<killed_report>true|false) capture_complete=(?P<capture_complete>true|false) pidfds_exited=(?P<pidfds_exited>true|false) '
  r'reaper_ok=(?P<reaper_ok>true|false) host_absent_after_cleanup=(?P<host_absent>true|false) group_empty=(?P<group_empty>true|false) '
  r'api="host=(?P<api_host>\d+) host_start=(?P<api_host_start>\d+) api_success=true api_outcome=child_report success=false code=(?:None|Some\(-?\d+\)) '
  r'signal=(?:None|Some\(-?\d+\)) stdout_complete=true stderr_complete=true cause=none diagnostic=none\\n" '
  r'reaped="worker=(?P<worker_reaped>\d+) start=(?P<worker_reaped_start>\d+) pgid=(?P<worker_group>\d+) reaped=true wait_status=\d+ leaf=(?P<leaf_reaped>\d+) start=(?P<leaf_reaped_start>\d+) pgid=(?P<leaf_group>\d+) reaped=true wait_status=\d+ complete=true\\n" '
  r'cleanup="pid=(?P<cleanup_reaper>\d+) prompt=true host_status=0 worker=(?P<cleanup_worker>\d+) start=(?P<cleanup_worker_start>\d+) pgid=(?P<cleanup_worker_group>\d+) reaped=true wait_status=\d+ '
  r'leaf=(?P<cleanup_leaf>\d+) start=(?P<cleanup_leaf_start>\d+) pgid=(?P<cleanup_leaf_group>\d+) reaped=true wait_status=\d+ complete=true\\n"$')
 matches=list(pattern.finditer(text))
 if len(matches)!=1: raise RuntimeError(f'{label}: complete source-format kill boundary/cleanup missing: {len(matches)}')
 m=matches[0]; names=pattern.groupindex
 def n(key): return int(m.group(key))
 def b(key): return m.group(key)=='true'
 exact={'host':facts['host'],'leader':(n('leader'),n('leader_start')),'worker':(n('worker'),n('worker_start')),'leaf':(n('leaf'),n('leaf_start')),'sentinel':(n('sentinel'),n('sentinel_start')),'reaper':facts['reaper']}
 for k in ('host','leader','worker','leaf','sentinel'):
  if exact[k]!=facts[k]: raise RuntimeError(f'{label}: boundary {k} differs from early PID/start')
 if (n('group'),n('sentinel_pgid'))!=(facts['group'],facts['sentinel_group']): raise RuntimeError(f'{label}: boundary process groups differ')
 if (n('api_host'),n('api_host_start'))!=facts['host']: raise RuntimeError(f'{label}: API report host identity differs')
 if (n('worker_reaped'),n('worker_reaped_start'),n('worker_group'),n('leaf_reaped'),n('leaf_reaped_start'),n('leaf_group'))!=(facts['worker'][0],facts['worker'][1],facts['group'],facts['leaf'][0],facts['leaf'][1],facts['group']): raise RuntimeError(f'{label}: prompt reaper did not wait exact worker/leaf PID/start/group')
 if n('cleanup_reaper')!=facts['reaper'][0] or (n('cleanup_worker'),n('cleanup_worker_start'),n('cleanup_worker_group'),n('cleanup_leaf'),n('cleanup_leaf_start'),n('cleanup_leaf_group'))!=(facts['worker'][0],facts['worker'][1],facts['group'],facts['leaf'][0],facts['leaf'][1],facts['group']): raise RuntimeError(f'{label}: final fixture cleanup receipt mismatches exact identities')
 if not all(b(k) for k in ('host_live','reaper_live','leader_absent','worker_absent','leaf_absent','exact_reaped','sentinel_live','sentinel_reaped','api_bound','report_returned','killed_report','capture_complete','pidfds_exited','reaper_ok','host_absent','group_empty')): raise RuntimeError(f'{label}: boundary invariant false')
 identities=[]
 for name,(pid,start) in exact.items():
  try:
   raw=Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==str(start)
  except FileNotFoundError: alive=False
  except (PermissionError,OSError,IndexError,ValueError) as exc: raise RuntimeError(f'{label}: exact post-cleanup PID/start readback unknown for {name}: {exc}')
  if alive: raise RuntimeError(f'{label}: exact fixture identity remains after cleanup: {name}={pid}/{start}')
  identities.append({'label':name,'pid':pid,'start_ticks':start,'matching_identity_alive':False})
 import subprocess
 groups={facts['group'],facts['sentinel_group']}
 ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
 members=[[int(row.split()[0]),int(row.split()[1])] for row in ps.splitlines() if len(row.split())==2 and int(row.split()[1]) in groups]
 if members: raise RuntimeError(f'{label}: managed/sentinel fixture process group remains populated: {members!r}')
 BASE.write_json(BASE.STAGE/f'{label}-fixture-closure.json',{'identities':identities,'groups':sorted(groups),'group_members_after_cleanup':members,'pidfd_identities':[{'pid':pid,'start_ticks':v[0],'ppid':v[1],'pgid':v[2]} for pid,v in sorted(pidfds.items())]})
 return {'facts':facts,'pidfds':pidfds,'identities':exact}

def verify_panic(out,err,label,diagnostic):
 terminal(out,TEST,True)
 if len(re.findall(r"(?m)^thread '"+re.escape(TEST)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err))!=1 or err.count(diagnostic)!=1: raise RuntimeError(f'{label}: failure did not reach the named post-cleanup control')
 closure=boundary(err,label)
 return closure

def one(cargo,env,label,features,expected,control=None):
 cmd=cargo_cmd(cargo,features)+[TEST]
 BASE.run_command(label,cmd,env,expected_status=expected)
 out,err=streams(label)
 if control:
  result=verify_panic(out,err,label,CONTROLS[control])
 else:
  terminal(out,TEST,False); result=boundary(err,label)
 return result

def main():
 global BASE, OLD
 stage=Path(os.environ['PROOF_STAGE']); runtime=Path(os.environ['AGENT_RUNTIME_DIR'])
 BASE=load(stage,'check-linux-current-msrv-examples.py',BASE_SHA,'accepted_base')
 install_bounded_du_retry(BASE)
 OLD=load(stage,'linux-managed-success-proof.py',OLD_PROOF_SHA,'accepted96_proof')
 signal.signal(signal.SIGTERM,BASE.on_signal); signal.signal(signal.SIGINT,BASE.on_signal)
 BASE.INPUT_STAGE=stage; BASE.EXPECTED_STAGE=Path(os.environ['EXPECTED_PROOF_STAGE']); BASE.PRESCRIBED_STAGE=STAGE_PATH; BASE.PRESCRIBED_SCOPE=SCOPE_PATH
 BASE.RUNTIME=runtime; BASE.STAGE=runtime/'evidence'; BASE.EVIDENCE=stage/'proof-evidence'; BASE.CONTRACT=stage/'contract.md'; BASE.SOURCE_ARCHIVE=stage/'source.tar'; BASE.LOCK_SOURCE=stage/'Cargo.lock.accepted'; BASE.RUSTUP=Path(os.environ['RUSTUP_BIN'])
 BASE.SOURCE_ARCHIVE_SHA256=ARCHIVE; BASE.LOCK_SHA256=LOCK; BASE.REVISION=REV; BASE.TOOLCHAIN='1.77.2-x86_64-unknown-linux-gnu'
 BASE.START=time.monotonic(); BASE.DEADLINE=BASE.START+540; BASE.WORK_DEADLINE=BASE.DEADLINE-30; BASE.SOURCE=runtime/'source'; BASE.CARGO_HOME=runtime/'cargo-home'; BASE.RUSTUP_HOME=runtime/'rustup-home'; BASE.TARGET=runtime/'target'; BASE.PRIVATE_HOME=runtime/'home'; BASE.PRIVATE_TMP=Path(os.environ['TMPDIR'])
 BASE.capture_runtime_proof(); BASE.validate_stage_inputs()
 if platform.system()!='Linux' or platform.machine().lower() not in ('x86_64','amd64'): raise RuntimeError('native Linux x86_64 required')
 BASE.extract_archive(BASE.SOURCE_ARCHIVE); shutil.copy2(BASE.LOCK_SOURCE,BASE.SOURCE/'Cargo.lock')
 manifest=BASE.manifest_hashes(); test=BASE.SOURCE/'tests/sys_process.rs'; original=test.read_bytes()
 if sha(test)!=TEST_SHA: raise RuntimeError('frozen sys_process source mismatch')
 BASE.ORIGINAL_EXAMPLES[test]=original; BASE.ORIGINAL_EXAMPLE_HASHES['tests/sys_process.rs']=TEST_SHA
 for p in (BASE.CARGO_HOME,BASE.RUSTUP_HOME,BASE.PRIVATE_HOME): p.mkdir(mode=0o700)
 BASE.PRIVATE_TMP.mkdir(mode=0o700,exist_ok=True)
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(BASE.PRIVATE_HOME),'TMPDIR':str(BASE.PRIVATE_TMP),'TMP':str(BASE.PRIVATE_TMP),'TEMP':str(BASE.PRIVATE_TMP),'CARGO_HOME':str(BASE.CARGO_HOME),'RUSTUP_HOME':str(BASE.RUSTUP_HOME),'CARGO_TARGET_DIR':str(BASE.TARGET),'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_PROFILE_DEV_DEBUG':'0','CARGO_TERM_COLOR':'never','RUST_BACKTRACE':'0','AGENT_RUNTIME_DIR':str(runtime)}
 BASE.run_command('rustup-install',[str(BASE.RUSTUP),'toolchain','install',BASE.TOOLCHAIN,'--profile','minimal','--no-self-update'],env,cwd=runtime)
 bindir=BASE.RUSTUP_HOME/'toolchains'/BASE.TOOLCHAIN/'bin'; rustc=bindir/'rustc'; cargo=bindir/'cargo'
 if not rustc.is_file() or not cargo.is_file(): raise RuntimeError('private toolchain incomplete')
 env.update(PATH=f'{bindir}:/usr/bin:/bin:/usr/sbin:/sbin',RUSTC=str(rustc))
 BASE.run_command('rustc-version',[str(rustc),'--version','--verbose'],env); BASE.run_command('cargo-version',[str(cargo),'--version','--verbose'],env)
 # One semantic wrong-control is falsifiable only after exact fixture closure and receipt output.
 for control in CONTROLS:
  test.write_bytes(overlay(original,control)); BASE.INJECTED_EXAMPLE_HASHES[control]=sha(test)
  one(cargo,env,control,ROWS[0],101,control)
  BASE.verify_control(control,101,101,BASE.read_text(BASE.STAGE/f'{control}.stderr'),[CONTROLS[control]])
  test.write_bytes(original)
  if sha(test)!=TEST_SHA: raise RuntimeError(f'exact source restoration after {control} failed')
 # The accepted96 prompt-success and held-zombie cases are retained in the same base-feature build.
 for label,name in (('native96-success-row1',SUCCESS),('native96-held-row1',HELD)):
  BASE.run_command(label,cargo_cmd(cargo,ROWS[0])+[name],env)
  out,err=streams(label); terminal(out,name,False); text=out+err
  if name==SUCCESS:
   OLD.require_success(text); OLD.identity_closure(text,'kill-package-'+label,BASE,label)
  else:
   OLD.require_held(text,BASE,label)
 for i,features in enumerate(ROWS):
  label=f'green-row-{i+1}'; result=one(cargo,env,label,features,0)
  BASE.verify_pass(label,0,BASE.read_text(BASE.STAGE/f'{label}.stdout'),terminal(BASE.read_text(BASE.STAGE/f'{label}.stdout'),TEST,False))
 if sha(test)!=TEST_SHA or BASE.manifest_hashes()!=manifest or sha(BASE.SOURCE/'Cargo.lock')!=LOCK: raise RuntimeError('source/manifests/lock restoration mismatch')
 BASE.write_json(BASE.STAGE/'package-result.json',{'source_revision':REV,'test_sha256':TEST_SHA,'test':TEST,'feature_rows':list(ROWS),'wrong_controls':list(CONTROLS),'green_rows':4,'native96_applicability':['managed_run_succeeds_after_fixture_reaper_reaps_descendants','managed_run_reports_while_fixture_reaper_holds_stopped_zombies'],'source_restored':True,'acceptance_claim':False,'limitations':['No no_float/no_index row is included. Native evidence and exact remote cleanup require collector readback.']})
 return 0

def export():
 if BASE is None or not BASE.STAGE.is_dir() or BASE.EVIDENCE.exists(): return
 error=None
 try:
  if BASE.ORIGINAL_EXAMPLES: BASE.restore_example_sources()
 except BaseException: error=traceback.format_exc(); (BASE.STAGE/'restoration-failure.txt').write_text(error)
 BASE.write_json(BASE.STAGE/'source-restoration.json',{'original_sha256':BASE.ORIGINAL_EXAMPLE_HASHES,'overlay_sha256':BASE.INJECTED_EXAMPLE_HASHES,'restored':bool(BASE.ORIGINAL_EXAMPLES) and all(sha(p)==BASE.ORIGINAL_EXAMPLE_HASHES[p.relative_to(BASE.SOURCE).as_posix()] for p in BASE.ORIGINAL_EXAMPLES),'error':error})
 BASE.write_json(BASE.STAGE/'export.json',{'runtime':str(BASE.RUNTIME),'scope':str(BASE.RUNTIME.parent),'destination':str(BASE.EVIDENCE),'elapsed_seconds':round(time.monotonic()-BASE.START,3),'reserve_seconds':30})
 BASE.EVIDENCE.mkdir(mode=0o700)
 for item in BASE.STAGE.iterdir(): BASE.check_deadline(during_export=True); shutil.copytree(item,BASE.EVIDENCE/item.name) if item.is_dir() else shutil.copy2(item,BASE.EVIDENCE/item.name)
 if error: raise RuntimeError('source restoration failed')
if __name__=='__main__':
 status=1
 try: status=main()
 except BaseException as exc:
  if BASE is not None and BASE.STAGE.is_dir(): (BASE.STAGE/'failure.txt').write_text(''.join(traceback.format_exception(type(exc),exc,exc.__traceback__)))
  traceback.print_exc(); status=1
 finally:
  try: export()
  except BaseException: traceback.print_exc(); status=1
 raise SystemExit(status)
