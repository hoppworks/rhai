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
set "BASELINE_RC=999"
set "ROOT_RC=999"
set "DENIAL_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_cwd_uses_allowed_directory_without_mutating_parent -- --exact --nocapture > cwd-baseline.log 2>&1
set "BASELINE_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_CWD_REQUIRE_JOB=1
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_cwd_keeps_configured_root_when_rename_is_refused -- --exact --nocapture > cwd-root.log 2>&1
set "ROOT_RC=!ERRORLEVEL!"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_cwd_rejects_outside_and_missing_directories -- --exact --nocapture > cwd-denial.log 2>&1
set "DENIAL_RC=!ERRORLEVEL!"
echo RHAI_CWD_REQUIRE_JOB=1
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo RHAI_CWD_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_CWD_BASELINE_EXIT=!BASELINE_RC!
echo RHAI_CWD_ROOT_EXIT=!ROOT_RC!
echo RHAI_CWD_DENIAL_EXIT=!DENIAL_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!BASELINE_RC!"=="101" exit /b 61
findstr /C:"CWD_CONTRACT direct-run" cwd-baseline.log > NUL || exit /b 62
findstr /C:"unsupported Windows process option" cwd-baseline.log > NUL || exit /b 63
findstr /C:"test result: FAILED. 0 passed; 1 failed;" cwd-baseline.log > NUL || exit /b 64
if not "!ROOT_RC!"=="101" exit /b 65
if not "!DENIAL_RC!"=="101" exit /b 66
findstr /C:"windows_cwd_root_rename_refused label=direct-run" cwd-root.log > NUL || exit /b 67
findstr /C:"CWD_ROOT_IDENTITY direct-run" cwd-root.log > NUL || exit /b 68
findstr /C:"windows_cwd_rejected mode=direct-run label=outside" cwd-denial.log > NUL || exit /b 69
findstr /C:"missing cwd error" cwd-denial.log > NUL || exit /b 70
for %%F in (cwd-root.log cwd-denial.log) do findstr /C:"test result: FAILED. 0 passed; 1 failed;" %%F > NUL || exit /b 71
echo RHAI_CWD_BASELINE_REPRODUCED
exit /b 0
