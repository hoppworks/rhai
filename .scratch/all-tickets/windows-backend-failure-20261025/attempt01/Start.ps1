$ErrorActionPreference = 'Stop'
$id = 'rhai-backend-failure-3cd277ed37eb4926b06e55c9c44279a4'
$nonce = '3cd277ed37eb4926b06e55c9c44279a4'
$marker = 'backend-failure-3cd277ed37eb4926b06e55c9c44279a4.bundle'
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
$publicSession = Join-Path $private ('backend-public-'+$nonce)
$fixtureSession = Join-Path $private ('backend-fixture-'+$nonce)
$controls = @(
    @{ Scope=(Join-Path $private 'env-control-0e6872acee8647af927c9023af25d331'); Id='rhai-backend-evidence-0e6872acee8647af927c9023af25d331'; Contract='backend-evidence-hardlink' },
    @{ Scope=(Join-Path $private 'env-control-60e5e70f35564d85bf8f08f18e911f5d'); Id='rhai-backend-cleanup-60e5e70f35564d85bf8f08f18e911f5d'; Contract='backend-cleanup-readonly' }
)
foreach ($path in @($publicSession,$fixtureSession)+@($controls | ForEach-Object {$_.Scope})) {
    if (Test-Path -LiteralPath $path) { throw "Own guest scope already exists; preserve it: $path" }
    $cursor = [IO.Path]::GetFullPath($path)
    while ($cursor) {
        if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse ancestor refused: $cursor" }
        $parent = [IO.Directory]::GetParent($cursor)
        $cursor = if ($null -eq $parent) { $null } else { $parent.FullName }
    }
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
$fixtureBuild = Invoke-OwnedBuild $fixtureSession '-CompilerClosureOnly' '0e6872acee8647af927c9023af25d331' @('PayloadFixture.exe')
$fixture = Join-Path $fixtureBuild 'PayloadFixture.exe'
$fixtureHash = (Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash.ToLowerInvariant()
foreach ($case in $controls) {
    $controlScript = Join-Path (Join-Path $publicSession 'source-input') 'tools\windows-scoped-runner\fixtures\RunPayloadEnvironmentControl.ps1'
    $tokens = $null; $parseErrors = $null
    $null = [Management.Automation.Language.Parser]::ParseFile($controlScript,[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count -ne 0) { throw ($parseErrors | Out-String) }
    $command = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$controlScript,'-FixturePath',$fixture,'-FixtureSha256',$fixtureHash,'-BuildRoot',$publicBuild,'-FixtureBuildRoot',$fixtureBuild,'-Session',$case.Scope,'-Id',$case.Id,'-Phase','GREEN','-Contract',$case.Contract)
    $line = ($command | ForEach-Object { '"'+$_+'"' }) -join ' '
    $stdout = Join-Path $publicSession ($case.Contract+'.stdout')
    $stderr = Join-Path $publicSession ($case.Contract+'.stderr')
    $process = $null; $confirmed = $false; $started = $false
    try {
        $process = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $line -WorkingDirectory (Join-Path $publicSession 'source-input') -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -PassThru
        $started = $true
        if ($process.Handle -eq [IntPtr]::Zero) { throw 'Control child has no exact process handle.' }
        if (!$process.WaitForExit(360000)) {
            try { $process.Kill() } catch { }
            if (!$process.WaitForExit(30000)) { $global:RhaiBackendPendingControl = $process; $process = $null; throw 'Exact control child exit remains unconfirmed after bounded termination.' }
            $confirmed = $true
            throw 'Native backend control exceeded 360 seconds and was terminated.'
        }
        $confirmed = $true; $process.Refresh()
        if ($process.ExitCode -ne 0) { throw "Native backend control $($case.Contract) exited $($process.ExitCode); preserve originals." }
        $observer = Get-Content -LiteralPath (Join-Path $case.Scope 'observer.json') -Raw | ConvertFrom-Json
        if (!$observer.accepted -or !$observer.backend_failure_accepted -or !$observer.backend_failure_sensitivity -or $observer.exit -ne 2 -or $observer.custody_pending) { throw "Native backend control $($case.Contract) lacks its exact negative proof." }
    }
    finally {
        if ($null -ne $process -and $confirmed) { $process.Dispose() }
        elseif ($null -ne $process -and $started) { $global:RhaiBackendPendingControl = $process }
    }
}
Write-Output 'BACKEND_FAILURE_CONTROLS_COMPLETE;guest originals retained for independent export/readback and exact cleanup'
