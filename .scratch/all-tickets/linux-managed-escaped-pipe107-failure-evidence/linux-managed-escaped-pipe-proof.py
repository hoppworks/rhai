#!/usr/bin/env python3
"""Bounded Rust 1.77.2 proof for escaped-pipe deadline closure."""
from __future__ import annotations
import ast, errno, hashlib, importlib.util, json, os, platform, re, shutil, signal, subprocess, sys, time, traceback
from pathlib import Path

REV = '523608648dcae99bc0f6b46eaf2bb91fa4ecc752'
ARCHIVE = '998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
BASE_SHA = '59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06'
TEST_SHA = '5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb'
CONTRACT_SHA = '0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68'
SUCCESS_PROOF_SHA = '83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0'
TEST = 'managed_run_deadline_cancels_escaped_pipe_holder_under_fixture_reaper'
SUCCESS_TEST = 'managed_run_succeeds_after_fixture_reaper_reaps_descendants'
HELD_TEST = 'managed_run_reports_while_fixture_reaper_holds_stopped_zombies'
ROWS = ('testing-environ,sys', 'testing-environ,sys,sync,metadata', 'testing-environ,sys,f32_float', 'testing-environ,sys,unchecked')
RETAINED_TEST = 'managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes'
CONTROL = 'require-escaped-holder-control'
DIAGNOSTIC = 'managed-escaped-pipe-control require-timeout-report assertion'
STAGE_PATH = Path('/root/rhai-linux-managed-escaped-pipe-20261003-52360864-107')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/linux-managed-escaped-pipe-20261003-52360864-107')
BASE = OLD = None

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def load(stage, name, expected, module_name):
    path = stage / name
    if sha(path) != expected: raise RuntimeError(f'{name} hash mismatch')
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    return module

def overlay(original):
    text = original.decode()
    anchor = '    assert!(timeout_report && partial_capture, "managed run must return its bounded deadline report with partial incomplete captures: {api_result}");'
    replacement = f'    assert!(!timeout_report, "{DIAGNOSTIC}");'
    if text.count(anchor) != 1: raise RuntimeError('post-cleanup deadline assertion anchor is not unique')
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

def parse_escaped_pipe(text, label):
    # `boundary` is a Rust String ending in a real newline. The following API,
    # challenge, and cleanup fields therefore begin on the next physical line.
    records = re.findall(r'(?m)^managed_deadline_escaped_pipe_boundary ([^\n]*)\n (api=.*)$', text)
    if len(records) != 1: raise RuntimeError(f'{label}: exact escaped-pipe boundary missing/duplicated')
    record = records[0][0] + ' ' + records[0][1]
    try:
        boundary, rest = record.split(' api=', 1)
        api_literal, rest = rest.split(' challenge=', 1)
        challenge_literal, rest = rest.split(' no_watchdog_through_challenge=', 1)
        through, rest = rest.split(' holder_reap=', 1)
        reap_literal, rest = rest.split(' reaper_cleanup=', 1)
        cleanup_literal, tail = rest.rsplit(' reaper_ok=', 1)
        reaper_ok, tail = tail.split(' host_absent=', 1)
        host_absent, tail = tail.split(' host_absence=', 1)
        host_absence, tail = tail.split(' leader_absent=', 1)
        leader_absent, tail = tail.split(' leader_absence=', 1)
        leader_absence, tail = tail.split(' holder_absent=', 1)
        holder_absent, tail = tail.split(' holder_absence=', 1)
        holder_absence, tail = tail.split(' sentinel_absent=', 1)
        sentinel_absent, tail = tail.split(' sentinel_absence=', 1)
        sentinel_absence, tail = tail.split(' sentinel_group_probe=', 1)
        sentinel_probe, sentinel_errno = tail.split(' sentinel_group_errno=', 1)
        api_part, challenge = map(ast.literal_eval, (api_literal, challenge_literal))
        holder_reap = ast.literal_eval(reap_literal)
        cleanup = ast.literal_eval(cleanup_literal)
    except (ValueError, SyntaxError) as exc: raise RuntimeError(f'{label}: malformed escaped-pipe boundary/API/challenge/reaper receipt') from exc
    fields = dict(re.findall(r'([a-z_]+)=([^\s]+)', boundary))
    required = ('host','host_start','reaper','reaper_start','leader','leader_start','leader_live','leader_pidfd_exited','managed_group','group_probe','group_errno','holder','holder_start','holder_group','holder_live','holder_pidfd_live','sentinel','sentinel_start','sentinel_group','sentinel_live','timeout_report','partial_capture','no_watchdog')
    if any(key not in fields for key in required): raise RuntimeError(f'{label}: missing escaped-pipe fields: {fields!r}')
    nums = {key:int(fields[key]) for key in ('host','host_start','reaper','reaper_start','leader','leader_start','managed_group','group_probe','group_errno','holder','holder_start','holder_group','sentinel','sentinel_start','sentinel_group')}
    if len({nums[k] for k in ('host','reaper','leader','holder','sentinel')}) != 5 or nums['managed_group'] != nums['leader'] or nums['holder_group'] != nums['sentinel_group'] or nums['holder_group'] == nums['managed_group']:
        raise RuntimeError(f'{label}: fixture PID/group identities are not distinct and bound')
    for key in ('leader_pidfd_exited','holder_live','holder_pidfd_live','host_live','reaper_live','sentinel_live','timeout_report','partial_capture','no_watchdog'):
        if fields[key] != 'true': raise RuntimeError(f'{label}: escaped-pipe boundary {key}={fields[key]}')
    if fields['leader_live'] != 'false' or fields['group_probe'] != '-1' or fields['group_errno'] != '3': raise RuntimeError(f'{label}: managed group was not closed at API return')
    if through != 'true' or reaper_ok != 'true' or any(x != 'true' for x in (host_absent,leader_absent,holder_absent,sentinel_absent)) or sentinel_probe != '-1' or sentinel_errno != '3':
        raise RuntimeError(f'{label}: watchdog/reaper/exact cleanup receipts failed')
    for name, raw, expected_start in (('host',host_absence,nums['host_start']),('leader',leader_absence,nums['leader_start']),('holder',holder_absence,nums['holder_start']),('sentinel',sentinel_absence,nums['sentinel_start'])):
        try: absence=ast.literal_eval(raw)
        except (ValueError,SyntaxError) as exc: raise RuntimeError(f'{label}: malformed {name} absence receipt') from exc
        reused=re.fullmatch(r'PID reused at start=(\d+)',absence)
        if absence!='not found' and (not reused or int(reused.group(1))==expected_start):
            raise RuntimeError(f'{label}: {name} absence receipt does not prove exact PID/start closure: {absence!r}')
    api = ' '.join(api_part.split())
    for token in (f'host={nums["host"]} host_start={nums["host_start"]}', 'api_success=true api_outcome=timeout_report success=Some(false) timed_out=Some(true)', 'stdout_complete=Some(false) stderr_complete=Some(false) stdout_marker=true stderr_marker=true'):
        if token not in api: raise RuntimeError(f'{label}: API result missing {token!r}')
    if 'api_success=false' in api or 'observe_process_group_closure' in api: raise RuntimeError(f'{label}: error result substituted for timeout report')
    challenge_text = challenge
    for token in (f'pid={nums["holder"]}', f'stdout_result=-1', f'stdout_error={errno.EPIPE}', f'stderr_result=-1', f'stderr_error={errno.EPIPE}'):
        if token not in challenge_text: raise RuntimeError(f'{label}: escaped-holder EPIPE challenge missing {token!r}')
    if not re.search(rf'holder={nums["holder"]} start={nums["holder_start"]} pgid={nums["holder_group"]} reaped=true wait_status=\d+', holder_reap):
        raise RuntimeError(f'{label}: exact escaped holder wait receipt missing: {holder_reap!r}')
    for token in (f'pid={nums["reaper"]} start={nums["reaper_start"]} host_status=0 complete=true', f'holder={nums["holder"]} start={nums["holder_start"]} pgid={nums["holder_group"]} reaped=true wait_status='):
        if token not in cleanup: raise RuntimeError(f'{label}: exact reaper cleanup missing {token!r}')
    pidrows=[tuple(map(int,m)) for m in re.findall(r'managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)',text)]
    expected={nums['leader']:(nums['leader_start'],nums['host'],nums['managed_group']),nums['holder']:(nums['holder_start'],nums['leader'],nums['holder_group'])}
    selected=[row for row in pidrows if row[0] in expected]; actual={pid:(start,parent,group) for pid,start,parent,group in selected}
    if len(selected)!=2 or len(actual)!=2 or actual!=expected: raise RuntimeError(f'{label}: exact leader/holder PIDFD identity mismatch: {actual!r}')
    identities=[]; owned={k:(nums[k],nums[k+'_start']) for k in ('host','reaper','leader','holder','sentinel')}
    for name,(pid,start) in owned.items():
        try:
            raw=Path('/proc',str(pid),'stat').read_text(); proc=raw[raw.rfind(')')+2:].split(); alive=proc[19]==str(start)
        except FileNotFoundError: alive=False
        except (PermissionError,OSError,IndexError,ValueError) as exc: raise RuntimeError(f'{label}: exact post-cleanup identity unknown for {name}: {exc}')
        if alive: raise RuntimeError(f'{label}: owned identity remains after cleanup: {name}={pid}/{start}')
        identities.append({'label':name,'pid':pid,'start_ticks':start,'matching_identity_alive':False})
    groups={nums['managed_group'],nums['holder_group']}
    ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
    members=[[int(row.split()[0]),int(row.split()[1])] for row in ps.splitlines() if len(row.split())==2 and int(row.split()[1]) in groups]
    if members: raise RuntimeError(f'{label}: managed/escaped/sentinel group remains: {members!r}')
    BASE.write_json(BASE.STAGE/f'{label}-fixture-closure.json',{'identities':identities,'groups':sorted(groups),'group_members_after_cleanup':members,'pidfd_identities':[{'pid':pid,'start_ticks':v[0],'ppid':v[1],'pgid':v[2]} for pid,v in sorted(actual.items())]})
    return {'fields':fields,'pidfds':actual,'identities':owned}

def verify_control(out, err, label):
    terminal(out, TEST, True)
    if len(re.findall(r"(?m)^thread '"+re.escape(TEST)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err)) != 1 or err.count(DIAGNOSTIC) != 1:
        raise RuntimeError(f'{label}: did not reach the exact post-cleanup timeout-report control assertion')
    return parse_escaped_pipe(err,label)

def run_final(cargo, env, label, features, expected, control=False):
    BASE.run_command(label,[str(cargo),'test','--locked','--features',features,'--test','sys_process','--','--exact','--nocapture','--test-threads=1',TEST],env,expected_status=expected)
    out=BASE.read_text(BASE.STAGE/f'{label}.stdout'); err=BASE.read_text(BASE.STAGE/f'{label}.stderr')
    result=verify_control(out,err,label) if control else (terminal(out,TEST,False),parse_escaped_pipe(err,label))[1]
    return result

def main():
    global BASE,OLD
    stage=Path(os.environ['PROOF_STAGE']); runtime=Path(os.environ['AGENT_RUNTIME_DIR'])
    BASE=load(stage,'check-linux-current-msrv-examples.py',BASE_SHA,'accepted_base')
    OLD=load(stage,'linux-managed-success-proof.py',SUCCESS_PROOF_SHA,'accepted_success')
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
    for label,name,check in (('base-prompt-regression-row1',SUCCESS_TEST,'success'),('base-held-regression-row1',HELD_TEST,'held'),('base-retained-pipe-regression-row1',RETAINED_TEST,'retained')):
        BASE.run_command(label,[str(cargo),'test','--locked','--features',ROWS[0],'--test','sys_process','--','--exact','--nocapture','--test-threads=1',name],env)
        out=BASE.read_text(BASE.STAGE/f'{label}.stdout'); err=BASE.read_text(BASE.STAGE/f'{label}.stderr'); terminal(out,name,False); text=out+err
        if check=='success': OLD.require_success(text); OLD.identity_closure(text,'escaped-pipe-'+label,BASE,label)
        elif check=='held': OLD.require_held(text,BASE,'escaped-pipe-'+label)
        elif check=='retained':
            retained=out+err
            for token in ('managed_escaped_pipe_wait ', 'leader_esrch=true', 'holder_live_after_wait=true', 'sentinel_live_after_wait=true', 'identity_ok=true', 'wait_unit=true', 'stdout_error=32', 'stderr_error=32', 'managed_escaped_pipe_terminal ', 'holder_esrch=true', 'sentinel_esrch=true'):
                if token not in retained: raise RuntimeError(f'{label}: retained-pipe regression receipt missing {token!r}')
    for index,features in enumerate(ROWS,1): run_final(cargo,env,f'green-row-{index}',features,0)
    if sha(test)!=TEST_SHA or BASE.manifest_hashes()!=manifest or sha(BASE.SOURCE/'Cargo.lock')!=LOCK: raise RuntimeError('source/manifests/lock restoration mismatch')
    BASE.write_json(BASE.STAGE/'package-result.json',{'source_revision':REV,'test_sha256':TEST_SHA,'test':TEST,'feature_rows':list(ROWS),'wrong_controls':[CONTROL],'green_rows':4,'base_regressions':[SUCCESS_TEST,HELD_TEST,RETAINED_TEST],'source_restored':True,'acceptance_claim':False,'limitations':['No no_float/no_index feature row is included; full native acceptance and remote custody require collector readback.']})
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
