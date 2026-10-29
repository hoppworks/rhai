@echo off
setlocal EnableExtensions EnableDelayedExpansion
if /I not "%CD%"=="%AGENT_RUNTIME_DIR%" exit /b 85
if /I not "%CARGO_HOME%"=="%AGENT_RUNTIME_DIR%\work\cargo-home" exit /b 86
if /I not "%CARGO_TARGET_DIR%"=="%AGENT_RUNTIME_DIR%\work\target" exit /b 87
set PROBE_OUT=%AGENT_RUNTIME_DIR%\work
set PROBE_CL_EXE=C:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\cl.exe
set PROBE_LINK_EXE=C:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\link.exe
cd /d "%PROBE_OUT%"
if errorlevel 1 exit /b 60
if /I not "%CD%"=="%PROBE_OUT%" exit /b 88
"%PROBE_CL_EXE%" /nologo /c /GS- /Fo"%PROBE_OUT%\probe.obj" "%~dp0probe.c" > compile.log 2>&1
set CL_RC=!ERRORLEVEL!
if not "!CL_RC!"=="0" goto export
"%PROBE_LINK_EXE%" /NOLOGO /SUBSYSTEM:CONSOLE /ENTRY:mainCRTStartup /NODEFAULTLIB "%PROBE_OUT%\probe.obj" "C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\um\x64\kernel32.lib" /OUT:"%PROBE_OUT%\probe.exe" /LINKREPROFULLPATHRSP:"%PROBE_OUT%\link-inputs.rsp" > link.log 2>&1
set LINK_RC=!ERRORLEVEL!
if not "!LINK_RC!"=="0" goto export
set RSP_RC=0
if exist "%PROBE_OUT%\link-inputs.rsp" (echo PROBE_RSP_PRESENT) else (echo PROBE_RSP_MISSING & set RSP_RC=1)
if exist "%PROBE_OUT%\probe.exe" (echo PROBE_EXE_PRESENT) else (echo PROBE_EXE_MISSING & set RUN_RC=67 & goto export)
"%PROBE_OUT%\probe.exe" > probe-run.log 2>&1
set RUN_RC=!ERRORLEVEL!
:export
set EXPORT_RC=0
for %%F in (compile.log link.log probe-run.log probe.obj probe.exe link-inputs.rsp) do if exist "%%F" (
 if %%~zF GTR 4194304 (set EXPORT_RC=1) else (
  copy /Y "%%F" "%AGENT_RUNTIME_DIR%\%%F" >nul
  if errorlevel 1 set EXPORT_RC=1
 )
)
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ClearOwnedWorkReadOnly.ps1" > "%TEMP%\rhai-attributes.log" 2>&1
if errorlevel 1 (type "%TEMP%\rhai-attributes.log" & exit /b 92)
type "%TEMP%\rhai-attributes.log"
echo PROBE_CL_EXIT=!CL_RC!
echo PROBE_LINK_EXIT=!LINK_RC!
echo PROBE_RUN_EXIT=!RUN_RC!
echo PROBE_EXPORT_EXIT=!EXPORT_RC!
if not "!CL_RC!"=="0" exit /b 61
if not "!LINK_RC!"=="0" exit /b 62
if not "!RSP_RC!"=="0" exit /b 64
if not "!RUN_RC!"=="0" exit /b 63
if not "!EXPORT_RC!"=="0" exit /b 65
exit /b 0
