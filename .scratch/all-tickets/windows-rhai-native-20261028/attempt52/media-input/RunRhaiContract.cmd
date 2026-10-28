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
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_ -- --nocapture --test-threads=1 > suite.log 2>&1
set SUITE_RC=!ERRORLEVEL!
echo RHAI_MANAGED_SUITE_EXIT=!SUITE_RC!
set RHAI_WINDOWS_MANAGED_KILL_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_spawn_kill_closes_descendant_and_preserves_sentinel -- --exact --nocapture > wrong.log 2>&1
set WRONG_RC=!ERRORLEVEL!
set RHAI_WINDOWS_MANAGED_KILL_WRONG_EXPECTATION=
echo RHAI_MANAGED_WRONG_EXIT=!WRONG_RC!
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_CLEANED
if not "!SUITE_RC!"=="0" exit /b 61
findstr /C:"test result: ok. 9 passed; 0 failed;" suite.log > NUL || exit /b 62
if not "!WRONG_RC!"=="101" exit /b 63
findstr /C:"deliberately wrong managed kill closure expectation" wrong.log > NUL || exit /b 64
findstr /C:"test result: FAILED. 0 passed; 1 failed;" wrong.log > NUL || exit /b 65
echo RHAI_MANAGED_CLOSURE_GREEN_AND_WRONG_REJECTED
exit /b 0
