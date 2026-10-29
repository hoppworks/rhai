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
set TARGET=--test sys_windows_reparse_probe
set "COMPILE_RC=999"
set "WRONG_RC=999"
set "SUITE_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_REPARSE_WRONG_EXPECTATION=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% pinned_directory_can_become_a_junction_before_child_start -- --exact --nocapture > reparse-wrong.log 2>&1
set "WRONG_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_REPARSE_WRONG_EXPECTATION=
if not "!WRONG_RC!"=="101" goto cleanup
findstr /C:"REPARSE_WRONG_EXPECTATION" reparse-wrong.log > NUL || goto cleanup
findstr /C:"windows_reparse_probe_cleanup exact_junction_removed=true" reparse-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" reparse-wrong.log > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > reparse-suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo RHAI_REPARSE_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_REPARSE_WRONG_EXIT=!WRONG_RC!
echo RHAI_REPARSE_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!WRONG_RC!"=="101" exit /b 61
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_REPARSE_CONTROLS_PASS
exit /b 0
