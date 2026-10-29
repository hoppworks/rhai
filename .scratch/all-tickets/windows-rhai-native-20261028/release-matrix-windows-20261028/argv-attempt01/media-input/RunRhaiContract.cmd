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
set TARGET=--test sys_process_windows_argv
set "COMPILE_RC=999"
set "SUITE_RC=999"
set "DIRECT_RUN_RC=999"
set "DIRECT_RAW_RC=999"
set "DIRECT_SPAWN_RC=999"
set "MANAGED_RUN_RC=999"
set "MANAGED_RAW_RC=999"
set "MANAGED_SPAWN_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_ARGV_WRONG_EXPECTATION=direct-run
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_process_arguments_reach_the_child_without_shell_interpretation -- --exact --nocapture > direct-run-wrong.log 2>&1
set "DIRECT_RUN_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ARGV_WRONG_EXPECTATION=direct-raw
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_process_arguments_reach_the_child_without_shell_interpretation -- --exact --nocapture > direct-raw-wrong.log 2>&1
set "DIRECT_RAW_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ARGV_WRONG_EXPECTATION=direct-spawn
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_process_arguments_reach_the_child_without_shell_interpretation -- --exact --nocapture > direct-spawn-wrong.log 2>&1
set "DIRECT_SPAWN_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ARGV_WRONG_EXPECTATION=managed-run
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_process_arguments_reach_the_child_without_shell_interpretation -- --exact --nocapture > managed-run-wrong.log 2>&1
set "MANAGED_RUN_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ARGV_WRONG_EXPECTATION=managed-raw
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_process_arguments_reach_the_child_without_shell_interpretation -- --exact --nocapture > managed-raw-wrong.log 2>&1
set "MANAGED_RAW_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ARGV_WRONG_EXPECTATION=managed-spawn
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_process_arguments_reach_the_child_without_shell_interpretation -- --exact --nocapture > managed-spawn-wrong.log 2>&1
set "MANAGED_SPAWN_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_ARGV_WRONG_EXPECTATION=
if not "!DIRECT_RUN_RC!"=="101" goto cleanup
findstr /C:"ARGV_WRONG_EXPECTATION direct-run" direct-run-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-run-wrong.log > NUL || goto cleanup
if not "!DIRECT_RAW_RC!"=="101" goto cleanup
findstr /C:"ARGV_WRONG_EXPECTATION direct-raw" direct-raw-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-raw-wrong.log > NUL || goto cleanup
if not "!DIRECT_SPAWN_RC!"=="101" goto cleanup
findstr /C:"ARGV_WRONG_EXPECTATION direct-spawn" direct-spawn-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-spawn-wrong.log > NUL || goto cleanup
if not "!MANAGED_RUN_RC!"=="101" goto cleanup
findstr /C:"ARGV_WRONG_EXPECTATION managed-run" managed-run-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-run-wrong.log > NUL || goto cleanup
if not "!MANAGED_RAW_RC!"=="101" goto cleanup
findstr /C:"ARGV_WRONG_EXPECTATION managed-raw" managed-raw-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-raw-wrong.log > NUL || goto cleanup
if not "!MANAGED_SPAWN_RC!"=="101" goto cleanup
findstr /C:"ARGV_WRONG_EXPECTATION managed-spawn" managed-spawn-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-spawn-wrong.log > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > argv-suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo RHAI_ARGV_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_ARGV_DIRECT_RUN_EXIT=!DIRECT_RUN_RC!
echo RHAI_ARGV_DIRECT_RAW_EXIT=!DIRECT_RAW_RC!
echo RHAI_ARGV_DIRECT_SPAWN_EXIT=!DIRECT_SPAWN_RC!
echo RHAI_ARGV_MANAGED_RUN_EXIT=!MANAGED_RUN_RC!
echo RHAI_ARGV_MANAGED_RAW_EXIT=!MANAGED_RAW_RC!
echo RHAI_ARGV_MANAGED_SPAWN_EXIT=!MANAGED_SPAWN_RC!
echo RHAI_ARGV_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!DIRECT_RUN_RC!"=="101" exit /b 61
if not "!DIRECT_RAW_RC!"=="101" exit /b 61
if not "!DIRECT_SPAWN_RC!"=="101" exit /b 61
if not "!MANAGED_RUN_RC!"=="101" exit /b 61
if not "!MANAGED_RAW_RC!"=="101" exit /b 61
if not "!MANAGED_SPAWN_RC!"=="101" exit /b 61
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_ARGV_CONTROLS_PASS
exit /b 0
