$ErrorActionPreference = 'Stop'
$id = 'rhai-public-loop-readback01-20261008T125846Z-b7f83433'
$session = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\custody-loop01-20261008-b7f83433'
$run = Join-Path $session 'run'
$prior = Get-Content -Raw -LiteralPath (Join-Path $session 'observer.json') | ConvertFrom-Json
if (!$prior.exact_driver_exited -or !$prior.pipes_drained -or $prior.accepted) { throw 'Unexpected prior boundary; preserve all guest state.' }
$active = @(Get-Process ScopedRunner,MonitorAcceptanceDriver,PayloadFixture -ErrorAction SilentlyContinue)
if ($active.Count -ne 0) { throw 'Native custody process still present; preserve live state and do not infer terminal evidence.' }
$stdout = Join-Path $session 'bootstrap.stdout'; $stderr = Join-Path $session 'bootstrap.stderr'
$complete = $false; $status = [int]$prior.exit; $started = $false
$record = [ordered]@{id=$id;scope=$session;exit=$status;accepted=$false;driver_launched=$false;read_only_original_snapshot=$true;active_custody_names=0;prior_exact_driver_exited=$true;prior_pipes_drained=$true;product_run=$false}
$files = @(Get-Item -LiteralPath $stdout,$stderr,(Join-Path $session 'observer.json'))
$files += @(Get-ChildItem -LiteralPath $run -Recurse -File -Force)
if ($files.Count -gt 64 -or ($files | Measure-Object Length -Sum).Sum -gt 16MB) { throw 'Export inventory exceeds the declared bounds; preserve all guest evidence.' }
$serial = [IO.Ports.SerialPort]::new('COM1',115200); $serial.WriteTimeout = 2000; $script:sequence = 0
$exportDeadline = [Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string] $Kind, [object] $Value) {
    if ($exportDeadline.Elapsed.TotalSeconds -gt 180) { throw 'Serial export exceeded its 180-second bound; guest evidence retained.' }
    $json = $Value | ConvertTo-Json -Compress -Depth 8
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    if ($encoded.Length -gt 3500) { throw 'Export frame exceeds its declared bound.' }
    $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded")
    $script:sequence++
}
try {
    $serial.Open(); Emit-Frame 'BEGIN' $record
    foreach ($file in $files) {
        if ($file.Length -gt 4MB -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Export file exceeds cap or is a reparse point.' }
        $relative = $file.FullName.Substring($session.Length + 1).Replace('\','/')
        $bytes = [IO.File]::ReadAllBytes($file.FullName)
        $digest = [Security.Cryptography.SHA256]::Create()
        try { $hash = [BitConverter]::ToString($digest.ComputeHash($bytes)).Replace('-','').ToLowerInvariant() } finally { $digest.Dispose() }
        Emit-Frame 'FILE' @{path=$relative;length=$bytes.Length;sha256=$hash}
        for ($offset=0; $offset -lt $bytes.Length; $offset+=1024) {
            $length = [Math]::Min(1024,$bytes.Length-$offset)
            Emit-Frame 'CHUNK' @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}
        }
        Emit-Frame 'FILE_END' @{path=$relative;length=$bytes.Length;sha256=$hash}
    }
    Emit-Frame 'END' @{id=$id;files=$files.Count;accepted=$complete;exit=$status;guest_evidence_retained=$true;driver_launched=$started}
} finally { $serial.Dispose() }
$record | ConvertTo-Json -Compress
