@echo off
setlocal EnableExtensions EnableDelayedExpansion
if /I not "%CD%"=="%AGENT_RUNTIME_DIR%" exit /b 85
set "SOURCE_ROOT=%CD%"
if not exist "%SOURCE_ROOT%\Cargo.toml" exit /b 89
if not exist "%SOURCE_ROOT%\ClearOwnedWorkReadOnly.ps1" exit /b 90
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 86
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 87
if /I not "%RUSTUP_HOME%"=="C:\Users\RhaiTest\.local\share\agent-builds\rhai\n-a7e54f39\toolchain-home" exit /b 88
if /I not "%RUSTUP_TOOLCHAIN%"=="1.77.2-x86_64-pc-windows-msvc" exit /b 91
set "RUSTC=%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\rustc.exe"
set "RUSTC_WRAPPER="
set "RUSTC_WORKSPACE_WRAPPER="
set "CARGO_BUILD_RUSTC="
set "CARGO_PROFILE_TEST_DEBUG=0"
set "CARGO_INCREMENTAL=0"
set "CARGO_PROFILE_TEST_CODEGEN_UNITS=256"
set "CARGO_BUILD_JOBS=2"
set "RSP=%AGENT_RUNTIME_DIR%\work\link-inputs.rsp"
"%SOURCE_ROOT%\cargo.exe" --version > "%AGENT_RUNTIME_DIR%\cargo-version.txt" 2>&1
if errorlevel 1 exit /b 95
"%RUSTC%" --version > "%AGENT_RUNTIME_DIR%\rustc-version.txt" 2>&1
if errorlevel 1 exit /b 96
"%SOURCE_ROOT%\cargo.exe" rustc --locked --manifest-path "%SOURCE_ROOT%\Cargo.toml" --features testing-environ,sys,net --test combined_sys_net -- --print=link-args -C link-arg=/LINKREPROFULLPATHRSP:%RSP% > "%AGENT_RUNTIME_DIR%\cargo-link.log" 2>&1
set "CARGO_RC=!ERRORLEVEL!"
set "RSP_RC=1"
set "EXPORT_RC=1"
if exist "%RSP%" (
 for %%F in ("%RSP%") do if %%~zF LEQ 1048576 if %%~zF GTR 20 (
  copy /Y "%RSP%" "%AGENT_RUNTIME_DIR%\link-inputs.rsp" >nul
  if not errorlevel 1 set "RSP_RC=0"
 )
)
for %%F in ("%AGENT_RUNTIME_DIR%\cargo-link.log") do if %%~zF LEQ 4194304 set "EXPORT_RC=0"
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%SOURCE_ROOT%\ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
set "HELPER_RC=!ERRORLEVEL!"
type "%TEMP%\rhai-attributes.log"
echo RHAI_SDK_HELPER_EXIT=!HELPER_RC!
if not "!HELPER_RC!"=="0" exit /b 92
set "ALIAS_OK=0"
set "CLEARED_OK=0"
for /f "usebackq delims=" %%L in ("%TEMP%\rhai-attributes.log") do (
 if "%%L"=="RHAI_READONLY_ALIAS_SCOPE_CONFIRMED" set "ALIAS_OK=1"
 if "%%L"=="RHAI_WORK_READONLY_CLEARED" set "CLEARED_OK=1"
)
if not "!ALIAS_OK!"=="1" exit /b 93
if not "!CLEARED_OK!"=="1" exit /b 94
echo RHAI_SDK_CARGO_EXIT=!CARGO_RC!
echo RHAI_SDK_RSP_EXPORT_EXIT=!RSP_RC!
echo RHAI_SDK_LOG_BOUND_EXIT=!EXPORT_RC!
if not "!CARGO_RC!"=="0" exit /b 61
if not "!RSP_RC!"=="0" exit /b 64
if not "!EXPORT_RC!"=="0" exit /b 65
exit /b 0
