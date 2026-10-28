@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib --no-run > compile.log 2>&1
if errorlevel 1 exit /b 59
set RHAI_WINDOWS_MANAGED_RETRY_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::tests::windows_background_retries_failed_job_termination_and_retains_uncertain_owner -- --exact --nocapture > wrong.log 2>&1
set WRONG_RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_RETRY_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::tests::windows_background_retries_failed_job_termination_and_retains_uncertain_owner -- --exact --nocapture > green.log 2>&1
set GREEN_RC=!ERRORLEVEL!
echo RHAI_MANAGED_RETRY_WRONG_EXIT=!WRONG_RC!
echo RHAI_MANAGED_RETRY_GREEN_EXIT=!GREEN_RC!
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_RETRY_CLEANED
if not "!WRONG_RC!"=="101" exit /b 61
findstr /C:"deliberately wrong managed termination retry expectation" wrong.log > NUL || exit /b 62
if not "!GREEN_RC!"=="0" exit /b 63
findstr /C:"test result: ok. 1 passed; 0 failed;" green.log > NUL || exit /b 64
echo RHAI_MANAGED_RETRY_CONTROL_PASS
exit /b 0
