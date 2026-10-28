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
set RC=!ERRORLEVEL!
if not "!RC!"=="0" if not "!RC!"=="101" exit /b 61
findstr /C:"windows_managed_batch_argument_readback injected=" actual.log > NUL || exit /b 62
findstr /C:"test result:" actual.log > NUL || exit /b 63
echo RHAI_BATCH_ARGUMENT_ACTUAL_EXIT_!RC!
if "!RC!"=="0" (
 set RHAI_WINDOWS_BATCH_INJECTION_WRONG_EXPECTATION=1
 "%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_batch_argument_cannot_create_an_extra_file -- --exact --nocapture > wrong.log 2>&1
 set WRONG_RC=!ERRORLEVEL!
 set RHAI_WINDOWS_BATCH_INJECTION_WRONG_EXPECTATION=
 if not "!WRONG_RC!"=="101" exit /b 64
 findstr /C:"deliberately wrong batch injection expectation" wrong.log > NUL || exit /b 65
 findstr /C:"test result: FAILED. 0 passed; 1 failed;" wrong.log > NUL || exit /b 66
 echo RHAI_BATCH_ARGUMENT_WRONG_REJECTED
) else (
 echo WRONG_CONTROL_NOT_RUN_BECAUSE_ACTUAL_TEST_FAILED> wrong.log
 echo RHAI_BATCH_ARGUMENT_WRONG_NOT_RUN
)
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_BATCH_ARGUMENT_DIAGNOSTIC_CLEANED
exit /b 0
