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
set RHAI_WINDOWS_CPU_LIMIT_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::members::tests::job_cpu_limit_signal_is_observed_with_held_fixture_handles -- --exact --nocapture > wrong.log 2>&1
set RC=!ERRORLEVEL!
set RHAI_WINDOWS_CPU_LIMIT_WRONG_EXPECTATION=
if not "!RC!"=="101" exit /b 61
findstr /C:"windows_job_cpu_signal_readback job=0x0 child=0x0 helper=0x0" wrong.log > NUL || exit /b 62
findstr /C:"deliberately wrong job CPU signal expectation" wrong.log > NUL || exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed;" wrong.log > NUL || exit /b 64
echo RHAI_ARGUMENT_WRONG_REJECTED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::members::tests::job_cpu_limit_signal_is_observed_with_held_fixture_handles -- --exact --nocapture > green.log 2>&1
if errorlevel 1 exit /b 65
findstr /C:"windows_job_cpu_signal_readback job=0x0 child=0x0 helper=0x0" green.log > NUL || exit /b 66
findstr /C:"test result: ok. 1 passed; 0 failed; 0 ignored" green.log > NUL || exit /b 67
echo RHAI_ARGUMENT_GREEN
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_ARGUMENT_CLEANUP_CONFIRMED
exit /b 0
