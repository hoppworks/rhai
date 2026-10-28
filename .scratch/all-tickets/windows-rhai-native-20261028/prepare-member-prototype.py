from pathlib import Path
import hashlib
import json
import secrets
import shutil
import zipfile

root = Path.cwd()
base = root / '.scratch/all-tickets/windows-rhai-native-20261028'
previous = base / 'attempt39'
target = base / 'attempt40'
target.mkdir()
media = target / 'media-input'
media.mkdir()
nonce = secrets.token_hex(16)
old = json.loads((previous / 'binding.json').read_text())
old_manifest = json.loads((previous / 'media-input/source-manifest.json').read_text())
files = sorted(set(old_manifest['files']) | {'src/packages/sys/process/windows/members.rs'})
def sha(data): return hashlib.sha256(data).hexdigest()
entries = {}
with zipfile.ZipFile(media / 'rhai-source.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in files:
        data = (root / name).read_bytes()
        entries[name] = {'bytes': len(data), 'sha256': sha(data)}
        archive.writestr(name, data)
archive_data = (media / 'rhai-source.zip').read_bytes()
manifest = {'archive_bytes': len(archive_data), 'archive_sha256': sha(archive_data), 'file_count': len(files), 'files': entries, 'source_commit': old['source_commit'], 'source_dirty': True, 'total_source_bytes': sum(x['bytes'] for x in entries.values())}
(media / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
for name in ('Cargo.lock', 'ClearOwnedWorkReadOnly.ps1'):
    shutil.copyfile(previous / 'media-input' / name, media / name)
helper = media / 'ClearOwnedWorkReadOnly.ps1'
helper_data = helper.read_bytes()
assert b'n-2cb45485' in helper_data
helper.write_bytes(helper_data.replace(b'n-2cb45485', ('n-' + nonce[:8]).encode()))
(media / ('rhai-native-' + nonce + '.bundle')).write_text('rhai-native-' + nonce + '\n')
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
set RHAI_WINDOWS_MEMBER_CAPTURE_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::members::tests::captured_process_handle_requires_real_exit_before_candidate_closure -- --exact --nocapture > capture-wrong.log 2>&1
set RC=!ERRORLEVEL!
set RHAI_WINDOWS_MEMBER_CAPTURE_WRONG_EXPECTATION=
if not "!RC!"=="101" exit /b 61
findstr /C:"windows_member_capture_readback captured=1 exact_handle_signaled=true" capture-wrong.log > NUL || exit /b 62
findstr /C:"deliberately wrong captured member closure expectation" capture-wrong.log > NUL || exit /b 63
findstr /C:"test result: FAILED" capture-wrong.log > NUL || exit /b 64
echo RHAI_CAPTURE_WRONG_REJECTED
set RHAI_WINDOWS_MEMBER_MISSING_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::members::tests::unobserved_lifetime_member_cannot_certify_candidate_closure -- --exact --nocapture > missing-wrong.log 2>&1
set RC=!ERRORLEVEL!
set RHAI_WINDOWS_MEMBER_MISSING_WRONG_EXPECTATION=
if not "!RC!"=="101" exit /b 65
findstr /C:"windows_member_capture_missing_readback unverified=true" missing-wrong.log > NUL || exit /b 66
findstr /C:"deliberately wrong uncaptured member expectation" missing-wrong.log > NUL || exit /b 67
findstr /C:"test result: FAILED" missing-wrong.log > NUL || exit /b 68
echo RHAI_MISSING_WRONG_REJECTED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::members::tests:: -- --nocapture > green.log 2>&1
if errorlevel 1 exit /b 69
findstr /C:"test result: ok. 3 passed; 0 failed; 0 ignored" green.log > NUL || exit /b 70
findstr /C:"windows_member_capture_readback captured=1 exact_handle_signaled=true" green.log > NUL || exit /b 71
findstr /C:"windows_member_capture_missing_readback unverified=true" green.log > NUL || exit /b 72
echo RHAI_MEMBER_PROTOTYPE_GREEN
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MEMBER_PROTOTYPE_CLEANUP_CONFIRMED
exit /b 0
'''
(media / 'RunRhaiContract.cmd').write_bytes(cmd.replace('\n', '\r\n').encode())
control = (previous / 'media-input/RunRhaiContractControl.ps1').read_text()
control = control.replace(old['nonce'], nonce).replace(old['nonce'][:8], nonce[:8]).replace(old['manifest_sha256'], sha((media / 'source-manifest.json').read_bytes()))
start = control.index("  foreach($line in @('RHAI_DIAG_FOUR_SUITES_COMPLETE'")
end = control.index('  $journal=@(', start)
control = control[:start] + r'''  foreach($line in @('RHAI_CAPTURE_WRONG_REJECTED','RHAI_MISSING_WRONG_REJECTED','RHAI_MEMBER_PROTOTYPE_GREEN','RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_MEMBER_PROTOTYPE_CLEANUP_CONFIRMED')){if(!$payloadOutput.Contains($line)){throw "Native prototype marker missing: $line"}}
  if(!$compile.Contains('rhai')){throw 'Native test compile evidence missing.'}
  $capture=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\capture-wrong.log'))
  $missing=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\missing-wrong.log'))
  $green=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\green.log'))
  foreach($line in @('windows_member_capture_readback captured=1 exact_handle_signaled=true','deliberately wrong captured member closure expectation','test result: FAILED')){if(!$capture.Contains($line)){throw "Capture wrong control missing: $line"}}
  foreach($line in @('windows_member_capture_missing_readback unverified=true','deliberately wrong uncaptured member expectation','test result: FAILED')){if(!$missing.Contains($line)){throw "Missing-member wrong control missing: $line"}}
  foreach($line in @('windows_member_capture_readback captured=1 exact_handle_signaled=true','windows_member_capture_missing_readback unverified=true','test result: ok. 3 passed; 0 failed; 0 ignored')){if(!$green.Contains($line)){throw "Prototype green missing: $line"}}
  $wrongExpectationRejected=$true
''' + control[end:]
control = control.replace("'runtime\\suite-1.log','runtime\\suite-2.log','runtime\\suite-3.log','runtime\\suite-4.log'", "'runtime\\capture-wrong.log','runtime\\missing-wrong.log','runtime\\green.log'")
control = control.replace('wrong_expectation_rejected=$false;diagnostic_suites_complete=$wrongExpectationRejected', 'wrong_expectation_rejected=$wrongExpectationRejected;diagnostic_suites_complete=$false')
(media / 'RunRhaiContractControl.ps1').write_text(control)
start_ps = (previous / 'media-input/Start.ps1').read_text()
replace = {old['nonce']: nonce, old['archive_sha256']: manifest['archive_sha256'], old['manifest_sha256']: sha((media / 'source-manifest.json').read_bytes()), sha((previous / 'media-input/RunRhaiContractControl.ps1').read_bytes()): sha((media / 'RunRhaiContractControl.ps1').read_bytes()), sha((previous / 'media-input/RunRhaiContract.cmd').read_bytes()): sha((media / 'RunRhaiContract.cmd').read_bytes()), sha((previous / 'media-input/ClearOwnedWorkReadOnly.ps1').read_bytes()): sha(helper.read_bytes()), 'file_count -ne 447': f'file_count -ne {len(files)}', '$actual.Count -ne 447': f'$actual.Count -ne {len(files)}', 'total_source_bytes -ne 5304186': f'total_source_bytes -ne {manifest["total_source_bytes"]}', 'source_files=452': f'source_files={len(files)+5}'}
for a,b in replace.items():
    assert a in start_ps, a
    start_ps = start_ps.replace(a,b)
(media / 'Start.ps1').write_text(start_ps)
start_hash=sha((media/'Start.ps1').read_bytes())
(target/'dispatch-command.txt').write_text("if ((Get-FileHash E:\\Start.ps1).Hash -eq '" + start_hash.upper() + "') { & ([scriptblock]::Create((Get-Content E:\\Start.ps1 -Raw))) } else { throw 'SOURCE_MISMATCH' }\n")
decoder=(previous/'decode-native-export.py').read_text().replace('"attempt39": "'+old['nonce']+'"', '"attempt39": "'+old['nonce']+'", "attempt40": "'+nonce+'"')
(target/'decode-native-export.py').write_text(decoder)
binding={'nonce':nonce,'source_commit':old['source_commit'],'manifest_sha256':sha((media/'source-manifest.json').read_bytes()),'archive_sha256':manifest['archive_sha256'],'file_count':len(files),'source_bytes':manifest['total_source_bytes'],'expected':'two deliberate wrong controls and three native member prototype unit tests; no product acceptance','cargo_jobs':2,'guest_free_ram_floor_bytes':3221225472,'driver_seconds':185,'export_seconds':180,'native_started':False,'command_dispatched':False,'product_test_started':False}
(target/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
print(json.dumps(binding,indent=2))
