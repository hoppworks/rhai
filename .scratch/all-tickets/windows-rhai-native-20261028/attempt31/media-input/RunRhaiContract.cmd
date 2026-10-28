@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --no-run > compile.log 2>&1
set COMPILE_EXIT=%ERRORLEVEL%
type compile.log
if not "%COMPILE_EXIT%"=="0" exit /b 59
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_managed_run_closes_descendant_on_normal_parent_exit -- --exact --nocapture > managed-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
type managed-red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"windows_managed_contract_denied_before_launch observation=false" managed-red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"Windows managed run must execute and close its descendant scope" managed-red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed" managed-red.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_MANAGED_DENIED_BASELINE_RED_CONFIRMED
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 83
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 84
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 85
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 87)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_BASELINE_CLEANUP_CONFIRMED
exit /b 0
