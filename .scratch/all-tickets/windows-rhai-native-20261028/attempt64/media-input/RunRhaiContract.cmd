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
set RHAI_WINDOWS_DIRECT_RUN_SURVIVAL_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_direct_run_keeps_descendant_alive_after_normal_parent_exit -- --exact --nocapture > direct-wrong.log 2>&1
set DIRECT_WRONG_RC=!ERRORLEVEL!
set RHAI_WINDOWS_DIRECT_RUN_SURVIVAL_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_direct_run_keeps_descendant_alive_after_normal_parent_exit -- --exact --nocapture > direct-green.log 2>&1
set DIRECT_GREEN_RC=!ERRORLEVEL!
echo RHAI_X35_DIRECT_WRONG_EXIT=!DIRECT_WRONG_RC!
echo RHAI_X35_DIRECT_GREEN_EXIT=!DIRECT_GREEN_RC!
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_X35_DIRECT_CLEANED
if not "!DIRECT_WRONG_RC!"=="101" exit /b 61
findstr /C:"deliberately wrong direct descendant survival expectation" direct-wrong.log > NUL || exit /b 62
if not "!DIRECT_GREEN_RC!"=="0" exit /b 65
findstr /C:"windows_direct_os_readback" direct-green.log > NUL || exit /b 66
echo RHAI_X35_DIRECT_CONTROLS_PASS
exit /b 0
