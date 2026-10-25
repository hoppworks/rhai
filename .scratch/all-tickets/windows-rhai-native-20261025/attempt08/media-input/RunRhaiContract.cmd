@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=1
echo RHAI_CARGO_LOW_MEMORY_PROFILE debug=0 incremental=0 codegen_units=256 jobs=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,net,metadata --test net_connect --test net_listen --test net_reads --test net_writes --test net_metadata --test combined_sys_net --no-run > compile.log 2>&1
set COMPILE_EXIT=%ERRORLEVEL%
type compile.log
if not "%COMPILE_EXIT%"=="0" exit /b 59
set RHAI_NET_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,net,metadata --test net_connect authorized_connect_is_observed_and_clone_close_is_shared -- --exact --nocapture > red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_NET_WRONG_EXPECTATION=
type red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"deliberately wrong peer EOF expectation" red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"test result: FAILED. 0 passed; 1 failed" red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"authorized_connect_is_observed_and_clone_close_is_shared" red.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_RED_EXPECTED_ASSERTION_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,net,metadata --test net_connect --test net_listen --test net_reads --test net_writes --test net_metadata --test combined_sys_net -- --nocapture > green.log 2>&1
set GREEN_EXIT=%ERRORLEVEL%
type green.log
if not "%GREEN_EXIT%"=="0" exit /b 65
findstr /C:"authorized_connect_is_observed_and_clone_close_is_shared ... ok" green.log > NUL
if errorlevel 1 exit /b 66
findstr /C:"test result: ok." green.log > NUL
if errorlevel 1 exit /b 67
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
