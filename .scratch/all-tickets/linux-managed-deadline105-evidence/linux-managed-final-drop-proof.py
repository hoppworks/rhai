#!/usr/bin/env python3
"""Bounded Rust 1.77.2 proof for final managed Child lease drop."""
from __future__ import annotations
import hashlib, importlib.util, json, os, platform, re, shutil, signal, subprocess, sys, time, traceback
from pathlib import Path

REV = '61b3739a785503d6a74d769b30c218b82f5dd249'
ARCHIVE = '47361b26246a615e74d6d5d774729acd4380f136ac553723f028ac6605274c24'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
BASE_SHA = '59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06'
TEST_SHA = 'd0a8842cc6be749a98ab7786ae66fdeca4a0488ad48aacfc88b24d48bdc660d8'
CONTRACT_SHA = '1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41'
KILL_PROOF_SHA = '4a80d60a826e1db80e174fe0627e01194d46cc54c4d22e55c1c49425637e50d1'
SUCCESS_PROOF_SHA = '83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0'
TEST = 'managed_spawn_final_clone_drop_closes_group_under_fixture_reaper'
KILL_TEST = 'managed_child_kill_reports_group_closed_under_fixture_reaper'
SUCCESS_TEST = 'managed_run_succeeds_after_fixture_reaper_reaps_descendants'
HELD_TEST = 'managed_run_reports_while_fixture_reaper_holds_stopped_zombies'
ROWS = ('testing-environ,sys', 'testing-environ,sys,sync,metadata', 'testing-environ,sys,f32_float', 'testing-environ,sys,unchecked')
CONTROL = 'require-member-live-control'
DIAGNOSTIC = 'managed-final-drop-control require-member-live assertion'
STAGE_PATH = Path('/root/rhai-linux-managed-final-drop-20261003-106f2472-102')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/linux-managed-final-drop-20261003-106f2472-102')
BASE = KILL = OLD = None

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def load(stage, name, expected, module_name):
    path = stage / name
    if sha(path) != expected: raise RuntimeError(f'{name} hash mismatch')
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    return module

def overlay(original):
    text = original.decode()
    anchor = '    assert!(!final_members_live, "final managed Child lease drop left an exact process-group member live");'
    replacement = f'    assert!(final_members_live, "{DIAGNOSTIC}");'
    if text.count(anchor) != 1: raise RuntimeError('post-cleanup final-member assertion anchor is not unique')
    return text.replace(anchor, replacement, 1).encode()

def terminal(out, name, failed):
    if len(re.findall(r'(?m)^test '+re.escape(name)+r' \.\.\..*$', out)) != 1: raise RuntimeError(f'{name}: exact outer test prefix missing/duplicated')
    summaries = re.findall(r'(?m)^test result: .*?$', out)
    pattern = (r'test result: FAILED\. 0 passed; 1 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s' if failed
               else r'test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s')
    if not summaries or not re.fullmatch(pattern, summaries[-1]): raise RuntimeError(f'{name}: wrong final outer summary')
    if failed:
        parts = out.split('failures:', 1)
        names = [x.strip() for x in parts[-1].split('test result:', 1)[0].splitlines() if x.strip() and x.strip() != 'failures:']
        if names != [name]: raise RuntimeError(f'{name}: wrong outer failure list: {names!r}')

def parse_final_drop(text, label):
    early_pat = (r'(?m)^managed_final_drop_live reaper=(\d+) reaper_start=(\d+) host=(\d+) host_start=(\d+) '
      r'leader=(\d+) leader_start=(\d+) worker=(\d+) worker_start=(\d+) leaf=(\d+) leaf_start=(\d+) '
      r'group=(\d+) sentinel=(\d+) sentinel_start=(\d+) sentinel_pgid=(\d+)$')
    early = list(re.finditer(early_pat, text))
    if len(early) != 1: raise RuntimeError(f'{label}: exact early PID/start/group receipt missing or duplicated')
    r,rs,h,hs,l,ls,w,ws,f,fs,g,s,ss,sg = map(int, early[0].groups())
    facts = {'reaper':(r,rs),'host':(h,hs),'leader':(l,ls),'worker':(w,ws),'leaf':(f,fs),'sentinel':(s,ss),'group':g,'sentinel_group':sg}
    if len({r,h,l,w,f,s}) != 6 or g != l or sg != s: raise RuntimeError(f'{label}: distinct fixture PID/group ownership failed')
    rows = [tuple(map(int, m)) for m in re.findall(r'managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)', text)]
    expected = {l:(ls,h,g),w:(ws,l,g),f:(fs,w,g)}
    acquired = [row for row in rows if row[0] in expected]
    if len(acquired) != 3 or len({row[0] for row in acquired}) != 3: raise RuntimeError(f'{label}: expected three exact acquired PIDFD rows, got {acquired!r}')
    pidfds = {pid:(start,ppid,pgid) for pid,start,ppid,pgid in acquired}
    if pidfds != expected: raise RuntimeError(f'{label}: PIDFD identities/parent/group mismatch: {pidfds!r}')
    boundary_lines = re.findall(r'(?m)^managed_final_drop_boundary .*$', text)
    if len(boundary_lines) != 1: raise RuntimeError(f'{label}: final-drop boundary receipt missing/duplicated')
    line = boundary_lines[0]
    if ' api=' not in line or ' reaped=' not in line or ' cleanup=' not in line: raise RuntimeError(f'{label}: boundary lacks API/reaper/cleanup records')
    fields = dict(re.findall(r'([a-z_]+)=([^\s]+)', line.split(' api=',1)[0]))
    expected_numbers = {'leader':l,'leader_start':ls,'worker':w,'worker_start':ws,'leaf':f,'leaf_start':fs,'group':g}
    for key,value in expected_numbers.items():
        if fields.get(key) != str(value): raise RuntimeError(f'{label}: boundary {key} mismatch')
    true_fields = ('leader_record_start_matches_pidfd','worker_record_start_matches_pidfd','leaf_record_start_matches_pidfd',
      'worker_record_group_matches','leaf_record_group_matches','nonfinal_preserved','drop_return_recorded','closure_observed',
      'leader_absent','worker_absent','leaf_absent','exact_reaped','host_live_before_drop','reaper_live_before_drop',
      'sentinel_live_before_drop','host_live_through_closure','reaper_live_through_closure','sentinel_live_through_closure','exceptional_cleanup_not_started',
      'pidfds_exited','reaper_ok','host_absent_after_cleanup','sentinel_reaped','group_empty_after_closure')
    if any(fields.get(key) != 'true' for key in true_fields) or fields.get('final_members_live') != 'false':
        raise RuntimeError(f'{label}: final-drop lifecycle boundary invariants are incomplete: {fields!r}')
    if fields.get('reaper_status') != 'Some(ExitStatus(unix_wait_status(0)))': raise RuntimeError(f'{label}: reaper terminal status is not exact success')
    api = line.split(' api=',1)[1].split(' reaped=',1)[0]
    if f'host={h} host_start={hs} final_drop_returned=true nonfinal_wait_unit=true' not in api: raise RuntimeError(f'{label}: final-drop-return receipt not bound to host')
    reaped = line.split(' reaped="',1)[1].split('" cleanup=',1)[0]
    cleanup = line.split(' cleanup="',1)[1].rsplit('"',1)[0]
    for receipt in (reaped, cleanup):
        if f'worker={w} start={ws} pgid={g} reaped=true wait_status=' not in receipt or f'leaf={f} start={fs} pgid={g} reaped=true wait_status=' not in receipt or 'complete=true' not in receipt:
            raise RuntimeError(f'{label}: exact fixture worker/leaf wait receipts missing')
    if 'prompt=true host_status=0' not in cleanup or f'pid={r} ' not in cleanup: raise RuntimeError(f'{label}: reaper cleanup host/reaper binding mismatch')
    exact = {**{name:facts[name] for name in ('host','leader','worker','leaf','reaper','sentinel')}}
    identities=[]
    for name,(pid,start) in exact.items():
        try:
            raw=Path('/proc',str(pid),'stat').read_text(); proc=raw[raw.rfind(')')+2:].split(); alive=proc[19]==str(start)
        except FileNotFoundError: alive=False
        except (PermissionError,OSError,IndexError,ValueError) as exc: raise RuntimeError(f'{label}: exact post-cleanup identity readback unknown for {name}: {exc}')
        if alive: raise RuntimeError(f'{label}: owned identity remains after cleanup: {name}={pid}/{start}')
        identities.append({'label':name,'pid':pid,'start_ticks':start,'matching_identity_alive':False})
    groups={g,sg}
    ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
    members=[[int(row.split()[0]),int(row.split()[1])] for row in ps.splitlines() if len(row.split())==2 and int(row.split()[1]) in groups]
    if members: raise RuntimeError(f'{label}: managed/sentinel group remains after cleanup: {members!r}')
    BASE.write_json(BASE.STAGE/f'{label}-fixture-closure.json', {'identities':identities,'groups':sorted(groups),'group_members_after_cleanup':members,
      'pidfd_identities':[{'pid':pid,'start_ticks':v[0],'ppid':v[1],'pgid':v[2]} for pid,v in sorted(pidfds.items())]})
    return {'facts':facts,'pidfds':pidfds,'identities':exact}

def verify_control(out, err, label):
    terminal(out, TEST, True)
    if len(re.findall(r"(?m)^thread '"+re.escape(TEST)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err)) != 1 or err.count(DIAGNOSTIC) != 1:
        raise RuntimeError(f'{label}: did not reach the exact post-cleanup final-member control assertion')
    return parse_final_drop(err,label)

def run_final(cargo, env, label, features, expected, control=False):
    BASE.run_command(label,[str(cargo),'test','--locked','--features',features,'--test','sys_process','--','--exact','--nocapture','--test-threads=1',TEST],env,expected_status=expected)
    out=BASE.read_text(BASE.STAGE/f'{label}.stdout'); err=BASE.read_text(BASE.STAGE/f'{label}.stderr')
    result=verify_control(out,err,label) if control else (terminal(out,TEST,False),parse_final_drop(err,label))[1]
    return result

def main():
    global BASE,KILL,OLD
    stage=Path(os.environ['PROOF_STAGE']); runtime=Path(os.environ['AGENT_RUNTIME_DIR'])
    BASE=load(stage,'check-linux-current-msrv-examples.py',BASE_SHA,'accepted_base')
    KILL=load(stage,'linux-managed-kill-proof.py',KILL_PROOF_SHA,'accepted_kill'); KILL.BASE=BASE
    OLD=load(stage,'linux-managed-success-proof.py',SUCCESS_PROOF_SHA,'accepted_success')
    KILL.install_bounded_du_retry(BASE)
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
    for path in (BASE.CARGO_HOME,BASE.RUSTUP_HOME,BASE.PRIVATE_HOME): path.mkdir(mode=0o700)
    BASE.PRIVATE_TMP.mkdir(mode=0o700,exist_ok=True)
    env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(BASE.PRIVATE_HOME),'TMPDIR':str(BASE.PRIVATE_TMP),'TMP':str(BASE.PRIVATE_TMP),'TEMP':str(BASE.PRIVATE_TMP),'CARGO_HOME':str(BASE.CARGO_HOME),'RUSTUP_HOME':str(BASE.RUSTUP_HOME),'CARGO_TARGET_DIR':str(BASE.TARGET),'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_PROFILE_DEV_DEBUG':'0','CARGO_TERM_COLOR':'never','RUST_BACKTRACE':'0','AGENT_RUNTIME_DIR':str(runtime)}
    BASE.run_command('rustup-install',[str(BASE.RUSTUP),'toolchain','install',BASE.TOOLCHAIN,'--profile','minimal','--no-self-update'],env,cwd=runtime)
    bindir=BASE.RUSTUP_HOME/'toolchains'/BASE.TOOLCHAIN/'bin'; rustc=bindir/'rustc'; cargo=bindir/'cargo'
    if not rustc.is_file() or not cargo.is_file(): raise RuntimeError('private toolchain incomplete')
    env.update(PATH=f'{bindir}:/usr/bin:/bin:/usr/sbin:/sbin',RUSTC=str(rustc))
    BASE.run_command('rustc-version',[str(rustc),'--version','--verbose'],env); BASE.run_command('cargo-version',[str(cargo),'--version','--verbose'],env)
    injected=overlay(original); test.write_bytes(injected); BASE.INJECTED_EXAMPLE_HASHES[CONTROL]=sha(test)
    run_final(cargo,env,CONTROL,ROWS[0],101,True)
    BASE.verify_control(CONTROL,101,101,BASE.read_text(BASE.STAGE/f'{CONTROL}.stderr'),[DIAGNOSTIC])
    test.write_bytes(original)
    if sha(test)!=TEST_SHA: raise RuntimeError('exact source restoration after wrong-control failed')
    for label,name,check in (('native101-kill-regression-row1',KILL_TEST,'kill'),('native101-success-regression-row1',SUCCESS_TEST,'success'),('native101-held-regression-row1',HELD_TEST,'held')):
        BASE.run_command(label,[str(cargo),'test','--locked','--features',ROWS[0],'--test','sys_process','--','--exact','--nocapture','--test-threads=1',name],env)
        out=BASE.read_text(BASE.STAGE/f'{label}.stdout'); err=BASE.read_text(BASE.STAGE/f'{label}.stderr'); terminal(out,name,False); text=out+err
        if check=='kill': KILL.boundary(err,label)
        elif check=='success': OLD.require_success(text); OLD.identity_closure(text,'final-drop-'+label,BASE,label)
        else: OLD.require_held(text,BASE,label)
    for index,features in enumerate(ROWS,1): run_final(cargo,env,f'green-row-{index}',features,0)
    if sha(test)!=TEST_SHA or BASE.manifest_hashes()!=manifest or sha(BASE.SOURCE/'Cargo.lock')!=LOCK: raise RuntimeError('source/manifests/lock restoration mismatch')
    BASE.write_json(BASE.STAGE/'package-result.json',{'source_revision':REV,'test_sha256':TEST_SHA,'test':TEST,'feature_rows':list(ROWS),'wrong_controls':[CONTROL],'green_rows':4,'base_regressions':[KILL_TEST,SUCCESS_TEST,HELD_TEST],'source_restored':True,'acceptance_claim':False,'limitations':['No no_float/no_index feature row is included; full native acceptance and remote custody require collector readback.']})
    return 0

def export():
    if BASE is None or not BASE.STAGE.is_dir() or BASE.EVIDENCE.exists(): return
    error=None
    try:
        if BASE.ORIGINAL_EXAMPLES: BASE.restore_example_sources()
    except BaseException:
        error=traceback.format_exc(); (BASE.STAGE/'restoration-failure.txt').write_text(error)
    BASE.write_json(BASE.STAGE/'source-restoration.json',{'original_sha256':BASE.ORIGINAL_EXAMPLE_HASHES,'overlay_sha256':BASE.INJECTED_EXAMPLE_HASHES,'restored':bool(BASE.ORIGINAL_EXAMPLES) and all(sha(path)==BASE.ORIGINAL_EXAMPLE_HASHES[path.relative_to(BASE.SOURCE).as_posix()] for path in BASE.ORIGINAL_EXAMPLES),'error':error})
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
