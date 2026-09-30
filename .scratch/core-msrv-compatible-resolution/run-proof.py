#!/usr/bin/env python3
import os
import pathlib
import shutil
import subprocess
import sys
import time

repo = pathlib.Path('/Users/hoppworks/projects/rhai-core-msrv-resolution')
evidence = repo / '.scratch/core-msrv-compatible-resolution'
runtime = pathlib.Path(os.environ['AGENT_RUNTIME_DIR'])
source = runtime / 'source'
home = runtime / 'cargo-home'
target = runtime / 'target'
home.mkdir()
source.mkdir()
(home / 'registry').mkdir()

# Copy read-only local Cargo caches into the private runtime. Do not copy user config.
for part in ('cache', 'index'):
    shutil.copytree(pathlib.Path('/Users/hoppworks/.cargo/registry') / part, home / 'registry' / part)
shutil.copytree(pathlib.Path('/Users/hoppworks/.cargo/git'), home / 'git')
archive = subprocess.run(['git', '-C', str(repo), 'archive', 'c4646230e5c757beafab93b3978ab5afc6b15c6f'], check=True, stdout=subprocess.PIPE)
subprocess.run(['tar', '-x', '-C', str(source)], input=archive.stdout, check=True)

env = dict(os.environ)
env['CARGO_HOME'] = str(home)
env['CARGO_TARGET_DIR'] = str(target)
env.pop('CARGO_NET_OFFLINE', None)
env.pop('CARGO_HOME_CONFIG', None)


def runtime_size_kib():
    output = subprocess.check_output(['du', '-sk', str(runtime)], text=True)
    return int(output.split()[0])


def run(label, command, lock_export=False):
    log = evidence / (label + '.log')
    print(f'COMMAND {label}: {" ".join(command)}', flush=True)
    print(f'LOG {log}', flush=True)
    with log.open('w') as stream:
        process = subprocess.Popen(command, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            stream.write(line)
        result = process.wait()
    print(f'STATUS {label}: {result}', flush=True)
    size = runtime_size_kib()
    print(f'PRIVATE_RUNTIME_SAMPLED_STORAGE {label}: {size} KiB (du -sk after command)', flush=True)
    if size > 2 * 1024 * 1024:
        raise RuntimeError(f'private storage bound exceeded: {size} KiB')
    if lock_export:
        lock = source / 'Cargo.lock'
        if lock.exists():
            shutil.copy2(lock, evidence / 'Cargo.lock')
            print(f'EXPORTED_LOCK {evidence / "Cargo.lock"}', flush=True)
    return result


print('SOURCE c4646230e5c757beafab93b3978ab5afc6b15c6f', flush=True)
print(f'PRIVATE_RUNTIME {runtime}', flush=True)
print(f'PRIVATE_RUNTIME_INITIAL_STORAGE {runtime_size_kib()} KiB (du -sk after private cache/source copy)', flush=True)
if runtime_size_kib() > 2 * 1024 * 1024:
    raise RuntimeError('private storage bound exceeded before Cargo')

# Modern Cargo only prepares the resolution, using locally cached index data. Its
# fallback policy prefers dependency versions declaring compatibility with 1.66.
result = run('resolve', ['cargo', '+stable', 'generate-lockfile', '--config', 'resolver.incompatible-rust-versions="fallback"'], lock_export=True)
if result:
    sys.exit(result)
# Keep the complete upstream manifests and workspace. Cargo 1.66 rejects the
# latest inactive wasm js-sys feature graph, so select a compatible release in
# this exact resolution rather than editing or pruning any manifest.
# Unlock only js-sys' exact wasm-bindgen dependency family, then let Cargo
# recompute that family while applying the precise js-sys compatibility version.
lock = source / 'Cargo.lock'
parts = lock.read_text().split('[[package]]')
family = {'wasm-bindgen', 'wasm-bindgen-macro', 'wasm-bindgen-macro-support', 'wasm-bindgen-shared'}
kept = []
removed = []
for part in parts:
    if any(f'name = "{name}"' in part for name in family):
        removed.append(next(name for name in family if f'name = "{name}"' in part))
    else:
        kept.append(part)
if set(removed) != family:
    raise RuntimeError(f'expected to unlock only the four locked wasm-bindgen family packages, found {removed}')
lock.write_text('[[package]]'.join(kept))
print('UNLOCKED_LOCK_PACKAGES: ' + ', '.join(sorted(removed)), flush=True)
update_result = run('compatibility-lock-update', ['cargo', '+stable', 'update', '-p', 'js-sys', '--precise', '0.3.91'], lock_export=True)
if update_result:
    print('LOCK_UPDATE_BOUNDARY: Cargo could not select the compatible js-sys/wasm-bindgen family from the original full graph; keep original manifests and stop rather than narrow the manifest.', flush=True)
    sys.exit(update_result)
lock = source / 'Cargo.lock'
if not lock.exists():
    raise RuntimeError('Cargo did not create a lockfile')
lock_text = lock.read_text()
# The generated v4 lock schema uses entries also understood by Cargo 1.66 once the
# schema marker is set to v3. Verify with old Cargo metadata before the build.
lock_text = lock_text.replace('version = 4\n', 'version = 3\n', 1)
lock.write_text(lock_text)
shutil.copy2(lock, evidence / 'Cargo.lock')
print('LOCK_SCHEMA: normalized marker to version 3; next step checks Cargo 1.66 parser', flush=True)
print('OLD_CARGO_METADATA_DIAGNOSTIC: a preliminary metadata invocation on the full workspace rejected inactive wasm web-time/js-sys feature syntax; preserving it as an out-of-scope workspace boundary and attempting the requested direct core library check.', flush=True)
result = run('core-check', ['cargo', '+1.66.0', 'check', '--lib', '--locked', '--target', 'aarch64-apple-darwin'], lock_export=True)
if result:
    sys.exit(result)

# This temporary example executes a real Rhai Engine and preserves both a passing
# expected-result assertion and an intentional wrong-result control.
example = source / 'examples' / 'core_msrv_eval.rs'
example.parent.mkdir(parents=True, exist_ok=True)
example.write_text('''use rhai::Engine;\nfn main() {\n    let engine = Engine::new();\n    let actual: i64 = engine.eval("40 + 2").expect("script evaluation");\n    let expected = if std::env::args().any(|arg| arg == "--wrong-result-control") { 43 } else { 42 };\n    assert_eq!(actual, expected, "Engine result must match independently specified expectation");\n    println!("Engine evaluated 40 + 2 to {actual}; expected {expected}");\n}\n''')
result = run('engine-positive', ['cargo', '+1.66.0', 'run', '--locked', '--target', 'aarch64-apple-darwin', '--example', 'core_msrv_eval'])
if result:
    sys.exit(result)
result = run('engine-wrong-control', ['cargo', '+1.66.0', 'run', '--locked', '--target', 'aarch64-apple-darwin', '--example', 'core_msrv_eval', '--', '--wrong-result-control'])
if result == 0:
    raise RuntimeError('intentional wrong-result control unexpectedly passed')
print('WRONG_RESULT_CONTROL: expected nonzero status observed', flush=True)
