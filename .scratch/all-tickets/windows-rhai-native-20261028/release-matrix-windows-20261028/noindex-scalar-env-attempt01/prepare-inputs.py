"""Bind the env_remove fix, assertion controls and affected Windows suite."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent; old=root.parent/'managed-overflow-attempt01'; media=root/'media-input'
p=json.loads((root/'preparation.json').read_text());m=json.loads((media/'source-manifest.json').read_text());ob=json.loads((old/'binding.json').read_text())
n=p['nonce'];oldn=ob['nonce'];assert n=='ed665e3968e2453db7cba4dd594abeb2'
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
contract=header+"""set PROFILE=testing-environ,sys,net,no_index
set TARGET=--test sys_process_windows_scalar
set "COMPILE_RC=999"
set "HOST_DIRECT_RC=999"
set "HOST_MANAGED_RC=999"
set "DENIAL_DIRECT_RC=999"
set "DENIAL_MANAGED_RC=999"
set "SUITE_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_SCALAR_WRONG_EXPECTATION=direct
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_scalar_run_reports_native_hostname -- --exact --nocapture > host-direct-wrong.log 2>&1
set "HOST_DIRECT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SCALAR_WRONG_EXPECTATION=managed
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_scalar_run_reports_native_hostname -- --exact --nocapture > host-managed-wrong.log 2>&1
set "HOST_MANAGED_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SCALAR_WRONG_EXPECTATION=
set RHAI_WINDOWS_SCALAR_DENIAL_WRONG_EXPECTATION=direct
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_scalar_rejects_unavailable_env_remove_option -- --exact --nocapture > denial-direct-wrong.log 2>&1
set "DENIAL_DIRECT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SCALAR_DENIAL_WRONG_EXPECTATION=managed
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_scalar_rejects_unavailable_env_remove_option -- --exact --nocapture > denial-managed-wrong.log 2>&1
set "DENIAL_MANAGED_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SCALAR_DENIAL_WRONG_EXPECTATION=
for %%R in (!HOST_DIRECT_RC! !HOST_MANAGED_RC! !DENIAL_DIRECT_RC! !DENIAL_MANAGED_RC!) do if not "%%R"=="101" goto cleanup
for %%F in (host-direct-wrong.log host-managed-wrong.log) do findstr /C:"deliberately wrong Windows scalar hostname expectation" %%F > NUL || goto cleanup
for %%F in (denial-direct-wrong.log denial-managed-wrong.log) do findstr /C:"deliberately wrong scalar denial expectation" %%F > NUL || goto cleanup
for %%F in (host-direct-wrong.log host-managed-wrong.log denial-direct-wrong.log denial-managed-wrong.log) do findstr /C:"test result: FAILED. 0 passed; 1 failed;" %%F > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > scalar-suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\\rhai-attributes.log" & exit /b 92)
type "%TEMP%\\rhai-attributes.log"
echo RHAI_SCALAR_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_SCALAR_HOST_DIRECT_EXIT=!HOST_DIRECT_RC!
echo RHAI_SCALAR_HOST_MANAGED_EXIT=!HOST_MANAGED_RC!
echo RHAI_SCALAR_DENIAL_DIRECT_EXIT=!DENIAL_DIRECT_RC!
echo RHAI_SCALAR_DENIAL_MANAGED_EXIT=!DENIAL_MANAGED_RC!
echo RHAI_SCALAR_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!HOST_DIRECT_RC!"=="101" exit /b 61
if not "!HOST_MANAGED_RC!"=="101" exit /b 62
if not "!DENIAL_DIRECT_RC!"=="101" exit /b 63
if not "!DENIAL_MANAGED_RC!"=="101" exit /b 64
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_SCALAR_CONTROLS_PASS
exit /b 0
"""
contract=contract.replace('set "SUITE_RC=!ERRORLEVEL!\n"','set "SUITE_RC=!ERRORLEVEL!"')
contracth=write('RunRhaiContract.cmd',contract,True)
control=text('RunRhaiContractControl.ps1')
control=rep(control,oldn[:8],n[:8]);control=rep(control,ob['source_manifest_sha256'],p['manifest_sha256'])
start=control.index("  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'")
end=control.index("  $journal=@(Get-ChildItem",start)
checks="""  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_CARGO_CLEAN_EXIT=0','RHAI_SCALAR_COMPILE_EXIT=0','RHAI_SCALAR_HOST_DIRECT_EXIT=101','RHAI_SCALAR_HOST_MANAGED_EXIT=101','RHAI_SCALAR_DENIAL_DIRECT_EXIT=101','RHAI_SCALAR_DENIAL_MANAGED_EXIT=101','RHAI_SCALAR_SUITE_EXIT=0','RHAI_SCALAR_CONTROLS_PASS')){if(!$payloadOutput.Contains($line)){throw "Native scalar marker missing: $line"}}
  if(!$compile.Contains('tests\\sys_process_windows_scalar.rs')){throw 'Native scalar target was not compiled.'}
  $cargoVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\cargo-version.txt')).Trim()
  $rustcVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\rustc-version.txt')).Trim()
  if($cargoVersionFile -cne 'cargo 1.77.2 (e52e36006 2024-03-26)' -or $rustcVersionFile -cne 'rustc 1.77.2 (25ef9e3d8 2024-04-09)'){throw 'Native MSRV versions differ inside the supervised run.'}
  $cases=@(
   @{File='host-direct-wrong.log';Tokens=@('windows_scalar_hostname_readback label=direct','deliberately wrong Windows scalar hostname expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='host-managed-wrong.log';Tokens=@('windows_scalar_hostname_readback label=managed','deliberately wrong Windows scalar hostname expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='denial-direct-wrong.log';Tokens=@('windows_scalar_env_remove_readback label=direct','deliberately wrong scalar denial expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='denial-managed-wrong.log';Tokens=@('windows_scalar_env_remove_readback label=managed','deliberately wrong scalar denial expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='scalar-suite.log';Tokens=@('windows_scalar_hostname_readback label=direct','windows_scalar_hostname_readback label=managed','windows_scalar_env_remove_readback label=direct','windows_scalar_env_remove_readback label=managed','windows_scalar_raw_unavailable','test result: ok. 3 passed; 0 failed; 0 ignored;')}
  )
  foreach($case in $cases){
   $actual=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName ('runtime\\'+$case.File)))
   foreach($token in $case.Tokens){if(!$actual.Contains($token)){throw "Native scalar log missing: $($case.File) $token"}}
  }
  $productTestRun=$true;$actualOutcome='pass';$wrongExpectationRejected=$true
"""
control=control[:start]+checks+control[end:]
control=rep(control,"'runtime\\managed-overflow-wrong.log','runtime\\managed-overflow-green.log'","'runtime\\host-direct-wrong.log','runtime\\host-managed-wrong.log','runtime\\denial-direct-wrong.log','runtime\\denial-managed-wrong.log','runtime\\scalar-suite.log'")
controlh=write('RunRhaiContractControl.ps1',control)
startscript=text('Start.ps1');om=json.loads((old/'media-input/source-manifest.json').read_text())
for a,b in [(oldn,n),(ob['archive_sha256'],p['archive_sha256']),(ob['source_manifest_sha256'],p['manifest_sha256']),(ob['media_files']['RunRhaiContractControl.ps1']['sha256'],controlh),(ob['media_files']['RunRhaiContract.cmd']['sha256'],contracth),(ob['media_files']['ClearOwnedWorkReadOnly.ps1']['sha256'],clearh),(ob['base_head'],p['base_head']),(str(om['total_source_bytes']),str(m['total_source_bytes']))]:
 startscript=rep(startscript,a,b)
startscript=rep(startscript, '-ne 448', '-ne 449'); startscript=rep(startscript, 'source_files=453', 'source_files=449;staged_files=454')
starth=write('Start.ps1',startscript);write('rhai-native-'+n+'.bundle','rhai-native-'+n+'\n')
assert len(list(media.iterdir()))==8
files={x.name:{'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in media.iterdir()}
b={'nonce':n,'base_head':p['base_head'],'overlay_sha256':p['overlay_sha256'],'source_manifest_sha256':p['manifest_sha256'],'archive_sha256':p['archive_sha256'],'lock_sha256':p['lock_sha256'],'features':'testing-environ,sys,net,no_index','target':'sys_process_windows_scalar','test':'windows_scalar_run_reports_native_hostname','media_files':files,'driver_deadline_seconds':180,'observer_deadline_seconds':185,'export_deadline_seconds':180,'start_sha256':starth,'native_started':False}
(root/'binding.json').write_text(json.dumps(b,indent=2)+'\n')
print(json.dumps({'start_sha256':starth,'control_sha256':controlh,'contract_sha256':contracth},indent=2))
