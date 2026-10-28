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
set RHAI_WINDOWS_STDIN_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_run_raw_transfers_blob_while_draining_both_streams -- --exact --nocapture > blob-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_STDIN_WRONG_EXPECTATION=
type blob-red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"deliberately wrong stdin round-trip expectation" blob-red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"test result: FAILED. 0 passed; 1 failed" blob-red.log > NUL
if errorlevel 1 exit /b 63
echo RHAI_BLOB_RED_CONFIRMED
set RHAI_WINDOWS_STDIN_SCALAR_WRONG_EXPECTATION=string
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_run_string_empty_and_unit_stdin_reach_child_eof -- --exact --nocapture > scalar-string-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_STDIN_SCALAR_WRONG_EXPECTATION=
type scalar-string-red.log
if not "%RED_EXIT%"=="101" exit /b 70
findstr /C:"deliberately wrong scalar stdin string expectation" scalar-string-red.log > NUL
if errorlevel 1 exit /b 71
findstr /C:"test result: FAILED. 0 passed; 1 failed" scalar-string-red.log > NUL
if errorlevel 1 exit /b 72
echo RHAI_SCALAR_STRING_RED_CONFIRMED
set RHAI_WINDOWS_STDIN_SCALAR_WRONG_EXPECTATION=empty
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_run_string_empty_and_unit_stdin_reach_child_eof -- --exact --nocapture > scalar-empty-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_STDIN_SCALAR_WRONG_EXPECTATION=
type scalar-empty-red.log
if not "%RED_EXIT%"=="101" exit /b 73
findstr /C:"deliberately wrong scalar stdin empty expectation" scalar-empty-red.log > NUL
if errorlevel 1 exit /b 74
findstr /C:"test result: FAILED. 0 passed; 1 failed" scalar-empty-red.log > NUL
if errorlevel 1 exit /b 75
echo RHAI_SCALAR_EMPTY_RED_CONFIRMED
set RHAI_WINDOWS_STDIN_SCALAR_WRONG_EXPECTATION=unit
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_run_string_empty_and_unit_stdin_reach_child_eof -- --exact --nocapture > scalar-unit-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_STDIN_SCALAR_WRONG_EXPECTATION=
type scalar-unit-red.log
if not "%RED_EXIT%"=="101" exit /b 76
findstr /C:"deliberately wrong scalar stdin unit expectation" scalar-unit-red.log > NUL
if errorlevel 1 exit /b 77
findstr /C:"test result: FAILED. 0 passed; 1 failed" scalar-unit-red.log > NUL
if errorlevel 1 exit /b 78
echo RHAI_SCALAR_UNIT_RED_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report -- --nocapture > green.log 2>&1
set GREEN_EXIT=%ERRORLEVEL%
type green.log
if not "%GREEN_EXIT%"=="0" exit /b 80
findstr /C:"windows_run_raw_transfers_blob_while_draining_both_streams ... ok" green.log > NUL
if errorlevel 1 exit /b 81
findstr /C:"windows_run_string_empty_and_unit_stdin_reach_child_eof ... ok" green.log > NUL
if errorlevel 1 exit /b 82
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 83
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 84
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
set CLEAN_EXIT=%ERRORLEVEL%
type "%TEMP%\rhai-cargo-clean.log"
if not "%CLEAN_EXIT%"=="0" exit /b 85
if exist "%CARGO_TARGET_DIR%\debug\rhai-run.exe" exit /b 86
echo RHAI_CARGO_TARGET_CLEAN_CONFIRMED
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (
 type "%TEMP%\rhai-attributes.log"
 exit /b 87
)
type "%TEMP%\rhai-attributes.log"
echo RHAI_GREEN_HOST_READBACK_CONFIRMED
exit /b 0
