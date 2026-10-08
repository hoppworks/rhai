$ErrorActionPreference = 'Stop'
$id = 'rhai-capture-parser04-20261008T125846Z-b7f83433'
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
$session = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\cap-g04-b7f83433'
$parent = Join-Path $session 'run'
$run = Join-Path $parent 'monitor-source-3f5a7e0c39fd4b9bbdcaf7228a320a47'
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
$arguments = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$bootstrap,'-SourceRoot',$source,'-RunRoot',$run,'-BuildOnly','-CustodyFixtureMode','payload-evidence','-DriverParserFixture')
$line = ($arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
$process = $null; $status = -1; $failure = ''; $complete = $false
try {
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
    $complete = $true
} catch { $failure = $_.Exception.ToString() }
finally { if ($null -ne $process) { $process.Dispose() } }
$record = [ordered]@{id=$id;scope=$session;run=$run;exit=$status;accepted=$complete;failure=$failure;input_manifest_sha256=(Get-FileHash (Join-Path $media 'input-manifest.json')).Hash.ToLowerInvariant();execution_policy_changed=$false;driver_launched=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'), ($record | ConvertTo-Json -Compress), [Text.UTF8Encoding]::new($false))
$files = @(Get-Item -LiteralPath $stdout,$stderr,(Join-Path $session 'observer.json'))
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
