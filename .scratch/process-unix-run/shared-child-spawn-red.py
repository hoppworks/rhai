import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path('/Users/hoppworks/projects/rhai-process-unix-run')
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
EVIDENCE_CAP = 256 * 1024
SAMPLED_STOP_KIB = 1_572_864
BASE_LOCK_SHA = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
TOOLCHAIN = Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO = TOOLCHAIN / 'cargo'
RUSTC = TOOLCHAIN / 'rustc'
RUSTDOC = TOOLCHAIN / 'rustdoc'
TEST_NAME = 'shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable'
OVERLAYS = [
    'Cargo.toml',
    'src/packages/sys/mod.rs',
    'src/packages/sys/process.rs',
    'src/packages/sys/process/unix.rs',
    'src/types/token.rs',
    'tests/tokens.rs',
    'tests/sys_process.rs',
    'tests/fixtures/sys_process_shared_child_contract.rs',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_storage():
    result = subprocess.run(['du', '-sk', str(RUNTIME)], capture_output=True, text=True, timeout=5)
    print(f'storage_sample_status={result.returncode} stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}', flush=True)
    if result.returncode != 0:
        raise RuntimeError('private runtime storage sample failed')
    kib = int(result.stdout.split()[0])
    if kib >= SAMPLED_STOP_KIB:
        raise RuntimeError(f'sampled private runtime reached existing stop threshold {SAMPLED_STOP_KIB} KiB')


def emit_log(path, complete):
    data = path.read_bytes() if path.exists() else b''
    clipped = len(data) > EVIDENCE_CAP
    print(f'cargo_output_begin complete={str(complete).lower()} bytes={len(data)} clipped={str(clipped).lower()}', flush=True)
    if clipped:
        print('[earlier output truncated; retained final 256 KiB]', flush=True)
    print((data[-EVIDENCE_CAP:] if clipped else data).decode(errors='replace'), flush=True)
    print('cargo_output_end', flush=True)


def run_cargo(argv, cwd, env, log_path):
    print('cargo_argv=' + repr(argv), flush=True)
    print('cargo_cwd=' + str(cwd), flush=True)
    print('cargo_log=' + str(log_path), flush=True)
    with log_path.open('wb') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
        print(f'cargo_pid={proc.pid} cargo_pgid={os.getpgid(proc.pid)}', flush=True)
        deadline = time.monotonic() + 540
        try:
            while proc.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('development RED cargo command reached 540s watchdog')
                sample_storage()
                time.sleep(1)
            status = proc.returncode
        except BaseException:
            emit_log(log_path, False)
            raise
    sample_storage()
    print(f'cargo_status={status}', flush=True)
    emit_log(log_path, True)
    return status, log_path.read_text(errors='replace')


RUNTIME.mkdir(parents=True, exist_ok=True)
(RUNTIME / 'tmp').mkdir(exist_ok=True)
print('phase=development_toolchain_red_only', flush=True)
print('runtime_path=' + str(RUNTIME), flush=True)
print(f'python={sys.version.replace(chr(10), " ")}', flush=True)
print('platform=' + platform.platform(), flush=True)
print(f'runner_pid={os.getpid()} supervisor_pid={os.getppid()} owned_pgid={os.getpgid(0)}', flush=True)
for name, path in [('cargo', CARGO), ('rustc', RUSTC), ('rustdoc', RUSTDOC)]:
    if not path.is_file():
        raise RuntimeError(f'expected existing development tool missing: {path}')
    version = subprocess.check_output([str(path), '--version', '--verbose'] if name == 'rustc' else [str(path), '--version'], text=True, timeout=10).strip().replace('\n', ' | ')
    print(f'{name}_path={path} {name}_version={version}', flush=True)

source_hashes = {name: sha(REPO / name) for name in OVERLAYS}
print('repo_head=' + subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('repo_dirty=' + repr(subprocess.check_output(['git', '-C', str(REPO), 'status', '--short', '--untracked-files=all'], text=True).splitlines()), flush=True)
print('original_overlay_hashes=' + repr(source_hashes), flush=True)
print('test_fixture_hash=' + sha(REPO / 'tests/fixtures/sys_process_shared_child_contract.rs'), flush=True)
print('harness_hash=' + sha(Path(__file__)), flush=True)
runner_script = Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
wrapper_script = REPO / '.scratch/process-unix-run/run-shared-child-spawn-red.sh'
print('run_scoped_hash=' + sha(runner_script), flush=True)
print('wrapper_hash=' + sha(wrapper_script), flush=True)

source = RUNTIME / 'source'
source.mkdir()
archive = RUNTIME / 'baseline.tar'
with archive.open('wb') as output:
    proc = subprocess.Popen(['git', '-C', str(REPO), 'archive', 'HEAD'], stdout=output, stderr=subprocess.PIPE, start_new_session=False)
    deadline = time.monotonic() + 90
    while proc.poll() is None:
        if time.monotonic() >= deadline:
            raise TimeoutError('baseline git archive exceeded 90s')
        sample_storage()
        time.sleep(0.5)
    stderr = proc.stderr.read().decode(errors='replace')
    if proc.returncode != 0:
        raise RuntimeError(f'git archive status={proc.returncode} stderr={stderr}')
sample_storage()
extract = subprocess.run(['tar', '-xf', str(archive), '-C', str(source)], timeout=90, check=False)
if extract.returncode != 0:
    raise RuntimeError(f'baseline tar extraction status={extract.returncode}')
archive.unlink()

for name in OVERLAYS:
    destination = source / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / name, destination)
private_hashes = {name: sha(source / name) for name in OVERLAYS}
if private_hashes != source_hashes:
    raise RuntimeError('private source overlays do not match frozen source hashes')

test_file = source / 'tests/sys_process.rs'
test_text = test_file.read_text()
registration = '\n#[cfg(all(feature = "sys", unix, not(feature = "no_index")))]\n#[path = "fixtures/sys_process_shared_child_contract.rs"]\nmod shared_child_contract;\n'
if 'mod shared_child_contract;' in test_text:
    raise RuntimeError('shared fixture unexpectedly already registered in baseline')
test_file.write_text(test_text + registration)
injected_test_hash = sha(test_file)
print('private_source_hashes=' + repr(private_hashes), flush=True)
print('private_injected_test_hash=' + injected_test_hash, flush=True)
print('private_source=' + str(source), flush=True)

accepted_lock = REPO / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
lock_hash = sha(accepted_lock)
if lock_hash != BASE_LOCK_SHA:
    raise RuntimeError(f'accepted compatible lock hash mismatch: {lock_hash}')
private_lock = source / 'Cargo.lock'
shutil.copy2(accepted_lock, private_lock)
lock_text = private_lock.read_text()
marker = 'name = "rhai"\nversion = "1.26.1"\ndependencies = [\n'
if lock_text.count(marker) != 1:
    raise RuntimeError('accepted lock has an unexpected rhai package entry')
start = lock_text.index(marker)
end = lock_text.index('\n]', start)
section = lock_text[start:end]
if ' "libc",\n' not in section:
    insert_at = section.index(' "libm",\n')
    section = section[:insert_at] + ' "libc",\n' + section[insert_at:]
    lock_text = lock_text[:start] + section + lock_text[end:]
    private_lock.write_text(lock_text)
print(f'accepted_lock_sha256={lock_hash} private_lock_sha256={sha(private_lock)} private_lock_direct_libc_edge=true', flush=True)

env = dict(os.environ)
for key in ('RUSTUP_TOOLCHAIN', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_BUILD_RUSTC_WRAPPER'):
    env.pop(key, None)
env.update({
    'PATH': f'{TOOLCHAIN}:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',
    'CARGO_HOME': str(RUNTIME / 'cargo-home'),
    'RUSTUP_HOME': str(RUNTIME / 'rustup-home'),
    'CARGO_TARGET_DIR': str(RUNTIME / 'target'),
    'CARGO_BUILD_JOBS': '2',
    'CARGO_INCREMENTAL': '0',
    'CARGO_PROFILE_DEV_DEBUG': '0',
    'CARGO_PROFILE_TEST_DEBUG': '0',
    'RUSTC': str(RUSTC),
    'RUSTDOC': str(RUSTDOC),
    'TMPDIR': str(RUNTIME / 'tmp'),
    'TMP': str(RUNTIME / 'tmp'),
    'TEMP': str(RUNTIME / 'tmp'),
})
(RUNTIME / 'cargo-home').mkdir()
(RUNTIME / 'rustup-home').mkdir()
token_command = [
    str(CARGO), 'test', '--locked', '--test', 'tokens',
    '--features', 'sys', '--',
    'sys_spawn_keyword_can_be_called_as_the_documented_global_function',
    '--exact', '--nocapture', '--test-threads=1',
]
token_status, token_output = run_cargo(token_command, source, env, RUNTIME / 'cargo-token-test.log')
token_sys_passed = (
    token_status == 0
    and 'running 1 test' in token_output
    and 'sys_spawn_keyword_can_be_called_as_the_documented_global_function ... ok' in token_output
)
print(f'parser_sys_callability_test status={token_status} passed={token_sys_passed}', flush=True)
if not token_sys_passed:
    raise RuntimeError('sys-enabled public parser callability test did not pass')

token_nocustom_command = [
    str(CARGO), 'test', '--locked', '--test', 'tokens',
    '--features', 'sys,no_custom_syntax', '--',
    'sys_spawn_keyword_can_be_called_as_the_documented_global_function',
    '--exact', '--nocapture', '--test-threads=1',
]
token_nocustom_status, token_nocustom_output = run_cargo(
    token_nocustom_command, source, env, RUNTIME / 'cargo-token-nocustom-test.log'
)
token_nocustom_passed = (
    token_nocustom_status == 0
    and 'running 1 test' in token_nocustom_output
    and 'sys_spawn_keyword_can_be_called_as_the_documented_global_function ... ok' in token_nocustom_output
)
print(f'parser_sys_no_custom_syntax_test status={token_nocustom_status} passed={token_nocustom_passed}', flush=True)
if not token_nocustom_passed:
    raise RuntimeError('sys plus no_custom_syntax parser callability test did not pass')

token_no_sys_command = [
    str(CARGO), 'test', '--locked', '--test', 'tokens', '--no-default-features',
    '--features', 'std', '--', 'spawn_remains_reserved_when_sys_is_disabled',
    '--exact', '--nocapture', '--test-threads=1',
]
token_no_sys_status, token_no_sys_output = run_cargo(
    token_no_sys_command, source, env, RUNTIME / 'cargo-token-no-sys-test.log'
)
token_no_sys_passed = (
    token_no_sys_status == 0
    and 'running 1 test' in token_no_sys_output
    and 'spawn_remains_reserved_when_sys_is_disabled ... ok' in token_no_sys_output
)
token_test_passed = token_sys_passed and token_nocustom_passed and token_no_sys_passed
print(f'parser_no_sys_test status={token_no_sys_status} passed={token_no_sys_passed}', flush=True)
if not token_no_sys_passed:
    raise RuntimeError('non-sys reserved-keyword behavior changed')

command = [
    str(CARGO), 'test', '--locked', '--test', 'sys_process',
    '--features', 'testing-environ,sys,sync', '--', TEST_NAME,
    '--exact', '--nocapture', '--test-threads=1',
]
status, output = run_cargo(command, source, env, RUNTIME / 'cargo-test.log')

expected = 'Function not found: spawn' in output
test_failed = bool(re.search(rf'(?m)^    {re.escape(TEST_NAME)}$', output))
one_test_failed = bool(re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output))
one_test = 'running 1 test' in output
controller_reaped = 'shared-child controller_reaped scenario=blocked_input_wait_snapshot' in output
root_match = re.search(r'shared-child controller_started scenario=blocked_input_wait_snapshot pid=(\d+) root=(\S+)', output)
controller_esrch = False
root_contained = False
root_absent = False
if root_match:
    controller_pid = int(root_match.group(1))
    fixture_root = Path(root_match.group(2))
    lexical_root = Path(os.path.abspath(fixture_root))
    runtime_lexical = Path(os.path.abspath(os.environ['AGENT_RUNTIME_DIR']))
    root_contained = (
        lexical_root == fixture_root
        and not fixture_root.is_symlink()
        and fixture_root.parent == runtime_lexical
        and runtime_lexical.resolve() == RUNTIME
        and fixture_root.resolve() == RUNTIME / fixture_root.name
        and re.fullmatch(r'shared-child-fixture-[0-9]+-[0-9]+', fixture_root.name) is not None
    )
    try:
        os.kill(controller_pid, 0)
    except ProcessLookupError:
        controller_esrch = f'shared-child controller_esrch pid={controller_pid} verified=true' in output
    except PermissionError:
        controller_esrch = False
    root_absent = not fixture_root.exists()
    print(f'controller_pid={controller_pid} controller_esrch={controller_esrch} fixture_root={fixture_root} fixture_root_contained={root_contained} fixture_root_absent={root_absent}', flush=True)

final_private_hashes = {name: sha(source / name) for name in OVERLAYS}
final_injected_test_hash = sha(source / 'tests/sys_process.rs')
expected_private_hashes = dict(private_hashes)
expected_private_hashes['tests/sys_process.rs'] = injected_test_hash
print('final_private_source_hashes=' + repr(final_private_hashes), flush=True)
print('final_private_injected_test_hash=' + final_injected_test_hash, flush=True)
source_unchanged = final_private_hashes == expected_private_hashes and final_injected_test_hash == injected_test_hash
final_original_hashes = {name: sha(REPO / name) for name in OVERLAYS}
original_unchanged = final_original_hashes == source_hashes
print('final_original_overlay_hashes=' + repr(final_original_hashes), flush=True)
print(f'red_classifier status={status} one_test={one_test} intended_public_spawn_error={expected} exact_test_failed={test_failed} one_test_failure_summary={one_test_failed} parser_sys={token_sys_passed} parser_sys_no_custom={token_nocustom_passed} parser_no_sys={token_no_sys_passed} controller_reaped={controller_reaped} controller_esrch={controller_esrch} fixture_root_contained={root_contained} fixture_root_absent={root_absent} private_source_unchanged={source_unchanged} original_sources_unchanged={original_unchanged}', flush=True)
if not (status == 101 and one_test and expected and test_failed and one_test_failed and token_test_passed and controller_reaped and controller_esrch and root_contained and root_absent and source_unchanged and original_unchanged):
    raise RuntimeError('expected public Engine FunctionNotFound RED was not isolated; do not count as contract evidence')
print('classification=expected_development_toolchain_public_engine_red; no_os_fixture_spawned; not_msrv_or_release_acceptance', flush=True)
