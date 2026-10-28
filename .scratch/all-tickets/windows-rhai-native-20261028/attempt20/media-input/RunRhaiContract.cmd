@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=1
echo RHAI_CARGO_LOW_MEMORY_PROFILE debug=0 incremental=0 codegen_units=256 jobs=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --no-run > compile.log 2>&1
set COMPILE_EXIT=%ERRORLEVEL%
type compile.log
if not "%COMPILE_EXIT%"=="0" exit /b 59
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_run_raw_transfers_blob_while_draining_both_streams -- --exact --nocapture > red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
type red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"stdin must support concurrent transfer" red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"unsupported Windows process option" red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"child_observed=false" red.log > NUL
if errorlevel 1 exit /b 64
findstr /C:"test result: FAILED. 0 passed; 1 failed" red.log > NUL
if errorlevel 1 exit /b 65
echo RHAI_STDIN_MISSING_RED_CONFIRMED
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 68
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 69
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
set CLEAN_EXIT=%ERRORLEVEL%
type "%TEMP%\rhai-cargo-clean.log"
if not "%CLEAN_EXIT%"=="0" exit /b 71
if exist "%CARGO_TARGET_DIR%\debug\rhai-run.exe" exit /b 72
echo RHAI_CARGO_TARGET_CLEAN_CONFIRMED
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (
 type "%TEMP%\rhai-attributes.log"
 exit /b 70
)
type "%TEMP%\rhai-attributes.log"
exit /b 0
