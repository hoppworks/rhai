$ErrorActionPreference = 'Stop'
$id = 'rhai-public-tools01-b3801b3255364e68b1da6d50ec37d038'
$media = 'E:\'
$source = Join-Path $media 'input'
$pins = Get-Content -LiteralPath (Join-Path $media 'input-manifest.json') -Raw | ConvertFrom-Json
foreach ($pin in $pins.PSObject.Properties) {
    $inputPath = Join-Path $source $pin.Name
    if ((Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pin.Value) { throw "Frozen source mismatch: $($pin.Name)" }
}
$bootstrap = Join-Path $source 'tools\windows-scoped-runner\fixtures\RunSourceFixtures.ps1'
$tokens = $null; $parseErrors = $null
$null = [Management.Automation.Language.Parser]::ParseFile($bootstrap, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -ne 0) { throw ($parseErrors | Out-String) }
$session = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\tools-wh01-b3801b325536'
$parent = Join-Path $session 'run'
$run = Join-Path $parent 'monitor-source-b3801b3255364e68b1da6d50ec37d038'
if (Test-Path -LiteralPath $session) { throw 'This owned session already exists; preserve and inspect it.' }
$cursor = [IO.Path]::GetFullPath($parent)
while ($cursor) {
    if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse ancestor rejected: $cursor" }
    $ancestor = [IO.Directory]::GetParent($cursor)
    $cursor = if ($null -eq $ancestor) { $null } else { $ancestor.FullName }
}
New-Item -ItemType Directory -Path $parent | Out-Null
$stdout = Join-Path $session 'bootstrap.stdout'
$stderr = Join-Path $session 'bootstrap.stderr'
# This child invocation is private to the reviewed, hash-verified bootstrap.
# No persistent execution-policy or parent environment setting is changed.
$arguments = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$bootstrap,'-SourceRoot',$source,'-RunRoot',$run,'-BuildOnly','-PublicToolsOnly')
$line = ($arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
$process = $null; $status = -1; $redStatus = -1; $failure = ''; $complete = $false
try {

    # Mutually exclusive selections must reject before creating any compile root.
    $redRun = Join-Path $parent 'monitor-source-f73c396fe6c445078e83ff52311ba270'
    $redStdout = Join-Path $session 'selection-red.stdout'
    $redStderr = Join-Path $session 'selection-red.stderr'
    $redArgs = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$bootstrap,'-SourceRoot',$source,'-RunRoot',$redRun,'-BuildOnly','-CompilerClosureOnly','-PublicToolsOnly')
    $redLine = ($redArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $redProcess = $null
    try {
        $redProcess = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $redLine -WorkingDirectory $source -RedirectStandardOutput $redStdout -RedirectStandardError $redStderr -NoNewWindow -PassThru
        if ($redProcess.Handle -eq [IntPtr]::Zero) { throw 'Selection control has no exact process handle.' }
        if (!$redProcess.WaitForExit(30000)) {
            $redProcess.Kill()
            if (!$redProcess.WaitForExit(10000)) { throw 'Selection controller remains live; retain exact scope.' }
            throw 'Selection RED exceeded its 30-second bound.'
        }
        $redProcess.Refresh()
        if ($null -eq $redProcess.ExitCode) { throw 'Selection RED exit unavailable.' }
        $redStatus = [int]$redProcess.ExitCode
        if ($redStatus -ne 1 -or !(Get-Content -LiteralPath $redStderr -Raw).Contains('CompilerClosureOnly requires BuildOnly without other diagnostic selections.')) {
            throw 'Selection control did not reach the exact rejection assertion.'
        }
        if (Test-Path -LiteralPath $redRun) { throw 'Rejected selection created protected compile state.' }
    } finally { if ($null -ne $redProcess) { $redProcess.Dispose() } }

    $process = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $line -WorkingDirectory $source -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -PassThru
    $handle = $process.Handle
    if ($handle -eq [IntPtr]::Zero) { throw 'Bootstrap child has no retained exact process handle.' }
    if (!$process.WaitForExit(930000)) {
        $process.Kill()
        if (!$process.WaitForExit(10000)) { throw 'Exact bootstrap controller did not exit; retain this session for diagnosis.' }
        throw 'Bootstrap exceeded its independent 930-second observer limit.'
    }
    $process.Refresh()
    if ($null -eq $process.ExitCode) { throw 'Bootstrap exit status unavailable.' }
    $status = [int]$process.ExitCode
    if ($status -ne 0) { throw "Bootstrap exited $status; preserve original logs." }
    $result = [IO.File]::ReadAllText((Join-Path $run 'run-result.txt'))
    if (!$result.StartsWith('BUILD_ONLY_PASS:')) { throw 'Missing exact post-disposition bootstrap result.' }
    $binaryNames = @((Get-ChildItem -LiteralPath (Join-Path $run 'build') -File).Name | Sort-Object)
    if (($binaryNames -join ',') -cne 'MonitorAcceptanceDriver.exe,ScopedRunner.exe') { throw 'PublicToolsOnly did not produce exactly the two public tools.' }
    $complete = $true
} catch { $failure = $_.Exception.ToString() }
finally { if ($null -ne $process) { $process.Dispose() } }
$record = [ordered]@{id=$id;scope=$session;run=$run;exit=$status;selection_red_exit=$redStatus;accepted=$complete;failure=$failure;input_manifest_sha256=(Get-FileHash (Join-Path $media 'input-manifest.json')).Hash.ToLowerInvariant();execution_policy_changed=$false;driver_launched=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'), ($record | ConvertTo-Json -Compress), [Text.UTF8Encoding]::new($false))
$files = @(Get-Item -LiteralPath (Join-Path $session 'observer.json'))
foreach ($path in @($stdout,$stderr)) { if (Test-Path -LiteralPath $path) { $files += @(Get-Item -LiteralPath $path) } }
foreach ($path in @((Join-Path $session 'selection-red.stdout'),(Join-Path $session 'selection-red.stderr'))) { if (Test-Path -LiteralPath $path) { $files += @(Get-Item -LiteralPath $path) } }
if (Test-Path -LiteralPath (Join-Path $run 'logs')) { $files += @(Get-ChildItem -LiteralPath (Join-Path $run 'logs') -File) }
foreach ($name in @('build-manifest.txt','run-result.txt')) {
    $path = Join-Path $run $name
    if (Test-Path -LiteralPath $path) { $files += @(Get-Item -LiteralPath $path) }
}
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
    Emit-Frame 'END' @{id=$id;files=$files.Count;accepted=$complete;exit=$status;guest_evidence_retained=$true;driver_launched=$false}
} finally { $serial.Dispose() }
$record | ConvertTo-Json -Compress
