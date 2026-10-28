@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib --no-run > compile.log 2>&1
set COMPILE_EXIT=%ERRORLEVEL%
type compile.log
if not "%COMPILE_EXIT%"=="0" exit /b 59
set RHAI_WINDOWS_PENDING_SKIP_CANCEL=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::child::pending_tests::public_kill_cancels_an_observed_pending_stdin_write -- --exact --nocapture > spawn-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_PENDING_SKIP_CANCEL=
type spawn-red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"windows_pending_mutant_readback" spawn-red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"deliberately suppressed initial pending write cancellation" spawn-red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed" spawn-red.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_PENDING_MUTANT_RED_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::child::pending_tests::public_kill_cancels_an_observed_pending_stdin_write -- --exact --nocapture > green.log 2>&1
set GREEN_EXIT=%ERRORLEVEL%
type green.log
if not "%GREEN_EXIT%"=="0" exit /b 80
findstr /C:"windows_pending_public_kill_readback" green.log > NUL
if errorlevel 1 exit /b 81
findstr /C:"test result: ok. 1 passed; 0 failed" green.log > NUL
if errorlevel 1 exit /b 82
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 83
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 84
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 85
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 87)
type "%TEMP%\rhai-attributes.log"
echo RHAI_PENDING_GREEN_CLEANUP_CONFIRMED
exit /b 0
