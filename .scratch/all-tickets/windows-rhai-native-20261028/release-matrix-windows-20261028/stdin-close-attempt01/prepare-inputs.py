"""Create attempt-specific native inputs from the accepted supervised route."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
previous = root.parent / "managed-controls-attempt01"
media = root / "media-input"
p = json.loads((root / "preparation.json").read_text())
manifest = json.loads((media / "source-manifest.json").read_text())
nonce = p["nonce"]
old_nonce = "73bbed61f32a48679390d099b4c3a9f5"
assert nonce == "4197aac65a57420ba09fa6855525c353"
def digest(data):
    return hashlib.sha256(data).hexdigest()
def old(name):
    return (previous / "media-input" / name).read_text()
def write(name, text, crlf=False):
    data = text.replace("\r\n", "\n")
    if crlf:
        data = data.replace("\n", "\r\n")
    (media / name).write_bytes(data.encode())
    return digest((media / name).read_bytes())
def rep(text, old_value, new_value):
    assert old_value in text, old_value
    return text.replace(old_value, new_value)

clear = rep(old("ClearOwnedWorkReadOnly.ps1"), old_nonce[:8], nonce[:8])
clear_hash = write("ClearOwnedWorkReadOnly.ps1", clear)
template = old("RunRhaiContract.cmd")
header = template[:template.index("set PROFILE=")]
contract = header + """set PROFILE=testing-environ,sys,net
set TARGET=--test sys_process_windows
set "COMPILE_RC=999"
set "WRONG_RC=999"
set "GREEN_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_STDIN_CLOSE_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_spawn_retains_early_stdin_close_error -- --exact --nocapture > stdin-close-wrong.log 2>&1
set "WRONG_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STDIN_CLOSE_WRONG_EXPECTATION=
if not "!WRONG_RC!"=="101" goto cleanup
findstr /C:"windows_stdin_close_readback" stdin-close-wrong.log > NUL || goto cleanup
findstr /C:"deliberately wrong stdin-close error expectation" stdin-close-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" stdin-close-wrong.log > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_spawn_retains_early_stdin_close_error -- --exact --nocapture > stdin-close-green.log 2>&1
set "GREEN_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\\rhai-attributes.log" & exit /b 92)
type "%TEMP%\\rhai-attributes.log"
echo RHAI_STDIN_CLOSE_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_STDIN_CLOSE_WRONG_EXIT=!WRONG_RC!
echo RHAI_STDIN_CLOSE_GREEN_EXIT=!GREEN_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!WRONG_RC!"=="101" exit /b 61
if not "!GREEN_RC!"=="0" exit /b 65
echo RHAI_STDIN_CLOSE_CONTROLS_PASS
exit /b 0
"""
contract_hash = write("RunRhaiContract.cmd", contract, True)
control = old("RunRhaiContractControl.ps1")
control = rep(control, old_nonce[:8], nonce[:8])
control = rep(control, "b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd", p["manifest_sha256"])
start = control.index("  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'")
end = control.index("  $journal=@(Get-ChildItem", start)
checks = """  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_CARGO_CLEAN_EXIT=0','RHAI_STDIN_CLOSE_COMPILE_EXIT=0','RHAI_STDIN_CLOSE_WRONG_EXIT=101','RHAI_STDIN_CLOSE_GREEN_EXIT=0','RHAI_STDIN_CLOSE_CONTROLS_PASS')){if(!$payloadOutput.Contains($line)){throw "Native stdin-close marker missing: $line"}}
  if(!$compile.Contains('tests\\sys_process_windows.rs')){throw 'Native target was not compiled.'}
  $cargoVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\cargo-version.txt')).Trim()
  $rustcVersionFile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\rustc-version.txt')).Trim()
  if($cargoVersionFile -cne 'cargo 1.77.2 (e52e36006 2024-03-26)' -or $rustcVersionFile -cne 'rustc 1.77.2 (25ef9e3d8 2024-04-09)'){throw 'Native MSRV versions differ inside the supervised run.'}
  $cases=@(
   @{File='stdin-close-wrong.log';Tokens=@('windows_spawn_retains_early_stdin_close_error','windows_stdin_close_readback','retained=true','deliberately wrong stdin-close error expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='stdin-close-green.log';Tokens=@('windows_spawn_retains_early_stdin_close_error','windows_stdin_close_readback','retained=true','test result: ok. 1 passed; 0 failed; 0 ignored;')}
  )
  foreach($case in $cases){
   $actual=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName ('runtime\\'+$case.File)))
   foreach($token in $case.Tokens){if(!$actual.Contains($token)){throw "Native stdin-close log missing: $($case.File) $token"}}
  }
  $productTestRun=$true;$actualOutcome='pass';$wrongExpectationRejected=$true
"""
control = control[:start] + checks + control[end:]
export_old = "'runtime\\managed-kill-wrong.log','runtime\\managed-timeout-wrong.log','runtime\\managed-drop-kill-wrong.log','runtime\\managed-drop-retain-wrong.log','runtime\\suite.log'"
control = rep(control, export_old, "'runtime\\stdin-close-wrong.log','runtime\\stdin-close-green.log'")
control_hash = write("RunRhaiContractControl.ps1", control)
start_script = old("Start.ps1")
for before, after in [
    (old_nonce, nonce),
    ("6ff82b95cbbf65ba919161932a63d74f668f8e6e6d88682418797eca93565384", p["archive_sha256"]),
    ("b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd", p["manifest_sha256"]),
    ("4c3c7ad0bb0ec0c714ee3aa2671b81577bd2f1300fe23f763c122b8593804409", control_hash),
    ("34470cc6d296c9e02aba5a5779f7f3dccafc9577ada280ddad4f74b09aca41f5", contract_hash),
    ("3a0766ec64f83135d1fd8a6dbae443dea07023c0aec94b6ee3130860de38440f", clear_hash),
    ("7019821fc9d7814d0632fea06de50933aa9e35ee", p["base_head"]),
    ("5386977", str(manifest["total_source_bytes"])),
]:
    start_script = rep(start_script, before, after)
start_hash = write("Start.ps1", start_script)
write("rhai-native-" + nonce + ".bundle", "rhai-native-" + nonce + "\n")
assert len(list(media.iterdir())) == 8
files = {x.name: {"bytes": x.stat().st_size, "sha256": digest(x.read_bytes())} for x in media.iterdir()}
(root / "binding.json").write_text(json.dumps({"nonce":nonce,"base_head":p["base_head"],"overlay_sha256":p["overlay_sha256"],"source_manifest_sha256":p["manifest_sha256"],"archive_sha256":p["archive_sha256"],"lock_sha256":p["lock_sha256"],"features":"testing-environ,sys,net","target":"sys_process_windows","test":"windows_spawn_retains_early_stdin_close_error","media_files":files,"driver_deadline_seconds":180,"observer_deadline_seconds":185,"export_deadline_seconds":180,"start_sha256":start_hash,"native_started":False},indent=2)+"\n")
print(json.dumps({"media_files":len(files),"start_sha256":start_hash,"control_sha256":control_hash,"contract_sha256":contract_hash,"attribute_sha256":clear_hash},indent=2))
