$ErrorActionPreference = 'Stop'
$root = 'C:\RhaiQuality'
$env:PATH = "$env:USERPROFILE\.cargo\bin;" + $env:PATH
Set-Location "$root\baseline-source-v2"
function Report([string]$message) {
    Write-Host $message
    $port = New-Object System.IO.Ports.SerialPort COM1,115200,None,8,One
    try { $port.Open(); $port.WriteLine($message) } finally { $port.Dispose() }
}
function Run-Control([string]$label) {
    $exitFile = "$root\$label.exit.txt"
    if (Test-Path $exitFile) { throw "Existing control result: $label" }
    @"
@echo off
call cargo test --features testing-environ,sys,metadata --test sys_fs test_write_append_blob -- --exact --test-threads=1 > "$root\$label.stdout.log" 2> "$root\$label.stderr.log"
set result=%ERRORLEVEL%
echo %result% > "$exitFile"
exit /b %result%
"@ | Set-Content "$root\$label.cmd" -Encoding ASCII
    $process = Start-Process cmd.exe -ArgumentList "/c $root\$label.cmd" -PassThru -NoNewWindow
    if (!$process.WaitForExit(300000)) {
        & taskkill /PID $process.Id /T /F | Out-Host
        throw "Control timeout: $label"
    }
    if (!(Test-Path $exitFile)) { throw "Missing control exit: $label" }
    $code = [int](Get-Content $exitFile -Raw).Trim()
    Report "RHAI_CONTROL_EXIT $label $code"
    foreach ($line in Get-Content "$root\$label.stdout.log") { Report $line }
    return $code
}
$path = Join-Path (Get-Location) 'tests\sys_fs.rs'
$original = [IO.File]::ReadAllBytes($path)
$originalHash = (Get-FileHash $path).Hash
$text = [Text.Encoding]::UTF8.GetString($original)
$needle = 'assert_eq!(t.read("w.txt"), b"second");'
if ($text.IndexOf($needle) -lt 0 -or $text.IndexOf($needle) -ne $text.LastIndexOf($needle)) {
    throw 'The expected independent file-read assertion is not unique'
}
try {
    Report 'RHAI_CONTROL_START'
    [IO.File]::WriteAllText($path, $text.Replace($needle, 'assert_eq!(t.read("w.txt"), b"WRONG-CONTROL");'), (New-Object Text.UTF8Encoding $false))
    $code = Run-Control 'control-wrong'
    if ($code -ne 101 -or !(Get-Content "$root\control-wrong.stdout.log" -Raw).Contains('assertion')) {
        throw 'Wrong expectation did not fail through the intended assertion'
    }
} finally { [IO.File]::WriteAllBytes($path, $original) }
if ((Get-FileHash $path).Hash -ne $originalHash) { throw 'Source restoration mismatch' }
Report "RHAI_CONTROL_SOURCE_RESTORED $originalHash"
if ((Run-Control 'control-correct') -ne 0) { throw 'Restored control failed' }
$leftovers = @(Get-ChildItem $env:TEMP -Directory -Filter 'rhai-sys-test-*')
$processes = @(Get-Process | Where-Object ProcessName -Match '^(cargo|rustc|sys_fs-|sys_policy-|sys_env-)')
Report "RHAI_CONTROL_CLEANUP Fixtures=$($leftovers.Count) Processes=$($processes.Count)"
if ($leftovers.Count -or $processes.Count) { throw 'Inspect recorded fixtures/processes; do not remove blindly' }
Report 'RHAI_CONTROL_PASSED'
