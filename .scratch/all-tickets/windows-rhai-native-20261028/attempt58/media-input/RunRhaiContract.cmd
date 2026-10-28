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
set RHAI_WINDOWS_MANAGED_CWD_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_resolves_simple_program_from_parent_cwd -- --exact --nocapture > wrong.log 2>&1
set WRONG_RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_CWD_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_resolves_simple_program_from_parent_cwd -- --exact --nocapture > green.log 2>&1
set GREEN_RC=!ERRORLEVEL!
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows > suite.log 2>&1
set SUITE_RC=!ERRORLEVEL!
echo RHAI_MANAGED_CWD_WRONG_EXIT=!WRONG_RC!
echo RHAI_MANAGED_CWD_GREEN_EXIT=!GREEN_RC!
echo RHAI_MANAGED_CWD_SUITE_EXIT=!SUITE_RC!
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_CWD_CLEANED
if not "!WRONG_RC!"=="101" exit /b 61
findstr /C:"deliberately wrong Managed cwd executable expectation" wrong.log > NUL || exit /b 62
if not "!GREEN_RC!"=="0" exit /b 63
findstr /C:"windows_managed_cwd_readback" green.log > NUL || exit /b 64
if not "!SUITE_RC!"=="0" exit /b 65
findstr /C:"test result: ok. 31 passed; 0 failed;" suite.log > NUL || exit /b 66
echo RHAI_MANAGED_CWD_CONTROL_PASS
exit /b 0
