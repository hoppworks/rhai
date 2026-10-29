"""Freeze an isolated native reparse investigation and its custody route."""
import hashlib
import io
import json
import subprocess
import tarfile
import uuid
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
old = root.parent / 'cwd-reparse-probe-attempt01'
media = root / 'media-input'
media.mkdir(exist_ok=False)
nonce = uuid.uuid4().hex
prior = json.loads((old / 'binding.json').read_text())
prior_manifest = json.loads((old / 'media-input/source-manifest.json').read_text())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert head == 'b2608fc7c0682c760a4e9599e2616318ad680563'
paths = prior_manifest['selected_paths']
archive = subprocess.check_output(['git', 'archive', head, '--', *paths])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    files = {item.name: tar.extractfile(item).read() for item in tar if item.isfile()}
assert len(files) == 451
test_path = 'tests/sys_windows_reparse_probe.rs'
files[test_path] = (root / 'probe.rs').read_bytes()
assert len(files) == 452
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
selector = 'suspended_cwd_candidate_identity_and_reparse'
command = header + '''set PROFILE=testing-environ,sys,net
set TARGET=--test sys_windows_reparse_probe
set "COMPILE_RC=999"
set "WRONG_RC=999"
set "SUITE_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_SUSPENDED_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% ''' + selector + ''' -- --exact --nocapture > suspended-wrong.log 2>&1
set "WRONG_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SUSPENDED_WRONG_EXPECTATION=
if not "!WRONG_RC!"=="101" goto cleanup
findstr /C:"SUSPENDED_WRONG_EXPECTATION" suspended-wrong.log > NUL || goto cleanup
findstr /C:"windows_reparse_probe_cleanup exact_junction_removed=true" suspended-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" suspended-wrong.log > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% ''' + selector + ''' -- --exact --test-threads=1 --nocapture > suspended-suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!"
'''
command += old_command[old_command.index(':cleanup'):old_command.index('echo RHAI_REPARSE_COMPILE_EXIT=')]
command += '''echo RHAI_SUSPENDED_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_SUSPENDED_WRONG_EXIT=!WRONG_RC!
echo RHAI_SUSPENDED_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!WRONG_RC!"=="101" exit /b 61
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_SUSPENDED_CONTROLS_PASS
exit /b 0
'''
command_hash = write('RunRhaiContract.cmd', command, True)

control = read('RunRhaiContractControl.ps1')
control = replace(control, prior['nonce'][:8], nonce[:8])
control = replace(control, prior['source_manifest_sha256'], sha(manifest_path.read_bytes()))
start = control.index("  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'")
end = control.index("  $journal=@(Get-ChildItem", start)
checks = '''  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_CARGO_CLEAN_EXIT=0','RHAI_SUSPENDED_COMPILE_EXIT=0','RHAI_SUSPENDED_WRONG_EXIT=101','RHAI_SUSPENDED_SUITE_EXIT=0','RHAI_SUSPENDED_CONTROLS_PASS')){if(!$payloadOutput.Contains($line)){throw "Native suspended marker missing: $line"}}
  if(!$compile.Contains('tests\\sys_windows_reparse_probe.rs')){throw 'Native reparse target was not compiled.'}
  $cargoVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\cargo-version.txt')).Trim()
  $rustcVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\rustc-version.txt')).Trim()
  if($cargoVersionFile -cne 'cargo 1.77.2 (e52e36006 2024-03-26)' -or $rustcVersionFile -cne 'rustc 1.77.2 (25ef9e3d8 2024-04-09)'){throw 'Native MSRV versions differ inside the supervised run.'}
  $wrong=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\suspended-wrong.log'))
  foreach($token in @('windows_suspended_probe_fixture_root=','windows_suspended_probe equal_before=true redirected_differs=true','SUSPENDED_WRONG_EXPECTATION','windows_reparse_probe_cleanup exact_junction_removed=true','test result: FAILED. 0 passed; 1 failed;')){if(!$wrong.Contains($token)){throw "Native suspended control missing: $token"}}
  $suite=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\suspended-suite.log'))
  foreach($token in @('windows_suspended_probe_fixture_root=','windows_suspended_probe equal_before=true redirected_differs=true','windows_reparse_probe_cleanup exact_junction_removed=true','test result: ok. 1 passed; 0 failed;')){if(!$suite.Contains($token)){throw "Native suspended suite missing: $token"}}
  $productTestRun=$false;$actualOutcome='prototype-pass';$wrongExpectationRejected=$true
'''
control = control[:start] + checks + control[end:]
labels = ['direct-run','direct-raw','direct-spawn','managed-run','managed-raw','managed-spawn']
quote = lambda value: "'" + value + "'"
control = replace(control, "'runtime\\reparse-wrong.log','runtime\\reparse-suite.log'", "'runtime\\suspended-wrong.log','runtime\\suspended-suite.log'")
control_hash = write('RunRhaiContractControl.ps1', control)

startscript = read('Start.ps1')
for before, after in [(prior['nonce'], nonce), (prior['archive_sha256'], manifest['archive_sha256']),
    (prior['source_manifest_sha256'], sha(manifest_path.read_bytes())),
    (prior['media_files']['RunRhaiContractControl.ps1']['sha256'], control_hash),
    (prior['media_files']['RunRhaiContract.cmd']['sha256'], command_hash),
    (prior['media_files']['ClearOwnedWorkReadOnly.ps1']['sha256'], clear_hash),
    (prior['base_head'], head), (str(prior_manifest['total_source_bytes']), str(manifest['total_source_bytes']))]:
    startscript = replace(startscript, before, after)
start_hash = write('Start.ps1', startscript)
write('rhai-native-' + nonce + '.bundle', 'rhai-native-' + nonce + '\n')
media_files = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in media.iterdir()}
assert len(media_files) == 8
binding = {'nonce': nonce, 'base_head': head, 'overlay_sha256': sha(files[test_path]),
    'source_manifest_sha256': sha(manifest_path.read_bytes()), 'archive_sha256': manifest['archive_sha256'],
    'lock_sha256': sha(lock), 'features': 'testing-environ,sys,net', 'target': 'sys_windows_reparse_probe',
    'test': selector, 'media_files': media_files, 'driver_deadline_seconds': 180,
    'observer_deadline_seconds': 185, 'export_deadline_seconds': 180, 'start_sha256': start_hash,
    'native_started': False}
(root / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
print(json.dumps({'head': head, 'test_sha256': binding['overlay_sha256'], 'files': len(files), 'nonce': nonce}))
