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
set PROFILE=testing-environ,sys,net,no_index
set TARGET=--test sys_process_windows_scalar
set "COMPILE_RC=999"
set "HOST_DIRECT_RC=999"
set "HOST_MANAGED_RC=999"
set "DENIAL_DIRECT_RC=999"
set "DENIAL_MANAGED_RC=999"
set "SUITE_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_SCALAR_WRONG_EXPECTATION=direct
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_scalar_run_reports_native_hostname -- --exact --nocapture > host-direct-wrong.log 2>&1
set "HOST_DIRECT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SCALAR_WRONG_EXPECTATION=managed
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_scalar_run_reports_native_hostname -- --exact --nocapture > host-managed-wrong.log 2>&1
set "HOST_MANAGED_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SCALAR_WRONG_EXPECTATION=
set RHAI_WINDOWS_SCALAR_DENIAL_WRONG_EXPECTATION=direct
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_scalar_rejects_unavailable_env_remove_option -- --exact --nocapture > denial-direct-wrong.log 2>&1
set "DENIAL_DIRECT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SCALAR_DENIAL_WRONG_EXPECTATION=managed
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_scalar_rejects_unavailable_env_remove_option -- --exact --nocapture > denial-managed-wrong.log 2>&1
set "DENIAL_MANAGED_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_SCALAR_DENIAL_WRONG_EXPECTATION=
for %%R in (!HOST_DIRECT_RC! !HOST_MANAGED_RC! !DENIAL_DIRECT_RC! !DENIAL_MANAGED_RC!) do if not "%%R"=="101" goto cleanup
for %%F in (host-direct-wrong.log host-managed-wrong.log) do findstr /C:"deliberately wrong Windows scalar hostname expectation" %%F > NUL || goto cleanup
for %%F in (denial-direct-wrong.log denial-managed-wrong.log) do findstr /C:"deliberately wrong scalar denial expectation" %%F > NUL || goto cleanup
for %%F in (host-direct-wrong.log host-managed-wrong.log denial-direct-wrong.log denial-managed-wrong.log) do findstr /C:"test result: FAILED. 0 passed; 1 failed;" %%F > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > scalar-suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo RHAI_SCALAR_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_SCALAR_HOST_DIRECT_EXIT=!HOST_DIRECT_RC!
echo RHAI_SCALAR_HOST_MANAGED_EXIT=!HOST_MANAGED_RC!
echo RHAI_SCALAR_DENIAL_DIRECT_EXIT=!DENIAL_DIRECT_RC!
echo RHAI_SCALAR_DENIAL_MANAGED_EXIT=!DENIAL_MANAGED_RC!
echo RHAI_SCALAR_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!HOST_DIRECT_RC!"=="101" exit /b 61
if not "!HOST_MANAGED_RC!"=="101" exit /b 62
if not "!DENIAL_DIRECT_RC!"=="101" exit /b 63
if not "!DENIAL_MANAGED_RC!"=="101" exit /b 64
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_SCALAR_CONTROLS_PASS
exit /b 0
