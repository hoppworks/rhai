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
set TARGET=--test sys_process_windows_streams
set "COMPILE_RC=999"
set "SUITE_RC=999"
set "DIRECT_RUN_STDOUT_RC=999"
set "DIRECT_RUN_STDERR_RC=999"
set "DIRECT_RAW_STDOUT_RC=999"
set "DIRECT_RAW_STDERR_RC=999"
set "DIRECT_SPAWN_STDOUT_RC=999"
set "DIRECT_SPAWN_STDERR_RC=999"
set "MANAGED_RUN_STDOUT_RC=999"
set "MANAGED_RUN_STDERR_RC=999"
set "MANAGED_RAW_STDOUT_RC=999"
set "MANAGED_RAW_STDERR_RC=999"
set "MANAGED_SPAWN_STDOUT_RC=999"
set "MANAGED_SPAWN_STDERR_RC=999"
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% --no-run > compile.log 2>&1
set "COMPILE_RC=!ERRORLEVEL!"
if not "!COMPILE_RC!"=="0" goto cleanup
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stdout
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_direct_run -- --exact --nocapture > direct-run-stdout-wrong.log 2>&1
set "DIRECT_RUN_STDOUT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stderr
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_direct_run -- --exact --nocapture > direct-run-stderr-wrong.log 2>&1
set "DIRECT_RUN_STDERR_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stdout
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_direct_raw -- --exact --nocapture > direct-raw-stdout-wrong.log 2>&1
set "DIRECT_RAW_STDOUT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stderr
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_direct_raw -- --exact --nocapture > direct-raw-stderr-wrong.log 2>&1
set "DIRECT_RAW_STDERR_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stdout
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_direct_spawn -- --exact --nocapture > direct-spawn-stdout-wrong.log 2>&1
set "DIRECT_SPAWN_STDOUT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stderr
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_direct_spawn -- --exact --nocapture > direct-spawn-stderr-wrong.log 2>&1
set "DIRECT_SPAWN_STDERR_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stdout
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_managed_run -- --exact --nocapture > managed-run-stdout-wrong.log 2>&1
set "MANAGED_RUN_STDOUT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stderr
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_managed_run -- --exact --nocapture > managed-run-stderr-wrong.log 2>&1
set "MANAGED_RUN_STDERR_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stdout
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_managed_raw -- --exact --nocapture > managed-raw-stdout-wrong.log 2>&1
set "MANAGED_RAW_STDOUT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stderr
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_managed_raw -- --exact --nocapture > managed-raw-stderr-wrong.log 2>&1
set "MANAGED_RAW_STDERR_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stdout
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_managed_spawn -- --exact --nocapture > managed-spawn-stdout-wrong.log 2>&1
set "MANAGED_SPAWN_STDOUT_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=stderr
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% windows_stream_managed_spawn -- --exact --nocapture > managed-spawn-stderr-wrong.log 2>&1
set "MANAGED_SPAWN_STDERR_RC=!ERRORLEVEL!"
set RHAI_WINDOWS_STREAM_WRONG_EXPECTATION=
if not "!DIRECT_RUN_STDOUT_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDOUT direct-run" direct-run-stdout-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-run-stdout-wrong.log > NUL || goto cleanup
if not "!DIRECT_RUN_STDERR_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDERR direct-run" direct-run-stderr-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-run-stderr-wrong.log > NUL || goto cleanup
if not "!DIRECT_RAW_STDOUT_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDOUT direct-raw" direct-raw-stdout-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-raw-stdout-wrong.log > NUL || goto cleanup
if not "!DIRECT_RAW_STDERR_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDERR direct-raw" direct-raw-stderr-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-raw-stderr-wrong.log > NUL || goto cleanup
if not "!DIRECT_SPAWN_STDOUT_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDOUT direct-spawn" direct-spawn-stdout-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-spawn-stdout-wrong.log > NUL || goto cleanup
if not "!DIRECT_SPAWN_STDERR_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDERR direct-spawn" direct-spawn-stderr-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" direct-spawn-stderr-wrong.log > NUL || goto cleanup
if not "!MANAGED_RUN_STDOUT_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDOUT managed-run" managed-run-stdout-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-run-stdout-wrong.log > NUL || goto cleanup
if not "!MANAGED_RUN_STDERR_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDERR managed-run" managed-run-stderr-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-run-stderr-wrong.log > NUL || goto cleanup
if not "!MANAGED_RAW_STDOUT_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDOUT managed-raw" managed-raw-stdout-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-raw-stdout-wrong.log > NUL || goto cleanup
if not "!MANAGED_RAW_STDERR_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDERR managed-raw" managed-raw-stderr-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-raw-stderr-wrong.log > NUL || goto cleanup
if not "!MANAGED_SPAWN_STDOUT_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDOUT managed-spawn" managed-spawn-stdout-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-spawn-stdout-wrong.log > NUL || goto cleanup
if not "!MANAGED_SPAWN_STDERR_RC!"=="101" goto cleanup
findstr /C:"STREAM_WRONG_STDERR managed-spawn" managed-spawn-stderr-wrong.log > NUL || goto cleanup
findstr /C:"test result: FAILED. 0 passed; 1 failed;" managed-spawn-stderr-wrong.log > NUL || goto cleanup
"%~dp0cargo.exe" test --locked --features %PROFILE% %TARGET% -- --test-threads=1 --nocapture > streams-suite.log 2>&1
set "SUITE_RC=!ERRORLEVEL!"
:cleanup
"%~dp0cargo.exe" clean --locked > "%AGENT_RUNTIME_DIR%\cargo-clean.log" 2>&1
set "CLEAN_RC=!ERRORLEVEL!"
echo RHAI_CARGO_CLEAN_EXIT=!CLEAN_RC!
if not "!CLEAN_RC!"=="0" exit /b 87
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo RHAI_STREAM_COMPILE_EXIT=!COMPILE_RC!
echo RHAI_STREAM_DIRECT_RUN_STDOUT_EXIT=!DIRECT_RUN_STDOUT_RC!
echo RHAI_STREAM_DIRECT_RUN_STDERR_EXIT=!DIRECT_RUN_STDERR_RC!
echo RHAI_STREAM_DIRECT_RAW_STDOUT_EXIT=!DIRECT_RAW_STDOUT_RC!
echo RHAI_STREAM_DIRECT_RAW_STDERR_EXIT=!DIRECT_RAW_STDERR_RC!
echo RHAI_STREAM_DIRECT_SPAWN_STDOUT_EXIT=!DIRECT_SPAWN_STDOUT_RC!
echo RHAI_STREAM_DIRECT_SPAWN_STDERR_EXIT=!DIRECT_SPAWN_STDERR_RC!
echo RHAI_STREAM_MANAGED_RUN_STDOUT_EXIT=!MANAGED_RUN_STDOUT_RC!
echo RHAI_STREAM_MANAGED_RUN_STDERR_EXIT=!MANAGED_RUN_STDERR_RC!
echo RHAI_STREAM_MANAGED_RAW_STDOUT_EXIT=!MANAGED_RAW_STDOUT_RC!
echo RHAI_STREAM_MANAGED_RAW_STDERR_EXIT=!MANAGED_RAW_STDERR_RC!
echo RHAI_STREAM_MANAGED_SPAWN_STDOUT_EXIT=!MANAGED_SPAWN_STDOUT_RC!
echo RHAI_STREAM_MANAGED_SPAWN_STDERR_EXIT=!MANAGED_SPAWN_STDERR_RC!
echo RHAI_STREAM_SUITE_EXIT=!SUITE_RC!
if not "!COMPILE_RC!"=="0" exit /b 59
if not "!DIRECT_RUN_STDOUT_RC!"=="101" exit /b 61
if not "!DIRECT_RUN_STDERR_RC!"=="101" exit /b 61
if not "!DIRECT_RAW_STDOUT_RC!"=="101" exit /b 61
if not "!DIRECT_RAW_STDERR_RC!"=="101" exit /b 61
if not "!DIRECT_SPAWN_STDOUT_RC!"=="101" exit /b 61
if not "!DIRECT_SPAWN_STDERR_RC!"=="101" exit /b 61
if not "!MANAGED_RUN_STDOUT_RC!"=="101" exit /b 61
if not "!MANAGED_RUN_STDERR_RC!"=="101" exit /b 61
if not "!MANAGED_RAW_STDOUT_RC!"=="101" exit /b 61
if not "!MANAGED_RAW_STDERR_RC!"=="101" exit /b 61
if not "!MANAGED_SPAWN_STDOUT_RC!"=="101" exit /b 61
if not "!MANAGED_SPAWN_STDERR_RC!"=="101" exit /b 61
if not "!SUITE_RC!"=="0" exit /b 65
echo RHAI_STREAM_CONTROLS_PASS
exit /b 0
