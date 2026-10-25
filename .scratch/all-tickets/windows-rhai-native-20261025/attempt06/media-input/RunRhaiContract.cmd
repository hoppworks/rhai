@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs --no-run > compile.log 2>&1
set COMPILE_EXIT=%ERRORLEVEL%
type compile.log
if not "%COMPILE_EXIT%"=="0" exit /b 59
set RHAI_FILE_HANDLE_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_fs test_open_file_default_preserves_contents_and_shares_cursor -- --exact --nocapture > red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_FILE_HANDLE_WRONG_EXPECTATION=
type red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"independent host readback:" red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"test result: FAILED. 0 passed; 1 failed" red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"test_open_file_default_preserves_contents_and_shares_cursor" red.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_RED_EXPECTED_ASSERTION_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs -- --nocapture > green.log 2>&1
set GREEN_EXIT=%ERRORLEVEL%
type green.log
if not "%GREEN_EXIT%"=="0" exit /b 65
findstr /C:"test_open_file_default_preserves_contents_and_shares_cursor ... ok" green.log > NUL
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
