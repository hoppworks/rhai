"""Reuse attempt59's exact source archive for native public final-drop proof."""
from pathlib import Path
import hashlib
import json
import secrets
import shutil

root = Path.cwd()
base = root / '.scratch/all-tickets/windows-rhai-native-20261028'
old = base / 'attempt59'
new = base / 'attempt60'
new.mkdir()
media = new / 'media-input'
media.mkdir()
previous = json.loads((old / 'binding.json').read_text())
nonce = secrets.token_hex(16)
sha = lambda data: hashlib.sha256(data).hexdigest()
file_sha = lambda path: sha(path.read_bytes())
manifest = json.loads((old / 'media-input/source-manifest.json').read_text())
assert all(file_sha(root / name) == entry['sha256'] for name, entry in manifest['files'].items())
for name in ('rhai-source.zip', 'source-manifest.json', 'Cargo.lock'):
    shutil.copyfile(old / 'media-input' / name, media / name)
assert file_sha(media / 'rhai-source.zip') == manifest['archive_sha256']
assert file_sha(media / 'source-manifest.json') == previous['manifest_sha256']
helper = (old / 'media-input/ClearOwnedWorkReadOnly.ps1').read_bytes()
assert ('n-' + previous['nonce'][:8]).encode() in helper
(media / 'ClearOwnedWorkReadOnly.ps1').write_bytes(
    helper.replace(('n-' + previous['nonce'][:8]).encode(), ('n-' + nonce[:8]).encode()))
(media / ('rhai-native-' + nonce + '.bundle')).write_text('rhai-native-' + nonce + '\n')

cmd = r'''@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --no-run > compile.log 2>&1
if errorlevel 1 exit /b 59
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=kill
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_final_drop_follows_host_policy -- --exact --nocapture > kill-wrong.log 2>&1
set KILL_RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=retain
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_final_drop_follows_host_policy -- --exact --nocapture > retain-wrong.log 2>&1
set RETAIN_RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_final_drop_follows_host_policy -- --exact --nocapture > green.log 2>&1
set GREEN_RC=!ERRORLEVEL!
echo RHAI_DROP_KILL_WRONG_EXIT=!KILL_RC!
echo RHAI_DROP_RETAIN_WRONG_EXIT=!RETAIN_RC!
echo RHAI_DROP_GREEN_EXIT=!GREEN_RC!
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_DROP_CONTROLS_CLEANED
if not "!KILL_RC!"=="101" exit /b 61
findstr /C:"deliberately wrong managed kill drop termination expectation" kill-wrong.log > NUL || exit /b 62
if not "!RETAIN_RC!"=="101" exit /b 63
findstr /C:"deliberately wrong managed retain drop survival expectation" retain-wrong.log > NUL || exit /b 64
if not "!GREEN_RC!"=="0" exit /b 65
findstr /C:"test result: ok. 1 passed; 0 failed;" green.log > NUL || exit /b 66
echo RHAI_DROP_CONTROLS_PASS
exit /b 0
'''
(media / 'RunRhaiContract.cmd').write_bytes(cmd.replace('\n', '\r\n').encode())
control = (old / 'media-input/RunRhaiContractControl.ps1').read_text()
control = control.replace(previous['nonce'], nonce).replace(previous['nonce'][:8], nonce[:8])
control = control.replace('260second', '185second').replace('-ge 260', '-ge 185')
begin = control.index("  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'")
end = control.index('  $journal=@(', begin)
control = control[:begin] + r'''  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_DROP_CONTROLS_CLEANED','RHAI_DROP_KILL_WRONG_EXIT=101','RHAI_DROP_RETAIN_WRONG_EXIT=101','RHAI_DROP_GREEN_EXIT=0','RHAI_DROP_CONTROLS_PASS')){if(!$payloadOutput.Contains($line)){throw "Drop control marker missing: $line"}}
  if(!$compile.Contains('sys_process_windows')){throw 'Native test compile evidence missing.'}
  $kill=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\kill-wrong.log'))
  $retain=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\retain-wrong.log'))
  $green=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\green.log'))
  foreach($line in @('windows_managed_drop_os_readback mode=kill','deliberately wrong managed kill drop termination expectation','test result: FAILED. 0 passed; 1 failed;')){if(!$kill.Contains($line)){throw "Kill wrong control missing: $line"}}
  foreach($line in @('windows_managed_drop_os_readback mode=retain','deliberately wrong managed retain drop survival expectation','test result: FAILED. 0 passed; 1 failed;')){if(!$retain.Contains($line)){throw "Retain wrong control missing: $line"}}
  foreach($line in @('windows_managed_drop_os_readback mode=kill','windows_managed_drop_os_readback mode=retain','test result: ok. 1 passed; 0 failed;')){if(!$green.Contains($line)){throw "Restored drop proof missing: $line"}}
  $productTestRun=$true;$actualOutcome='pass';$wrongExpectationRejected=$true
''' + control[end:]
control = control.replace("'runtime\\wrong.log','runtime\\green.log','runtime\\suite.log'", "'runtime\\kill-wrong.log','runtime\\retain-wrong.log','runtime\\green.log'")
(media / 'RunRhaiContractControl.ps1').write_text(control)
start = (old / 'media-input/Start.ps1').read_text()
replacements = {previous['nonce']: nonce}
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
    '"attempt59": "' + previous['nonce'] + '"',
    '"attempt59": "' + previous['nonce'] + '", "attempt60": "' + nonce + '"')
assert '"attempt60": "' + nonce + '"' in decoder
(new / 'decode-native-export.py').write_text(decoder)
binding = {'nonce': nonce, 'source_commit': previous['source_commit'],
           'manifest_sha256': previous['manifest_sha256'],
           'archive_sha256': previous['archive_sha256'], 'file_count': previous['file_count'],
           'source_bytes': previous['source_bytes'],
           'expected': 'native public final-drop kill/retain wrong controls and restored green on attempt59 source',
           'cargo_jobs': 2, 'guest_free_ram_floor_bytes': 3221225472,
           'driver_seconds': 185, 'export_seconds': 180, 'native_started': False,
           'command_dispatched': False, 'product_test_started': False}
(new / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
print(json.dumps(binding, indent=2))
