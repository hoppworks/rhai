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
set "REMOVED_RC=999"
set "OVERRIDE_RC=999"
set "PARENT_RC=999"
set "INVALID_RC=999"
set "SUITE_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_ENV_REMOVE_WRONG_EXPECTATION=removed
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_env_remove_preserves_parent_and_applies_overrides -- --exact --nocapture > env-removed-wrong.log 2>&1
set "REMOVED_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ENV_REMOVE_WRONG_EXPECTATION=override
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_env_remove_preserves_parent_and_applies_overrides -- --exact --nocapture > env-override-wrong.log 2>&1
set "OVERRIDE_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ENV_REMOVE_WRONG_EXPECTATION=parent
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_env_remove_preserves_parent_and_applies_overrides -- --exact --nocapture > env-parent-wrong.log 2>&1
set "PARENT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ENV_REMOVE_WRONG_EXPECTATION=
set RHAI_WINDOWS_ENV_REMOVE_INVALID_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_env_remove_rejects_invalid_options_before_child_start -- --exact --nocapture > env-invalid-wrong.log 2>&1
set "INVALID_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ENV_REMOVE_INVALID_WRONG_EXPECTATION=
if not "!REMOVED_RC!"=="101" goto cleanup
if not "!OVERRIDE_RC!"=="101" goto cleanup
if not "!PARENT_RC!"=="101" goto cleanup
if not "!INVALID_RC!"=="101" goto cleanup
findstr /C:"deliberately wrong removed-variable expectation" env-removed-wrong.log > NUL || goto cleanup
findstr /C:"deliberately wrong child-override expectation" env-override-wrong.log > NUL || goto cleanup
findstr /C:"deliberately wrong parent-environment expectation" env-parent-wrong.log > NUL || goto cleanup
findstr /C:"deliberately wrong invalid-option child-start expectation" env-invalid-wrong.log > NUL || goto cleanup
for %%F in (env-removed-wrong.log env-override-wrong.log env-parent-wrong.log env-invalid-wrong.log) do findstr /C:"test result: FAILED. 0 passed; 1 failed;" %%F > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > env-suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo RHAI_ENV_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_ENV_REMOVED_EXIT=!REMOVED_RC!
echo RHAI_ENV_OVERRIDE_EXIT=!OVERRIDE_RC!
echo RHAI_ENV_PARENT_EXIT=!PARENT_RC!
echo RHAI_ENV_INVALID_EXIT=!INVALID_RC!
echo RHAI_ENV_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!REMOVED_RC!"=="101" exit /b 61
if not "!OVERRIDE_RC!"=="101" exit /b 62
if not "!PARENT_RC!"=="101" exit /b 63
if not "!INVALID_RC!"=="101" exit /b 64
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_ENV_CONTROLS_PASS
exit /b 0
