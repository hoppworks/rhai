#!/usr/bin/env python3
"""Bounded Rust 1.77.2 proof for managed run deadline closure."""
from __future__ import annotations
import ast, hashlib, importlib.util, json, os, platform, re, shutil, signal, subprocess, sys, time, traceback
from pathlib import Path

REV = 'b5243017a5ff2926c12c13e6108a2064091e843b'
ARCHIVE = '6b473336359a770f359e3153ee3c467b3710f0b7621b10eee25849511e414b8a'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
BASE_SHA = '59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06'
TEST_SHA = 'de4cfc16a54b1cb5e0ef38337887c54d18a433114f3e7662a567d914f8918309'
CONTRACT_SHA = '0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68'
SUCCESS_PROOF_SHA = '83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0'
TEST = 'managed_run_deadline_reaps_group_under_fixture_reaper'
KILL_TEST = ''
SUCCESS_TEST = 'managed_run_succeeds_after_fixture_reaper_reaps_descendants'
HELD_TEST = 'managed_run_reports_while_fixture_reaper_holds_stopped_zombies'
ROWS = ('testing-environ,sys', 'testing-environ,sys,sync,metadata', 'testing-environ,sys,f32_float', 'testing-environ,sys,unchecked')
CONTROL = 'require-timeout-control'
DIAGNOSTIC = 'managed-deadline-control require-timeout assertion'
STAGE_PATH = Path('/root/rhai-linux-managed-deadline-20261003-bcecd9eb-103')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/linux-managed-deadline-20261003-bcecd9eb-103')
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
    anchor = '    assert!(api_is_timed_out, "managed public run did not return its deadline report after exact group closure: {api_result}");'
    replacement = f'    assert!(!api_is_timed_out, "{DIAGNOSTIC}");'
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

def parse_deadline(text, label):
    lines = re.findall(r'(?m)^managed_deadline_group_boundary ([^\n]*)\n([ \t]+api=.*)$', text)
    if len(lines) != 1: raise RuntimeError(f'{label}: exact deadline boundary missing/duplicated')
    line, continuation = lines[0]
    try:
        api_literal, remainder = continuation.strip().removeprefix('api=').split(' cleanup=', 1)
        cleanup_literal, tail = remainder.rsplit(' reaper_ok=', 1)
        reaper_ok, tail = tail.split(' sentinel_reaped=', 1)
        sentinel_reaped, no_watchdog_after = tail.split(' no_watchdog_cleanup_after_reap=', 1)
        api_part = ast.literal_eval(api_literal)
        cleanup = ast.literal_eval(cleanup_literal)
    except (ValueError, SyntaxError) as exc: raise RuntimeError(f'{label}: malformed multiline boundary/API/cleanup receipt') from exc
    fields = dict(re.findall(r'([a-z_]+)=([^\s]+)', line))
    required = ('host','host_start','reaper','reaper_start','leader','leader_start','leader_absent','worker','worker_start','worker_absent','leaf','leaf_start','leaf_absent','group','group_probe','group_errno','host_live','reaper_live','sentinel','sentinel_start','sentinel_live','timed_out','captures_incomplete','partial_output','pidfds_exited','cleanup_exact','no_watchdog_cleanup_through_boundary')
    if any(key not in fields for key in required): raise RuntimeError(f'{label}: missing deadline fields: {fields!r}')
    nums = {key:int(fields[key]) for key in ('host','host_start','reaper','reaper_start','leader','leader_start','worker','worker_start','leaf','leaf_start','group','sentinel','sentinel_start','group_probe','group_errno')}
    if len({nums[k] for k in ('host','reaper','leader','worker','leaf','sentinel')}) != 6 or nums['group'] != nums['leader']:
        raise RuntimeError(f'{label}: fixture PID/group identities are not distinct and bound')
    for key in ('leader_absent','worker_absent','leaf_absent','host_live','reaper_live','sentinel_live','timed_out','captures_incomplete','partial_output','pidfds_exited','cleanup_exact','no_watchdog_cleanup_through_boundary'):
        if fields[key] != 'true': raise RuntimeError(f'{label}: deadline boundary {key}={fields[key]}')
    if nums['group_probe'] != -1 or nums['group_errno'] != 3: raise RuntimeError(f'{label}: original process group not absent at deadline return')
    pidrows = [tuple(map(int, m)) for m in re.findall(r'managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)', text)]
    expected = {nums['leader']:(nums['leader_start'],nums['host'],nums['group']), nums['worker']:(nums['worker_start'],nums['leader'],nums['group']), nums['leaf']:(nums['leaf_start'],nums['worker'],nums['group'])}
    selected = [row for row in pidrows if row[0] in expected]
    actual = {pid:(start,parent,group) for pid,start,parent,group in selected}
    if len(selected)!=3 or len(actual)!=3 or actual!=expected: raise RuntimeError(f'{label}: exact PIDFD parent/start/group identities mismatch: {actual!r}')
    for token in (f'host={nums["host"]} host_start={nums["host_start"]}', 'api_success=true api_outcome=timeout_report success=Some(false) timed_out=Some(true)', 'stdout_complete=Some(false) stderr_complete=Some(false)', 'stdout_marker=true stderr_marker=true'):
        if token not in api_part: raise RuntimeError(f'{label}: timeout API receipt missing {token!r}')
    if 'api_success=false' in api_part or 'typed_timeout_error' in api_part or 'observe_process_group_closure' in api_part: raise RuntimeError(f'{label}: run ended in error/closure diagnostic instead of timeout report')
    if reaper_ok != 'true' or sentinel_reaped != 'true' or no_watchdog_after != 'true': raise RuntimeError(f'{label}: exact reaper/sentinel cleanup or watchdog exclusion did not succeed')
    for pid,start,name in ((nums['worker'],nums['worker_start'],'worker'),(nums['leaf'],nums['leaf_start'],'leaf')):
        if not re.search(rf'{name}={pid} start={start} pgid={nums["group"]} reaped=true wait_status=\d+(?:\s|$)', cleanup): raise RuntimeError(f'{label}: exact {name} wait receipt missing')
    if 'complete=true' not in cleanup:
        raise RuntimeError(f'{label}: exact prompt-reaper cleanup receipt incomplete')
    identities=[]; owned={key:(nums[key],nums[key+'_start']) for key in ('host','reaper','leader','worker','leaf','sentinel')}
    for name,(pid,start) in owned.items():
        try:
            raw=Path('/proc',str(pid),'stat').read_text(); proc=raw[raw.rfind(')')+2:].split(); alive=proc[19]==str(start)
        except FileNotFoundError: alive=False
        except (PermissionError,OSError,IndexError,ValueError) as exc: raise RuntimeError(f'{label}: exact post-cleanup identity readback unknown for {name}: {exc}')
        if alive: raise RuntimeError(f'{label}: owned identity remains after cleanup: {name}={pid}/{start}')
        identities.append({'label':name,'pid':pid,'start_ticks':start,'matching_identity_alive':False})
    groups={nums['group']}
    ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
    members=[[int(row.split()[0]),int(row.split()[1])] for row in ps.splitlines() if len(row.split())==2 and int(row.split()[1]) in groups]
    if members: raise RuntimeError(f'{label}: managed/sentinel group remains after cleanup: {members!r}')
    BASE.write_json(BASE.STAGE/f'{label}-fixture-closure.json', {'identities':identities,'groups':sorted(groups),'group_members_after_cleanup':members,'pidfd_identities':[{'pid':pid,'start_ticks':v[0],'ppid':v[1],'pgid':v[2]} for pid,v in sorted(actual.items())]})
    return {'fields':fields,'pidfds':actual,'identities':owned}

def verify_control(out, err, label):
    terminal(out, TEST, True)
    if len(re.findall(r"(?m)^thread '"+re.escape(TEST)+r"' panicked at tests/sys_process\.rs:\d+:\d+:$",err)) != 1 or err.count(DIAGNOSTIC) != 1:
        raise RuntimeError(f'{label}: did not reach the exact post-cleanup timeout-report control assertion')
    return parse_deadline(err,label)

def run_final(cargo, env, label, features, expected, control=False):
    BASE.run_command(label,[str(cargo),'test','--locked','--features',features,'--test','sys_process','--','--exact','--nocapture','--test-threads=1',TEST],env,expected_status=expected)
    out=BASE.read_text(BASE.STAGE/f'{label}.stdout'); err=BASE.read_text(BASE.STAGE/f'{label}.stderr')
    result=verify_control(out,err,label) if control else (terminal(out,TEST,False),parse_deadline(err,label))[1]
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
    for label,name,check in (('base-prompt-regression-row1',SUCCESS_TEST,'success'),('base-held-regression-row1',HELD_TEST,'held')):
        BASE.run_command(label,[str(cargo),'test','--locked','--features',ROWS[0],'--test','sys_process','--','--exact','--nocapture','--test-threads=1',name],env)
        out=BASE.read_text(BASE.STAGE/f'{label}.stdout'); err=BASE.read_text(BASE.STAGE/f'{label}.stderr'); terminal(out,name,False); text=out+err
        if check=='success': OLD.require_success(text); OLD.identity_closure(text,'deadline-'+label,BASE,label)
        elif check=='held': OLD.require_held(text,BASE,'deadline-'+label)
    for index,features in enumerate(ROWS,1): run_final(cargo,env,f'green-row-{index}',features,0)
    if sha(test)!=TEST_SHA or BASE.manifest_hashes()!=manifest or sha(BASE.SOURCE/'Cargo.lock')!=LOCK: raise RuntimeError('source/manifests/lock restoration mismatch')
    BASE.write_json(BASE.STAGE/'package-result.json',{'source_revision':REV,'test_sha256':TEST_SHA,'test':TEST,'feature_rows':list(ROWS),'wrong_controls':[CONTROL],'green_rows':4,'base_regressions':[SUCCESS_TEST,HELD_TEST],'source_restored':True,'acceptance_claim':False,'limitations':['No no_float/no_index feature row is included; full native acceptance and remote custody require collector readback.']})
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
