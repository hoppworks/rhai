"""Freeze the revised cwd tests and adapt the existing native RED control."""
import hashlib
import io
import json
import subprocess
import tarfile
import uuid
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
old = root.parent / 'cwd-baseline-attempt01'
media = root / 'media-input'
media.mkdir(exist_ok=False)
nonce = uuid.uuid4().hex
old_binding = json.loads((old / 'binding.json').read_text())
old_manifest = json.loads((old / 'media-input/source-manifest.json').read_text())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert head == '6dc2565bebe137063c218cc90fa748d24559d1a5'
paths = old_manifest['selected_paths']
archive = subprocess.check_output(['git', 'archive', head, '--', *paths])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    files = {item.name: tar.extractfile(item).read() for item in tar if item.isfile()}
assert len(files) == 450
test_path = 'tests/sys_process_windows.rs'
files[test_path] = (Path.cwd() / test_path).read_bytes()
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
assert sha(lock) == old_binding['lock_sha256']
def read(name): return (old / 'media-input' / name).read_text()
def write(name, data, crlf=False):
    data = data.replace('\r\n', '\n')
    if crlf: data = data.replace('\n', '\r\n')
    (media / name).write_bytes(data.encode())
    return sha((media / name).read_bytes())
def replace(data, before, after):
    assert before in data, before
    return data.replace(before, after)

clear_hash = write('ClearOwnedWorkReadOnly.ps1', replace(read('ClearOwnedWorkReadOnly.ps1'), old_binding['nonce'][:8], nonce[:8]))
command = read('RunRhaiContract.cmd')
old_baseline = 'set "BASELINE_RC=!ERRORLEVEL!"\n:cleanup'
new_baseline = '''set "BASELINE_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_CWD_REQUIRE_JOB=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_cwd_keeps_configured_root_when_rename_is_refused -- --exact --nocapture > cwd-root.log 2>&1
set "ROOT_RC=!ERRORLEVEL!"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_cwd_rejects_outside_and_missing_directories -- --exact --nocapture > cwd-denial.log 2>&1
set "DENIAL_RC=!ERRORLEVEL!"
echo RHAI_CWD_REQUIRE_JOB=1
:cleanup'''
command = replace(command, 'set "BASELINE_RC=999"', 'set "BASELINE_RC=999"\nset "ROOT_RC=999"\nset "DENIAL_RC=999"')
command = replace(command, old_baseline, new_baseline)
command = replace(command, 'echo RHAI_CWD_BASELINE_EXIT=!BASELINE_RC!', 'echo RHAI_CWD_BASELINE_EXIT=!BASELINE_RC!\necho RHAI_CWD_ROOT_EXIT=!ROOT_RC!\necho RHAI_CWD_DENIAL_EXIT=!DENIAL_RC!')
command = replace(command, 'echo RHAI_CWD_BASELINE_REPRODUCED', '''if not "!ROOT_RC!"=="101" exit /b 65
if not "!DENIAL_RC!"=="101" exit /b 66
findstr /C:"windows_cwd_root_rename_refused label=direct-run" cwd-root.log > NUL || exit /b 67
findstr /C:"CWD_ROOT_IDENTITY direct-run" cwd-root.log > NUL || exit /b 68
findstr /C:"windows_cwd_rejected mode=direct-run label=outside" cwd-denial.log > NUL || exit /b 69
findstr /C:"missing cwd error" cwd-denial.log > NUL || exit /b 70
for %%F in (cwd-root.log cwd-denial.log) do findstr /C:"test result: FAILED. 0 passed; 1 failed;" %%F > NUL || exit /b 71
echo RHAI_CWD_BASELINE_REPRODUCED''')
command_hash = write('RunRhaiContract.cmd', command, True)
control = read('RunRhaiContractControl.ps1')
control = replace(control, old_binding['nonce'][:8], nonce[:8])
control = replace(control, old_binding['source_manifest_sha256'], sha(manifest_path.read_bytes()))
control = replace(control, "'RHAI_CWD_BASELINE_EXIT=101','RHAI_CWD_BASELINE_REPRODUCED'", "'RHAI_CWD_BASELINE_EXIT=101','RHAI_CWD_ROOT_EXIT=101','RHAI_CWD_DENIAL_EXIT=101','RHAI_CWD_REQUIRE_JOB=1','RHAI_CWD_BASELINE_REPRODUCED'")
insertion = '''  $rootControl=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\cwd-root.log'))
  foreach($token in @('windows_cwd_root_rename_refused label=direct-run','CWD_ROOT_IDENTITY direct-run','unsupported Windows process option','test result: FAILED. 0 passed; 1 failed;')){if(!$rootControl.Contains($token)){throw "Cwd root baseline missing: $token"}}
  $denial=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\cwd-denial.log'))
  foreach($token in @('windows_cwd_rejected mode=direct-run label=outside','job_total_before=Some(','job_total_after=Some(','missing cwd error','test result: FAILED. 0 passed; 1 failed;')){if(!$denial.Contains($token)){throw "Cwd denial baseline missing: $token"}}
'''
control = replace(control, "  $productTestRun=$true;$actualOutcome='expected-red';$baselineReproduced=$true", insertion + "  $productTestRun=$true;$actualOutcome='expected-red';$baselineReproduced=$true")
control = replace(control, "'runtime\\compile.log','runtime\\cwd-baseline.log','runtime\\cargo-clean.log'", "'runtime\\compile.log','runtime\\cwd-baseline.log','runtime\\cwd-root.log','runtime\\cwd-denial.log','runtime\\cargo-clean.log'")
control_hash = write('RunRhaiContractControl.ps1', control)
start = read('Start.ps1')
for before, after in [(old_binding['nonce'], nonce), (old_binding['archive_sha256'], manifest['archive_sha256']),
    (old_binding['source_manifest_sha256'], sha(manifest_path.read_bytes())),
    (old_binding['media_files']['RunRhaiContractControl.ps1']['sha256'], control_hash),
    (old_binding['media_files']['RunRhaiContract.cmd']['sha256'], command_hash),
    (old_binding['media_files']['ClearOwnedWorkReadOnly.ps1']['sha256'], clear_hash),
    (old_binding['base_head'], head), (str(old_manifest['total_source_bytes']), str(manifest['total_source_bytes'])),
    ('-ne 448', '-ne 450'), ('source_files=453', 'source_files=450;staged_files=455')]:
    start = replace(start, before, after)
start_hash = write('Start.ps1', start)
write('rhai-native-' + nonce + '.bundle', 'rhai-native-' + nonce + '\n')
media_files = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in media.iterdir()}
assert len(media_files) == 8
binding = {'nonce': nonce, 'base_head': head, 'overlay_sha256': sha(files[test_path]),
    'source_manifest_sha256': sha(manifest_path.read_bytes()), 'archive_sha256': manifest['archive_sha256'],
    'lock_sha256': sha(lock), 'features': 'testing-environ,sys,net', 'target': 'sys_process_windows',
    'test': 'windows_cwd_uses_allowed_directory_without_mutating_parent', 'media_files': media_files,
    'driver_deadline_seconds': 180, 'observer_deadline_seconds': 185, 'export_deadline_seconds': 180,
    'start_sha256': start_hash, 'native_started': False}
(root / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
print(json.dumps({'head': head, 'test_sha256': binding['overlay_sha256'], 'files': len(files), 'nonce': nonce}))
