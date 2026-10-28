@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report --no-run > compile.log 2>&1
if errorlevel 1 exit /b 59
set RHAI_WINDOWS_MANAGED_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_wait_closes_descendant_on_parent_exit -- --exact --nocapture > spawn-wrong.log 2>&1
set WRONG_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_MANAGED_WRONG_EXPECTATION=
type spawn-wrong.log
if not "%WRONG_EXIT%"=="101" exit /b 61
findstr /C:"windows_managed_spawn_os_readback" spawn-wrong.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"deliberately wrong managed spawn closure expectation" spawn-wrong.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed" spawn-wrong.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_MANAGED_SPAWN_WRONG_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report -- --nocapture > green.log 2>&1
if errorlevel 1 exit /b 80
type green.log
findstr /C:"windows_managed_spawn_os_readback" green.log > NUL
if errorlevel 1 exit /b 81
findstr /C:"windows_managed_run_closes_descendant_on_normal_parent_exit" green.log > NUL
if errorlevel 1 exit /b 82
findstr /C:"windows_managed_spawn_wait_closes_descendant_on_parent_exit" green.log > NUL
if errorlevel 1 exit /b 83
findstr /C:"test result: ok." green.log > NUL
if errorlevel 1 exit /b 84
echo RHAI_MANAGED_SPAWN_AND_REGRESSION_GREEN_CONFIRMED
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_COMBINED_CLEANUP_CONFIRMED
exit /b 0
