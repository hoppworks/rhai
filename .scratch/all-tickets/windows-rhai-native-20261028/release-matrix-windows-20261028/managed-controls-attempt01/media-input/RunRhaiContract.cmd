@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
if /I not "%RUSTUP_HOME%"=="C:\Users\RhaiTest\.local\share\agent-builds\rhai\n-a7e54f39\toolchain-home" exit /b 88
if /I not "%RUSTUP_TOOLCHAIN%"=="1.77.2-x86_64-pc-windows-msvc" exit /b 89
set "RUSTC=%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\rustc.exe"
set "RUSTC_WRAPPER="
set "RUSTC_WORKSPACE_WRAPPER="
set "CARGO_BUILD_RUSTC="
"%~dp0cargo.exe" --version > cargo-version.txt 2>&1
if errorlevel 1 exit /b 90
"%RUSTC%" --version > rustc-version.txt 2>&1
if errorlevel 1 exit /b 91
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
set PROFILE=testing-environ,sys,net
set TARGET=--test sys_process_windows
set "COMPILE_RC=999"
set "KILL_RC=999"
set "TIMEOUT_RC=999"
set "DROP_KILL_RC=999"
set "DROP_RETAIN_RC=999"
set "SUITE_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_MANAGED_KILL_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_managed_spawn_kill_closes_descendant_and_preserves_sentinel -- --exact --nocapture > managed-kill-wrong.log 2>&1
set "KILL_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_MANAGED_KILL_WRONG_EXPECTATION=
set RHAI_WINDOWS_MANAGED_TIMEOUT_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_managed_timeout_closes_descendant_and_preserves_sentinel -- --exact --nocapture > managed-timeout-wrong.log 2>&1
set "TIMEOUT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_MANAGED_TIMEOUT_WRONG_EXPECTATION=
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=kill
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_managed_spawn_final_drop_follows_host_policy -- --exact --nocapture > managed-drop-kill-wrong.log 2>&1
set "DROP_KILL_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=retain
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_managed_spawn_final_drop_follows_host_policy -- --exact --nocapture > managed-drop-retain-wrong.log 2>&1
set "DROP_RETAIN_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo RHAI_MANAGED_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_MANAGED_KILL_WRONG_EXIT=!KILL_RC!
echo RHAI_MANAGED_TIMEOUT_WRONG_EXIT=!TIMEOUT_RC!
echo RHAI_MANAGED_DROP_KILL_WRONG_EXIT=!DROP_KILL_RC!
echo RHAI_MANAGED_DROP_RETAIN_WRONG_EXIT=!DROP_RETAIN_RC!
echo RHAI_MANAGED_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!KILL_RC!"=="101" exit /b 61
if not "!TIMEOUT_RC!"=="101" exit /b 62
if not "!DROP_KILL_RC!"=="101" exit /b 63
if not "!DROP_RETAIN_RC!"=="101" exit /b 64
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_MANAGED_CONTROLS_PASS
exit /b 0
