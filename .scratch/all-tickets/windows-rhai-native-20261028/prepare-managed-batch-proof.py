from pathlib import Path
import hashlib
import json
import secrets
import shutil
import zipfile

root = Path.cwd()
base = root / '.scratch/all-tickets/windows-rhai-native-20261028'
old = base / 'attempt40'
new = base / 'attempt49'
new.mkdir()
media = new / 'media-input'
media.mkdir()
previous = json.loads((old / 'binding.json').read_text())
new_commit = 'c62a0a99113beb51601ee9ea39656367fe7b51c5'
nonce = secrets.token_hex(16)
digest = lambda data: hashlib.sha256(data).hexdigest()
file_digest = lambda path: digest(path.read_bytes())
files = sorted(json.loads((old / 'media-input/source-manifest.json').read_text())['files'])
entries = {}
with zipfile.ZipFile(media / 'rhai-source.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in files:
        content = (root / name).read_bytes()
        entries[name] = {'bytes': len(content), 'sha256': digest(content)}
        archive.writestr(name, content)
archive = (media / 'rhai-source.zip').read_bytes()
manifest = {'archive_bytes':len(archive),'archive_sha256':digest(archive),'file_count':len(files),'files':entries,'source_commit':new_commit,'source_dirty':True,'total_source_bytes':sum(x['bytes'] for x in entries.values())}
(media/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copyfile(old/'media-input/Cargo.lock',media/'Cargo.lock')
helper=(old/'media-input/ClearOwnedWorkReadOnly.ps1').read_bytes()
assert ('n-'+previous['nonce'][:8]).encode() in helper
(media/'ClearOwnedWorkReadOnly.ps1').write_bytes(helper.replace(('n-'+previous['nonce'][:8]).encode(),('n-'+nonce[:8]).encode()))
(media/('rhai-native-'+nonce+'.bundle')).write_text('rhai-native-'+nonce+'\n')
cmd=r'''@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --no-run > compile.log 2>&1
if errorlevel 1 exit /b 59
set RHAI_WINDOWS_MANAGED_BATCH_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_executes_explicitly_allowed_batch -- --exact --nocapture > wrong.log 2>&1
set RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_BATCH_WRONG_EXPECTATION=
if not "!RC!"=="101" exit /b 61
findstr /C:"windows_managed_batch_denial_readback batch_denied=true child_file_absent=true" wrong.log > NUL || exit /b 75
findstr /C:"windows_managed_batch_readback allowed=true child_file=managed-batch-ok" wrong.log > NUL || exit /b 62
findstr /C:"deliberately wrong managed batch expectation" wrong.log > NUL || exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed;" wrong.log > NUL || exit /b 64
echo RHAI_ARGUMENT_WRONG_REJECTED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_executes_explicitly_allowed_batch -- --exact --nocapture > green.log 2>&1
if errorlevel 1 exit /b 65
findstr /C:"windows_managed_batch_denial_readback batch_denied=true child_file_absent=true" green.log > NUL || exit /b 76
findstr /C:"windows_managed_batch_readback allowed=true child_file=managed-batch-ok" green.log > NUL || exit /b 66
findstr /C:"test result: ok. 1 passed; 0 failed; 0 ignored" green.log > NUL || exit /b 67
echo RHAI_ARGUMENT_GREEN
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_ARGUMENT_CLEANUP_CONFIRMED
exit /b 0
'''
(media/'RunRhaiContract.cmd').write_bytes(cmd.replace('\n','\r\n').encode())
control=(old/'media-input/RunRhaiContractControl.ps1').read_text().replace(previous['nonce'],nonce).replace(previous['nonce'][:8],nonce[:8]).replace(previous['manifest_sha256'],file_digest(media/'source-manifest.json'))
begin=control.index("  foreach($line in @('RHAI_CAPTURE_WRONG_REJECTED'")
end=control.index('  $journal=@(',begin)
control=control[:begin]+r'''  foreach($line in @('RHAI_ARGUMENT_WRONG_REJECTED','RHAI_ARGUMENT_GREEN','RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_ARGUMENT_CLEANUP_CONFIRMED')){if(!$payloadOutput.Contains($line)){throw "Native argument marker missing: $line"}}
  if(!$compile.Contains('sys_process_windows')){throw 'Native test compile evidence missing.'}
  $wrong=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\wrong.log'))
  $green=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\green.log'))
  foreach($line in @('windows_managed_batch_denial_readback batch_denied=true child_file_absent=true','windows_managed_batch_readback allowed=true child_file=managed-batch-ok','deliberately wrong managed batch expectation','test result: FAILED. 0 passed; 1 failed;')){if(!$wrong.Contains($line)){throw "Argument wrong control missing: $line"}}
  foreach($line in @('windows_managed_batch_denial_readback batch_denied=true child_file_absent=true','windows_managed_batch_readback allowed=true child_file=managed-batch-ok','test result: ok. 1 passed; 0 failed; 0 ignored')){if(!$green.Contains($line)){throw "Argument green missing: $line"}}
  $wrongExpectationRejected=$true
'''+control[end:]
control=control.replace("'runtime\\capture-wrong.log','runtime\\missing-wrong.log','runtime\\green.log'", "'runtime\\wrong.log','runtime\\green.log'")
(media/'RunRhaiContractControl.ps1').write_text(control)
start=(old/'media-input/Start.ps1').read_text()
replacements={previous['source_commit']:new_commit, previous['nonce']:nonce, previous['archive_sha256']:manifest['archive_sha256'], previous['manifest_sha256']:file_digest(media/'source-manifest.json'), str(previous['source_bytes']):str(manifest['total_source_bytes'])}
for name in ('RunRhaiContractControl.ps1','RunRhaiContract.cmd','ClearOwnedWorkReadOnly.ps1'):
    replacements[file_digest(old/'media-input'/name)]=file_digest(media/name)
for a,b in replacements.items():
    assert a in start,a
    start=start.replace(a,b)
(media/'Start.ps1').write_text(start)
start_hash=file_digest(media/'Start.ps1').upper()
(new/'dispatch-command.txt').write_text("if ((Get-FileHash E:\\Start.ps1).Hash -eq '"+start_hash+"') { & ([scriptblock]::Create((Get-Content E:\\Start.ps1 -Raw))) } else { throw 'SOURCE_MISMATCH' }\n")
decoder=(old/'decode-native-export.py').read_text().replace('"attempt40": "'+previous['nonce']+'"','"attempt40": "'+previous['nonce']+'", "attempt49": "'+nonce+'"')
(new/'decode-native-export.py').write_text(decoder)
binding={'nonce':nonce,'source_commit':new_commit,'manifest_sha256':file_digest(media/'source-manifest.json'),'archive_sha256':manifest['archive_sha256'],'file_count':len(files),'source_bytes':manifest['total_source_bytes'],'expected':'managed batch default denial and explicitly allowed wrong control/GREEN; no general managed closure','cargo_jobs':2,'guest_free_ram_floor_bytes':3221225472,'driver_seconds':185,'export_seconds':180,'native_started':False,'command_dispatched':False,'product_test_started':False}
(new/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
print(json.dumps(binding,indent=2))
