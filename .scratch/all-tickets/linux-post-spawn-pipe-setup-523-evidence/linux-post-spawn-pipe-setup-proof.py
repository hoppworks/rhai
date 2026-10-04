#!/usr/bin/env python3
"""Bounded Linux public-Engine proof for post-spawn pipe setup failure."""
from __future__ import annotations
import hashlib, importlib.util, json, os, platform, shutil, signal, subprocess, sys, tarfile, time, traceback
from pathlib import Path

REV='523608648dcae99bc0f6b46eaf2bb91fa4ecc752'
ARCHIVE='998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b'
LOCK='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
BASE_HELPER='c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9'
TEST='1b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a'
CONTRACT='ff4c5ed27bbdb55ef2ad66c28cddc31a1e624726cb7ec3f98078bc49cfc81b9d'
STAGE_PATH=Path('/root/rhai-linux-post-spawn-pipe-setup-523-20261004')
SCOPE_PATH=Path('/root/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004')
TEST_NAME='packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child'
CAUSE='primary cause must remain configure-pipe Io'
REPORT='setup failure must not fabricate EOF or timeout completion'
BASE=None


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path: Path,name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError('cannot load pinned helper '+str(path))
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def test_receipts(stdout: str) -> list[str]:
    inner=[line for line in stdout.splitlines() if line.startswith('setup-failure child_pid=')]
    outer=[line for line in stdout.splitlines() if line.startswith('setup-failure fixture child_pid=')]
    if len(inner)!=1 or len(outer)!=1 or 'reap=ESRCH owner_retired=true' not in inner[0] or 'reap=ESRCH' not in outer[0]:
        raise RuntimeError('required inner and outer post-reap receipts are missing or ambiguous')
    if stdout.index(inner[0])>=stdout.index(outer[0]): raise RuntimeError('outer receipt preceded inner reaping receipt')
    return [inner[0],outer[0]]

def run_case(label: str,cargo: Path,env: dict[str,str],*,expected: int,diagnostic: str|None=None):
    argv=[str(cargo),'test','--locked','--lib','--features','testing-environ,sys',TEST_NAME,'--','--exact','--nocapture','--test-threads=1']
    status=BASE.run_command(label,argv,env,expected_status=expected)
    stdout=BASE.read_text(BASE.STAGE/(label+'.stdout'));stderr=BASE.read_text(BASE.STAGE/(label+'.stderr'))
    receipts=test_receipts(stdout)
    if diagnostic:
        if diagnostic not in stderr or f"thread '{TEST_NAME}' panicked at src/packages/sys/process/unix.rs:" not in stderr:
            raise RuntimeError(label+' did not fail at exact named assertion '+diagnostic)
        BASE.verify_control(label,status,expected,stderr,[diagnostic],stdout=stdout,required_output=receipts)
    else:
        if status!=0 or 'test result: ok. 1 passed; 0 failed;' not in stdout:
            raise RuntimeError('restored baseline test did not pass exactly once')
        BASE.verify_pass(label,status,stdout,['test '+TEST_NAME+' ... ok',*receipts])

def mutate_once(path: Path,anchor: str,replacement: str,label: str):
    original=path.read_bytes();text=original.decode('utf-8')
    if text.count(anchor)!=1: raise RuntimeError(label+' source anchor is not unique')
    changed=text.replace(anchor,replacement,1).encode('utf-8')
    path.write_bytes(changed);BASE.ORIGINAL_EXAMPLES[path]=original
    rel=path.relative_to(BASE.SOURCE).as_posix();BASE.ORIGINAL_EXAMPLE_HASHES[rel]=hashlib.sha256(original).hexdigest()
    BASE.INJECTED_EXAMPLE_HASHES[label]=hashlib.sha256(changed).hexdigest()
    return original,changed

def main() -> int:
    global BASE
    stage=Path(os.environ['PROOF_STAGE']);runtime=Path(os.environ['AGENT_RUNTIME_DIR'])
    BASE=load(stage/'check-linux-current-msrv-examples.py','pipe_setup_accepted_base')
    BASE.INPUT_STAGE=stage;BASE.EXPECTED_STAGE=Path(os.environ['EXPECTED_PROOF_STAGE'])
    BASE.PRESCRIBED_STAGE=STAGE_PATH;BASE.PRESCRIBED_SCOPE=SCOPE_PATH;BASE.RUNTIME=runtime
    BASE.STAGE=runtime/'evidence';BASE.EVIDENCE=BASE.EXPECTED_STAGE/'proof-evidence'
    BASE.CONTRACT=stage/'contract.md';BASE.SOURCE_ARCHIVE=stage/'source.tar';BASE.LOCK_SOURCE=stage/'Cargo.lock.accepted'
    BASE.RUSTUP=Path(os.environ['RUSTUP_BIN']);BASE.SOURCE_ARCHIVE_SHA256=ARCHIVE;BASE.LOCK_SHA256=LOCK
    BASE.REVISION=REV;BASE.TOOLCHAIN='1.77.2-x86_64-unknown-linux-gnu';BASE.FEATURES='testing-environ,sys'
    BASE.SOURCE=runtime/'source';BASE.CARGO_HOME=runtime/'cargo-home';BASE.RUSTUP_HOME=runtime/'rustup-home'
    BASE.TARGET=runtime/'target';BASE.PRIVATE_HOME=runtime/'home';BASE.PRIVATE_TMP=Path(os.environ['TMPDIR'])
    signal.signal(signal.SIGTERM,BASE.on_signal);signal.signal(signal.SIGINT,BASE.on_signal)
    BASE.capture_runtime_proof();BASE.validate_stage_inputs()
    if platform.system()!='Linux' or platform.machine().lower() not in ('x86_64','amd64'): raise RuntimeError('native Linux x86_64 required')
    for name,digest in [('check-linux-current-msrv-examples.py',BASE_HELPER),('contract.md',CONTRACT)]:
        if sha(stage/name)!=digest: raise RuntimeError(name+' input hash mismatch')
    if sha(BASE.SOURCE_ARCHIVE)!=ARCHIVE or sha(BASE.LOCK_SOURCE)!=LOCK: raise RuntimeError('frozen source or accepted lock mismatch')
    shutil.copy2(Path(__file__),BASE.STAGE/'helper-used.py');shutil.copy2(BASE.CONTRACT,BASE.STAGE/'contract.md')
    for path in (BASE.CARGO_HOME,BASE.RUSTUP_HOME,BASE.PRIVATE_HOME,BASE.PRIVATE_TMP): path.mkdir(mode=0o700,parents=True,exist_ok=True)
    env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(BASE.PRIVATE_HOME),'TMPDIR':str(BASE.PRIVATE_TMP),'TMP':str(BASE.PRIVATE_TMP),'TEMP':str(BASE.PRIVATE_TMP),
      'CARGO_HOME':str(BASE.CARGO_HOME),'RUSTUP_HOME':str(BASE.RUSTUP_HOME),'CARGO_TARGET_DIR':str(BASE.TARGET),'CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_PROFILE_DEV_DEBUG':'0','CARGO_TERM_COLOR':'never','RUST_BACKTRACE':'0'}
    BASE.run_command('rustup-install',[str(BASE.RUSTUP),'toolchain','install',BASE.TOOLCHAIN,'--profile','minimal','--no-self-update'],env,cwd=runtime)
    bindir=BASE.RUSTUP_HOME/'toolchains'/BASE.TOOLCHAIN/'bin';rustc=bindir/'rustc';cargo=bindir/'cargo'
    if not rustc.is_file() or not cargo.is_file(): raise RuntimeError('private Rust 1.77.2 toolchain is incomplete')
    env.update(PATH=f'{bindir}:/usr/bin:/bin:/usr/sbin:/sbin',RUSTC=str(rustc))
    BASE.run_command('rustc-version',[str(rustc),'--version','--verbose'],env,cwd=runtime);BASE.run_command('cargo-version',[str(cargo),'--version','--verbose'],env,cwd=runtime)
    rustc_text=BASE.read_text(BASE.STAGE/'rustc-version.stdout');cargo_text=BASE.read_text(BASE.STAGE/'cargo-version.stdout')
    if not rustc_text.startswith('rustc 1.77.2 ') or 'host: x86_64-unknown-linux-gnu' not in rustc_text or not cargo_text.startswith('cargo 1.77.2 '): raise RuntimeError('direct private compiler/tool versions mismatch')
    archive_copy=runtime/'source-input.tar';shutil.copy2(BASE.SOURCE_ARCHIVE,archive_copy);BASE.extract_archive(archive_copy);archive_copy.unlink()
    test=BASE.SOURCE/'src/packages/sys/process/unix.rs';original=test.read_bytes()
    if sha(test)!=TEST: raise RuntimeError('baseline unix.rs bytes do not match frozen test hash')
    BASE.ORIGINAL_EXAMPLES[test]=original;BASE.ORIGINAL_EXAMPLE_HASHES['src/packages/sys/process/unix.rs']=TEST
    manifest=BASE.manifest_hashes();BASE.CARGO_MANIFESTS=manifest;shutil.copy2(BASE.LOCK_SOURCE,BASE.SOURCE/'Cargo.lock')
    if sha(BASE.SOURCE/'Cargo.lock')!=LOCK: raise RuntimeError('private compatible lock hash mismatch')
    BASE.write_json(BASE.STAGE/'source-inputs.json',{'revision':REV,'archive_sha256':ARCHIVE,'test_source_sha256':TEST,'cargo_lock_sha256':LOCK,'base_helper_sha256':BASE_HELPER,'cargo_manifests_sha256':manifest,'test_name':TEST_NAME,'features':'testing-environ,sys'})
    # Wrong cause only: inner reap precedes the inner assertion; outer reap precedes the wrapper status assertion.
    original,changed=mutate_once(test,'message == "injected post-spawn pipe configuration failure"','message == "wrong configure pipe message"','wrong-cause-red')
    run_case('wrong-cause-red',cargo,env,expected=101,diagnostic=CAUSE)
    test.write_bytes(original)
    if sha(test)!=TEST: raise RuntimeError('baseline source did not restore after wrong-cause RED')
    # Wrong incomplete-report only: the exact pristine source is the basis of this separate overlay.
    anchor='                    && !report.stdout_complete()';replacement='                    && report.stdout_complete()'
    original,changed=mutate_once(test,anchor,replacement,'wrong-incomplete-report-red')
    run_case('wrong-incomplete-report-red',cargo,env,expected=101,diagnostic=REPORT)
    test.write_bytes(original)
    if sha(test)!=TEST: raise RuntimeError('baseline source did not restore after wrong-report RED')
    run_case('restored-green',cargo,env,expected=0)
    if sha(test)!=TEST or BASE.manifest_hashes()!=manifest or sha(BASE.SOURCE/'Cargo.lock')!=LOCK: raise RuntimeError('baseline test/manifests/lock restoration mismatch')
    BASE.write_json(BASE.STAGE/'tool-versions.json',{'rustc_stdout':rustc_text,'cargo_stdout':cargo_text,'toolchain':'1.77.2-x86_64-unknown-linux-gnu'})
    BASE.write_json(BASE.STAGE/'package-result.json',{'source_revision':REV,'source_archive_sha256':ARCHIVE,'test_source_sha256':TEST,'compatible_lock_sha256':LOCK,'test_name':TEST_NAME,'features':'testing-environ,sys','commands':BASE.COMMANDS,'controls':BASE.CONTROL_RESULTS,'source_restored_to_baseline':True,'acceptance_claim':False})
    return 0

def export() -> None:
    if BASE is None or not BASE.STAGE.is_dir(): return
    try: BASE.restore_example_sources()
    except BaseException as exc: BASE.write_json(BASE.STAGE/'source-restoration-error.json',{'error':repr(exc)})
    restored=bool(BASE.ORIGINAL_EXAMPLES) and all(p.exists() and sha(p)==BASE.ORIGINAL_EXAMPLE_HASHES[p.relative_to(BASE.SOURCE).as_posix()] for p in BASE.ORIGINAL_EXAMPLES)
    BASE.write_json(BASE.STAGE/'source-restoration.json',{'original_example_sha256':BASE.ORIGINAL_EXAMPLE_HASHES,'injected_example_sha256':BASE.INJECTED_EXAMPLE_HASHES,'restored_examples_match_original_bytes':restored and BASE.REVISION==REV,'cargo_lock_sha256_after_execution':sha(BASE.SOURCE/'Cargo.lock') if (BASE.SOURCE/'Cargo.lock').is_file() else None,'manifest_sha256':BASE.manifest_hashes() if BASE.SOURCE.is_dir() else {},'error':None if restored else 'restoration incomplete'})
    BASE.write_json(BASE.STAGE/'package-result.json',{'source_revision':REV,'source_archive_sha256':ARCHIVE,'test_source_sha256':TEST,'compatible_lock_sha256':LOCK,'test_name':TEST_NAME,'features':'testing-environ,sys','commands':BASE.COMMANDS,'controls':BASE.CONTROL_RESULTS,'source_restored_to_baseline':restored,'acceptance_claim':False,'interrupted_signal':BASE.INTERRUPTED})
    BASE.write_json(BASE.STAGE/'sampled-maxima.json',{'maxima':BASE.MAXIMA,'sample_count':len(BASE.SAMPLES),'samples_are_periodic_not_continuous_peak':True,'storage_preemptive_stop_kib':1572864,'storage_hard_stop_kib':2097152,'rss_hard_stop_kib':2097152,'descendant_hard_stop':16})
    (BASE.STAGE/'resource-samples.jsonl').write_text(''.join(json.dumps(row,sort_keys=True)+'\n' for row in BASE.SAMPLES),encoding='utf-8')
    BASE.write_json(BASE.STAGE/'export.json',{'runtime':str(BASE.RUNTIME),'destination':str(BASE.EVIDENCE),'elapsed_seconds':round(time.monotonic()-BASE.START,3),'helper_deadline_seconds':540,'work_deadline_seconds':510,'partial_export_possible':True,'acceptance_claim':False})
    if not BASE.export_destination_is_safe(): raise RuntimeError('evidence export destination identity is unverified')
    BASE.EVIDENCE.mkdir(mode=0o700)
    for item in sorted(BASE.STAGE.iterdir()):
        target=BASE.EVIDENCE/item.name
        if item.is_dir(): shutil.copytree(item,target)
        else: shutil.copy2(item,target)
    print(f'evidence_exported={BASE.EVIDENCE}',flush=True)

if __name__=='__main__':
    status=1
    try: status=main()
    except BaseException as exc:
        if BASE is not None and BASE.STAGE.is_dir(): (BASE.STAGE/'failure.txt').write_text(''.join(traceback.format_exception(type(exc),exc,exc.__traceback__)))
        traceback.print_exc();status=1
    finally:
        try: export()
        except BaseException: traceback.print_exc();status=1
    raise SystemExit(status)
