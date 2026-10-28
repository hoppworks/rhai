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
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=kill
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_final_drop_follows_host_policy -- --exact --nocapture > kill-wrong.log 2>&1
set WRONG_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=
type kill-wrong.log
if not "%WRONG_EXIT%"=="101" exit /b 61
findstr /C:"windows_managed_drop_os_readback mode=kill" kill-wrong.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"deliberately wrong managed kill drop termination expectation" kill-wrong.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed" kill-wrong.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_MANAGED_DROP_KILL_WRONG_CONFIRMED
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=retain
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_final_drop_follows_host_policy -- --exact --nocapture > retain-wrong.log 2>&1
set WRONG_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=
type retain-wrong.log
if not "%WRONG_EXIT%"=="101" exit /b 65
findstr /C:"windows_managed_drop_os_readback mode=retain" retain-wrong.log > NUL
if errorlevel 1 exit /b 66
findstr /C:"deliberately wrong managed retain drop survival expectation" retain-wrong.log > NUL
if errorlevel 1 exit /b 67
findstr /C:"test result: FAILED. 0 passed; 1 failed" retain-wrong.log > NUL
if errorlevel 1 exit /b 68
echo RHAI_MANAGED_DROP_RETAIN_WRONG_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report -- --nocapture > green.log 2>&1
if errorlevel 1 exit /b 80
type green.log
findstr /C:"windows_managed_drop_os_readback mode=kill" green.log > NUL
if errorlevel 1 exit /b 81
findstr /C:"windows_managed_drop_os_readback mode=retain" green.log > NUL
if errorlevel 1 exit /b 82
echo RHAI_MANAGED_DROP_AND_REGRESSION_GREEN_CONFIRMED
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_COMBINED_CLEANUP_CONFIRMED
exit /b 0
