"""Freeze the two missing public Managed normal-completion assertion controls."""
from pathlib import Path
import hashlib
import json
import secrets
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parent
repo = Path.cwd()
old = root / "attempt61"
new = root / "attempt62"
assert not new.exists()
new.mkdir()
media = new / "media-input"
media.mkdir()
previous = json.loads((old / "binding.json").read_text())
nonce = secrets.token_hex(16)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
files = sorted(json.loads((old / "media-input/source-manifest.json").read_text())["files"])
entries = {}
with zipfile.ZipFile(media / "rhai-source.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in files:
        data = (repo / name).read_bytes()
        entries[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        archive.writestr(name, data)
current_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
manifest = {"archive_bytes": (media / "rhai-source.zip").stat().st_size,
            "archive_sha256": sha(media / "rhai-source.zip"), "file_count": len(files),
            "files": entries, "source_commit": current_commit, "source_dirty": True,
            "total_source_bytes": sum(entry["bytes"] for entry in entries.values())}
(media / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
shutil.copyfile(old / "media-input/Cargo.lock", media / "Cargo.lock")
assert manifest["file_count"] == 448

helper = (old / "media-input/ClearOwnedWorkReadOnly.ps1").read_bytes()
assert ("n-" + previous["nonce"][:8]).encode() in helper
(media / "ClearOwnedWorkReadOnly.ps1").write_bytes(
    helper.replace(("n-" + previous["nonce"][:8]).encode(), ("n-" + nonce[:8]).encode())
)
(media / ("rhai-native-" + nonce + ".bundle")).write_text("rhai-native-" + nonce + "\n")

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
set RHAI_WINDOWS_MANAGED_RUN_CLOSURE_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_closes_descendant_on_normal_parent_exit -- --exact --nocapture > run-closure-wrong.log 2>&1
set RUN_CLOSURE_WRONG_RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_RUN_CLOSURE_WRONG_EXPECTATION=
set RHAI_WINDOWS_MANAGED_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_closes_descendant_on_normal_parent_exit -- --exact --nocapture > run-sentinel-wrong.log 2>&1
set RUN_SENTINEL_WRONG_RC=!ERRORLEVEL!
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_wait_closes_descendant_on_parent_exit -- --exact --nocapture > spawn-wrong.log 2>&1
set SPAWN_WRONG_RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_closes_descendant_on_normal_parent_exit -- --exact --nocapture > run-green.log 2>&1
set RUN_GREEN_RC=!ERRORLEVEL!
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_wait_closes_descendant_on_parent_exit -- --exact --nocapture > spawn-green.log 2>&1
set SPAWN_GREEN_RC=!ERRORLEVEL!
echo RHAI_X35_RUN_CLOSURE_WRONG_EXIT=!RUN_CLOSURE_WRONG_RC!
echo RHAI_X35_RUN_SENTINEL_WRONG_EXIT=!RUN_SENTINEL_WRONG_RC!
echo RHAI_X35_SPAWN_WRONG_EXIT=!SPAWN_WRONG_RC!
echo RHAI_X35_RUN_GREEN_EXIT=!RUN_GREEN_RC!
echo RHAI_X35_SPAWN_GREEN_EXIT=!SPAWN_GREEN_RC!
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_X35_CLEANED
if not "!RUN_CLOSURE_WRONG_RC!"=="101" exit /b 61
findstr /C:"deliberately wrong managed run descendant closure expectation" run-closure-wrong.log > NUL || exit /b 62
if not "!RUN_SENTINEL_WRONG_RC!"=="101" exit /b 69
findstr /C:"deliberately wrong managed sentinel expectation" run-sentinel-wrong.log > NUL || exit /b 70
if not "!SPAWN_WRONG_RC!"=="101" exit /b 63
findstr /C:"deliberately wrong managed spawn closure expectation" spawn-wrong.log > NUL || exit /b 64
if not "!RUN_GREEN_RC!"=="0" exit /b 65
findstr /C:"windows_managed_os_readback" run-green.log > NUL || exit /b 66
if not "!SPAWN_GREEN_RC!"=="0" exit /b 67
findstr /C:"windows_managed_spawn_os_readback" spawn-green.log > NUL || exit /b 68
echo RHAI_X35_CONTROLS_PASS
exit /b 0
'''
(media / "RunRhaiContract.cmd").write_bytes(cmd.replace("\n", "\r\n").encode())
control = (old / "media-input/RunRhaiContractControl.ps1").read_text()
control = control.replace(previous["nonce"], nonce).replace(previous["nonce"][:8], nonce[:8])
control = control.replace(previous["manifest_sha256"], sha(media / "source-manifest.json"))
begin = control.index("  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED'")
end = control.index("  $journal=@(", begin)
control = control[:begin] + r'''  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_X35_CLEANED','RHAI_X35_RUN_CLOSURE_WRONG_EXIT=101','RHAI_X35_RUN_SENTINEL_WRONG_EXIT=101','RHAI_X35_SPAWN_WRONG_EXIT=101','RHAI_X35_RUN_GREEN_EXIT=0','RHAI_X35_SPAWN_GREEN_EXIT=0','RHAI_X35_CONTROLS_PASS')){if(!$payloadOutput.Contains($line)){throw "X35 control marker missing: $line"}}
  if(!$compile.Contains('sys_process_windows')){throw 'Native process test compile evidence missing.'}
  $cases=@(
   @{File='run-closure-wrong.log';Tokens=@('windows_managed_os_readback','deliberately wrong managed run descendant closure expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='run-sentinel-wrong.log';Tokens=@('windows_managed_os_readback','deliberately wrong managed sentinel expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='spawn-wrong.log';Tokens=@('windows_managed_spawn_os_readback','deliberately wrong managed spawn closure expectation','test result: FAILED. 0 passed; 1 failed;')},
   @{File='run-green.log';Tokens=@('windows_managed_os_readback','test result: ok. 1 passed; 0 failed;')},
   @{File='spawn-green.log';Tokens=@('windows_managed_spawn_os_readback','test result: ok. 1 passed; 0 failed;')}
  )
  foreach($case in $cases){
   $actual=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName ('runtime\'+$case.File)))
   foreach($token in $case.Tokens){if(!$actual.Contains($token)){throw "X35 original log missing: $($case.File) $token"}}
  }
  $productTestRun=$true;$actualOutcome='pass';$wrongExpectationRejected=$true
''' + control[end:]
control = control.replace(
    r"'runtime\wrong.log','runtime\green.log','runtime\suite.log'",
    r"'runtime\run-closure-wrong.log','runtime\run-sentinel-wrong.log','runtime\spawn-wrong.log','runtime\run-green.log','runtime\spawn-green.log'",
)
(media / "RunRhaiContractControl.ps1").write_text(control)
start = (old / "media-input/Start.ps1").read_text().replace(previous["nonce"], nonce)
for before, after in (
    (previous["source_commit"], current_commit),
    (previous["archive_sha256"], manifest["archive_sha256"]),
    (previous["manifest_sha256"], sha(media / "source-manifest.json")),
    (str(previous["source_bytes"]), str(manifest["total_source_bytes"])),
):
    assert before in start, before
    start = start.replace(before, after)
for name in ("RunRhaiContractControl.ps1", "RunRhaiContract.cmd", "ClearOwnedWorkReadOnly.ps1"):
    before, after = sha(old / "media-input" / name), sha(media / name)
    assert before in start, name
    start = start.replace(before, after)
(media / "Start.ps1").write_text(start)
start_hash = sha(media / "Start.ps1").upper()
(new / "dispatch-command.txt").write_text(
    r"if ((Get-FileHash E:\Start.ps1).Hash -eq '" + start_hash
    + r"') { & ([scriptblock]::Create((Get-Content E:\Start.ps1 -Raw))) } else { throw 'SOURCE_MISMATCH' }" + "\n"
)
decoder = (old / "decode-native-export.py").read_text()
needle = '"attempt61": "' + previous["nonce"] + '"'
assert needle in decoder
decoder = decoder.replace(needle, needle + ', "attempt62": "' + nonce + '"')
(new / "decode-native-export.py").write_text(decoder)
binding = dict(previous)
binding.update(nonce=nonce, source_commit=current_commit,
               manifest_sha256=sha(media / "source-manifest.json"),
               archive_sha256=manifest["archive_sha256"],
               source_bytes=manifest["total_source_bytes"],
               expected="X35 native Windows public Managed run/spawn closure and sentinel controls with restored greens",
               native_started=False, command_dispatched=False, product_test_started=False)
(new / "binding.json").write_text(json.dumps(binding, indent=2) + "\n")
print(json.dumps(binding, indent=2))
