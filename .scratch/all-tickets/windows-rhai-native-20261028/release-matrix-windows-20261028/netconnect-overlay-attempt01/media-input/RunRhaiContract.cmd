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
set "SYS_COMPILE_RC=999"
set "SYS_WRONG_RC=999"
set "SYS_SUITE_RC=999"
set "NET_COMPILE_RC=999"
set "NET_WRONG_RC=999"
set "NET_SUITE_RC=999"
"%~dp0cargo.exe" test --locked --features testing-environ,sys --test sys_policy --test sys_env --test sys_fs --no-run > sys-compile.log 2>&1
set "SYS_COMPILE_RC=!ERRORLEVEL!"
if not "!SYS_COMPILE_RC!"=="0" goto cleanup
set RHAI_FILE_HANDLE_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys --test sys_fs test_open_file_default_preserves_contents_and_shares_cursor -- --exact --nocapture > sys-wrong.log 2>&1
set "SYS_WRONG_RC=!ERRORLEVEL!"
set RHAI_FILE_HANDLE_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,sys --test sys_policy --test sys_env --test sys_fs -- --test-threads=1 --nocapture > sys-suite.log 2>&1
set "SYS_SUITE_RC=!ERRORLEVEL!"
if not "!SYS_SUITE_RC!"=="0" goto cleanup
"%~dp0cargo.exe" test --locked --features testing-environ,net --test net_connect --test net_listen --test net_reads --test net_writes --no-run > net-compile.log 2>&1
set "NET_COMPILE_RC=!ERRORLEVEL!"
if not "!NET_COMPILE_RC!"=="0" goto cleanup
set RHAI_NET_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,net --test net_connect authorized_connect_is_observed_and_clone_close_is_shared -- --exact --nocapture > net-wrong.log 2>&1
set "NET_WRONG_RC=!ERRORLEVEL!"
set RHAI_NET_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,net --test net_connect --test net_listen --test net_reads --test net_writes -- --test-threads=1 --nocapture > net-suite.log 2>&1
set "NET_SUITE_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo RHAI_SYS_COMPILE_EXIT=!SYS_COMPILE_RC!
echo RHAI_SYS_WRONG_EXIT=!SYS_WRONG_RC!
echo RHAI_SYS_SUITE_EXIT=!SYS_SUITE_RC!
echo RHAI_NET_COMPILE_EXIT=!NET_COMPILE_RC!
echo RHAI_NET_WRONG_EXIT=!NET_WRONG_RC!
echo RHAI_NET_SUITE_EXIT=!NET_SUITE_RC!
if not "!SYS_COMPILE_RC!"=="0" exit /b 59
if not "!SYS_WRONG_RC!"=="101" exit /b 61
if not "!SYS_SUITE_RC!"=="0" exit /b 62
if not "!NET_COMPILE_RC!"=="0" exit /b 63
if not "!NET_WRONG_RC!"=="101" exit /b 64
if not "!NET_SUITE_RC!"=="0" exit /b 65
echo RHAI_PACKAGE_ALONE_CONTROLS_PASS
exit /b 0
