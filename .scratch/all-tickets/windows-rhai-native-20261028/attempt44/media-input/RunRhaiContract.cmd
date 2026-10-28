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
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::tests::windows_cleanup_panic_preserves_exact_owner_and_permit -- --exact --nocapture > red.log 2>&1
set RC=!ERRORLEVEL!
if not "!RC!"=="101" exit /b 61
findstr /C:"deliberate per-owner cleanup panic" red.log > NUL || exit /b 62
findstr /C:"cleanup worker must preserve exact owner and permit after panic" red.log > NUL || exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed;" red.log > NUL || exit /b 64
echo RHAI_CLEANUP_CUSTODY_RED
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_CLEANUP_CUSTODY_RED_CLEANED
exit /b 0
