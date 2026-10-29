"""One bounded macOS 1.66 full core suite from a pinned, private source copy."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

repo = Path('/Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai')
proof = repo / '.scratch/all-tickets/release-matrix-20261028/macos-core-166-full'
runtime = Path(os.environ['AGENT_RUNTIME_DIR'])
assert runtime.is_dir() and str(runtime).startswith('/Users/hoppworks/.local/share/agent-builds/rhai/')
head = '8d8bf84febebb182ca65f2307f96676f05858eb2'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == head
reference = json.loads((repo / '.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/cwd-reparse-probe-attempt01/media-input/source-manifest.json').read_text())
archive = subprocess.check_output(['git', 'archive', head, '--', *reference['selected_paths']], cwd=repo)
source = runtime / 'source'
source.mkdir()
members = {}
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    for entry in tar:
        if not entry.isfile():
            assert entry.isdir(), entry.name
            continue
        assert not entry.name.startswith('/') and '..' not in Path(entry.name).parts
        data = tar.extractfile(entry).read()
        target = source / entry.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        members[entry.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
assert len(members) == 451
overlay = (repo / 'src/tests.rs').read_bytes()
(source / 'src/tests.rs').write_bytes(overlay)
members['src/tests.rs'] = {'bytes': len(overlay), 'sha256': hashlib.sha256(overlay).hexdigest()}
lock = (repo / '.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/cwd-reparse-probe-attempt01/media-input/Cargo.lock').read_bytes()
assert hashlib.sha256(lock).hexdigest() == '12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802'
(source / 'Cargo.lock').write_bytes(lock)
env = dict(os.environ)
cache = runtime / 'cargo-home'
cache.mkdir()
for name in ('registry', 'git'):
    shutil.copytree(Path.home() / '.cargo' / name, cache / name)
env.update(CARGO_HOME=str(runtime / 'cargo-home'), CARGO_TARGET_DIR=str(runtime / 'target'),
           CARGO_INCREMENTAL='0', CARGO_BUILD_JOBS='2', CARGO_PROFILE_TEST_DEBUG='0',
           CARGO_PROFILE_TEST_CODEGEN_UNITS='256', RUSTUP_TOOLCHAIN='1.66.0-aarch64-apple-darwin',
           CARGO_NET_OFFLINE='false')
for name in ('RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_BUILD_RUSTC'):
    env.pop(name, None)
commands = [['rustc', '--version'], ['cargo', '--version'],
            ['cargo', 'test', '--locked', '--lib', '--target', 'aarch64-apple-darwin']]
results = []
try:
    for index, command in enumerate(commands):
        start = time.monotonic()
        with (proof / f'command-{index}.log').open('wb') as output:
            completed = subprocess.run(command, cwd=source, env=env, stdout=output,
                                       stderr=subprocess.STDOUT, timeout=840 if index == 2 else 15)
        results.append({'argv': command, 'exit': completed.returncode,
                        'elapsed_seconds': round(time.monotonic()-start, 3),
                        'sha256': hashlib.sha256((proof / f'command-{index}.log').read_bytes()).hexdigest()})
        if completed.returncode != 0:
            break
finally:
    (proof / 'result.json').write_text(json.dumps({
        'source_commit': head, 'source_files': len(members),
        'test_overlay_sha256': hashlib.sha256(overlay).hexdigest(),
        'source_manifest_sha256': hashlib.sha256(json.dumps(members, sort_keys=True).encode()).hexdigest(),
        'lock_sha256': hashlib.sha256(lock).hexdigest(), 'runner_runtime': str(runtime),
        'commands': results, 'complete': len(results)==3 and all(x['exit']==0 for x in results),
    }, indent=2)+'\n')
assert len(results) == 3 and all(x['exit'] == 0 for x in results)
