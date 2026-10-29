"""Bind the env_remove fix, assertion controls and affected Windows suite."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent; old=root.parent/'managed-overflow-attempt01'; media=root/'media-input'
p=json.loads((root/'preparation.json').read_text());m=json.loads((media/'source-manifest.json').read_text());ob=json.loads((old/'binding.json').read_text())
n=p['nonce'];oldn=ob['nonce'];assert n=='686ed122eae4440e8d87d1a5942a615d'
def sha(b):return hashlib.sha256(b).hexdigest()
def text(n):return (old/'media-input'/n).read_text()
def write(n,s,crlf=False):
 s=s.replace('\r\n','\n')
 if crlf:s=s.replace('\n','\r\n')
 (media/n).write_bytes(s.encode());return sha((media/n).read_bytes())
def rep(s,a,b):
 assert a in s,a
 return s.replace(a,b)
clear=rep(text('ClearOwnedWorkReadOnly.ps1'),oldn[:8],n[:8]);clearh=write('ClearOwnedWorkReadOnly.ps1',clear)
template=text('RunRhaiContract.cmd');header=template[:template.index('set PROFILE=')]
contract=header+"""set PROFILE=testing-environ,sys,net
set TARGET=--test sys_process_windows
set "COMPILE_RC=999"
set "REMOVED_RC=999"
set "OVERRIDE_RC=999"
set "PARENT_RC=999"
set "INVALID_RC=999"
set "SUITE_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_ENV_REMOVE_WRONG_EXPECTATION=removed
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_env_remove_preserves_parent_and_applies_overrides -- --exact --nocapture > env-removed-wrong.log 2>&1
set "REMOVED_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ENV_REMOVE_WRONG_EXPECTATION=override
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_env_remove_preserves_parent_and_applies_overrides -- --exact --nocapture > env-override-wrong.log 2>&1
set "OVERRIDE_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ENV_REMOVE_WRONG_EXPECTATION=parent
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_env_remove_preserves_parent_and_applies_overrides -- --exact --nocapture > env-parent-wrong.log 2>&1
set "PARENT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ENV_REMOVE_WRONG_EXPECTATION=
set RHAI_WINDOWS_ENV_REMOVE_INVALID_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_env_remove_rejects_invalid_options_before_child_start -- --exact --nocapture > env-invalid-wrong.log 2>&1
set "INVALID_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ENV_REMOVE_INVALID_WRONG_EXPECTATION=
if not "!REMOVED_RC!"=="101" goto cleanup
if not "!OVERRIDE_RC!"=="101" goto cleanup
if not "!PARENT_RC!"=="101" goto cleanup
if not "!INVALID_RC!"=="101" goto cleanup
findstr /C:"deliberately wrong removed-variable expectation" env-removed-wrong.log > NUL || goto cleanup
findstr /C:"deliberately wrong child-override expectation" env-override-wrong.log > NUL || goto cleanup
findstr /C:"deliberately wrong parent-environment expectation" env-parent-wrong.log > NUL || goto cleanup
findstr /C:"deliberately wrong invalid-option child-start expectation" env-invalid-wrong.log > NUL || goto cleanup
for %%F in (env-removed-wrong.log env-override-wrong.log env-parent-wrong.log env-invalid-wrong.log) do findstr /C:"test result: FAILED. 0 passed; 1 failed;" %%F > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > env-suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!
"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\\rhai-attributes.log" & exit /b 92)
type "%TEMP%\\rhai-attributes.log"
echo RHAI_ENV_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_ENV_REMOVED_EXIT=!REMOVED_RC!
echo RHAI_ENV_OVERRIDE_EXIT=!OVERRIDE_RC!
echo RHAI_ENV_PARENT_EXIT=!PARENT_RC!
echo RHAI_ENV_INVALID_EXIT=!INVALID_RC!
echo RHAI_ENV_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!REMOVED_RC!"=="101" exit /b 61
if not "!OVERRIDE_RC!"=="101" exit /b 62
if not "!PARENT_RC!"=="101" exit /b 63
if not "!INVALID_RC!"=="101" exit /b 64
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_ENV_CONTROLS_PASS
exit /b 0
"""
contract=contract.replace('set "SUITE_RC=!ERRORLEVEL!\n"','set "SUITE_RC=!ERRORLEVEL!"')
contracth=write('RunRhaiContract.cmd',contract,True)
control=text('RunRhaiContractControl.ps1')
control=rep(control,oldn[:8],n[:8]);control=rep(control,ob['source_manifest_sha256'],p['manifest_sha256'])
start=control.index("  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'")
end=control.index("  $journal=@(Get-ChildItem",start)
checks="""  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_CARGO_CLEAN_EXIT=0','RHAI_ENV_COMPILE_EXIT=0','RHAI_ENV_REMOVED_EXIT=101','RHAI_ENV_OVERRIDE_EXIT=101','RHAI_ENV_PARENT_EXIT=101','RHAI_ENV_INVALID_EXIT=101','RHAI_ENV_SUITE_EXIT=0','RHAI_ENV_CONTROLS_PASS')){if(!$payloadOutput.Contains($line)){throw "Native env-remove marker missing: $line"}}
  if(!$compile.Contains('tests\\sys_process_windows.rs')){throw 'Native target was not compiled.'}
  $cargoVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\cargo-version.txt')).Trim()
  $rustcVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\rustc-version.txt')).Trim()
  if($cargoVersionFile -cne 'cargo 1.77.2 (e52e36006 2024-03-26)' -or $rustcVersionFile -cne 'rustc 1.77.2 (25ef9e3d8 2024-04-09)'){throw 'Native MSRV versions differ inside the supervised run.'}
  $cases=@(
   @{File='env-removed-wrong.log';Tokens=@('windows_env_remove_readback','exact_handle_signaled=true','deliberately wrong removed-variable expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='env-override-wrong.log';Tokens=@('windows_env_remove_readback','exact_handle_signaled=true','deliberately wrong child-override expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='env-parent-wrong.log';Tokens=@('windows_env_remove_readback label=managed-spawn','deliberately wrong parent-environment expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='env-invalid-wrong.log';Tokens=@('windows_env_remove_invalid_readback','child_record_exists=false','deliberately wrong invalid-option child-start expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='env-suite.log';Tokens=@('windows_env_remove_readback label=direct-run','windows_env_remove_readback label=direct-spawn','windows_env_remove_readback label=managed-run','windows_env_remove_readback label=managed-spawn','windows_env_remove_invalid_readback','test result: ok. 38 passed; 0 failed; 0 ignored;')}
  )
  foreach($case in $cases){
   $actual=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName ('runtime\\'+$case.File)))
   foreach($token in $case.Tokens){if(!$actual.Contains($token)){throw "Native env-remove log missing: $($case.File) $token"}}
  }
  $productTestRun=$true;$actualOutcome='pass';$wrongExpectationRejected=$true
"""
control=control[:start]+checks+control[end:]
control=rep(control,"'runtime\\managed-overflow-wrong.log','runtime\\managed-overflow-green.log'","'runtime\\env-removed-wrong.log','runtime\\env-override-wrong.log','runtime\\env-parent-wrong.log','runtime\\env-invalid-wrong.log','runtime\\env-suite.log'")
controlh=write('RunRhaiContractControl.ps1',control)
startscript=text('Start.ps1');om=json.loads((old/'media-input/source-manifest.json').read_text())
for a,b in [(oldn,n),(ob['archive_sha256'],p['archive_sha256']),(ob['source_manifest_sha256'],p['manifest_sha256']),(ob['media_files']['RunRhaiContractControl.ps1']['sha256'],controlh),(ob['media_files']['RunRhaiContract.cmd']['sha256'],contracth),(ob['media_files']['ClearOwnedWorkReadOnly.ps1']['sha256'],clearh),(ob['base_head'],p['base_head']),(str(om['total_source_bytes']),str(m['total_source_bytes']))]:
 startscript=rep(startscript,a,b)
starth=write('Start.ps1',startscript);write('rhai-native-'+n+'.bundle','rhai-native-'+n+'\n')
assert len(list(media.iterdir()))==8
files={x.name:{'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in media.iterdir()}
b={'nonce':n,'base_head':p['base_head'],'overlay_sha256':p['source_overlays']['tests/sys_process_windows.rs'],'source_overlays':p['source_overlays'],'source_manifest_sha256':p['manifest_sha256'],'archive_sha256':p['archive_sha256'],'lock_sha256':p['lock_sha256'],'features':'testing-environ,sys,net','target':'sys_process_windows','test':'windows_env_remove_preserves_parent_and_applies_overrides','media_files':files,'driver_deadline_seconds':180,'observer_deadline_seconds':185,'export_deadline_seconds':180,'start_sha256':starth,'native_started':False}
(root/'binding.json').write_text(json.dumps(b,indent=2)+'\n')
print(json.dumps({'start_sha256':starth,'control_sha256':controlh,'contract_sha256':contracth},indent=2))
