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
"%~dp0cargo.exe" test --locked --features testing-environ,sys,net,no_index,sync,metadata --test combined_sys_net --no-run > compile.log 2>&1
set COMPILE_RC=!ERRORLEVEL!
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_COMBINED_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features testing-environ,sys,net,no_index,sync,metadata --test combined_sys_net sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors -- --exact --nocapture > combined-wrong.log 2>&1
set WRONG_RC=!ERRORLEVEL!
set RHAI_COMBINED_WRONG_EXPECTATION=
"%~dp0cargo.exe" test --locked --features testing-environ,sys,net,no_index,sync,metadata --test combined_sys_net sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors -- --exact --nocapture > combined-green.log 2>&1
set GREEN_RC=!ERRORLEVEL!
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
if not "!COMPILE_RC!"=="0" exit /b 59
echo RHAI_MSRV_COMBINED_WRONG_EXIT=!WRONG_RC!
echo RHAI_MSRV_COMBINED_GREEN_EXIT=!GREEN_RC!
if not "!WRONG_RC!"=="101" exit /b 61
if not "!GREEN_RC!"=="0" exit /b 65
echo RHAI_MSRV_COMBINED_CONTROLS_PASS
exit /b 0
