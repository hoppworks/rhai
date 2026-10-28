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
set RHAI_WINDOWS_MANAGED_BATCH_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_executes_explicitly_allowed_batch -- --exact --nocapture > wrong.log 2>&1
set RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_BATCH_WRONG_EXPECTATION=
if not "!RC!"=="101" exit /b 61
findstr /C:"windows_managed_batch_denial_readback batch_denied=true child_file_absent=true" wrong.log > NUL || exit /b 75
findstr /C:"windows_managed_batch_readback allowed=true child_file=managed-batch-ok" wrong.log > NUL || exit /b 62
findstr /C:"deliberately wrong managed batch expectation" wrong.log > NUL || exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed;" wrong.log > NUL || exit /b 64
echo RHAI_ARGUMENT_WRONG_REJECTED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_executes_explicitly_allowed_batch -- --exact --nocapture > green.log 2>&1
if errorlevel 1 exit /b 65
findstr /C:"windows_managed_batch_denial_readback batch_denied=true child_file_absent=true" green.log > NUL || exit /b 76
findstr /C:"windows_managed_batch_readback allowed=true child_file=managed-batch-ok" green.log > NUL || exit /b 66
findstr /C:"test result: ok. 1 passed; 0 failed; 0 ignored" green.log > NUL || exit /b 67
echo RHAI_ARGUMENT_GREEN
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_ARGUMENT_CLEANUP_CONFIRMED
exit /b 0
