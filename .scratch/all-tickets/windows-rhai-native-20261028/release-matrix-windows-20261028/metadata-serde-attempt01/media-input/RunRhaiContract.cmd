@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 60
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 85
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 86
if /I not "%RUSTUP_HOME%"=="C:\Users\RhaiTest\.local\share\agent-builds\rhai\n-a7e54f39\toolchain-home" exit /b 88
if /I not "%RUSTUP_TOOLCHAIN%"=="1.77.2-x86_64-pc-windows-msvc" exit /b 89
set RUSTC=%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\rustc.exe
"%~dp0cargo.exe" --version > cargo-version.txt 2>&1
if errorlevel 1 exit /b 90
"%RUSTC%" --version > rustc-version.txt 2>&1
if errorlevel 1 exit /b 91
set CARGO_PROFILE_TEST_DEBUG=0
set CARGO_INCREMENTAL=0
set CARGO_PROFILE_TEST_CODEGEN_UNITS=256
set CARGO_BUILD_JOBS=2
set PROFILE=testing-environ,sys,net,metadata,serde
set TARGETS=--test combined_sys_net --test sys_env --test sys_fs --test sys_policy --test net_connect --test net_listen --test net_reads --test net_writes --test net_metadata --test sys_process --test sys_process_report --test sys_process_windows --test serde
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGETS% --no-run > compile.log 2>&1
set COMPILE_RC=!ERRORLEVEL!
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_COMBINED_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% --test combined_sys_net sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors -- --exact --nocapture > combined-wrong.log 2>&1
set WRONG_RC=!ERRORLEVEL!
set RHAI_COMBINED_WRONG_EXPECTATION=
set RHAI_SERDE_JSON_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% --test serde test_serde_json -- --exact --nocapture > serde-wrong.log 2>&1
set SERDE_WRONG_RC=!ERRORLEVEL!
set RHAI_SERDE_JSON_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGETS% -- --test-threads=1 > suite.log 2>&1
set SUITE_RC=!ERRORLEVEL!
:cleanup
"%~dp0cargo.exe" clean --locked > "%TEMP%\rhai-cargo-clean.log" 2>&1
if errorlevel 1 exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
if not "!COMPILE_RC!"=="0" exit /b 59
echo RHAI_MSRV_SERDE_WRONG_EXIT=!WRONG_RC!
echo RHAI_MSRV_SERDE_JSON_WRONG_EXIT=!SERDE_WRONG_RC!
echo RHAI_MSRV_SERDE_SUITE_EXIT=!SUITE_RC!
if not "!WRONG_RC!"=="101" exit /b 61
if not "!SERDE_WRONG_RC!"=="101" exit /b 63
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_MSRV_SERDE_CONTROLS_PASS
exit /b 0
