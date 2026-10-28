@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report --no-run > compile.log 2>&1
set COMPILE_EXIT=%ERRORLEVEL%
type compile.log
if not "%COMPILE_EXIT%"=="0" exit /b 59
set RHAI_WINDOWS_CHILD_DROP_WRONG_EXPECTATION=kill
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_spawn_child_drop_follows_host_policy -- --exact --nocapture > spawn-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_CHILD_DROP_WRONG_EXPECTATION=
type spawn-red.log
if not "%RED_EXIT%"=="101" exit /b 61
findstr /C:"deliberately wrong child drop kill survival expectation" spawn-red.log > NUL
if errorlevel 1 exit /b 62
findstr /C:"windows_child_drop_os_readback mode=kill" spawn-red.log > NUL
if errorlevel 1 exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed" spawn-red.log > NUL
if errorlevel 1 exit /b 64
echo RHAI_CHILD_DROP_KILL_RED_CONFIRMED
set RHAI_WINDOWS_CHILD_DROP_WRONG_EXPECTATION=retain
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows windows_spawn_child_drop_follows_host_policy -- --exact --nocapture > retain-red.log 2>&1
set RED_EXIT=%ERRORLEVEL%
set RHAI_WINDOWS_CHILD_DROP_WRONG_EXPECTATION=
type retain-red.log
if not "%RED_EXIT%"=="101" exit /b 65
findstr /C:"deliberately wrong child drop retain survival expectation" retain-red.log > NUL
if errorlevel 1 exit /b 66
findstr /C:"windows_child_drop_os_readback mode=retain" retain-red.log > NUL
if errorlevel 1 exit /b 67
findstr /C:"test result: FAILED. 0 passed; 1 failed" retain-red.log > NUL
if errorlevel 1 exit /b 68
echo RHAI_CHILD_DROP_RETAIN_RED_CONFIRMED
"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --test sys_process_windows --test sys_process_report -- --nocapture > green.log 2>&1
set GREEN_EXIT=%ERRORLEVEL%
type green.log
if not "%GREEN_EXIT%"=="0" exit /b 80
findstr /C:"windows_spawn_child_drop_follows_host_policy ... ok" green.log > NUL
if errorlevel 1 exit /b 81
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 83
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 84
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 85
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 87)
type "%TEMP%\rhai-attributes.log"
echo RHAI_CHILD_DROP_GREEN_CLEANUP_CONFIRMED
exit /b 0
