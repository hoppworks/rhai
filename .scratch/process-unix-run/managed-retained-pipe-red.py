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
EVIDENCE_DIR = REPO / '.scratch/process-unix-run/evidence'
LOG_PATH = Path(os.environ['RHAI_PIPE_CARGO_LOG']).absolute()
SAMPLED_STOP_KIB = 1_572_864
BASE_LOCK_SHA = '8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
TOOLCHAIN = Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO, RUSTC, RUSTDOC = (TOOLCHAIN / name for name in ('cargo', 'rustc', 'rustdoc'))
TEST_NAME = 'managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes'
OVERLAYS = [
    'Cargo.toml', 'src/packages/sys/config.rs', 'src/packages/sys/mod.rs',
    'src/packages/sys/process.rs', 'src/packages/sys/process/unix.rs', 'tests/sys_process.rs',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_storage(deadline):
    for attempt in range(1, 3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('storage sample exceeded command watchdog')
        timeout = min(5.0, remaining)
        try:
            result = subprocess.run(['du', '-sk', str(RUNTIME)], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            out = error.stdout.decode(errors='replace') if isinstance(error.stdout, bytes) else error.stdout
            err = error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else error.stderr
            print(f'storage_sample_attempt={attempt} status=timeout stdout={out!r} stderr={err!r}', flush=True)
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('storage sampling failed twice') from error
            time.sleep(min(.05, max(0, deadline - time.monotonic())))
            continue
        print(f'storage_sample_attempt={attempt} status={result.returncode} stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}', flush=True)
        if result.returncode:
            if attempt == 2 or time.monotonic() >= deadline:
                raise RuntimeError('storage sampling failed twice')
            time.sleep(min(.05, max(0, deadline - time.monotonic())))
            continue
        fields = result.stdout.strip().split(maxsplit=1)
        if len(fields) != 2 or not fields[0].isdigit() or fields[1] != str(RUNTIME):
            raise RuntimeError(f'malformed storage sample: {result.stdout!r}')
        kib = int(fields[0])
        print(f'storage_sample_kib={kib}', flush=True)
        if kib >= SAMPLED_STOP_KIB:
            raise RuntimeError(f'sampled storage reached stop threshold {SAMPLED_STOP_KIB} KiB')
        return kib
    raise RuntimeError('no successful storage measurement')


def emit_log(path, complete):
    data = path.read_bytes() if path.exists() else b''
    print(f'cargo_output_begin path={path} complete={str(complete).lower()} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()}', flush=True)
    print(data.decode(errors='replace'), flush=True)
    print('cargo_output_end', flush=True)


def parse_red(output):
    started = re.search(r'(?m)^test managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes \.\.\. managed_escaped_pipe_wait root=(\S+) test_pid=(\d+) leader=(\d+) leader_pgid=(\d+) leader_esrch=true holder=(\d+) holder_pgid=(\d+) holder_live_after_wait=true sentinel=(\d+) sentinel_pgid=(\d+) sentinel_live_after_wait=true wait_unit=true probe="pid=(\d+) stdout_result=(-?\d+) stdout_error=(\d+) stderr_result=(-?\d+) stderr_error=(\d+)\\n" identity_ok=true$', output)
    cleanup = re.search(r'(?m)^managed_escaped_pipe_cleanup root=(\S+) leader=Some\((\d+)\) leader_esrch=true holder=Some\((\d+)\) holder_esrch=true$', output)
    terminal = re.search(r'(?m)^managed_escaped_pipe_terminal leader=Some\((\d+)\) leader_esrch=true holder=Some\((\d+)\) holder_esrch=true sentinel=(\d+) sentinel_esrch=true$', output)
    sentinel_cleanup = re.search(r'(?m)^managed-scope sentinel_cleanup pid=(\d+) status=[^\n]* esrch=true$', output)
    test_start = re.search(r'(?m)^test managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes \.\.\. ', output)
    specific_failure = 'public wait must return the final process report' in output
    failure_list = re.search(r'(?m)^    managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes$', output)
    summary = re.search(r'(?m)^test result: FAILED\. 0 passed; 1 failed;', output)
    if not all((started, cleanup, terminal, sentinel_cleanup, test_start, failure_list, summary, specific_failure)):
        return {'valid': False, 'reason': 'missing intended panic or complete pre-failure identity/cleanup receipts'}
    root = Path(started.group(1))
    ids = tuple(map(int, started.groups()[1:]))
    test_pid, leader, leader_pgid, holder, holder_pgid, sentinel, sentinel_pgid, probe_pid, stdout_result, stdout_errno, stderr_result, stderr_errno = ids
    clean_ids = tuple(map(int, cleanup.groups()[1:]))
    terminal_ids = tuple(map(int, terminal.groups()))
    identity = (
        leader == leader_pgid and holder != leader and holder_pgid == sentinel_pgid
        and sentinel == sentinel_pgid and probe_pid == holder
        and stdout_result == 34 and stdout_errno == 0 and stderr_result == 34 and stderr_errno == 0
        and clean_ids == (leader, holder) and terminal_ids == (leader, holder, sentinel)
        and int(sentinel_cleanup.group(1)) == sentinel
        and len({test_pid, leader, holder, sentinel}) == 4
    )
    root_valid = root.is_absolute() and root.parent == RUNTIME / 'tmp' and root.name.startswith('rhai-sys-test-') and not root.is_symlink() and not root.exists()
    return {
        'valid': bool(identity and root_valid), 'identity': identity, 'fixture_root_absent': root_valid,
        'specific_failure': specific_failure, 'named_failure': bool(failure_list), 'single_failure': bool(summary),
        'test_pid': test_pid, 'leader_pid': leader, 'holder_pid': holder, 'sentinel_pid': sentinel,
        'receipt_root': str(root),
    }


def preflight_red_classifier():
    root = RUNTIME / 'tmp' / 'rhai-sys-test-123-fixture'
    output = (
        'test managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes ... '
        f'managed_escaped_pipe_wait root={root} test_pid=101 leader=201 leader_pgid=201 leader_esrch=true '
        'holder=202 holder_pgid=303 holder_live_after_wait=true sentinel=303 sentinel_pgid=303 '
        'sentinel_live_after_wait=true wait_unit=true '
        'probe="pid=202 stdout_result=34 stdout_error=0 stderr_result=34 stderr_error=0\\n" identity_ok=true\n'
        f'managed_escaped_pipe_cleanup root={root} leader=Some(201) leader_esrch=true holder=Some(202) holder_esrch=true\n'
        'managed_escaped_pipe_terminal leader=Some(201) leader_esrch=true holder=Some(202) holder_esrch=true sentinel=303 sentinel_esrch=true\n'
        'managed-scope sentinel_cleanup pid=303 status=Some(0) esrch=true\n'
        'public wait must return the final process report\n'
        '    managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes\n'
        'test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 10 filtered out\n'
    )
    baseline = parse_red(output)
    assert baseline['valid'], f'actual RED classifier rejects complete representative receipt: {baseline!r}'
    mutations = [
        output.replace('stdout_result=34', 'stdout_result=-1', 1),
        output.replace('holder_esrch=true', 'holder_esrch=false', 1),
        output.replace('holder_pgid=303', 'holder_pgid=304', 1),
        output.replace('public wait must return the final process report', 'unrelated panic', 1),
        output.replace('managed_escaped_pipe_cleanup', 'missing_cleanup', 1),
    ]
    assert all(not parse_red(candidate)['valid'] for candidate in mutations), 'RED classifier accepted an incorrect or incomplete receipt'
    print('retained_pipe_red_classifier_checks=6 valid_baseline_and_five_invalid_mutations_rejected', flush=True)


if RUNTIME.is_symlink() or not RUNTIME.is_dir():
    raise RuntimeError('private runtime is not an owned directory')
if LOG_PATH.parent != EVIDENCE_DIR or LOG_PATH.is_symlink():
    raise RuntimeError('Cargo log is not in the owned evidence directory')
RUNTIME.joinpath('tmp').mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
print('phase=managed_escaped_pipe_retained_cancellation_RED', flush=True)
print('acceptance_scope=public managed kill/wait closes local capture endpoints after cancellation when an escaped descendant retains writers', flush=True)
print('runtime_path=' + str(RUNTIME), flush=True)
preflight_red_classifier()
print(f'python={sys.version.replace(chr(10), " ")}', flush=True)
print('platform=' + platform.platform(), flush=True)
print(f'harness_pid={os.getpid()} supervisor_pid={os.getppid()} inherited_pgid={os.getpgid(0)}', flush=True)
for name, path in [('cargo', CARGO), ('rustc', RUSTC), ('rustdoc', RUSTDOC)]:
    if not path.is_file():
        raise RuntimeError(f'expected existing development tool missing: {path}')
    argv = [str(path), '--version', '--verbose'] if name == 'rustc' else [str(path), '--version']
    version = subprocess.check_output(argv, text=True, timeout=10).strip().replace('\n', ' | ')
    print(f'{name}_path={path} {name}_version={version}', flush=True)

original = {name: sha(REPO / name) for name in OVERLAYS}
print('repo_head=' + subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(), flush=True)
print('original_overlay_hashes=' + repr(original), flush=True)
print('harness_hash=' + sha(Path(__file__)), flush=True)
print('wrapper_hash=' + sha(REPO / '.scratch/process-unix-run/run-managed-retained-pipe-red.sh'), flush=True)

source = RUNTIME / 'source'
source.mkdir()
archive = RUNTIME / 'baseline.tar'
with archive.open('wb') as output:
    proc = subprocess.Popen(['git', '-C', str(REPO), 'archive', 'HEAD'], stdout=output, stderr=subprocess.PIPE, start_new_session=False)
    deadline = time.monotonic() + 90
    while proc.poll() is None:
        if time.monotonic() >= deadline:
            raise TimeoutError('baseline archive exceeded 90s')
        sample_storage(deadline)
        time.sleep(.5)
    stderr = proc.stderr.read().decode(errors='replace')
    if proc.returncode:
        raise RuntimeError(f'git archive failed: {stderr}')
extract = subprocess.run(['tar', '-xf', str(archive), '-C', str(source)], timeout=90)
if extract.returncode:
    raise RuntimeError('baseline extraction failed')
archive.unlink()
for name in OVERLAYS:
    (source / name).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / name, source / name)
private = {name: sha(source / name) for name in OVERLAYS}
if private != original:
    raise RuntimeError('private overlays differ from frozen source')
print('private_overlay_hashes=' + repr(private), flush=True)

accepted_lock = REPO / '.scratch/core-msrv-compatible-resolution/Cargo.lock'
lock_hash = sha(accepted_lock)
if lock_hash != BASE_LOCK_SHA:
    raise RuntimeError(f'accepted lock hash mismatch: {lock_hash}')
private_lock = source / 'Cargo.lock'
shutil.copy2(accepted_lock, private_lock)
lock_text = private_lock.read_text()
marker = 'name = "rhai"\nversion = "1.26.1"\ndependencies = [\n'
if lock_text.count(marker) != 1:
    raise RuntimeError('unexpected accepted-lock rhai entry')
start = lock_text.index(marker)
end = lock_text.index('\n]', start)
section = lock_text[start:end]
if ' "libc",\n' not in section:
    at = section.index(' "libm",\n')
    section = section[:at] + ' "libc",\n' + section[at:]
    lock_text = lock_text[:start] + section + lock_text[end:]
    private_lock.write_text(lock_text)
print(f'accepted_lock_sha256={lock_hash} private_lock_sha256={sha(private_lock)} private_direct_libc_edge=true', flush=True)

env = dict(os.environ)
for key in ('RUSTUP_TOOLCHAIN', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_BUILD_RUSTC_WRAPPER'):
    env.pop(key, None)
env.update({
    'PATH': f'{TOOLCHAIN}:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin',
    'CARGO_HOME': str(RUNTIME / 'cargo-home'), 'RUSTUP_HOME': str(RUNTIME / 'rustup-home'),
    'CARGO_TARGET_DIR': str(RUNTIME / 'target'), 'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
    'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0', 'RUSTC': str(RUSTC),
    'RUSTDOC': str(RUSTDOC), 'TMPDIR': str(RUNTIME / 'tmp'), 'TMP': str(RUNTIME / 'tmp'), 'TEMP': str(RUNTIME / 'tmp'),
})
(RUNTIME / 'cargo-home').mkdir()
(RUNTIME / 'rustup-home').mkdir()
argv = [str(CARGO), 'test', '--locked', '--test', 'sys_process', '--features', 'testing-environ,sys', '--', TEST_NAME, '--exact', '--nocapture', '--test-threads=1']
print('cargo_argv=' + repr(argv), flush=True)
print('cargo_cwd=' + str(source), flush=True)
print('cargo_log=' + str(LOG_PATH), flush=True)
deadline = time.monotonic() + 540
with LOG_PATH.open('wb') as log:
    proc = subprocess.Popen(argv, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=False)
    print(f'cargo_pid={proc.pid} cargo_pgid={os.getpgid(proc.pid)}', flush=True)
    try:
        while proc.poll() is None:
            if time.monotonic() >= deadline:
                raise TimeoutError('Cargo reached its 540s watchdog')
            sample_storage(deadline)
            time.sleep(1)
        status = proc.returncode
        print(f'cargo_status={status}', flush=True)
        emit_log(LOG_PATH, True)
        sample_storage(deadline)
    except BaseException:
        done = proc.poll()
        if done is not None:
            print(f'cargo_status={done}', flush=True)
        emit_log(LOG_PATH, done is not None)
        raise
output = LOG_PATH.read_text(errors='replace')
final = {name: sha(source / name) for name in OVERLAYS}
print('final_private_overlay_hashes=' + repr(final), flush=True)
if final != private:
    raise RuntimeError('private overlay changed during the test')
report = parse_red(output)
print('intended_red_receipt=' + repr(report), flush=True)
if status != 101 or not report['valid']:
    raise RuntimeError('run did not reach the specific retained-pipe public-report RED with all cleanup receipts')
print('retained_pipe_red=accepted_development_only', flush=True)
