$ErrorActionPreference = 'Stop'
$id = 'rhai-public-refresh-47066f0d4e2a4f8bb45f1e62e8f7e5ad'
$nonce = '47066f0d4e2a4f8bb45f1e62e8f7e5ad'
$marker = 'rhai-public-refresh-47066f0d4e2a4f8bb45f1e62e8f7e5ad.bundle'
$drives = @(('D:\','E:\','F:\') | Where-Object {
    $letter = $_.Substring(0,1)
    $null -ne (Get-PSDrive -Name $letter -PSProvider FileSystem -ErrorAction SilentlyContinue) -and
        (Test-Path -LiteralPath (Join-Path $_ $marker) -PathType Leaf)
})
if ($drives.Count -ne 1) { throw 'Expected exactly one immutable input medium.' }
$media = $drives[0]
if ((Get-Content -LiteralPath (Join-Path $media $marker) -Raw).Trim() -cne $id) { throw 'Input-medium identity differs.' }
$manifestPath = Join-Path $media 'input-manifest.json'
if ((Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne '175fee88ce1625dcd9efca0fb904d5c7cfeb7b96a9a80e25bc90187099a8a276') { throw 'Immutable source manifest differs.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$mediaSource = Join-Path $media 'input'
$sourceRoot = [IO.Path]::GetFullPath($mediaSource).TrimEnd('\') + '\'
$expected = @($manifest.files.PSObject.Properties.Name | Sort-Object)
$actual = @(Get-ChildItem -LiteralPath $mediaSource -File -Force -Recurse | ForEach-Object { $_.FullName.Substring($sourceRoot.Length).Replace('\','/') } | Sort-Object)
if ($expected.Count -ne 21 -or ($actual -join "`n") -cne ($expected -join "`n")) { throw 'Immutable source inventory differs.' }
foreach ($entry in @(Get-ChildItem -LiteralPath $mediaSource -Force -Recurse)) {
    if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Input reparse point refused.' }
}
foreach ($pin in $manifest.files.PSObject.Properties) {
    if ($pin.Name -match '(^|/)\.\.(/|$)' -or $pin.Name -match '^[/\\]') { throw 'Input traversal refused.' }
    $path = [IO.Path]::GetFullPath((Join-Path $mediaSource $pin.Name.Replace('/','\')))
    if (!$path.StartsWith($sourceRoot,[StringComparison]::OrdinalIgnoreCase) -or
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pin.Value) { throw "Input hash/path differs: $($pin.Name)" }
}
$compiler = 'C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
if ((Get-FileHash -LiteralPath $compiler -Algorithm SHA256).Hash.ToLowerInvariant() -cne 'cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1') { throw 'Native compiler differs.' }
if ($env:USERPROFILE -cne 'C:\Users\RhaiTest' -or $env:USERNAME -cne 'RhaiTest') { throw 'Wrong guest owner.' }
if ((Get-PSDrive -Name C -PSProvider FileSystem).Free -lt 2147483648) { throw 'Guest free disk below 2 GiB launch floor.' }
if (([long](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1024) -lt 1073741824) { throw 'Guest free physical memory below 1 GiB launch floor.' }

$private = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$publicSession = Join-Path $private ('public-refresh-'+$nonce)
if (Test-Path -LiteralPath $publicSession) { throw "Own guest scope already exists; preserve it: $publicSession" }
$cursor = [IO.Path]::GetFullPath($publicSession)
while ($cursor) {
    if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse ancestor refused: $cursor" }
    $parent = [IO.Directory]::GetParent($cursor)
    $cursor = if ($null -eq $parent) { $null } else { $parent.FullName }
}

function Invoke-OwnedBuild([string]$Scope,[string]$Selection,[string]$RunId,[string[]]$BinaryNames) {
    $source = Join-Path $Scope 'source-input'
    $run = Join-Path (Join-Path $Scope 'run') ('monitor-source-'+$RunId)
    New-Item -ItemType Directory -Path $source,(Join-Path $Scope 'run') | Out-Null
    foreach ($entry in @(Get-ChildItem -LiteralPath $mediaSource -Force)) { Copy-Item -LiteralPath $entry.FullName -Destination $source -Recurse }
    $copyFiles = @(Get-ChildItem -LiteralPath $source -File -Force -Recurse | ForEach-Object { $_.FullName.Substring($source.TrimEnd('\').Length+1).Replace('\','/') } | Sort-Object)
    if (($copyFiles -join "`n") -cne ($expected -join "`n")) { throw 'Private source copy inventory differs.' }
    foreach ($entry in @(Get-ChildItem -LiteralPath $source -Force -Recurse)) { if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Private source copy reparse point refused.' } }
    foreach ($pin in $manifest.files.PSObject.Properties) {
        $path = Join-Path $source $pin.Name.Replace('/','\')
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pin.Value) { throw "Private source copy differs: $($pin.Name)" }
    }
    $script = Join-Path $source 'tools\windows-scoped-runner\fixtures\RunSourceFixtures.ps1'
    $tokens = $null; $parseErrors = $null
    $null = [Management.Automation.Language.Parser]::ParseFile($script,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count -ne 0) { throw ($parseErrors | Out-String) }
    $stdout = Join-Path $Scope 'bootstrap.stdout'; $stderr = Join-Path $Scope 'bootstrap.stderr'
    $arguments = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$script,'-SourceRoot',$source,'-RunRoot',$run,'-BuildOnly',$Selection)
    $line = ($arguments | ForEach-Object { '"'+$_+'"' }) -join ' '
    $process = $null; $confirmed = $false; $status = -1; $failure = ''; $started = $false
    try {
        $process = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $line -WorkingDirectory $source -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -PassThru
        $started = $true
        if ($process.Handle -eq [IntPtr]::Zero) { throw 'Build child has no exact process handle.' }
        if (!$process.WaitForExit(600000)) {
            try { $process.Kill() } catch { $failure = $_.Exception.ToString() }
            if (!$process.WaitForExit(30000)) { $global:RhaiBackendPendingBuild = $process; $process = $null; throw 'Exact BuildOnly exit remains unconfirmed after bounded termination.' }
            $confirmed = $true
            throw ('BuildOnly exceeded 600 seconds and was terminated. '+$failure)
        }
        $confirmed = $true; $process.Refresh(); $status = [int]$process.ExitCode
        if ($status -ne 0) { throw "BuildOnly exited $status; preserve exact originals." }
        $result = [IO.File]::ReadAllText((Join-Path $run 'run-result.txt'))
        if (!$result.StartsWith('BUILD_ONLY_PASS:')) { throw 'BuildOnly post-disposition result missing.' }
        $build = Join-Path $run 'build'
        $actualBinaries = @(Get-ChildItem -LiteralPath $build -File | ForEach-Object {$_.Name} | Sort-Object)
        if (($actualBinaries -join ',') -cne ((@($BinaryNames | Sort-Object)) -join ',')) { throw 'Exact binary inventory differs.' }
        $rows = [IO.File]::ReadAllLines((Join-Path $run 'build-manifest.txt'))
        foreach ($name in $BinaryNames) {
            $matches = @($rows | Where-Object { $_ -cmatch ('^[0-9a-f]{64}  build/'+[regex]::Escape($name)+'$') })
            if ($matches.Count -ne 1 -or (Get-FileHash -LiteralPath (Join-Path $build $name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $matches[0].Substring(0,64)) { throw "Built binary differs from manifest: $name" }
        }
        $observer = @{scope=$Scope;run=$run;selection=$Selection;input_manifest_sha256='175fee88ce1625dcd9efca0fb904d5c7cfeb7b96a9a80e25bc90187099a8a276';exit=$status;accepted=$true;compiler_sha256='cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1';binaries=$BinaryNames;bound_seconds=600}
        [IO.File]::WriteAllText((Join-Path $Scope 'build-observer.json'),($observer | ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
        return $build
    }
    finally {
        if ($null -ne $process -and $confirmed) { $process.Dispose() }
        elseif ($null -ne $process -and $started) { $global:RhaiBackendPendingBuild = $process }
    }
}

$publicBuild = Invoke-OwnedBuild $publicSession '-PublicToolsOnly' $nonce @('ScopedRunner.exe','MonitorAcceptanceDriver.exe')
$run = Join-Path (Join-Path $publicSession 'run') ('monitor-source-'+$nonce)
$manifestFile = Join-Path $run 'build-manifest.txt'
$binaryNames = @('ScopedRunner.exe','MonitorAcceptanceDriver.exe')
$binaryPins = @{}
foreach ($name in $binaryNames) { $binaryPins[$name] = (Get-FileHash -LiteralPath (Join-Path $publicBuild $name) -Algorithm SHA256).Hash.ToLowerInvariant() }
$receipt = [ordered]@{id=$id;scope=$publicSession;run=$run;source_manifest_sha256='175fee88ce1625dcd9efca0fb904d5c7cfeb7b96a9a80e25bc90187099a8a276';build_manifest_sha256=(Get-FileHash -LiteralPath $manifestFile -Algorithm SHA256).Hash.ToLowerInvariant();binary_sha256=$binaryPins;compiler_sha256='cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1';build_only_pass=$true}
[IO.File]::WriteAllText((Join-Path $publicSession 'project-readback.json'),($receipt | ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
Write-Output ('PUBLIC_REFRESH_BUILD_COMPLETE '+($receipt | ConvertTo-Json -Compress))
$files=@(
 (Join-Path $publicSession 'build-observer.json'),
 (Join-Path $publicSession 'project-readback.json'),
 (Join-Path $publicSession 'bootstrap.stdout'),
 (Join-Path $publicSession 'bootstrap.stderr'),
 (Join-Path $run 'run-result.txt'),
 $manifestFile
)
$total=0L
foreach($path in $files){
 if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw "Build export input absent: $path"}
 $item=Get-Item -LiteralPath $path -Force
 if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.Length -gt 4MB){throw "Build export input unsafe: $path"}
 $total+=$item.Length
}
if($total -gt 16MB){throw 'Build export exceeds16MiB.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200)
$serial.WriteTimeout=2000
$script:sequence=0
$exportClock=[Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string]$Kind,[object]$Value){
 if($exportClock.Elapsed.TotalSeconds -gt 180){throw 'Build export exceeded180seconds; retain originals.'}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Compress -Depth 8)))
 if($encoded.Length -gt 3500){throw 'Build export frame exceeds bound.'}
 $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded")
 $script:sequence++
}
try{
 $serial.Open()
 Emit-Frame 'BEGIN' @{id=$id;scope=$publicSession;accepted=$true;exit=0}
 foreach($path in $files){
  $relative=$path.Substring($publicSession.Length+1).Replace('\','/')
  $bytes=[IO.File]::ReadAllBytes($path)
  $sha=[Security.Cryptography.SHA256]::Create()
  try{$hash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
  Emit-Frame 'FILE' @{path=$relative;length=$bytes.Length;sha256=$hash}
  for($offset=0;$offset -lt $bytes.Length;$offset+=1024){
   $length=[Math]::Min(1024,$bytes.Length-$offset)
   Emit-Frame 'CHUNK' @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}
  }
  Emit-Frame 'FILE_END' @{path=$relative;length=$bytes.Length;sha256=$hash}
 }
 Emit-Frame 'END' @{id=$id;files=$files.Count;accepted=$true;exit=0;guest_evidence_retained=$true}
}finally{$serial.Dispose()}
