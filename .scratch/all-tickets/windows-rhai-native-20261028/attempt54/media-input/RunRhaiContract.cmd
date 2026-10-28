@echo off
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
