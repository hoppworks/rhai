"""Freeze the 4-MiB stream contract and adapt the reviewed native route."""
import hashlib
import io
import json
import subprocess
import tarfile
import uuid
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
old = root.parent / 'argv-attempt01'
media = root / 'media-input'
media.mkdir(exist_ok=False)
nonce = uuid.uuid4().hex
prior = json.loads((old / 'binding.json').read_text())
prior_manifest = json.loads((old / 'media-input/source-manifest.json').read_text())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert head == '6dc2565bebe137063c218cc90fa748d24559d1a5'
paths = prior_manifest['selected_paths']
archive = subprocess.check_output(['git', 'archive', head, '--', *paths])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    files = {item.name: tar.extractfile(item).read() for item in tar if item.isfile()}
assert len(files) == 450
test_path = 'tests/sys_process_windows_streams.rs'
files[test_path] = (Path.cwd() / test_path).read_bytes()
assert len(files) == 451
def sha(data): return hashlib.sha256(data).hexdigest()
zip_path = media / 'rhai-source.zip'
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as out:
    for name, data in sorted(files.items()): out.writestr(name, data)
manifest = {'source_commit': head, 'git_source_only': False,
    'source_overlays': {test_path: sha(files[test_path])}, 'selected_paths': paths,
    'file_count': len(files), 'total_source_bytes': sum(map(len, files.values())),
    'archive_sha256': sha(zip_path.read_bytes()), 'archive_bytes': zip_path.stat().st_size,
    'files': {name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(files.items())}}
manifest_path = media / 'source-manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
lock = (old / 'media-input/Cargo.lock').read_bytes()
(media / 'Cargo.lock').write_bytes(lock)
assert sha(lock) == prior['lock_sha256']
def read(name): return (old / 'media-input' / name).read_text()
def write(name, data, crlf=False):
    data = data.replace('\r\n', '\n')
    if crlf: data = data.replace('\n', '\r\n')
    (media / name).write_bytes(data.encode())
    return sha((media / name).read_bytes())
def replace(data, before, after):
    assert before in data, before
    return data.replace(before, after)

clear_hash = write('ClearOwnedWorkReadOnly.ps1', replace(read('ClearOwnedWorkReadOnly.ps1'), prior['nonce'][:8], nonce[:8]))
old_command = read('RunRhaiContract.cmd')
header = old_command[:old_command.index('set PROFILE=')]
labels = ['direct-run', 'direct-raw', 'direct-spawn', 'managed-run', 'managed-raw', 'managed-spawn']
controls = [(label, stream) for label in labels for stream in ('stdout', 'stderr')]
command = header + 'set PROFILE=testing-environ,sys,net\nset TARGET=--test sys_process_windows_streams\nset "COMPILE_RC=999"\nset "SUITE_RC=999"\n'
for label, stream in controls:
    key = (label + '_' + stream).replace('-', '_').upper()
    command += f'set "{key}_RC=999"\n'
command += '"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1\nset "COMPILE_RC=!ERRORLEVEL!"\nif not "!COMPILE_RC!"=="0" goto cleanup\n'
for label, stream in controls:
    key = (label + '_' + stream).replace('-', '_').upper()
    selector = 'windows_stream_' + label.replace('-', '_')
    command += f'set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION={stream}\n"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% {selector} -- --exact --nocapture > {label}-{stream}-wrong.log 2>&1\nset "{key}_RC=!ERRORLEVEL!"\n'
command += 'set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=\n'
for label, stream in controls:
    key = (label + '_' + stream).replace('-', '_').upper()
    command += f'if not "!{key}_RC!"=="101" goto cleanup\nfindstr /C:"STREAM_WRONG_{stream.upper()} {label}" {label}-{stream}-wrong.log > NUL || goto cleanup\nfindstr /C:"test result: FAILED. 0 passed; 1 failed;" {label}-{stream}-wrong.log > NUL || goto cleanup\n'
command += '"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > streams-suite.log 2>&1\nset "SUITE_RC=!ERRORLEVEL!"\n'
command += old_command[old_command.index(':cleanup'):old_command.index('echo RHAI_ARGV_COMPILE_EXIT=')]
command += 'echo RHAI_STREAM_COMPILE_EXIT=!COMPILE_RC!\n'
for label, stream in controls:
    key = (label + '_' + stream).replace('-', '_').upper()
    command += f'echo RHAI_STREAM_{key}_EXIT=!{key}_RC!\n'
command += 'echo RHAI_STREAM_SUITE_EXIT=!SUITE_RC!\nif not "!COMPILE_RC!"=="0" exit /b 59\n'
for label, stream in controls:
    key = (label + '_' + stream).replace('-', '_').upper()
    command += f'if not "!{key}_RC!"=="101" exit /b 61\n'
command += 'if not "!SUITE_RC!"=="0" exit /b 65\necho RHAI_STREAM_CONTROLS_PASS\nexit /b 0\n'
command_hash = write('RunRhaiContract.cmd', command, True)

control = read('RunRhaiContractControl.ps1')
control = replace(control, prior['nonce'][:8], nonce[:8])
control = replace(control, prior['source_manifest_sha256'], sha(manifest_path.read_bytes()))
start = control.index("  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'")
end = control.index("  $journal=@(Get-ChildItem", start)
quote = lambda value: "'" + value + "'"
markers = ['RHAI_READONLY_ALIAS_SCOPE_CONFIRMED', 'RHAI_WORK_READONLY_CLEARED', 'RHAI_CARGO_CLEAN_EXIT=0', 'RHAI_STREAM_COMPILE_EXIT=0'] + ['RHAI_STREAM_' + (label + '_' + stream).replace('-', '_').upper() + '_EXIT=101' for label, stream in controls] + ['RHAI_STREAM_SUITE_EXIT=0', 'RHAI_STREAM_CONTROLS_PASS']
checks = '  foreach($line in @(' + ','.join(map(quote, markers)) + ')){if(!$payloadOutput.Contains($line)){throw "Native stream marker missing: $line"}}\n'
checks += "  if(!$compile.Contains('tests\\sys_process_windows_streams.rs')){throw 'Native stream target was not compiled.'}\n"
checks += "  $cargoVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\cargo-version.txt')).Trim()\n  $rustcVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\rustc-version.txt')).Trim()\n"
checks += "  if($cargoVersionFile -cne 'cargo 1.77.2 (e52e36006 2024-03-26)' -or $rustcVersionFile -cne 'rustc 1.77.2 (25ef9e3d8 2024-04-09)'){throw 'Native MSRV versions differ inside the supervised run.'}\n"
for label, stream in controls:
    checks += f"  $actual=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\{label}-{stream}-wrong.log'))\n"
    tokens = ['windows_stream_readback label=' + label, 'STREAM_WRONG_' + stream.upper() + ' ' + label, 'test result: FAILED. 0 passed; 1 failed;']
    checks += "  foreach($token in @(" + ','.join(map(quote, tokens)) + ")){if(!$actual.Contains($token)){throw \"Native stream control missing: $token\"}}\n"
checks += "  $actual=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\streams-suite.log'))\n"
checks += "  foreach($token in @(" + ','.join(map(quote, ['windows_stream_readback label=' + x for x in labels] + ['test result: ok. 7 passed; 0 failed; 0 ignored;'])) + ")){if(!$actual.Contains($token)){throw \"Native stream suite missing: $token\"}}\n"
checks += "  $productTestRun=$true;$actualOutcome='pass';$wrongExpectationRejected=$true\n"
control = control[:start] + checks + control[end:]
old_logs = ','.join(quote('runtime\\' + label + '-wrong.log') for label in labels) + ",'runtime\\argv-suite.log'"
new_logs = ','.join(quote('runtime\\' + label + '-' + stream + '-wrong.log') for label, stream in controls) + ",'runtime\\streams-suite.log'"
control = replace(control, old_logs, new_logs)
control_hash = write('RunRhaiContractControl.ps1', control)

startscript = read('Start.ps1')
for before, after in [(prior['nonce'], nonce), (prior['archive_sha256'], manifest['archive_sha256']),
    (prior['source_manifest_sha256'], sha(manifest_path.read_bytes())),
    (prior['media_files']['RunRhaiContractControl.ps1']['sha256'], control_hash),
    (prior['media_files']['RunRhaiContract.cmd']['sha256'], command_hash),
    (prior['media_files']['ClearOwnedWorkReadOnly.ps1']['sha256'], clear_hash),
    (prior['base_head'], head), (str(prior_manifest['total_source_bytes']), str(manifest['total_source_bytes'])),
    ('-ne 450', '-ne 451'), ('source_files=450;staged_files=455', 'source_files=451;staged_files=456')]:
    startscript = replace(startscript, before, after)
start_hash = write('Start.ps1', startscript)
write('rhai-native-' + nonce + '.bundle', 'rhai-native-' + nonce + '\n')
media_files = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in media.iterdir()}
assert len(media_files) == 8
binding = {'nonce': nonce, 'base_head': head, 'overlay_sha256': sha(files[test_path]),
    'source_manifest_sha256': sha(manifest_path.read_bytes()), 'archive_sha256': manifest['archive_sha256'],
    'lock_sha256': sha(lock), 'features': 'testing-environ,sys,net', 'target': 'sys_process_windows_streams',
    'test': 'windows_stream_direct_run', 'media_files': media_files,
    'driver_deadline_seconds': 180, 'observer_deadline_seconds': 185, 'export_deadline_seconds': 180,
    'start_sha256': start_hash, 'native_started': False}
(root / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
print(json.dumps({'head': head, 'test_sha256': binding['overlay_sha256'], 'files': len(files), 'nonce': nonce}))
