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
set RHAI_WINDOWS_CLEANUP_PANIC_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::tests::windows_cleanup_panic_preserves_exact_owner_and_permit -- --exact --nocapture > wrong.log 2>&1
set RC=!ERRORLEVEL!
set RHAI_WINDOWS_CLEANUP_PANIC_WRONG_EXPECTATION=
if not "!RC!"=="101" exit /b 61
findstr /C:"windows_cleanup_panic_readback exact_child_reaped=true owner_retained=true" wrong.log > NUL || exit /b 62
findstr /C:"deliberately wrong cleanup custody expectation" wrong.log > NUL || exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed;" wrong.log > NUL || exit /b 64
echo RHAI_CLEANUP_WRONG_REJECTED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::tests::windows_cleanup_panic_preserves_exact_owner_and_permit -- --exact --nocapture > green.log 2>&1
if errorlevel 1 exit /b 65
findstr /C:"windows_cleanup_panic_readback exact_child_reaped=true owner_retained=true" green.log > NUL || exit /b 66
findstr /C:"test result: ok. 1 passed; 0 failed; 0 ignored" green.log > NUL || exit /b 67
echo RHAI_CLEANUP_GREEN
set RHAI_WINDOWS_PENDING_SKIP_CANCEL=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::child::pending_tests::public_kill_cancels_an_observed_pending_stdin_write -- --exact --nocapture > pending-red.log 2>&1
set RC=!ERRORLEVEL!
set RHAI_WINDOWS_PENDING_SKIP_CANCEL=
if not "!RC!"=="101" exit /b 68
findstr /C:"windows_pending_mutant_readback" pending-red.log > NUL || exit /b 69
findstr /C:"deliberately suppressed initial pending write cancellation" pending-red.log > NUL || exit /b 70
findstr /C:"test result: FAILED. 0 passed; 1 failed;" pending-red.log > NUL || exit /b 71
echo RHAI_PENDING_RED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::child::pending_tests::public_kill_cancels_an_observed_pending_stdin_write -- --exact --nocapture > pending-green.log 2>&1
if errorlevel 1 exit /b 72
findstr /C:"windows_pending_public_kill_readback" pending-green.log > NUL || exit /b 73
findstr /C:"test result: ok. 1 passed; 0 failed; 0 ignored" pending-green.log > NUL || exit /b 74
echo RHAI_PENDING_GREEN
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_CLEANUP_PACKAGE_CLEANED
exit /b 0
