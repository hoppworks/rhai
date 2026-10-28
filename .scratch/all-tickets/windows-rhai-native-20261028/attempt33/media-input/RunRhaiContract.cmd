@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --no-run > compile.log 2>&1
if errorlevel 1 exit /b 59
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_wait_closes_descendant_on_parent_exit -- --exact --nocapture > spawn-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
type spawn-red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"windows_managed_spawn_denied_before_launch observation=false" spawn-red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"Windows managed spawn must execute and close its descendant scope" spawn-red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed" spawn-red.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_MANAGED_SPAWN_RED_CONFIRMED
set RHAI_WINDOWS_MANAGED_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_closes_descendant_on_normal_parent_exit -- --exact --nocapture > run-wrong.log 2>&1
set WRONG_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_MANAGED_WRONG_EXPECTATION=
type run-wrong.log
if not "%WRONG_EXIT%"=="101" exit /b 65
findstr /C:"windows_managed_os_readback" run-wrong.log > NUL
if errorlevel 1 exit /b 66
findstr /C:"deliberately wrong managed sentinel expectation" run-wrong.log > NUL
if errorlevel 1 exit /b 67
findstr /C:"test result: FAILED. 0 passed; 1 failed" run-wrong.log > NUL
if errorlevel 1 exit /b 68
echo RHAI_MANAGED_RUN_WRONG_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_closes_descendant_on_normal_parent_exit -- --exact --nocapture > run-green.log 2>&1
if errorlevel 1 exit /b 80
type run-green.log
findstr /C:"windows_managed_os_readback" run-green.log > NUL
if errorlevel 1 exit /b 81
findstr /C:"test result: ok. 1 passed" run-green.log > NUL
if errorlevel 1 exit /b 82
echo RHAI_MANAGED_RUN_GREEN_CONFIRMED
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 83
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 84
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 85
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 87)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_COMBINED_CLEANUP_CONFIRMED
exit /b 0
