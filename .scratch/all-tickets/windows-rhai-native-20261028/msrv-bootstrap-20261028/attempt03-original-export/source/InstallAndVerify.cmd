@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if errorlevel 1 exit /b 70
if not defined RUSTUP_HOME exit /b 71
if not defined AGENT_RUNTIME_DIR exit /b 72
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 73
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 74
"%~dp0rustup.exe" toolchain install 1.77.2-x86_64-pc-windows-msvc --profile minimal --no-self-update
if errorlevel 1 exit /b 75
"%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\rustc.exe" --version > rustc-version.txt 2>&1
if errorlevel 1 exit /b 76
findstr /X /C:"rustc 1.77.2 (25ef9e3d8 2024-04-09)" rustc-version.txt > NUL
if errorlevel 1 (type rustc-version.txt & exit /b 77)
"%RUSTUP_HOME%\toolchains\1.77.2-x86_64-pc-windows-msvc\bin\cargo.exe" --version > cargo-version.txt 2>&1
if errorlevel 1 exit /b 78
findstr /X /C:"cargo 1.77.2 (e52e36006 2024-03-26)" cargo-version.txt > NUL
if errorlevel 1 (type cargo-version.txt & exit /b 79)
type rustc-version.txt
type cargo-version.txt
echo RHAI_MSRV_TOOLCHAIN_EXACT_VERSIONS_OK
exit /b 0
