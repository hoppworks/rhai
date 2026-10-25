$ErrorActionPreference = 'Stop'
$id = 'rhai-process-quota-c8d7629099fd47d1b6f10ef65649db5e'
$bundleId = 'process-quota-c8d7629099fd47d1b6f10ef65649db5e'
$nonce = 'c8d7629099fd47d1b6f10ef65649db5e'
$markerName = 'process-quota-c8d7629099fd47d1b6f10ef65649db5e.bundle'
$mediaCandidates = @(('D:\','E:\','F:\') | Where-Object { $driveName = $_.Substring(0,1); if ($null -ne (Get-PSDrive -Name $driveName -PSProvider FileSystem -ErrorAction SilentlyContinue)) { Test-Path -LiteralPath (Join-Path $_ $markerName) } else { $false } })
if ($mediaCandidates.Count -ne 1) { throw 'Expected exactly one inserted immutable source medium with this session marker.' }
$media = $mediaCandidates[0]
if ((Get-Content -LiteralPath (Join-Path $media $markerName) -Raw).Trim() -cne $id) { throw 'Source-medium marker does not match invocation identity.' }
$startPath = Join-Path $media 'Start.ps1'
if (!(Test-Path -LiteralPath $startPath -PathType Leaf)) { throw 'Start script is missing from the verified source medium.' }
$startHash = (Get-FileHash -LiteralPath $startPath -Algorithm SHA256).Hash.ToLowerInvariant()
$manifestPath = Join-Path $media 'input-manifest.json'
$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($manifestHash -cne '573b944522a9721406b380a7e0d2169aaae3fea6b9a14a72127981481ad97ef3') { throw 'Immutable input manifest differs from its frozen host binding.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$source = Join-Path $media 'input'
foreach ($pin in $manifest.files.PSObject.Properties) {
    if ($pin.Name -match '(^|/)\.\.(/|$)' -or $pin.Name -match '^[/\\]') { throw 'Manifest path traversal rejected.' }
    $inputPath = Join-Path $source ($pin.Name.Replace('/','\'))
    $resolved = [IO.Path]::GetFullPath($inputPath)
    if (!$resolved.StartsWith(([IO.Path]::GetFullPath($source).TrimEnd('\')+'\'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Manifest path escaped immutable source root.' }
    if ((Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pin.Value) { throw "Frozen source mismatch: $($pin.Name)" }
}
$mediaSource = $source
$mediaEntries = @(Get-ChildItem -LiteralPath $mediaSource -Force -Recurse)
foreach ($entry in $mediaEntries) { if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Immutable input contains a reparse point: $($entry.FullName)" } }
$expectedFiles = @($manifest.files.PSObject.Properties.Name | Sort-Object)
$mediaFiles = @(Get-ChildItem -LiteralPath $mediaSource -File -Force -Recurse | ForEach-Object { $_.FullName.Substring($mediaSource.TrimEnd('\').Length+1).Replace('\','/') } | Sort-Object)
if (($expectedFiles -join "`n") -cne ($mediaFiles -join "`n")) { throw 'Immutable source file inventory differs from its frozen manifest.' }
$compiler='C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
if((Get-FileHash -LiteralPath $compiler).Hash.ToLowerInvariant() -cne 'cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1'){throw 'Native compiler changed.'}
$guestFreeDiskBytes=(Get-PSDrive -Name C -PSProvider FileSystem).Free
if($guestFreeDiskBytes -lt 2147483648){throw 'Guest free disk below declared2GiB floor.'}
$memory=Get-CimInstance Win32_OperatingSystem
if(([long]$memory.FreePhysicalMemory*1024) -lt 1073741824){throw 'Guest free physical memory below declared1GiB floor.'}
$private = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$session = Join-Path $private ('quota-fixture-'+$nonce)
$parent = Join-Path $session 'run'
$run = Join-Path $parent ('monitor-source-'+$nonce)
$controlSessions = @((Join-Path $private 'env-control-50a587ef233d4b54a1586bf029a426e9'),(Join-Path $private 'env-control-f2d86c851ad3489b9400719bb8db2490'),(Join-Path $private 'env-control-48845f7338c94693a54b957d6b6c8b96'))
foreach ($ownedPath in (@($session)+$controlSessions)) { if (Test-Path -LiteralPath $ownedPath) { throw "Exact owned guest scope already exists; preserve and inspect it: $ownedPath" } }
$cursor = [IO.Path]::GetFullPath($parent)
while ($cursor) {
    if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse ancestor rejected: $cursor" }
    $ancestor = [IO.Directory]::GetParent($cursor)
    $cursor = if ($null -eq $ancestor) { $null } else { $ancestor.FullName }
}
$publicBuild = 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\quota-build-e6ce6222dba147a8b43b2c79187d3184\run\monitor-source-e6ce6222dba147a8b43b2c79187d3184\build'
$publicManifest = [IO.File]::ReadAllLines((Join-Path ([IO.Directory]::GetParent($publicBuild).FullName) 'build-manifest.txt'))
if($publicManifest[0] -cne 'compiler_sha256=cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1'){throw 'Retained compiler provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq 'e08957b13d5ed5f86cb37d0545aa876aac50e507692d112b39882f465fff8f2b  tools/windows-scoped-runner/LaunchSpecification.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq '49591cc15aaa68add9d8632188506e153179de37e0158d814a81d49d98252550  tools/windows-scoped-runner/LeaseMonitor.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq '98df6be690e4cfe1440d6eb11358688e75ca1f0adde12ef003d20dc2a8426c6c  tools/windows-scoped-runner/MonitorAcceptanceDriver.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq '559fda324f59768f2d5119c2f2fec7442c2cff543b694dc744b4c4ecc2524e4f  tools/windows-scoped-runner/MonitorPayloadJob.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq '0f0a71563e6c3d99f0c643644d4b56951f6c69ceb3b10b03157f68dc37bb8412  tools/windows-scoped-runner/MonitorSpecificationIntake.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq 'c541f7d885d032c074461a5a0173b9ae6291ef7d8cd1b9fd2ce4a4f56d1e0e6e  tools/windows-scoped-runner/MonitorStagingHandoff.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq '792918d1cac67691fc9f7ee4c9e82b0c4377ba869c33458fedd56e9519e71c7c  tools/windows-scoped-runner/MonitorTransport.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq 'd3a77f0daeebd5beed2b277fae9dc6a522acf1454bb5d8d776d84e1dc8e896c8  tools/windows-scoped-runner/ScopedRunner.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq '7a9edfe98d84868b55146280bd5ed29576ee0c8725cf9f6c785b784bc0ad25c2  tools/windows-scoped-runner/SpecificationTransfer.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if(@($publicManifest | Where-Object {$_ -ceq '26b7468a0868271a555f6ed450212267b01d7d3fd0a8dd5b3fb51b01b7a05629  tools/windows-scoped-runner/WindowsCustodyBackend.cs'}).Count -ne 1){throw 'Retained public source provenance differs.'}
if((Get-FileHash -LiteralPath (Join-Path $publicBuild 'ScopedRunner.exe')).Hash.ToLowerInvariant() -cne '30a33cdb5e13089ba71dca135b61a838b32e8f03823b55abcaf61ef8acae3c62' -or @($publicManifest | Where-Object {$_ -ceq '30a33cdb5e13089ba71dca135b61a838b32e8f03823b55abcaf61ef8acae3c62  build/ScopedRunner.exe'}).Count -ne 1){throw 'Retained public binary differs.'}
if((Get-FileHash -LiteralPath (Join-Path $publicBuild 'MonitorAcceptanceDriver.exe')).Hash.ToLowerInvariant() -cne 'ac032063f99e976bec450b41aeee41bece876630073a776ac380c00b2058ab24' -or @($publicManifest | Where-Object {$_ -ceq 'ac032063f99e976bec450b41aeee41bece876630073a776ac380c00b2058ab24  build/MonitorAcceptanceDriver.exe'}).Count -ne 1){throw 'Retained public binary differs.'}
New-Item -ItemType Directory -Path $parent | Out-Null
$source = Join-Path $session 'source-input'
New-Item -ItemType Directory -Path $source | Out-Null
foreach ($entry in (Get-ChildItem -LiteralPath $mediaSource -Force)) {
    Copy-Item -LiteralPath $entry.FullName -Destination $source -Recurse
}
$privateEntries = @(Get-ChildItem -LiteralPath $source -Force -Recurse)
foreach ($entry in $privateEntries) { if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Private source copy contains a reparse point: $($entry.FullName)" } }
$privateFiles = @(Get-ChildItem -LiteralPath $source -File -Force -Recurse | ForEach-Object { $_.FullName.Substring($source.TrimEnd('\').Length+1).Replace('\','/') } | Sort-Object)
if (($expectedFiles -join "`n") -cne ($privateFiles -join "`n")) { throw 'Private source-copy file inventory differs from its frozen manifest.' }
foreach ($pin in $manifest.files.PSObject.Properties) {
    $inputPath = Join-Path $source ($pin.Name.Replace('/','\'))
    $resolved = [IO.Path]::GetFullPath($inputPath)
    if (!$resolved.StartsWith(([IO.Path]::GetFullPath($source).TrimEnd('\')+'\'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Private source-copy path escaped its owner scope.' }
    if (!(Test-Path -LiteralPath $inputPath -PathType Leaf) -or (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pin.Value) { throw "Private source-copy readback differs from manifest: $($pin.Name)" }
}
$bootstrap = Join-Path $source 'tools\windows-scoped-runner\fixtures\RunSourceFixtures.ps1'
$control = Join-Path $source 'tools\windows-scoped-runner\fixtures\RunPayloadEnvironmentControl.ps1'
foreach ($scriptPath in @($bootstrap,$control)) {
    $tokens = $null; $parseErrors = $null
    $null = [Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count -ne 0) { throw ($parseErrors | Out-String) }
}
$stdout = Join-Path $session 'bootstrap.stdout'
$stderr = Join-Path $session 'bootstrap.stderr'
$arguments = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$bootstrap,'-SourceRoot',$source,'-RunRoot',$run,'-BuildOnly','-CompilerClosureOnly')
$line = ($arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
$process = $null; $status = -1; $failure = ''; $complete = $false
$nativeStarted = $false; $processExitConfirmed = $false; $custodyIndeterminate = $false
$processId = $null; $processStartUtc = $null
try {
    $process = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $line -WorkingDirectory $source -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -PassThru
    $handle = $process.Handle
    if ($handle -eq [IntPtr]::Zero) { throw 'BuildOnly child has no retained exact process handle.' }
    $processId = [int]$process.Id
    $processStartUtc = $process.StartTime.ToUniversalTime().ToString('o')
    $nativeStarted = $true
    if (!$process.WaitForExit(240000)) {
        $killFailure = ''
        try { $process.Kill() } catch { $killFailure = $_.Exception.Message }
        if (!$process.WaitForExit(30000)) {
            $custodyIndeterminate = $true
            $failure = 'Exact BuildOnly exit remains unconfirmed after bounded termination reserve. '+$killFailure
            $global:RhaiAbortBuildPendingProcess = $process
            $process = $null
        } else {
            $processExitConfirmed = $true; $process.Refresh()
            if ($null -ne $process.ExitCode) { $status = [int]$process.ExitCode }
            $failure = 'BuildOnly exceeded its 240-second observer bound and was terminated; result is diagnostic only.'
        }
    } else {
        $processExitConfirmed = $true; $process.Refresh()
        if ($null -eq $process.ExitCode) { throw 'BuildOnly exit status unavailable.' }
        $status = [int]$process.ExitCode
        if ($status -ne 0) { throw "BuildOnly exited $status; preserve original logs." }
        $result = [IO.File]::ReadAllText((Join-Path $run 'run-result.txt'))
        if (!$result.StartsWith('BUILD_ONLY_PASS:')) { throw 'Missing exact post-disposition BuildOnly result.' }
        $binaryNames = @((Get-ChildItem -LiteralPath (Join-Path $run 'build') -File).Name | Sort-Object)
        if (($binaryNames -join ',') -cne 'PayloadFixture.exe') { throw 'BuildOnly produced an unexpected native binary inventory.' }
        $manifestLines = [IO.File]::ReadAllLines((Join-Path $run 'build-manifest.txt'))
        foreach ($name in @('PayloadFixture.exe')) {
            $matches = @($manifestLines | Where-Object { $_ -match ('^[0-9a-f]{64}  build/'+[regex]::Escape($name)+'$') })
            if ($matches.Count -ne 1) { throw "Build manifest does not bind exactly one $name." }
            $expectedHash = [regex]::Match($matches[0],'^([0-9a-f]{64})  ').Groups[1].Value
            if ((Get-FileHash -LiteralPath (Join-Path (Join-Path $run 'build') $name) -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedHash) { throw "Built binary differs from build manifest: $name" }
        }
        $complete = $true
    }
} catch {
    if (!$failure) { $failure = $_.Exception.ToString() }
} finally {
    if ($null -ne $process) {
        if ($processExitConfirmed) { $process.Dispose() }
        else { $custodyIndeterminate = $true; $global:RhaiAbortBuildPendingProcess = $process; $process = $null; if (!$failure) { $failure = 'Exact BuildOnly handle retained because exit is unconfirmed.' } }
    }
}
$buildObserver = [ordered]@{id=$id;bundle=$bundleId;nonce=$nonce;session=$session;run=$run;control_sessions=$controlSessions;phase='BuildOnly CompilerClosureOnly';guest_free_disk_bytes=$guestFreeDiskBytes;guest_free_physical_bytes=([long]$memory.FreePhysicalMemory*1024);os_version=[Environment]::OSVersion.VersionString;clr_version=[Environment]::Version.ToString();powershell_version=$PSVersionTable.PSVersion.ToString();compiler_version=(Get-Item -LiteralPath $compiler).VersionInfo.FileVersion;exit=$status;accepted=$complete;failure=$failure;native_started=$nativeStarted;process_id=$processId;process_start_utc=$processStartUtc;custody_indeterminate=$custodyIndeterminate;input_manifest_sha256=$manifestHash;start_sha256=$startHash;driver_launched=$false;limits=@{compiler_seconds=180;bootstrap_seconds=240;termination_reserve_seconds=30;fixture_driver_seconds=180;serial_export_seconds=180;max_files=64;max_file_bytes=4194304;max_total_bytes=16777216}}
$observerPath = Join-Path $session 'build-observer.json'
[IO.File]::WriteAllText($observerPath,($buildObserver|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
if (!$complete) {
    $files = @((Get-Item -LiteralPath $observerPath))
    foreach ($path in @($stdout,$stderr,(Join-Path $run 'run-result.txt'),(Join-Path $run 'build-manifest.txt'))) { if (Test-Path -LiteralPath $path -PathType Leaf) { $files += @(Get-Item -LiteralPath $path) } }
    $logs = Join-Path $run 'logs'; if (Test-Path -LiteralPath $logs -PathType Container) { $files += @(Get-ChildItem -LiteralPath $logs -File) }
    if ($files.Count -gt 64 -or ($files | Measure-Object Length -Sum).Sum -gt 16MB) { throw 'Build failure evidence exceeds declared export bounds; guest evidence is retained.' }
    foreach ($file in $files) { if ($file.Length -gt 4MB -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Build failure evidence exceeds file cap or is a reparse point.' } }
    $serial = [IO.Ports.SerialPort]::new('COM1',115200); $serial.WriteTimeout=2000; $script:sequence=0
    $exportDeadline=[Diagnostics.Stopwatch]::StartNew()
    function Emit-Frame([string]$Kind,[object]$Value) { if ($exportDeadline.Elapsed.TotalSeconds -gt 180) { throw 'Build failure serial export exceeded bound; preserve guest evidence.' }; $json=$Value|ConvertTo-Json -Compress -Depth 8; $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json)); if($encoded.Length -gt 3500){throw 'Build failure frame exceeds cap.'}; $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded");$script:sequence++ }
    try { $serial.Open();Emit-Frame 'BEGIN' @{id=$id;exit=$status;accepted=$false;custody_indeterminate=$custodyIndeterminate};foreach($file in $files){$relative=$file.FullName.Substring($session.Length+1).Replace('\','/');$bytes=[IO.File]::ReadAllBytes($file.FullName);$sha=[Security.Cryptography.SHA256]::Create();try{$hash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()};Emit-Frame 'FILE' @{path=$relative;length=$bytes.Length;sha256=$hash};for($offset=0;$offset -lt $bytes.Length;$offset+=1024){$length=[Math]::Min(1024,$bytes.Length-$offset);Emit-Frame 'CHUNK' @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}};Emit-Frame 'FILE_END' @{path=$relative;length=$bytes.Length;sha256=$hash}};Emit-Frame 'END' @{id=$id;files=$files.Count;accepted=$false;exit=$status;custody_indeterminate=$custodyIndeterminate;guest_evidence_retained=$true} } finally { $serial.Dispose() }
    throw "Resource build/control incomplete; retain originals and exact custody."
}

$build=Join-Path $run 'build';$fixture=Join-Path $build 'PayloadFixture.exe';$fixtureHash=(Get-FileHash -LiteralPath $fixture).Hash.ToLowerInvariant()

& ([scriptblock]::Create([IO.File]::ReadAllText($control))) -FixturePath $fixture -FixtureSha256 $fixtureHash -BuildRoot $publicBuild -FixtureBuildRoot $build -Session (Join-Path $private 'env-control-50a587ef233d4b54a1586bf029a426e9') -Id 'rhai-process-quota-quota02-50a587ef233d4b54a1586bf029a426e9' -Phase GREEN -Contract 'job-quota' -ReturnStatusToCaller
if($global:RhaiPayloadControlExitCode -ne 0){throw 'Public payload case incomplete; preserve exact originals and pending custody.'}

& ([scriptblock]::Create([IO.File]::ReadAllText($control))) -FixturePath $fixture -FixtureSha256 $fixtureHash -BuildRoot $publicBuild -FixtureBuildRoot $build -Session (Join-Path $private 'env-control-f2d86c851ad3489b9400719bb8db2490') -Id 'rhai-process-quota-resources02-f2d86c851ad3489b9400719bb8db2490' -Phase GREEN -Contract 'job-resources' -ReturnStatusToCaller
if($global:RhaiPayloadControlExitCode -ne 0){throw 'Public payload case incomplete; preserve exact originals and pending custody.'}

& ([scriptblock]::Create([IO.File]::ReadAllText($control))) -FixturePath $fixture -FixtureSha256 $fixtureHash -BuildRoot $publicBuild -FixtureBuildRoot $build -Session (Join-Path $private 'env-control-48845f7338c94693a54b957d6b6c8b96') -Id 'rhai-process-quota-environment02-48845f7338c94693a54b957d6b6c8b96' -Phase GREEN -Contract 'environment' -ReturnStatusToCaller
if($global:RhaiPayloadControlExitCode -ne 0){throw 'Public payload case incomplete; preserve exact originals and pending custody.'}
Write-Output 'PROCESS_QUOTA_AND_AFFECTED_REGRESSIONS_COMPLETE'
