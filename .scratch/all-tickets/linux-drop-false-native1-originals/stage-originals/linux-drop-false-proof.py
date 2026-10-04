#!/usr/bin/env python3
"""Bounded Linux final-drop proof for the two existing kill_on_drop(false) tests."""
from __future__ import annotations
import hashlib, importlib.util, json, os, platform, shutil, signal, subprocess, sys, threading, time, traceback
from pathlib import Path

REV = '523608648dcae99bc0f6b46eaf2bb91fa4ecc752'
ARCHIVE = '998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b'
LOCK = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
BASE_HELPER = 'c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9'
TEST = '5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb'
PATCH = '78d7f123c570e5efb94563b77c737fd4ed97ac9a594090c4a7dba664b461e9dd'
OBSERVER_HASH = '07d2ab6e1f2015a18b1ee83f59585b16b97852a00cc45dfb5778f836d78ad0d2'
CONTRACT = '5f26d4fd99bddda2fcd5f3a0ee863b361c930a69f915be4c9f8389bfadb072f5'
STAGE_PATH = Path('/root/rhai-linux-drop-false-523-20261004')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/linux-drop-false-523-20261004')
DIRECT = 'direct_spawn_kill_on_drop_false_preserves_child_and_capture'
MANAGED = 'managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit'
BASE = None
OBS = None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load pinned helper: {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_case(case: str, test_name: str, cargo: Path, env: dict[str, str], *, expected: int,
             assertion: str | None = None, handshake: bool = False) -> None:
    label = f'{case}-'+('red' if assertion else 'green')
    observer_result: dict = {}
    command_identity: dict = {}
    done = threading.Event()
    thread = None
    invocation_env = dict(env)
    if handshake:
        directory = BASE.RUNTIME / f'observer-{case}'
        directory.mkdir(mode=0o700)
        if any(directory.iterdir()):
            raise RuntimeError(f'{case} observer directory is not fresh and empty')
        invocation_env['RHAI_DROP_FALSE_OBSERVER_DIR'] = str(directory)
    command = [str(cargo), 'test', '--locked', '--features', 'testing-environ,sys', '--test', 'sys_process',
               test_name, '--', '--exact', '--nocapture', '--test-threads=1']
    original_record = BASE.record_process_identity
    def record_and_publish(row_label, pid, identity):
        nonlocal thread
        original_record(row_label, pid, identity)
        if row_label != f'command:{label}':
            return
        if not identity or int(identity.get('pid', 0)) != int(pid) or int(identity.get('start_ticks', 0)) <= 0:
            if handshake:
                observer_result['error'] = 'target Cargo command identity is missing or incomplete'
            return
        command_identity.update(identity)
        if handshake:
            observer_result['cargo_process_identity'] = dict(command_identity)
            thread = threading.Thread(target=OBS.observe, args=(BASE.RUNTIME / f'observer-{case}', case,
                                      BASE.RUNTIME, done, observer_result), name=f'{case}-observer', daemon=True)
            thread.start()
    BASE.record_process_identity = record_and_publish
    try:
        BASE.run_command(label, command, invocation_env, expected_status=expected)
    except BaseException as exc:
        if handshake:
            observer_result.setdefault('error', f'{type(exc).__name__}: {exc}')
        raise
    finally:
        BASE.record_process_identity = original_record
        done.set()
        if handshake:
            req_dir = BASE.RUNTIME / f'observer-{case}'
            if req_dir.is_dir() and not (BASE.STAGE / f'{case}-handshake').exists():
                shutil.copytree(req_dir, BASE.STAGE / f'{case}-handshake')
            if thread is not None:
                thread.join(timeout=5)
                if thread.is_alive():
                    observer_result.setdefault('error', 'observer did not stop within five seconds')
            BASE.write_json(BASE.STAGE / f'{case}-observer-partial.json', observer_result)
    stdout = BASE.read_text(BASE.STAGE / f'{label}.stdout')
    stderr = BASE.read_text(BASE.STAGE / f'{label}.stderr')
    if assertion:
        if f'test {test_name} ... FAILED' not in stdout or assertion not in stderr or f"thread '{test_name}' panicked at tests/sys_process.rs:" not in stderr:
            raise RuntimeError(f'{label} did not fail at its named expectation assertion')
        BASE.verify_control(label, 101, 101, stderr, [assertion])
        OBS.control_terminal(stderr, case, BASE.STAGE)
        if observer_result.get('ack_written') or observer_result.get('live') or list((BASE.RUNTIME / f'observer-{case}').glob('*.request')):
            raise RuntimeError(f'{label} unexpectedly entered the observer handshake before intended RED')
        return
    if f'test {test_name} ... ok' not in stdout or 'test result: ok. 1 passed; 0 failed;' not in stdout:
        raise RuntimeError(f'{label} lacks the exact one-test successful Cargo result')
    if not observer_result.get('ack_written'):
        raise RuntimeError(f'{label} observer did not independently acknowledge: {observer_result!r}')
    cargo = observer_result.get('cargo_process_identity')
    if not cargo or int(observer_result['live']['host']['ppid']) != int(cargo['pid']):
        raise RuntimeError(f'{label} observer test-host parent does not bind to the recorded Cargo command')
    observer_result['live']['cargo'] = cargo
    OBS.terminal(observer_result, case, BASE.STAGE)
    BASE.write_json(BASE.STAGE / f'{case}-observer-live.json', observer_result['live'])
    BASE.verify_pass(label, 0, stdout, f'test {test_name} ... ok')


def main() -> int:
    global BASE, OBS
    stage = Path(os.environ['PROOF_STAGE'])
    runtime = Path(os.environ['AGENT_RUNTIME_DIR'])
    BASE = load(stage / 'check-linux-current-msrv-examples.py', 'accepted_linux_example_base')
    OBS = load(stage / 'drop-false-observer.py', 'drop_false_observer')
    BASE.INPUT_STAGE = stage
    BASE.EXPECTED_STAGE = Path(os.environ['EXPECTED_PROOF_STAGE'])
    BASE.PRESCRIBED_STAGE = STAGE_PATH
    BASE.PRESCRIBED_SCOPE = SCOPE_PATH
    BASE.RUNTIME = runtime
    signal.signal(signal.SIGTERM, BASE.on_signal)
    signal.signal(signal.SIGINT, BASE.on_signal)
    BASE.STAGE = runtime / 'evidence'
    BASE.EVIDENCE = BASE.EXPECTED_STAGE / 'proof-evidence'
    BASE.CONTRACT = stage / 'contract.md'
    BASE.SOURCE_ARCHIVE = stage / 'source.tar'
    BASE.LOCK_SOURCE = stage / 'Cargo.lock.accepted'
    BASE.RUSTUP = Path(os.environ['RUSTUP_BIN'])
    BASE.SOURCE_ARCHIVE_SHA256 = ARCHIVE
    BASE.LOCK_SHA256 = LOCK
    BASE.REVISION = REV
    BASE.TOOLCHAIN = '1.77.2-x86_64-unknown-linux-gnu'
    BASE.SOURCE = runtime / 'source'
    BASE.CARGO_HOME = runtime / 'cargo-home'
    BASE.RUSTUP_HOME = runtime / 'rustup-home'
    BASE.TARGET = runtime / 'target'
    BASE.PRIVATE_HOME = runtime / 'home'
    BASE.PRIVATE_TMP = Path(os.environ['TMPDIR'])
    BASE.capture_runtime_proof()
    BASE.validate_stage_inputs()
    if platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise RuntimeError('native Linux x86_64 required')
    for name, digest in [('check-linux-current-msrv-examples.py', BASE_HELPER),
                         ('drop-false-observer.py', OBSERVER_HASH), ('contract.md', CONTRACT),
                         ('drop-false-observer-handshake.patch', PATCH)]:
        if sha(stage / name) != digest:
            raise RuntimeError(f'{name} input hash mismatch')
    if sha(BASE.SOURCE_ARCHIVE) != ARCHIVE or sha(BASE.LOCK_SOURCE) != LOCK:
        raise RuntimeError('source archive or compatible lock pin mismatch')
    BASE.extract_archive(BASE.SOURCE_ARCHIVE)
    test = BASE.SOURCE / 'tests/sys_process.rs'
    original = test.read_bytes()
    if sha(test) != TEST:
        raise RuntimeError('baseline sys_process test source hash mismatch')
    BASE.ORIGINAL_EXAMPLES[test] = original
    BASE.ORIGINAL_EXAMPLE_HASHES['tests/sys_process.rs'] = TEST
    manifest = BASE.manifest_hashes()
    BASE.CARGO_MANIFESTS = manifest
    shutil.copy2(BASE.LOCK_SOURCE, BASE.SOURCE / 'Cargo.lock')
    for path in (BASE.CARGO_HOME, BASE.RUSTUP_HOME, BASE.PRIVATE_HOME):
        path.mkdir(mode=0o700)
    BASE.PRIVATE_TMP.mkdir(mode=0o700, parents=True, exist_ok=True)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(BASE.PRIVATE_HOME),
           'TMPDIR': str(BASE.PRIVATE_TMP), 'TMP': str(BASE.PRIVATE_TMP), 'TEMP': str(BASE.PRIVATE_TMP),
           'CARGO_HOME': str(BASE.CARGO_HOME), 'RUSTUP_HOME': str(BASE.RUSTUP_HOME),
           'CARGO_TARGET_DIR': str(BASE.TARGET), 'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
           'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_TERM_COLOR': 'never', 'RUST_BACKTRACE': '0'}
    BASE.run_command('rustup-install', [str(BASE.RUSTUP), 'toolchain', 'install', BASE.TOOLCHAIN,
                                        '--profile', 'minimal', '--no-self-update'], env, cwd=runtime)
    bindir = BASE.RUSTUP_HOME / 'toolchains' / BASE.TOOLCHAIN / 'bin'
    rustc, cargo = bindir / 'rustc', bindir / 'cargo'
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError('private Rust 1.77.2 toolchain is incomplete')
    env.update(PATH=f'{bindir}:/usr/bin:/bin:/usr/sbin:/sbin', RUSTC=str(rustc))
    BASE.run_command('rustc-version', [str(rustc), '--version', '--verbose'], env)
    BASE.run_command('cargo-version', [str(cargo), '--version', '--verbose'], env)
    patch = stage / 'drop-false-observer-handshake.patch'
    subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)], cwd=BASE.SOURCE, check=True,
                   stdout=(BASE.STAGE / 'patch-apply.stdout').open('wb'), stderr=(BASE.STAGE / 'patch-apply.stderr').open('wb'))
    handshaked = test.read_bytes()
    BASE.write_json(BASE.STAGE / 'source-inputs.json', {'revision': REV, 'baseline_test_sha256': TEST,
                    'observer_patch_sha256': PATCH, 'test_after_patch_sha256': sha(test),
                    'cargo_lock_sha256': LOCK, 'cargo_manifests_sha256': manifest,
                    'archive_sha256': ARCHIVE, 'cargo_manifests_sha256': manifest})
    for case, name, needle, replacement, diagnostic in (
        ('direct', DIRECT, 'assert!(alive_after_drop && ack_matches, "kill_on_drop(false) must preserve the child after final handle drop");',
         'assert!(!(alive_after_drop && ack_matches), "drop_false-control direct survival expectation");',
         'drop_false-control direct survival expectation'),
        ('managed', MANAGED, 'assert!(members_live && challenge_ok, "kill_on_drop(false) must preserve all managed members after final handle drop");',
         'assert!(!(members_live && challenge_ok), "drop_false-control managed survival expectation");',
         'drop_false-control managed survival expectation')):
        text = handshaked.decode('utf-8')
        if text.count(needle) != 1:
            raise RuntimeError(f'{case} wrong-expectation assertion anchor is not unique')
        test.write_text(text.replace(needle, replacement, 1), encoding='utf-8')
        BASE.INJECTED_EXAMPLE_HASHES[f'{case}-wrong-expectation'] = sha(test)
        run_case(case, name, cargo, env, expected=101, assertion=diagnostic)
        test.write_bytes(handshaked)
        if test.read_bytes() != handshaked:
            raise RuntimeError(f'{case} handshake source did not restore byte-for-byte after RED')
    for case, name in (('direct', DIRECT), ('managed', MANAGED)):
        run_case(case, name, cargo, env, expected=0, handshake=True)
    test.write_bytes(original)
    if sha(test) != TEST or BASE.manifest_hashes() != manifest or sha(BASE.SOURCE / 'Cargo.lock') != LOCK:
        raise RuntimeError('baseline test/manifests/compatible lock restoration mismatch')
    BASE.write_json(BASE.STAGE / 'package-result.json', {'source_revision': REV, 'archive_sha256': ARCHIVE,
        'baseline_test_sha256': TEST, 'test_only_handshake_patch_sha256': PATCH, 'compatible_lock_sha256': LOCK,
        'tests': [DIRECT, MANAGED], 'controls': ['direct-red', 'managed-red'], 'green_rows': 2,
        'source_restored_to_baseline': True, 'acceptance_claim': False,
        'limitations': ['Execution is platform/feature scoped; original export and independent fresh cleanup readback are required.']})
    return 0


def export() -> None:
    if BASE is None or not BASE.STAGE.is_dir():
        return
    if BASE.ORIGINAL_EXAMPLES:
        try:
            BASE.restore_example_sources()
        except BaseException as exc:
            BASE.write_json(BASE.STAGE / 'source-restoration-error.json', {'error': repr(exc)})
    restored = bool(BASE.ORIGINAL_EXAMPLES) and all(
        sha(p) == BASE.ORIGINAL_EXAMPLE_HASHES[p.relative_to(BASE.SOURCE).as_posix()]
        for p in BASE.ORIGINAL_EXAMPLES if p.exists()) and all(p.exists() for p in BASE.ORIGINAL_EXAMPLES)
    BASE.write_json(BASE.STAGE / 'source-restoration.json', {
        'original_sha256': BASE.ORIGINAL_EXAMPLE_HASHES,
        'overlay_sha256': BASE.INJECTED_EXAMPLE_HASHES,
        'restored': restored,
        'restored_to_baseline_revision': restored and BASE.REVISION == REV,
        'cargo_lock_sha256': sha(BASE.SOURCE / 'Cargo.lock') if (BASE.SOURCE / 'Cargo.lock').is_file() else None,
        'manifest_sha256': BASE.manifest_hashes() if BASE.SOURCE.is_dir() else {},
        'error': None if restored else 'restoration incomplete or original bytes unavailable',
    })
    controls = list(BASE.CONTROL_RESULTS)
    commands = list(BASE.COMMANDS)
    BASE.write_json(BASE.STAGE / 'package-result.json', {
        'source_revision': REV, 'source_archive_sha256': ARCHIVE, 'baseline_test_sha256': TEST,
        'test_only_handshake_patch_sha256': PATCH, 'compatible_lock_sha256': LOCK,
        'base_helper_sha256': BASE_HELPER, 'cargo_manifests_sha256': getattr(BASE, 'CARGO_MANIFESTS', {}), 'tests': [DIRECT, MANAGED], 'commands': commands,
        'controls': controls, 'status': 0 if len(controls) == 4 and all(x.get('status') == x.get('expected_status') for x in controls) else 1,
        'source_restored_to_baseline': restored, 'acceptance_claim': False,
        'interrupted_signal': BASE.INTERRUPTED,
    })
    # Preserve partial originals even when a previous export was interrupted.
    BASE.STAGE.mkdir(mode=0o700, exist_ok=True)
    evidence = BASE.EVIDENCE
    if evidence.exists() and not evidence.is_dir():
        raise RuntimeError('evidence destination is not a directory')
    evidence.mkdir(mode=0o700, exist_ok=True)
    BASE.write_json(BASE.STAGE / 'export.json', {'destination': str(evidence), 'partial_export': True,
        'source_revision': REV, 'elapsed_seconds': round(time.monotonic() - BASE.START, 3),
        'helper_deadline_seconds': 540, 'work_deadline_seconds': 510,
        'no_native_acceptance_claim': True})
    for item in sorted(BASE.STAGE.iterdir()):
        target = evidence / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


if __name__ == '__main__':
    try:
        status = main()
    except BaseException as exc:
        if BASE is not None and BASE.STAGE.is_dir():
            (BASE.STAGE / 'failure.txt').write_text(''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        traceback.print_exc()
        status = 1
    finally:
        try:
            export()
        except BaseException:
            traceback.print_exc()
            status = 1
    raise SystemExit(status)
