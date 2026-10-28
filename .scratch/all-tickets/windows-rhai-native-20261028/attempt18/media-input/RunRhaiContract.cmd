@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=1
echo RHAI_CARGO_LOW_MEMORY_PROFILE debug=0 incremental=0 codegen_units=256 jobs=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report --no-run > compile.log 2>&1
set COMPILE_EXIT=%ERRORLEVEL%
type compile.log
if not "%COMPILE_EXIT%"=="0" exit /b 59
set RHAI_WINDOWS_TIMEOUT_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_run_raw_timeout_terminates_exact_child_and_retains_output -- --exact --nocapture > red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_TIMEOUT_WRONG_EXPECTATION=
type red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"deliberately wrong timeout expectation" red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"test result: FAILED. 0 passed; 1 failed" red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"windows_run_raw_timeout_terminates_exact_child_and_retains_output" red.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_RED_EXPECTED_ASSERTION_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report -- --nocapture > green.log 2>&1
set GREEN_EXIT=%ERRORLEVEL%
type green.log
if not "%GREEN_EXIT%"=="0" exit /b 65
findstr /C:"windows_run_raw_timeout_terminates_exact_child_and_retains_output ... ok" green.log > NUL
if errorlevel 1 exit /b 66
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 68
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 69
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
set CLEAN_EXIT=%ERRORLEVEL%
type "%TEMP%\rhai-cargo-clean.log"
if not "%CLEAN_EXIT%"=="0" exit /b 71
if exist "%CARGO_TARGET_DIR%\debug\rhai-run.exe" exit /b 72
if exist "%CARGO_TARGET_DIR%\debug\deps\rhai_run.exe" exit /b 73
echo RHAI_CARGO_TARGET_CLEAN_CONFIRMED
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (
 type "%TEMP%\rhai-attributes.log"
 exit /b 70
)
type "%TEMP%\rhai-attributes.log"
echo RHAI_GREEN_HOST_READBACK_CONFIRMED
exit /b 0
