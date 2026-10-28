$ErrorActionPreference = 'Stop'
$nonce = 'a7e54f39104e47c7ad826b2b9938365f'
$id = 'rhai-msrv-bootstrap-' + $nonce
$marker = $id + '.bundle'
$mediaCandidates = @(@('D:\', 'E:\', 'F:\') | Where-Object {
    $drive = $_.Substring(0, 1)
    $null -ne (Get-PSDrive -Name $drive -PSProvider FileSystem -ErrorAction SilentlyContinue) -and
        (Test-Path -LiteralPath (Join-Path $_ $marker) -PathType Leaf)
})
if ($mediaCandidates.Count -ne 1) { throw 'Expected exactly one owned bootstrap medium.' }
$media = $mediaCandidates[0]
if ((Get-Content -LiteralPath (Join-Path $media $marker) -Raw).Trim() -cne $id) {
    throw 'Bootstrap medium identity differs.'
}
if ($env:USERNAME -cne 'RhaiTest' -or $env:USERPROFILE -cne 'C:\Users\RhaiTest') {
    throw 'Wrong native guest owner.'
}
$freeBefore = [long](Get-PSDrive C -PSProvider FileSystem).Free
if ($freeBefore -lt 20GB) { throw 'Guest disk cannot cover four GiB estimate plus sixteen GiB reserve.' }
$private = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$session = Join-Path $private 'n-a7e54f39'
$resume = Test-Path -LiteralPath $session
$priorRun = Join-Path $session 'run'
if ($resume) {
    foreach ($name in @('run', 'toolchain-home')) {
        $priorPath = Join-Path $session $name
        if (!(Test-Path -LiteralPath $priorPath -PathType Container) -or
            ((Get-Item -LiteralPath $priorPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Prior owned path is absent or redirected: $name"
        }
    }
    $priorPreflight = Join-Path $session 'preflight.json'
    if ((Get-FileHash -LiteralPath $priorPreflight).Hash.ToLowerInvariant() -cne
        '34907dd6b5943fac0b8cdd9a01a9614103792148941d435156de2a4cd1abe360') {
        throw 'Prior owned bootstrap preflight differs.'
    }
    $priorJournals = @(Get-ChildItem -LiteralPath $priorRun -File -Force -Filter '.scoped-run-*.journal')
    if ($priorJournals.Count -ne 1 -or
        !(Get-Content -LiteralPath $priorJournals[0].FullName -Tail 1).Contains('REMOVED')) {
        throw 'Prior bounded native run has no terminal removal record.'
    }
    foreach ($name in @('source-verify', 'bin-verify', 'run-verify')) {
        if (@(Get-ChildItem -LiteralPath $session -Force | Where-Object { $_.Name -ceq $name }).Count -ne 0) {
            throw "Prior verification path exists; inspect it before any retry: $name"
        }
    }
}
$cursor = [IO.Path]::GetFullPath($session)
while ($cursor) {
    if ((Test-Path -LiteralPath $cursor) -and
        ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Reparse ancestor refused: $cursor"
    }
    $parent = [IO.Directory]::GetParent($cursor)
    $cursor = if ($null -eq $parent) { $null } else { $parent.FullName }
}
$build = Join-Path $private 'public-refresh-e2047d40e48afb4426d07e2a1e881f19\run\monitor-source-e2047d40e48afb4426d07e2a1e881f19\build'
$buildManifest = Join-Path ([IO.Directory]::GetParent($build).FullName) 'build-manifest.txt'
if (!(Test-Path -LiteralPath $build -PathType Container)) { throw 'Accepted public runner build absent.' }
if ((Get-FileHash -LiteralPath $buildManifest).Hash.ToLowerInvariant() -cne
    '8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1') {
    throw 'Accepted public runner manifest differs.'
}
$pins = @{
    'ScopedRunner.exe' = 'ff836aa0ce75807c817097327b60a2a9cd8741a0937cfb072bd17adefd994c7f'
    'MonitorAcceptanceDriver.exe' = '090d29d3eb3642c6acb53f241c340cd7ef800f07977671039465ae140837e5a0'
}
foreach ($name in $pins.Keys) {
    if ((Get-FileHash -LiteralPath (Join-Path $build $name)).Hash.ToLowerInvariant() -cne $pins[$name]) {
        throw "Accepted public runner binary differs: $name"
    }
}
$rustup = Join-Path $env:USERPROFILE '.cargo\bin\rustup.exe'
$rustupHash = '6f4bef66261261fcb43131be8720bab817d403a09edec7455c371974b90bdb7e'
if ((Get-FileHash -LiteralPath $rustup).Hash.ToLowerInvariant() -cne $rustupHash) {
    throw 'Installed rustup proxy differs.'
}
$cmdExe = 'C:\Windows\System32\cmd.exe'
$cmdHash = '15cd209c995b7d3009c91ca40892d5b8f1fb162f3e5f10716642ea278e8e0d7b'
if ((Get-FileHash -LiteralPath $cmdExe).Hash.ToLowerInvariant() -cne $cmdHash) {
    throw 'Guest command interpreter differs.'
}
$installCommand = Join-Path $media 'InstallAndVerify.cmd'
$installCommandHash = 'ad351600c96d10253a0be97aa8ca7aa810664064dec48fe18e19fbe50355b4d1'
if ((Get-FileHash -LiteralPath $installCommand).Hash.ToLowerInvariant() -cne $installCommandHash) {
    throw 'Bootstrap install command differs.'
}

$suffix = if ($resume) { '-verify' } else { '' }
$source = Join-Path $session ('source' + $suffix)
$bin = Join-Path $session ('bin' + $suffix)
$run = Join-Path $session ('run' + $suffix)
$toolchainHome = Join-Path $session 'toolchain-home'
if ($resume -and !(Test-Path -LiteralPath $toolchainHome -PathType Container)) {
    throw 'Prior owned toolchain home is absent.'
}
if ($resume -and @(Get-ChildItem -LiteralPath $toolchainHome -Force -Recurse | Where-Object {
    ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
}).Count -ne 0) { throw 'Prior owned toolchain home contains a reparse point.' }
foreach ($path in @($source, $bin, $run)) {
    if (Test-Path -LiteralPath $path) { throw "New private path already exists: $path" }
    [IO.Directory]::CreateDirectory($path) | Out-Null
}
if (!$resume) { [IO.Directory]::CreateDirectory($toolchainHome) | Out-Null }
Copy-Item -LiteralPath $rustup -Destination (Join-Path $source 'rustup.exe')
Copy-Item -LiteralPath $cmdExe -Destination (Join-Path $source 'cmd.exe')
Copy-Item -LiteralPath $installCommand -Destination (Join-Path $source 'InstallAndVerify.cmd')
foreach ($name in $pins.Keys) { Copy-Item -LiteralPath (Join-Path $build $name) -Destination $bin }
if ((Get-FileHash -LiteralPath (Join-Path $source 'rustup.exe')).Hash.ToLowerInvariant() -cne $rustupHash) {
    throw 'Private rustup copy differs.'
}
if ((Get-FileHash -LiteralPath (Join-Path $source 'cmd.exe')).Hash.ToLowerInvariant() -cne $cmdHash -or
    (Get-FileHash -LiteralPath (Join-Path $source 'InstallAndVerify.cmd')).Hash.ToLowerInvariant() -cne $installCommandHash) {
    throw 'Private command copy differs.'
}
foreach ($name in $pins.Keys) {
    if ((Get-FileHash -LiteralPath (Join-Path $bin $name)).Hash.ToLowerInvariant() -cne $pins[$name]) {
        throw "Private runner copy differs: $name"
    }
}
$preflight = [ordered]@{
    id = $id; guest_user = $env:USERNAME; free_before_bytes = $freeBefore
    runner_manifest_sha256 = '8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5a4160ee0d1'
    runner_pins = $pins; rustup_sha256 = $rustupHash; cmd_sha256 = $cmdHash
    install_command_sha256 = $installCommandHash
    retained_toolchain_home = $toolchainHome
    retention_owner = 'rhai all-tickets coordinator'
    retention_purpose = 'native Windows Rust 1.77.2 sys/net release checks'
    retention_expiry_utc = '2026-11-01T00:00:00Z'
    retention_acceptance_ceiling_bytes = 2147483648
    additional_occupancy_estimate_bytes = 4294967296
    guest_free_reserve_bytes = 17179869184
    disk_quota_enforced = $false
    live_retained_home_abort_bytes = 4294967296
    live_free_disk_abort_bytes = 19327352832
    driver_deadline_ms = 180000; outer_deadline_ms = 185000
    driver_output_ceiling_per_stream_bytes = 4194304
    resumed_prior_preflight_sha256 = if ($resume) {
        '34907dd6b5943fac0b8cdd9a01a9614103792148941d435156de2a4cd1abe360'
    } else { '' }
}
$preflightPath = Join-Path $session ('preflight' + $suffix + '.json')
[IO.File]::WriteAllText($preflightPath,
    ($preflight | ConvertTo-Json -Compress -Depth 5), [Text.UTF8Encoding]::new($false))

$driverOut = Join-Path $session ('driver' + $suffix + '.stdout')
$driverErr = Join-Path $session ('driver' + $suffix + '.stderr')
$driverExit = -1
$outerTimeout = $false
$started = $false
$exited = $false
$pipesDrained = $false
$failure = ''
$driverPid = 0
$driverCreation = 0L
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $bin 'MonitorAcceptanceDriver.exe'
$info.Arguments = '--mode success --source "' + $source + '" --exe cmd.exe --expected-payload-exit 00000000 -- /D /C InstallAndVerify.cmd'
$info.WorkingDirectory = $bin
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true
$info.RedirectStandardError = $true
$info.EnvironmentVariables['AGENT_RUNTIME_DIR'] = $run
$info.EnvironmentVariables['RUSTUP_HOME'] = $toolchainHome
if ($null -ne $global:RhaiMsrvPendingCustody) { throw 'Previous MSRV custody remains pending.' }
$process = [Diagnostics.Process]::new()
$process.StartInfo = $info
$readers = [Collections.Generic.List[object]]::new()
$global:RhaiMsrvPendingCustody = [pscustomobject]@{
    Process=$process; Readers=$readers; Scope=$session
    ExactExitConfirmed=$false; PipesDrained=$false; ProcessDisposed=$false
}
$clock = [Diagnostics.Stopwatch]::StartNew()
$lastDiskSample = -10.0
function Save-Chunk([object]$channel) {
    if ($null -eq $channel.Task -or !$channel.Task.IsCompleted) { return }
    try {
        $task = $channel.Task
        $channel.Task = $null
        $count = $task.GetAwaiter().GetResult()
        if ($count -eq 0) { $channel.Eof = $true; return }
        $channel.Bytes += [Text.Encoding]::UTF8.GetByteCount($channel.Buffer, 0, $count)
        if ($channel.Bytes -gt 4MB) { throw 'Driver output exceeds four MiB; prefix preserved.' }
        $channel.Writer.Write($channel.Buffer, 0, $count)
        $channel.Writer.Flush()
        $channel.Task = $channel.Reader.ReadAsync($channel.Buffer, 0, $channel.Buffer.Length)
    } catch { $channel.Error = $_.Exception.ToString(); throw }
}
try {
    if (!$process.Start()) { throw 'Native bootstrap Driver did not start.' }
    $started = $true
    $driverPid = $process.Id
    $driverCreation = $process.StartTime.ToUniversalTime().ToFileTimeUtc()
    if ($process.Handle -eq [IntPtr]::Zero) { throw 'Exact Driver handle missing.' }
    foreach ($definition in @(@{Output=$true;Path=$driverOut}, @{Output=$false;Path=$driverErr})) {
        $channel = [pscustomobject]@{
            Reader=$null; Writer=$null; Buffer=[char[]]::new(1024); Task=$null
            Bytes=0; Eof=$false; Error=''; WriterDisposed=$false; ReaderDisposed=$false
        }
        $readers.Add($channel)
        $channel.Reader = if ($definition.Output) { $process.StandardOutput } else { $process.StandardError }
        $channel.Writer = [IO.StreamWriter]::new($definition.Path, $false, [Text.UTF8Encoding]::new($false))
        $channel.Task = $channel.Reader.ReadAsync($channel.Buffer, 0, $channel.Buffer.Length)
    }
    while (!$process.WaitForExit(20)) {
        foreach ($channel in $readers) { Save-Chunk $channel }
        if ($clock.Elapsed.TotalSeconds - $lastDiskSample -ge 2) {
            $lastDiskSample = $clock.Elapsed.TotalSeconds
            if ([long](Get-PSDrive C).Free -lt 18GB) {
                throw 'Guest free disk crossed the live eighteen GiB abort floor.'
            }
            $currentBytes = [long]((Get-ChildItem -LiteralPath $toolchainHome -File -Force -Recurse |
                Measure-Object -Property Length -Sum).Sum)
            if ($currentBytes -gt 4GB) { throw 'Retained toolchain home crossed live four GiB abort threshold.' }
        }
        if ($clock.Elapsed.TotalSeconds -ge 185) { $outerTimeout = $true; throw 'Native bootstrap Driver exceeded 185 seconds.' }
    }
    $exited = $true
    $process.Refresh()
    $driverExit = [int]$process.ExitCode
} catch { $failure = $_.Exception.ToString() }
finally {
    if ($started -and !$exited) {
        try {
            if (!$process.HasExited) { $process.Kill() }
            if (!$process.WaitForExit(10000)) { throw 'Exact Driver exit unconfirmed after bounded kill.' }
            $exited = $true
            $process.Refresh()
            $driverExit = [int]$process.ExitCode
        } catch { $failure += "`nDriver cleanup: " + $_.Exception.ToString() }
    }
    $drain = [Diagnostics.Stopwatch]::StartNew()
    do {
        foreach ($channel in $readers) {
            try { Save-Chunk $channel } catch { $failure += "`nPipe drain: " + $_.Exception.ToString() }
        }
        if (@($readers | Where-Object { $null -ne $_.Task }).Count -eq 0) { break }
        [Threading.Thread]::Sleep(10)
    } while ($drain.Elapsed.TotalSeconds -lt 10)
    $pipesDrained = $readers.Count -eq 2 -and @($readers | Where-Object { !$_.Eof -or $_.Error }).Count -eq 0
    $global:RhaiMsrvPendingCustody.ExactExitConfirmed = $exited
    $global:RhaiMsrvPendingCustody.PipesDrained = $pipesDrained
    foreach ($channel in $readers) {
        if ($null -ne $channel.Writer) {
            try { $channel.Writer.Flush(); $channel.Writer.Dispose(); $channel.WriterDisposed = $true }
            catch { $failure += "`nWriter disposal: " + $_.Exception.ToString() }
        }
    }
    if ($exited -and $pipesDrained) {
        foreach ($channel in $readers) {
            if ($null -ne $channel.Reader) {
                try { $channel.Reader.Dispose(); $channel.ReaderDisposed = $true }
                catch { $failure += "`nReader disposal: " + $_.Exception.ToString() }
            }
        }
        if (@($readers | Where-Object { !$_.WriterDisposed -or !$_.ReaderDisposed }).Count -eq 0) {
            try { $process.Dispose(); $global:RhaiMsrvPendingCustody.ProcessDisposed = $true }
            catch { $failure += "`nProcess disposal: " + $_.Exception.ToString() }
        }
    }
    if ($global:RhaiMsrvPendingCustody.ExactExitConfirmed -and
        $global:RhaiMsrvPendingCustody.PipesDrained -and
        $global:RhaiMsrvPendingCustody.ProcessDisposed) { $global:RhaiMsrvPendingCustody = $null }
}
if ($null -ne $global:RhaiMsrvPendingCustody) {
    throw "Native bootstrap custody remains pending; retain exact handles and scope. $failure"
}

$driverText = ''
if (Test-Path -LiteralPath $driverOut) { $driverText = [IO.File]::ReadAllText($driverOut) }
$installed = Join-Path $toolchainHome 'toolchains\1.77.2-x86_64-pc-windows-msvc'
$rustc = Join-Path $installed 'bin\rustc.exe'
$cargo = Join-Path $installed 'bin\cargo.exe'
$evidenceDirectories = @(Get-ChildItem -LiteralPath $run -Directory -Force -Filter '.scoped-evidence-*')
$payloadOutput = ''
$rustcVersion = ''
$cargoVersion = ''
if ($evidenceDirectories.Count -eq 1) {
    $evidenceRoot = $evidenceDirectories[0].FullName
    $payloadLog = Join-Path $evidenceRoot 'stdout.log'
    if (Test-Path -LiteralPath $payloadLog -PathType Leaf) {
        $payloadOutput = [IO.File]::ReadAllText($payloadLog)
    }
    $rustcVersionPath = Join-Path $evidenceRoot 'runtime\rustc-version.txt'
    $cargoVersionPath = Join-Path $evidenceRoot 'runtime\cargo-version.txt'
    if (Test-Path -LiteralPath $rustcVersionPath -PathType Leaf) {
        $rustcVersion = [IO.File]::ReadAllText($rustcVersionPath).Trim()
    }
    if (Test-Path -LiteralPath $cargoVersionPath -PathType Leaf) {
        $cargoVersion = [IO.File]::ReadAllText($cargoVersionPath).Trim()
    }
}
$retainedEntries = @(Get-ChildItem -LiteralPath $toolchainHome -Force -Recurse)
$retainedReparsePoint = @($retainedEntries | Where-Object {
    ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
}).Count -ne 0
$bytes = [long]((Get-ChildItem -LiteralPath $toolchainHome -File -Force -Recurse |
    Measure-Object -Property Length -Sum).Sum)
$runtimeMatch = [regex]::Match($driverText, '(?m)^RUNTIME=(.+)\r?$')
$runtimePath = if ($runtimeMatch.Success) { $runtimeMatch.Groups[1].Value.Trim() } else { '' }
$runtimeAbsent = $runtimePath -and [IO.Path]::GetDirectoryName($runtimePath) -ceq $run -and
    !(Test-Path -LiteralPath $runtimePath)
$accepted = !$failure -and !$outerTimeout -and $driverExit -eq 0 -and $runtimeAbsent -and
    $driverText.Contains('CLIENT_EXIT=0x0000004E') -and
    $driverText.Contains('MODE=success;ACTION_CONFIRMED=True;') -and
    $driverText.Contains('PAYLOAD_EXIT=00000000') -and
    $driverText.Contains('CLEANUP_CONFIRMED=True') -and
    $driverText.Contains('RUNTIME_REMOVED=True') -and
    $payloadOutput.Contains('RHAI_MSRV_TOOLCHAIN_EXACT_VERSIONS_OK') -and
    $rustcVersion -ceq 'rustc 1.77.2 (25ef9e3d8 2024-04-09)' -and
    $cargoVersion -ceq 'cargo 1.77.2 (e52e36006 2024-03-26)' -and
    (Test-Path -LiteralPath $rustc -PathType Leaf) -and
    (Test-Path -LiteralPath $cargo -PathType Leaf) -and
    !$retainedReparsePoint -and $bytes -gt 0 -and $bytes -le 2147483648 -and
    [long](Get-PSDrive C).Free -ge 16GB
$record = [ordered]@{
    id = $id; accepted = $accepted; driver_exit = $driverExit
    driver_pid = $driverPid; driver_creation = $driverCreation
    outer_timeout = $outerTimeout; failure = $failure
    runtime = $runtimePath; runtime_absent = $runtimeAbsent
    rustc_version = $rustcVersion; cargo_version = $cargoVersion
    rustc_sha256 = if ($rustcVersion -and (Test-Path -LiteralPath $rustc -PathType Leaf)) {
        (Get-FileHash -LiteralPath $rustc).Hash.ToLowerInvariant()
    } else { '' }
    cargo_sha256 = if ($cargoVersion -and (Test-Path -LiteralPath $cargo -PathType Leaf)) {
        (Get-FileHash -LiteralPath $cargo).Hash.ToLowerInvariant()
    } else { '' }
    toolchain_bytes = $bytes; retained_reparse_point = $retainedReparsePoint
    free_after_bytes = [long](Get-PSDrive C).Free
    retained_toolchain_home = $toolchainHome
    resumed_prior_attempt = $resume
    product_acceptance = $false
}
$recordPath = Join-Path $session ('bootstrap' + $suffix + '.json')
[IO.File]::WriteAllText($recordPath,
    ($record | ConvertTo-Json -Compress -Depth 5), [Text.UTF8Encoding]::new($false))

$files = @((Get-Item -LiteralPath $preflightPath),
    (Get-Item -LiteralPath $recordPath),
    (Get-Item -LiteralPath (Join-Path $source 'InstallAndVerify.cmd')))
foreach ($path in @($driverOut, $driverErr)) {
    if (Test-Path -LiteralPath $path -PathType Leaf) { $files += @(Get-Item -LiteralPath $path) }
}
$exportRuns = @($run)
if ($resume) {
    $files += @(Get-Item -LiteralPath (Join-Path $session 'preflight.json'))
    $files += @(Get-Item -LiteralPath (Join-Path $session 'source\InstallAndVerify.cmd'))
    foreach ($path in @((Join-Path $session 'driver.stdout'), (Join-Path $session 'driver.stderr'))) {
        if (Test-Path -LiteralPath $path -PathType Leaf) { $files += @(Get-Item -LiteralPath $path) }
    }
    $exportRuns += $priorRun
}
foreach ($runPath in $exportRuns) {
    $files += @(Get-ChildItem -LiteralPath $runPath -File -Force -Filter '.scoped-run-*.journal')
    foreach ($evidence in @(Get-ChildItem -LiteralPath $runPath -Directory -Force -Filter '.scoped-evidence-*')) {
    foreach ($name in @('manifest.txt', 'stdout.log', 'stderr.log',
        'runtime\rustc-version.txt', 'runtime\cargo-version.txt')) {
        $path = Join-Path $evidence.FullName $name
        if (Test-Path -LiteralPath $path -PathType Leaf) { $files += @(Get-Item -LiteralPath $path) }
    }
    }
}
if ($files.Count -gt 32 -or ($files | Measure-Object Length -Sum).Sum -gt 8MB) {
    throw 'Bootstrap evidence exceeds export cap; retain guest originals.'
}
$serial = [IO.Ports.SerialPort]::new('COM1', 115200)
$serial.WriteTimeout = 2000
$sequence = 0
$exportDeadline = [Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string]$kind, [object]$value) {
    if ($exportDeadline.Elapsed.TotalSeconds -gt 120) { throw 'Bootstrap export deadline exceeded.' }
    $json = $value | ConvertTo-Json -Compress -Depth 6
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    if ($encoded.Length -gt 3500) { throw 'Bootstrap export frame exceeds bound.' }
    $serial.WriteLine("RHAI_BOOTSTRAP $id $sequence $kind $encoded")
    $script:sequence++
}
try {
    $serial.Open()
    Emit-Frame 'BEGIN' @{id=$id; accepted=$accepted; exit=$driverExit}
    foreach ($file in $files) {
        if ($file.Length -gt 4MB -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'Bootstrap export file exceeds cap or is a reparse point.'
        }
        $relative = $file.FullName.Substring($session.Length + 1).Replace('\', '/')
        $content = [IO.File]::ReadAllBytes($file.FullName)
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $hash = [BitConverter]::ToString($sha.ComputeHash($content)).Replace('-', '').ToLowerInvariant() }
        finally { $sha.Dispose() }
        Emit-Frame 'FILE' @{path=$relative; length=$content.Length; sha256=$hash}
        for ($offset=0; $offset -lt $content.Length; $offset+=1024) {
            $count = [Math]::Min(1024, $content.Length - $offset)
            Emit-Frame 'CHUNK' @{path=$relative; offset=$offset; data=[Convert]::ToBase64String($content,$offset,$count)}
        }
        Emit-Frame 'FILE_END' @{path=$relative; length=$content.Length; sha256=$hash}
    }
    Emit-Frame 'END' @{id=$id; accepted=$accepted; exit=$driverExit; files=$files.Count; guest_evidence_retained=$true}
} finally { $serial.Dispose() }
$record | ConvertTo-Json -Compress -Depth 5
if (!$accepted) { throw 'Native Windows MSRV bootstrap incomplete; retain exact guest originals.' }
