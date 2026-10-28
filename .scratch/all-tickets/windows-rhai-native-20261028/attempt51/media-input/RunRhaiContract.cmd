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
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_batch_argument_cannot_create_an_extra_file -- --exact --nocapture > actual.log 2>&1
if not "!ERRORLEVEL!"=="0" exit /b 61
findstr /C:"windows_managed_batch_argument_readback injected=false" actual.log > NUL || exit /b 62
findstr /C:"test result: ok. 1 passed; 0 failed;" actual.log > NUL || exit /b 63
echo RHAI_BATCH_ARGUMENT_ACTUAL_EXIT_0
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_executes_explicitly_allowed_batch -- --exact --nocapture > noargs.log 2>&1
if not "!ERRORLEVEL!"=="0" exit /b 64
findstr /C:"windows_managed_batch_denial_readback batch_denied=true child_file_absent=true" noargs.log > NUL || exit /b 65
findstr /C:"windows_managed_batch_readback allowed=true child_file=managed-batch-ok" noargs.log > NUL || exit /b 66
findstr /C:"test result: ok. 1 passed; 0 failed;" noargs.log > NUL || exit /b 67
echo RHAI_BATCH_NOARGS_GREEN
set RHAI_WINDOWS_BATCH_INJECTION_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_batch_argument_cannot_create_an_extra_file -- --exact --nocapture > wrong.log 2>&1
set WRONG_RC=!ERRORLEVEL!
set RHAI_WINDOWS_BATCH_INJECTION_WRONG_EXPECTATION=
if not "!WRONG_RC!"=="101" exit /b 68
findstr /C:"deliberately wrong batch injection expectation" wrong.log > NUL || exit /b 69
findstr /C:"test result: FAILED. 0 passed; 1 failed;" wrong.log > NUL || exit /b 70
echo RHAI_BATCH_ARGUMENT_WRONG_REJECTED
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_BATCH_ARGUMENT_GREEN_CLEANED
exit /b 0
