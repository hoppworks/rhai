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
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows -- --nocapture --test-threads=1 > suite.log 2>&1
set SUITE_RC=!ERRORLEVEL!
echo RHAI_PROCESS_SUITE_EXIT=!SUITE_RC!
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::members::tests:: -- --nocapture --test-threads=1 > member.log 2>&1
set MEMBER_RC=!ERRORLEVEL!
echo RHAI_MEMBER_TEST_EXIT=!MEMBER_RC!
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_PROCESS_FOLLOWUP_CLEANED
if not "!SUITE_RC!"=="0" exit /b 61
findstr /C:"test result: ok. 29 passed; 0 failed;" suite.log > NUL || exit /b 62
if not "!MEMBER_RC!"=="0" exit /b 63
findstr /C:"test result: ok. 5 passed; 0 failed;" member.log > NUL || exit /b 64
echo RHAI_PROCESS_FOLLOWUP_GREEN
exit /b 0
