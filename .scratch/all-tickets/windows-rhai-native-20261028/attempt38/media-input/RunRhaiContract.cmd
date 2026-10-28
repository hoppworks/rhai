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
set RHAI_DEBUG_JOB_MEMBERS=1
for %%I in (1 2 3 4) do (
 "%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows -- --nocapture > suite-%%I.log 2>&1
 set RC=!ERRORLEVEL!
 echo RHAI_DIAG_SUITE_%%I_EXIT_!RC!
 type suite-%%I.log
 if not "!RC!"=="0" if not "!RC!"=="101" exit /b 61
 findstr /C:"[DEBUG-kill36]" suite-%%I.log > NUL
 if errorlevel 1 exit /b 62
 findstr /C:"test result:" suite-%%I.log > NUL
 if errorlevel 1 exit /b 63
)
echo RHAI_DIAG_FOUR_SUITES_COMPLETE
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 88)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_DIAG_CLEANUP_CONFIRMED
exit /b 0
