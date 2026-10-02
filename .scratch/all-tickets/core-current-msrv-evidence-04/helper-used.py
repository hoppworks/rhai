"""Verify the frozen current default core with a private compatible lock."""
import hashlib
import json
import tomllib
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

REPO = Path('/Users/hoppworks/projects/rhai-all-tickets')
REVISION = '52d9797b250abcd29ca3d264be9aa0e42acd43bb'
EVIDENCE = REPO / '.scratch/all-tickets/core-current-msrv-evidence-04'
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR'])
TOOLS = Path('/Users/hoppworks/.rustup/toolchains')
OLD = TOOLS / '1.66.0-aarch64-apple-darwin/bin'
START = time.monotonic()
DEADLINE = START + 540
MAX_STORAGE_KIB = 2 * 1024 * 1024
PEAK_STORAGE_KIB = 0
PEAK_RSS_KIB = 0
PEAK_DESCENDANTS = 0


def size():
    global PEAK_STORAGE_KIB, PEAK_RSS_KIB, PEAK_DESCENDANTS
    result = subprocess.run(['/usr/bin/du', '-sk', str(RUNTIME)],
                            capture_output=True, text=True, check=True, timeout=5)
    kib = int(result.stdout.split()[0])
    PEAK_STORAGE_KIB = max(PEAK_STORAGE_KIB, kib)
    if kib >= MAX_STORAGE_KIB:
        raise RuntimeError('private runtime reached sampled 2 GiB stop')
    snapshot = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,rss='],
                              capture_output=True, text=True, check=True, timeout=5)
    rows = {}
    for line in snapshot.stdout.splitlines():
        pid, ppid, rss = map(int, line.split())
        if pid in rows:
            raise RuntimeError('duplicate PID in process sample')
        rows[pid] = (ppid, rss)
    owned = {os.getpid()}
    if os.getpid() not in rows:
        raise RuntimeError('proof host missing from process sample')
    while True:
        more = {pid for pid, (ppid, _) in rows.items() if ppid in owned} - owned
        if not more:
            break
        owned.update(more)
    rss = sum(rows[pid][1] for pid in owned)
    descendants = len(owned) - 1
    PEAK_RSS_KIB = max(PEAK_RSS_KIB, rss)
    PEAK_DESCENDANTS = max(PEAK_DESCENDANTS, descendants)
    print(f'sampled_storage_kib={kib} sampled_rss_kib={rss} sampled_descendants={descendants}', flush=True)
    if rss >= 2 * 1024 * 1024 or descendants > 16:
        raise RuntimeError('proof exceeded sampled RSS2GiB/descendants16 stop')
    return kib


def command(name, argv, env, expected=0):
    remaining = DEADLINE - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('aggregate proof deadline exhausted')
    print(f'command={name} argv={argv!r}', flush=True)
    path = EVIDENCE / (name + '.log')
    with path.open('wb') as output:
        child = subprocess.Popen(argv, cwd=source, env=env, stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                if time.monotonic() >= DEADLINE:
                    raise TimeoutError('aggregate proof deadline exhausted during ' + name)
                size()
                time.sleep(1)
            status = child.wait()
        except BaseException:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            raise
    size()
    if hashlib.sha256(lock.read_bytes()).hexdigest() != lock_sha:
        raise RuntimeError('locked resolution changed during ' + name)
    print(f'status={name}:{status}', flush=True)
    if status != expected:
        raise RuntimeError(f'{name} expected {expected}, observed {status}; see {path}')
    return path.read_text(errors='replace')


if EVIDENCE.exists():
    raise RuntimeError('evidence destination already exists; preserve prior run')
EVIDENCE.mkdir()
shutil.copy2(__file__, EVIDENCE / 'helper-used.py')
source = RUNTIME / 'source'
home = RUNTIME / 'cargo-home'
source.mkdir()
(home / 'registry').mkdir(parents=True)
for part in ('cache', 'index'):
    shutil.copytree(Path('/Users/hoppworks/.cargo/registry') / part, home / 'registry' / part)
shutil.copytree(Path('/Users/hoppworks/.cargo/git'), home / 'git')
size()
archive = RUNTIME / 'source.tar'
with archive.open('wb') as stream:
    subprocess.run(['/usr/bin/git', '-C', str(REPO), 'archive', REVISION],
                   stdout=stream, check=True, timeout=20)
archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
with tarfile.open(archive) as bundle:
    bundle.extractall(source, filter='data')
archive.unlink()
shutil.copy2(REPO / '.scratch/all-tickets/core-current-msrv-evidence-03/Cargo.lock', source / 'Cargo.lock')
lock = source / 'Cargo.lock'
lock_sha = hashlib.sha256(lock.read_bytes()).hexdigest()
shutil.copy2(lock, EVIDENCE / 'Cargo.lock')
(EVIDENCE / 'source.txt').write_text(f'revision={REVISION}\narchive_sha256={archive_sha}\nlock_sha256={lock_sha}\n')
configs = list((home / 'registry/index').glob('*/config.json'))
if not configs:
    raise RuntimeError('no public registry download configuration found')
for config in configs:
    data = json.loads(config.read_text())
    if data.get('dl') != 'https://static.crates.io/crates' or data.get('api') != 'https://crates.io':
        raise RuntimeError('unexpected registry endpoint: ' + str(config))
(EVIDENCE / 'registry-configs.json').write_text(json.dumps([{'namespace': c.parent.name, 'config': json.loads(c.read_text())} for c in configs], indent=2)+'\n')
private_home = RUNTIME / 'home'
private_home.mkdir()
env = {'PATH': str(OLD) + ':/usr/bin:/bin', 'HOME': str(private_home),
       'TMPDIR': os.environ['TMPDIR'], 'TMP': os.environ['TMPDIR'], 'TEMP': os.environ['TMPDIR'],
       'CARGO_HOME': str(home), 'CARGO_TARGET_DIR': str(RUNTIME / 'target'),
       'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
       'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_PROFILE_TEST_DEBUG': '0',
       'CARGO_TERM_COLOR': 'never', 'RUSTC': str(OLD / 'rustc'), 'RUSTDOC': str(OLD / 'rustdoc')}
command('rustc-version', [str(OLD / 'rustc'), '--version', '--verbose'], env)
command('cargo-version', [str(OLD / 'cargo'), '--version'], env)
command('core-check', [str(OLD / 'cargo'), 'check', '--locked', '--lib', '--target', 'aarch64-apple-darwin'], env)
example = source / 'examples/core_current_msrv.rs'
example.write_text('''use rhai::Engine;
fn main() {
    let engine = Engine::new();
    let actual: i64 = engine.eval("40 + 2").expect("real Engine evaluation");
    assert!(engine.compile("spawn()").is_err(), "spawn remains reserved without sys");
    let expected = if std::env::args().any(|x| x == "--wrong") { 43 } else { 42 };
    assert_eq!(actual, expected, "independent Engine expectation");
    println!("actual={actual} expected={expected} spawn_reserved=true");
}
''')
argv = [str(OLD / 'cargo'), 'run', '--locked', '--target', 'aarch64-apple-darwin', '--example', 'core_current_msrv']
positive = command('engine-positive', argv, env)
archive_rows = []
for package in tomllib.loads(lock.read_text())['package']:
    if not package.get('source', '').startswith('registry+'):
        continue
    name = package['name'] + '-' + package['version'] + '.crate'
    for cached in sorted((home / 'registry/cache').glob('*/' + name)):
        digest = hashlib.sha256(cached.read_bytes()).hexdigest()
        if digest != package['checksum']:
            raise RuntimeError('registry archive checksum mismatch: ' + str(cached))
        archive_rows.append({'namespace': cached.parent.name, 'archive': name, 'sha256': digest})
(EVIDENCE / 'cached-lock-archives.json').write_text(json.dumps(archive_rows, indent=2) + '\n')
offline = argv[:2] + ['--offline'] + argv[2:]
wrong = command('engine-wrong-control', offline + ['--', '--wrong'], env, expected=101)
if 'actual=42 expected=42 spawn_reserved=true' not in positive or 'left: `42`' not in wrong or 'right: `43`' not in wrong:
    raise RuntimeError('Engine output/control diagnostic is not the expected assertion')
restored = command('engine-restored', offline, env)
if 'actual=42 expected=42 spawn_reserved=true' not in restored:
    raise RuntimeError('restored Engine marker missing')
(EVIDENCE / 'source.txt').write_text(f'revision={REVISION}\narchive_sha256={archive_sha}\nlock_sha256={hashlib.sha256(lock.read_bytes()).hexdigest()}\n')
(EVIDENCE / 'result.txt').write_text('default core Rust1.66 check0 Engine42 wrong43 assertion101 restored0; not optional/platform matrix proof\n')
(EVIDENCE / 'sampled-resources.txt').write_text(
    f'storage_kib={PEAK_STORAGE_KIB}\nrss_kib={PEAK_RSS_KIB}\ndescendants={PEAK_DESCENDANTS}\n'
    'Approximately one-second and post-setup samples; not continuous peak or byte accounting\n')
print('core_current_msrv_proof=pass', flush=True)
