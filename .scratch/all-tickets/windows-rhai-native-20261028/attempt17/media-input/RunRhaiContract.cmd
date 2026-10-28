@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=1
echo RHAI_CARGO_LOW_MEMORY_PROFILE debug=0 incremental=0 codegen_units=256 jobs=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib --test sys_process_windows --test sys_process_report --no-run > compile.log 2>&1
set COMPILE_EXIT=%ERRORLEVEL%
type compile.log
if not "%COMPILE_EXIT%"=="0" exit /b 59
set RHAI_WINDOWS_PROCESS_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_run_returns_lossy_text_and_nonzero_exit -- --exact --nocapture > red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_PROCESS_WRONG_EXPECTATION=
type red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"deliberately wrong native text process exit expectation" red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"test result: FAILED. 0 passed; 1 failed" red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"windows_run_returns_lossy_text_and_nonzero_exit" red.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_RED_EXPECTED_ASSERTION_CONFIRMED
set RHAI_WINDOWS_TEXT_LIMIT_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_run_rejects_decoded_text_expansion_with_original_raw_report -- --exact --nocapture > limit-red.log 2>&1
set LIMIT_RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_TEXT_LIMIT_WRONG_EXPECTATION=
type limit-red.log
if not "%LIMIT_RED_EXIT%"=="101" exit /b 81
findstr /C:"deliberately wrong decoded expansion expectation" limit-red.log > NUL
if errorlevel 1 exit /b 82
findstr /C:"test result: FAILED. 0 passed; 1 failed" limit-red.log > NUL
if errorlevel 1 exit /b 83
findstr /C:"windows_run_rejects_decoded_text_expansion_with_original_raw_report" limit-red.log > NUL
if errorlevel 1 exit /b 84
echo RHAI_TEXT_LIMIT_RED_EXPECTED_ASSERTION_CONFIRMED
set RHAI_WINDOWS_DEADLINE_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib windows_deadline_overflow_is_denied -- --nocapture > deadline-red.log 2>&1
set DEADLINE_RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_DEADLINE_WRONG_EXPECTATION=
type deadline-red.log
if not "%DEADLINE_RED_EXIT%"=="101" exit /b 74
findstr /C:"deliberately wrong deadline overflow expectation" deadline-red.log > NUL
if errorlevel 1 exit /b 75
findstr /C:"test result: FAILED. 0 passed; 1 failed" deadline-red.log > NUL
if errorlevel 1 exit /b 76
findstr /C:"windows_deadline_overflow_is_denied" deadline-red.log > NUL
if errorlevel 1 exit /b 77
echo RHAI_DEADLINE_RED_EXPECTED_ASSERTION_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib windows_deadline_overflow_is_denied -- --nocapture > deadline-green.log 2>&1
set DEADLINE_GREEN_EXIT=%ERRORLEVEL%
type deadline-green.log
if not "%DEADLINE_GREEN_EXIT%"=="0" exit /b 78
findstr /C:"test result: ok. 1 passed; 0 failed" deadline-green.log > NUL
if errorlevel 1 exit /b 79
findstr /C:"windows_deadline_overflow_is_denied ... ok" deadline-green.log > NUL
if errorlevel 1 exit /b 80
echo RHAI_DEADLINE_GREEN_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report -- --nocapture > green.log 2>&1
set GREEN_EXIT=%ERRORLEVEL%
type green.log
if not "%GREEN_EXIT%"=="0" exit /b 65
findstr /C:"windows_run_returns_lossy_text_and_nonzero_exit ... ok" green.log > NUL
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
