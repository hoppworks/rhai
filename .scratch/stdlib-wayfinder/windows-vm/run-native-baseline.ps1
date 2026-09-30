$ErrorActionPreference = 'Stop'
$root = 'C:\RhaiQuality'
$env:PATH = "$env:USERPROFILE\.cargo\bin;" + $env:PATH
Start-Transcript -Path "$root\native-baseline.log" -Append
function Report([string]$message) {
    Write-Host $message
    $port = New-Object System.IO.Ports.SerialPort COM1,115200,None,8,One
    try { $port.Open(); $port.WriteLine($message) } finally { $port.Dispose() }
}
try {
    Report 'RHAI_NATIVE_BASELINE_START'
    $source = "$root\baseline-source-v2"
    if (Test-Path $source) { throw 'Baseline source already exists; preserve it and inspect before repeating' }
    Expand-Archive -LiteralPath (Join-Path $PSScriptRoot 'rhai-source.zip') -DestinationPath $source
    Set-Location $source
    & rustc -Vv
    & cargo -V
    foreach ($target in 'sys_policy','sys_env','sys_fs') {
        Report "RHAI_NATIVE_TARGET_START $target"
        $exitFile = "$root\$target.exit.txt"
        if (Test-Path $exitFile) { throw "Existing exit file for $target; preserve and inspect before repeating" }
        $batch = "$root\$target.cmd"
        @"
@echo off
call cargo test --features testing-environ,sys,metadata --test $target -- --test-threads=1 > "$root\$target.stdout.log" 2> "$root\$target.stderr.log"
set result=%ERRORLEVEL%
echo %result% > "$exitFile"
exit /b %result%
"@ | Set-Content $batch -Encoding ASCII
        $process = Start-Process cmd.exe -ArgumentList "/c $batch" -PassThru -NoNewWindow
        if (!$process.WaitForExit(1200000)) {
            & taskkill /PID $process.Id /T /F
            Report "RHAI_NATIVE_TARGET_TIMEOUT $target"
            throw "Native target $target exceeded 20 minutes; its owned process tree was stopped"
        }
        if (!(Test-Path $exitFile)) { throw "Missing exit read-back for $target" }
        $exitCode = [int](Get-Content $exitFile -Raw).Trim()
        Report "RHAI_NATIVE_TARGET_EXIT $target $exitCode"
        foreach ($log in "$root\$target.stdout.log","$root\$target.stderr.log") {
            foreach ($line in Get-Content $log) { Report $line }
        }
    }
    Report 'RHAI_NATIVE_BASELINE_FINISHED (diagnostics only; inspect every target exit)'
} catch {
    Report "RHAI_NATIVE_BASELINE_FAILED $($_.Exception.Message)"
    throw
} finally { Stop-Transcript }
