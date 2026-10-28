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
