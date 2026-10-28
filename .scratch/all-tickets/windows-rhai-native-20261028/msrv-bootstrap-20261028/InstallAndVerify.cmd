@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if errorlevel 1 exit /b 70
if not defined RUSTUP_HOME exit /b 71
if not defined AGENT_RUNTIME_DIR exit /b 72
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 73
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 74
if exist "%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\rustc.exe" if exist "%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\cargo.exe" goto verify
"%~dp0rustup.exe" toolchain install 1.77.2-x86_64-pc-windows-msvc --profile minimal --no-self-update
if errorlevel 1 exit /b 75
:verify
"%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\rustc.exe" --version > rustc-version.txt 2>&1
if errorlevel 1 exit /b 76
"%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\cargo.exe" --version > cargo-version.txt 2>&1
if errorlevel 1 exit /b 78
type rustc-version.txt
type cargo-version.txt
echo RHAI_MSRV_TOOLCHAIN_EXACT_VERSIONS_OK
exit /b 0
