#!/usr/bin/env python3
"""Bounded Rust 1.77.2 Linux managed success and held-zombie proof."""
from __future__ import annotations
import hashlib, importlib.util, json, os, platform, re, shutil, signal, sys, time, traceback
from pathlib import Path

REV = '003da06421fbd11c26e0c96ab5013416c0939a1d'
ARCHIVE = 'f62ea7430f8a92db7210055373f9e96b2d850d3564c4962844c80056b7294d1a'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
BASE_SHA = '59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06'
TEST_SHA = 'e0034cf3a69ccf6107a9dfbc0854c0147ec2d93fdda8acf5ed6b07e683e1dc14'
CONTRACT_SHA = '1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41'
FEATURE_ROWS = ('testing-environ,sys', 'testing-environ,sys,sync,metadata', 'testing-environ,sys,f32_float', 'testing-environ,sys,unchecked')
SUCCESS = 'managed_run_succeeds_after_fixture_reaper_reaps_descendants'
HELD = 'managed_run_reports_while_fixture_reaper_holds_stopped_zombies'
ASSERTIONS = {
 'require-exit-seven': 'managed-success-control require-exit-seven assertion',
 'require-sentinel-absent': 'managed-success-control require-sentinel-absent assertion',
}
STAGE_PATH = Path('/root/rhai-linux-managed-success-20261003-7d045f21-96')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/linux-managed-success-20261003-7d045f21-96')
BASE = None

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load_base(stage):
 p=stage/'check-linux-current-msrv-examples.py'
 if sha(p)!=BASE_SHA: raise RuntimeError('base helper hash mismatch')
 spec=importlib.util.spec_from_file_location('accepted_base',p); mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def overlay(original, control):
 text=original.decode(); anchor='    eprintln!("managed_prompt_reap_success host='
 if text.count(anchor)!=1: raise RuntimeError('success receipt anchor is not unique')
 if control=='require-exit-seven': line='    assert!(api_result.contains("exit=Some(7)"), "managed-success-control require-exit-seven assertion");'
 elif control=='require-sentinel-absent': line='    assert!(!sentinel_live_at_return, "managed-success-control require-sentinel-absent assertion");'
 else: raise RuntimeError(control)
 # The assertion executes after success-boundary and cleanup receipts and exact child reaping.
 idx=text.index(anchor); end=text.index('\n',idx)
 return (text[:end+1]+line+'\n'+text[end+1:]).encode()

def streams(h,name): return h.read_text(h.STAGE/f'{name}.stdout'),h.read_text(h.STAGE/f'{name}.stderr')
def outer(stdout,names,failed=False):
 for name in names:
  if len(re.findall(r'(?m)^test '+re.escape(name)+r' \.\.\..*$',stdout))!=1: raise RuntimeError(f'outer exact test prefix missing/duplicated: {name}')
 summaries=re.findall(r'(?m)^test result: .*?$',stdout)
 if not summaries: raise RuntimeError('outer terminal summary missing')
 result=summaries[-1]
 expected=(r'test result: FAILED\. 0 passed; 1 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s' if failed else r'test result: ok\. 2 passed; 0 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s')
 if not re.fullmatch(expected,result): raise RuntimeError(f'outer final summary mismatch: {result!r}')
 if failed:
  block=stdout.split('failures:',1)
  failures=[x.strip() for x in block[-1].split('test result:',1)[0].splitlines() if x.strip() and x.strip()!='failures:']
  if failures!=[SUCCESS]: raise RuntimeError(f'wrong outer failure list: {failures!r}')
 return result

def outer_segments(stdout,names):
 starts={}
 for name in names:
  found=list(re.finditer(r'(?m)^test '+re.escape(name)+r' \.\.\..*$',stdout))
  if len(found)!=1: raise RuntimeError(f'outer exact test prefix missing/duplicated: {name}')
  starts[name]=found[0].start()
 ordered=sorted((pos,name) for name,pos in starts.items())
 return {name:stdout[pos:(ordered[i+1][0] if i+1<len(ordered) else len(stdout))] for i,(pos,name) in enumerate(ordered)}

def verify_red_outer(out,err,label,diagnostic):
 summary=re.findall(r'(?m)^test result: .*?$',out)
 if len(re.findall(r'(?m)^test '+re.escape(SUCCESS)+r' \.\.\..*$',out))!=1: raise RuntimeError(f'{label} missing exact outer test prefix')
 if not summary or not re.fullmatch(r'test result: FAILED\. 0 passed; 1 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s',summary[-1]): raise RuntimeError(f'{label} lacks outer one-test FAILED summary')
 failures=out.split('failures:',1)
 if len(failures)!=2 or [x.strip() for x in failures[1].split('test result:',1)[0].splitlines() if x.strip() and x.strip()!='failures:']!=[SUCCESS]: raise RuntimeError(f'{label} outer failure list is not the intended test')
 if len(re.findall(r"(?m)^thread '"+re.escape(SUCCESS)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err))!=1 or err.count(diagnostic)!=1: raise RuntimeError(f'{label} panic/assertion origin mismatch')

def cargo_cmd(cargo,features,names):
 return [str(cargo),'test','--locked','--features',features,'--test','sys_process','--','--exact','--nocapture','--test-threads=1',*names]
def early_receipt(text, label):
 m=re.search(r'managed_prompt_reap_live_boundary reaper=(\d+) reaper_start=(\d+) host=(\d+) host_start=(\d+) leader=(\d+) leader_start=(\d+) worker=(\d+) worker_start=(\d+) leaf=(\d+) leaf_start=(\d+) group=(\d+) sentinel=(\d+) sentinel_start=(\d+)',text)
 if not m: raise RuntimeError(f'{label} lacks the exact pre-assertion fixture identity receipt')
 v=list(map(int,m.groups())); r,rs,h,hs,l,ls,w,ws,f,fs,g,s,ss=v
 if len({r,h,l,w,f,s})!=6 or g!=l: raise RuntimeError(f'{label} fixture PID/group identities conflict')
 return {'reaper':(r,rs),'host':(h,hs),'leader':(l,ls),'worker':(w,ws),'leaf':(f,fs),'sentinel':(s,ss),'group':g}

def acquired_rows(text):
 return [(int(pid),int(start),int(ppid),int(pgid)) for pid,start,ppid,pgid in re.findall(r'managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)',text)]

def require_acquisition_inventory(text, expected, label):
 rows=acquired_rows(text); got={pid:(start,ppid,pgid) for pid,start,ppid,pgid in rows}
 if len(rows)!=expected or len(got)!=expected: raise RuntimeError(f'{label} acquired PIDFD inventory count/uniqueness mismatch: {rows!r}')
 return got

def acquired_for_early(text, early, label):
 acquired=acquired_rows(text)
 l,ls=early['leader']; w,ws=early['worker']; f,fs=early['leaf']; h,_=early['host']; g=early['group']
 expected={l:(ls,h,g),w:(ws,l,g),f:(fs,w,g)}
 selected=[row for row in acquired if row[0] in expected]
 if len(selected)!=3 or len({row[0] for row in selected})!=3: raise RuntimeError(f'{label} needs exactly one PIDFD receipt for each expected process: {selected!r}')
 got={pid:(start,ppid,pgid) for pid,start,ppid,pgid in selected}
 if got!=expected: raise RuntimeError(f'{label} PIDFD identities/parents/groups mismatch: {got!r}')
 return got

def identity_closure(text, prefix, h, label):
 early=early_receipt(text,label); pidfds=acquired_for_early(text,early,label)
 success=re.search(r'managed_prompt_reap_success host=(\d+) host_start=(\d+) leader=(\d+) leader_start=(\d+) leader_absent=true worker=(\d+) worker_start=(\d+) worker_absent=true leaf=(\d+) leaf_start=(\d+) leaf_absent=true sentinel=(\d+) sentinel_start=(\d+) sentinel_live_at_return=true sentinel_reaped_after_return=true',text)
 if success:
  vals=list(map(int,success.groups())); expected=(early['host'][0],early['host'][1],early['leader'][0],early['leader'][1],early['worker'][0],early['worker'][1],early['leaf'][0],early['leaf'][1],early['sentinel'][0],early['sentinel'][1])
  if tuple(vals)!=expected: raise RuntimeError(f'{label} final success boundary disagrees with early live identity receipt')
  require_success(text)
 sentinel_cleanup=re.search(r'managed-scope sentinel_cleanup pid=(\d+) status=Some\(ExitStatus\(unix_wait_status\(\d+\)\)\) esrch=true',text)
 if not sentinel_cleanup or int(sentinel_cleanup.group(1))!=early['sentinel'][0]: raise RuntimeError(f'{label} exact sentinel cleanup receipt missing/mismatched')
 rows=[]; group=early['group']
 for name,(pid,start) in [(k,v) for k,v in early.items() if k!='group']:
  try:
   raw=Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==str(start)
  except FileNotFoundError: alive=False
  except (PermissionError,OSError,IndexError,ValueError) as exc: raise RuntimeError(f'{label} exact identity readback unknown for {name}: {exc}')
  if alive: raise RuntimeError(f'{label} exact fixture process remains: {name}={pid}/{start}')
  rows.append({'label':name,'pid':pid,'start_ticks':start,'matching_identity_alive':False})
 import subprocess
 ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
 members=[line.split() for line in ps.splitlines() if len(line.split())==2 and int(line.split()[1])==group]
 if members: raise RuntimeError(f'{label} fixture process group remains populated: {members}')
 h.write_json(h.STAGE/f'{prefix}-fixture-closure.json',{'identities':rows,'group':group,'group_members_after_cleanup':members,'pidfd_identities':[{'pid':pid,'start_ticks':v[0],'ppid':v[1],'pgid':v[2]} for pid,v in sorted(pidfds.items())]})

def success_api_receipt(text):
 pattern=re.compile(r'^managed_prompt_reap_success host=(?P<host>\d+) host_start=(?P<host_start>\d+) leader=(?P<leader>\d+) leader_start=(?P<leader_start>\d+) leader_absent=true worker=(?P<worker>\d+) worker_start=(?P<worker_start>\d+) worker_absent=true leaf=(?P<leaf>\d+) leaf_start=(?P<leaf_start>\d+) leaf_absent=true sentinel=(?P<sentinel>\d+) sentinel_start=(?P<sentinel_start>\d+) sentinel_live_at_return=true sentinel_reaped_after_return=true api_exit_zero_at_return=true captures_complete_at_return=true api=host=(?P<api_host>\d+) host_start=(?P<api_host_start>\d+) api_success=true api_outcome=success_report code=0 exit=Some\(0\) stdout_complete=true stderr_complete=true cause=none diagnostic=none\r?\n cleanup="worker=(?P<cworker>\d+) start=(?P<cworker_start>\d+) pgid=(?P<cworker_group>\d+) reaped=true wait_status=\d+ leaf=(?P<cleaf>\d+) start=(?P<cleaf_start>\d+) pgid=(?P<cleaf_group>\d+) reaped=true wait_status=\d+ complete=true\\n"\r?\n',re.MULTILINE)
 matches=list(pattern.finditer(text))
 if len(matches)!=1: raise RuntimeError(f'success record count is not exactly one complete source-format receipt: {len(matches)}')
 m=matches[0]
 vals={key:int(value) for key,value in m.groupdict().items()}
 if (vals['api_host'],vals['api_host_start'])!=(vals['host'],vals['host_start']): raise RuntimeError('success API host PID/start differs from the observed live host')
 if (vals['cworker'],vals['cworker_start'],vals['cleaf'],vals['cleaf_start'])!=(vals['worker'],vals['worker_start'],vals['leaf'],vals['leaf_start']) or vals['cworker_group']!=vals['leader'] or vals['cleaf_group']!=vals['leader']: raise RuntimeError('success reaper cleanup does not bind exact worker/leaf PID/start/group')
 return m

def require_success(text):
 m=success_api_receipt(text)
 v={key:int(value) for key,value in m.groupdict().items()}
 identity_keys=('host','leader','worker','leaf','sentinel')
 if len({v[k] for k in identity_keys})!=5: raise RuntimeError('success fixture PID identities are not distinct')
 early=early_receipt(text,'success')
 for key in identity_keys:
  if early[key]!=(v[key],v[key+'_start']): raise RuntimeError(f'success receipt disagrees with independently captured live {key} identity receipt')
 got=acquired_for_early(text,early,'success'); group=early['group']
 return {'host':(v['host'],v['host_start']),'leader':(v['leader'],v['leader_start']),'worker':(v['worker'],v['worker_start']),'leaf':(v['leaf'],v['leaf_start']),'sentinel':(v['sentinel'],v['sentinel_start']),'group':group,'pidfds':got}

def exact_boundary(output: str) -> tuple[list[tuple[str, int, str]], int, list[dict[str, int]]]:
    pattern = re.compile(
        r"managed_held_zombie_boundary host_live_at_return=true "
        r"leader=(\d+) leader_start=(\d+) leader_reaped=true "
        r"worker=(\d+) worker_start=(\d+) worker_state=Z worker_pgid=(\d+) "
        r"leaf=(\d+) leaf_start=(\d+) leaf_state=Z leaf_pgid=(\d+) group=(\d+) "
        r".*?capture_complete=true host=(\d+) host_start=(\d+) "
        r"api_success=false api_outcome=typed_process_io "
        r"cause_op=observe_process_group_closure cause_op_matches=true kind=TimedOut exit=Some\(0\) "
        r"stdout_complete=true stderr_complete=true diagnostic=true cause_details=.*? cleanup_diagnostics=.*?\s+held=\"pid=(\d+) start=(\d+) host_status=(\d+) "
        r"worker=Some\((\d+)\) worker_start=Some\((\d+)\) "
        r"leaf=Some\((\d+)\) leaf_start=Some\((\d+)\) held_zombies=true\\n\" "
        r"reaper_status=ExitStatus\(unix_wait_status\(0\)\)", re.DOTALL)
    match = pattern.search(output)
    if not match:
        raise RuntimeError("exact managed-zombie boundary, held-reaper, typed timeout, direct exit, or successful cleanup status receipt missing")
    values = list(map(int, match.groups()))
    (leader, leader_start, worker, worker_start, worker_pgid, leaf, leaf_start,
     leaf_pgid, group, host, host_start, reaper, reaper_start, host_status,
     held_worker, held_worker_start, held_leaf, held_leaf_start) = values
    if len({leader, worker, leaf}) != 3 or len({leader, group, worker_pgid, leaf_pgid}) != 1:
        raise RuntimeError("leader/worker/leaf identities must be distinct members of the exact leader process group")
    if host_status != 0 or (held_worker, held_worker_start, held_leaf, held_leaf_start) != (worker, worker_start, leaf, leaf_start):
        raise RuntimeError("fixture reaper held record does not match the exact successful host/worker/leaf identities")
    cleanup = re.search(
        r"managed_held_zombie_cleanup worker=(\d+) reaped=true leaf=(\d+) reaped=true", output)
    if not cleanup or tuple(map(int, cleanup.groups())) != (worker, leaf):
        raise RuntimeError("fixture cleanup receipt does not name the exact held worker and leaf")
    expected = {
        leader: (leader_start, host, group),
        worker: (worker_start, leader, worker_pgid),
        leaf: (leaf_start, worker, leaf_pgid),
    }
    acquired = [row for row in acquired_rows(output) if row[0] in expected]
    if len(acquired) != 3 or len({row[0] for row in acquired}) != 3:
        raise RuntimeError(f"expected exactly one managed pidfd receipt per held identity, got {acquired!r}")
    pidfds = {pid: (start, ppid, pgid) for pid, start, ppid, pgid in acquired}
    if set(pidfds) != set(expected):
        raise RuntimeError("acquired pidfd PID set differs from boundary leader/worker/leaf")
    for pid, facts in expected.items():
        if pidfds[pid] != facts:
            raise RuntimeError(f"acquired pidfd identity disagrees with exact boundary for pid={pid}: {pidfds[pid]} != {facts}")
    identities = [("leader", leader, str(leader_start)), ("worker", worker, str(worker_start)),
                  ("leaf", leaf, str(leaf_start)), ("host", host, str(host_start)),
                  ("fixture-reaper", reaper, str(reaper_start))]
    pidfd_rows = sorted(
        ({"pid": pid, "start_ticks": fields[0], "ppid": fields[1], "pgid": fields[2]}
         for pid, fields in pidfds.items()), key=lambda row: row["pid"])
    return identities, group, pidfd_rows


def require_held(text, h, label):
 for token in ('managed_held_zombie_boundary host_live_at_return=true','leader_reaped=true','worker_state=Z','leaf_state=Z','cause_op=observe_process_group_closure','kind=TimedOut exit=Some(0)','stdout_complete=true stderr_complete=true','managed_held_zombie_cleanup','reaper_status=ExitStatus(unix_wait_status(0))'):
  if token not in text: raise RuntimeError(f'accepted held-zombie boundary missing {token!r}')
 identities, group, pidfds = exact_boundary(text)
 rows=[]
 for name,pid,start in identities:
  try:
   raw=Path('/proc',str(pid),'stat').read_text(); fields=raw[raw.rfind(')')+2:].split(); alive=fields[19]==start
  except FileNotFoundError: alive=False
  except (PermissionError,OSError,IndexError,ValueError) as exc: raise RuntimeError(f'{label} exact held identity readback unknown: {name}: {exc}')
  if alive: raise RuntimeError(f'{label} held fixture identity remains: {name}={pid}/{start}')
  rows.append({'label':name,'pid':pid,'start_ticks':start,'matching_identity_alive':False})
 import subprocess
 ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
 members=[line.split() for line in ps.splitlines() if len(line.split())==2 and int(line.split()[1])==group]
 if members: raise RuntimeError(f'{label} held fixture group remains: {members}')
 h.write_json(h.STAGE/f'{label}-held-closure.json',{'identities':rows,'group':group,'pidfd_identities':pidfds,'group_members_after_cleanup':members})

def main():
 global BASE
 stage=Path(os.environ['PROOF_STAGE']); runtime=Path(os.environ['AGENT_RUNTIME_DIR']); BASE=load_base(stage)
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
 # A held-mode RED replaces only the child reaper mode: it must reach the new test's
 # successful-report assertion, after fixture readiness and with cleanup receipts.
 prompt='    std::fs::write(fixture.path("begin-run"), b"begin\\n").unwrap();'
 text=original.decode(); old='.env("RHAI_SYS_MANAGED_ZOMBIE_REAP_MODE", "prompt")'
 if text.count(old)!=1: raise RuntimeError('prompt-mode source anchor not unique')
 test.write_bytes(text.replace(old,'.env("RHAI_SYS_MANAGED_ZOMBIE_REAP_MODE", "held")',1).encode())
 BASE.INJECTED_EXAMPLE_HASHES['held-mode-red']=sha(test)
 features=FEATURE_ROWS[0]
 # The RED requires the report assertion; readiness, identity acquisition and cleanup must also be present.
 cmd=cargo_cmd(cargo,features,[SUCCESS])
 BASE.run_command('held-mode-red',cmd,env,expected_status=101)
 out,err=streams(BASE,'held-mode-red'); joined=out+err
 diagnostic='managed run must return a successful zero-exit report after exact foreign reaping'
 if diagnostic not in err or 'managed_prompt_reap_live_boundary' not in joined or 'managed-scope sentinel_cleanup' not in joined: raise RuntimeError('held-mode RED failed before the intended assertion or lacks early identity/sentinel cleanup receipts')
 verify_red_outer(out,err,'held-mode-red',diagnostic); require_acquisition_inventory(joined,3,'held-mode-red'); identity_closure(joined,'held-mode-red',BASE,'held-mode-red'); BASE.verify_control('held-mode-red',101,101,err,[diagnostic])
 test.write_bytes(original)
 for control,diagnostic in ASSERTIONS.items():
  test.write_bytes(overlay(original,control)); BASE.INJECTED_EXAMPLE_HASHES[control]=sha(test)
  BASE.run_command(control,cargo_cmd(cargo,FEATURE_ROWS[0],[SUCCESS]),env,expected_status=101)
  out,err=streams(BASE,control); joined=out+err
  if diagnostic not in err or 'managed_prompt_reap_success' not in joined or 'sentinel_reaped_after_return=true' not in joined: raise RuntimeError(f'{control} did not fail after complete success cleanup')
  verify_red_outer(out,err,control,diagnostic); identity_closure(joined,control,BASE,control)
  if not re.search(r"(?m)^thread '"+re.escape(SUCCESS)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err): raise RuntimeError('control panic did not originate at named success test')
  require_acquisition_inventory(joined,3,control); BASE.verify_control(control,101,101,err,[diagnostic]); test.write_bytes(original)
  if sha(test)!=TEST_SHA: raise RuntimeError('source restoration after control failed')
 for i,features in enumerate(FEATURE_ROWS):
  label=f'green-row-{i+1}'
  BASE.run_command(label,cargo_cmd(cargo,features,[SUCCESS,HELD]),env)
  out,err=streams(BASE,label); summary=outer(out,[SUCCESS,HELD]); segments=outer_segments(out,[SUCCESS,HELD])
  sf=require_success(segments[SUCCESS]+err); held_ids,held_group,held_rows=exact_boundary(segments[HELD]+err)
  held_map={int(x['pid']):(int(x['start_ticks']),int(x['ppid']),int(x['pgid'])) for x in held_rows}
  all_rows=require_acquisition_inventory(out+err,6,label); union=dict(sf['pidfds']); union.update(held_map)
  if all_rows!=union or set(sf['pidfds']).intersection(held_map): raise RuntimeError(f'{label} two exact tests do not bind a disjoint complete six-PIDFD inventory')
  require_held(segments[HELD]+err,BASE,label); identity_closure(segments[SUCCESS]+err,'success-'+label,BASE,label); BASE.verify_pass(label,0,out,summary)
 if sha(test)!=TEST_SHA or BASE.manifest_hashes()!=manifest or sha(BASE.SOURCE/'Cargo.lock')!=LOCK: raise RuntimeError('source/manifests/lock restoration mismatch')
 BASE.write_json(BASE.STAGE/'package-result.json',{'source_revision':REV,'test_sha256':TEST_SHA,'tests':[SUCCESS,HELD],'feature_rows':list(FEATURE_ROWS),'red_controls':['held-mode-red',*ASSERTIONS],'green_rows':4,'source_restored':True,'acceptance_claim':False,'limitations':['Native outputs and identity closure require independent collector readback; four rows exclude no_float/no_index.']})
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
