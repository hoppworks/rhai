@echo off
powershell.exe -NoProfile -Command "$p = Get-CimInstance Win32_OperatingSystem; $r = 'RHAI_WINDOWS_READY ' + $p.Caption + ' Build=' + $p.BuildNumber; $r | Out-File ($env:ProgramData + '\rhai-windows-ready.txt'); $s = New-Object System.IO.Ports.SerialPort COM1,115200,None,8,One; $s.Open(); $s.WriteLine($r); $s.Close()"
exit /b 0
