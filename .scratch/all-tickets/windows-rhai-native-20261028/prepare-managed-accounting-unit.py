"""Freeze one native test-only Job accounting retry contract in the existing runner."""
from pathlib import Path
import hashlib
import json
import secrets
import shutil
import zipfile

root = Path.cwd()
base = root / '.scratch/all-tickets/windows-rhai-native-20261028'
old = base / 'attempt55'
new = base / 'attempt56'
new.mkdir()
media = new / 'media-input'
media.mkdir()
previous = json.loads((old / 'binding.json').read_text())
nonce = secrets.token_hex(16)
sha = lambda data: hashlib.sha256(data).hexdigest()
file_sha = lambda path: sha(path.read_bytes())
files = sorted(json.loads((old / 'media-input/source-manifest.json').read_text())['files'])
entries = {}
with zipfile.ZipFile(media / 'rhai-source.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in files:
        data = (root / name).read_bytes()
        entries[name] = {'bytes': len(data), 'sha256': sha(data)}
        archive.writestr(name, data)
archive_data = (media / 'rhai-source.zip').read_bytes()
manifest = {'archive_bytes': len(archive_data), 'archive_sha256': sha(archive_data),
            'file_count': len(files), 'files': entries, 'source_commit': previous['source_commit'],
            'source_dirty': True, 'total_source_bytes': sum(entry['bytes'] for entry in entries.values())}
(media / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
shutil.copyfile(old / 'media-input/Cargo.lock', media / 'Cargo.lock')
helper = (old / 'media-input/ClearOwnedWorkReadOnly.ps1').read_bytes()
assert ('n-' + previous['nonce'][:8]).encode() in helper
(media / 'ClearOwnedWorkReadOnly.ps1').write_bytes(
    helper.replace(('n-' + previous['nonce'][:8]).encode(), ('n-' + nonce[:8]).encode()))
(media / ('rhai-native-' + nonce + '.bundle')).write_text('rhai-native-' + nonce + '\n')

selector = 'packages::sys::process::windows::tests::windows_background_retries_after_job_accounting_observation_error'
cmd = r'''@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib --no-run > compile.log 2>&1
if errorlevel 1 exit /b 59
set RHAI_WINDOWS_ACCOUNTING_RETRY_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib SELECTOR -- --exact --nocapture > wrong.log 2>&1
set WRONG_RC=!ERRORLEVEL!
set RHAI_WINDOWS_ACCOUNTING_RETRY_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib SELECTOR -- --exact --nocapture > green.log 2>&1
set GREEN_RC=!ERRORLEVEL!
echo RHAI_ACCOUNTING_RETRY_WRONG_EXIT=!WRONG_RC!
echo RHAI_ACCOUNTING_RETRY_GREEN_EXIT=!GREEN_RC!
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_ACCOUNTING_RETRY_CLEANED
if not "!WRONG_RC!"=="101" exit /b 61
findstr /C:"deliberately wrong Job accounting retry expectation" wrong.log > NUL || exit /b 62
if not "!GREEN_RC!"=="0" exit /b 63
findstr /C:"test result: ok. 1 passed; 0 failed;" green.log > NUL || exit /b 64
echo RHAI_ACCOUNTING_RETRY_CONTROL_PASS
exit /b 0
'''.replace('SELECTOR', selector)
(media / 'RunRhaiContract.cmd').write_bytes(cmd.replace('\n', '\r\n').encode())
control = (old / 'media-input/RunRhaiContractControl.ps1').read_text()
control = control.replace(previous['nonce'], nonce).replace(previous['nonce'][:8], nonce[:8])
control = control.replace(previous['manifest_sha256'], file_sha(media / 'source-manifest.json'))
begin = control.index("  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'")
end = control.index('  $journal=@(', begin)
control = control[:begin] + r'''  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_ACCOUNTING_RETRY_CLEANED','RHAI_ACCOUNTING_RETRY_WRONG_EXIT=101','RHAI_ACCOUNTING_RETRY_GREEN_EXIT=0','RHAI_ACCOUNTING_RETRY_CONTROL_PASS')){if(!$payloadOutput.Contains($line)){throw "Managed accounting retry marker missing: $line"}}
  if(!$compile.Contains('rhai')){throw 'Native library test compile evidence missing.'}
  $wrong=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\wrong.log'))
  $green=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\green.log'))
  foreach($line in @('windows_managed_accounting_retry_readback attempts=2 accounting_errors=1 exact_child_stopped=true owner_retired=true','deliberately wrong Job accounting retry expectation','test result: FAILED. 0 passed; 1 failed;')){if(!$wrong.Contains($line)){throw "Accounting retry wrong control missing: $line"}}
  foreach($line in @('windows_managed_accounting_retry_readback attempts=2 accounting_errors=1 exact_child_stopped=true owner_retired=true','test result: ok. 1 passed; 0 failed;')){if(!$green.Contains($line)){throw "Accounting retry green proof missing: $line"}}
  $productTestRun=$true;$actualOutcome='pass';$wrongExpectationRejected=$true
''' + control[end:]
control = control.replace("'runtime\\kill-wrong.log','runtime\\retain-wrong.log','runtime\\green.log'", "'runtime\\wrong.log','runtime\\green.log'")
(media / 'RunRhaiContractControl.ps1').write_text(control)
start = (old / 'media-input/Start.ps1').read_text()
replacements = {previous['nonce']: nonce, previous['archive_sha256']: manifest['archive_sha256'],
                previous['manifest_sha256']: file_sha(media / 'source-manifest.json'),
                str(previous['source_bytes']): str(manifest['total_source_bytes'])}
for name in ('RunRhaiContractControl.ps1', 'RunRhaiContract.cmd', 'ClearOwnedWorkReadOnly.ps1'):
    replacements[file_sha(old / 'media-input' / name)] = file_sha(media / name)
for before, after in replacements.items():
    assert before in start, before
    start = start.replace(before, after)
(media / 'Start.ps1').write_text(start)
start_hash = file_sha(media / 'Start.ps1').upper()
(new / 'dispatch-command.txt').write_text(
    "if ((Get-FileHash E:\\Start.ps1).Hash -eq '" + start_hash
    + "') { & ([scriptblock]::Create((Get-Content E:\\Start.ps1 -Raw))) } else { throw 'SOURCE_MISMATCH' }\n")
decoder = (old / 'decode-native-export.py').read_text().replace(
    '"attempt55": "' + previous['nonce'] + '"',
    '"attempt55": "' + previous['nonce'] + '", "attempt56": "' + nonce + '"')
assert '"attempt56": "' + nonce + '"' in decoder
(new / 'decode-native-export.py').write_text(decoder)
binding = {'nonce': nonce, 'source_commit': previous['source_commit'],
           'manifest_sha256': file_sha(media / 'source-manifest.json'),
           'archive_sha256': manifest['archive_sha256'], 'file_count': len(files),
           'source_bytes': manifest['total_source_bytes'],
           'expected': 'native Windows injected accounting-error retry with wrong and restored unit controls',
           'cargo_jobs': 2, 'guest_free_ram_floor_bytes': 3221225472,
           'driver_seconds': 185, 'export_seconds': 180, 'native_started': False,
           'command_dispatched': False, 'product_test_started': False}
(new / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
print(json.dumps(binding, indent=2))
