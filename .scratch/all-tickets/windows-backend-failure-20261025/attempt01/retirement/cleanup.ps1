param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference = 'Stop'
if ($env:USERPROFILE -cne 'C:\Users\RhaiTest' -or $env:USERNAME -cne 'RhaiTest') { throw 'Wrong cleanup owner.' }
$manifestPath = 'E:\cleanup-host-manifest.json'
if ((Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ManifestSha256) { throw 'Host-accepted cleanup manifest changed.' }
$proof = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if (!$proof.accepted_for_cleanup -or $proof.nonce -cne '3cd277ed37eb4926b06e55c9c44279a4' -or
    $proof.scopes.Count -ne 2 -or $proof.retained_builds.Count -ne 2 -or
    $proof.max_entries_per_scope -ne 128 -or $proof.max_bytes_per_scope -ne 33554432) { throw 'Unexpected cleanup manifest contract.' }
$private = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$wanted = @('env-control-0e6872acee8647af927c9023af25d331','env-control-60e5e70f35564d85bf8f08f18e911f5d')
$retainedLeaves = @('backend-public-3cd277ed37eb4926b06e55c9c44279a4','backend-fixture-3cd277ed37eb4926b06e55c9c44279a4')

function No-ReparseAncestors([string]$Path) {
    $cursor = [IO.Path]::GetFullPath($Path)
    while ($cursor) {
        if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Reparse ancestor: $cursor" }
        $parent = [IO.Directory]::GetParent($cursor)
        $cursor = if ($null -eq $parent) { $null } else { $parent.FullName }
    }
}
function Assert-RetainedBuilds {
    foreach ($build in $proof.retained_builds) {
        $scope = [IO.Path]::GetFullPath($build.scope)
        if ([IO.Path]::GetDirectoryName($scope) -cne $private -or $retainedLeaves -cnotcontains [IO.Path]::GetFileName($scope) -or
            [IO.Path]::GetDirectoryName([IO.Path]::GetDirectoryName($build.run)) -cne $scope -or
            [IO.Path]::GetFileName([IO.Path]::GetDirectoryName($build.run)) -cne 'run') { throw 'Retained build path differs.' }
        No-ReparseAncestors $build.run
        if ((Get-FileHash -LiteralPath (Join-Path $scope 'build-observer.json')).Hash.ToLowerInvariant() -cne $build.observer_sha256 -or
            (Get-FileHash -LiteralPath (Join-Path $build.run 'build-manifest.txt')).Hash.ToLowerInvariant() -cne $build.manifest_sha256) { throw 'Retained build provenance differs.' }
        $pins = @($build.binaries.PSObject.Properties)
        if ($pins.Count -lt 1 -or $pins.Count -gt 2) { throw 'Unexpected retained binary set.' }
        foreach ($pin in $pins) {
            $file = Join-Path (Join-Path $build.run 'build') $pin.Name
            No-ReparseAncestors $file
            if ($pin.Name -notmatch '^[A-Za-z]+\.exe$' -or $pin.Value -cnotmatch '^[0-9a-f]{64}$' -or
                (Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $pin.Value) { throw 'Retained binary changed.' }
        }
    }
}
Assert-RetainedBuilds

$roots = @(); $actors = @(); $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($scope in $proof.scopes) {
    $root = [IO.Path]::GetFullPath($scope.scope)
    if ([IO.Path]::GetDirectoryName($root) -cne $private -or $wanted -cnotcontains [IO.Path]::GetFileName($root) -or
        $scope.leaf -cne [IO.Path]::GetFileName($root) -or !$seen.Add($root) -or
        $scope.id -notmatch '^rhai-backend-(evidence|cleanup)-[0-9a-f]{32}$' -or
        $scope.contract -cnotin @('backend-evidence-hardlink','backend-cleanup-readonly')) { throw 'Unknown or duplicate control scope.' }
    No-ReparseAncestors $root
    if (!(Test-Path -LiteralPath $root -PathType Container)) { throw 'Own control scope absent.' }
    $allowed = @{}; $directories = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $scope.files.PSObject.Properties) {
        $relative = $entry.Name.Replace('/','\')
        if ([IO.Path]::IsPathRooted($relative) -or $relative.Contains(':') -or
            $relative.Split([char[]]@('\','/')) -contains '..' -or $entry.Value -cnotmatch '^[0-9a-f]{64}$') { throw 'Unsafe expected file.' }
        $full = [IO.Path]::GetFullPath((Join-Path $root $relative))
        if (!$full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or $allowed.ContainsKey($full)) { throw 'Unexpected expected path.' }
        $allowed[$full] = $entry.Value
        $cursor = [IO.Path]::GetDirectoryName($full)
        while ($cursor -cne $root) { $null = $directories.Add($cursor); $cursor = [IO.Path]::GetDirectoryName($cursor) }
    }
    foreach ($relative in $scope.optional_empty_dirs) {
        $full = [IO.Path]::GetFullPath((Join-Path $root $relative.Replace('/','\')))
        if (!$full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or
            [IO.Path]::GetFileName($full) -cne 'runtime') { throw 'Unsafe optional empty directory.' }
        $null = $directories.Add($full)
    }
    $queue = [Collections.Generic.Queue[string]]::new(); $queue.Enqueue($root)
    $observed = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $entries = 0; $bytes = 0L
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        foreach ($entry in @(Get-ChildItem -LiteralPath $current -Force)) {
            $entries++
            if ($entries -gt 128 -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Unexpected inventory or reparse point.' }
            if ($entry.PSIsContainer) {
                if (!$directories.Contains($entry.FullName)) { throw "Unknown directory: $($entry.FullName)" }
                $queue.Enqueue($entry.FullName)
            } else {
                if (!$allowed.ContainsKey($entry.FullName) -or !$observed.Add($entry.FullName) -or $entry.Length -gt 4MB -or
                    (Get-FileHash -LiteralPath $entry.FullName).Hash.ToLowerInvariant() -cne $allowed[$entry.FullName]) { throw "Unknown or changed file: $($entry.FullName)" }
                $bytes += $entry.Length
                if ($bytes -gt 33554432) { throw 'Control scope exceeds cleanup byte cap.' }
            }
        }
    }
    if ($observed.Count -ne $allowed.Count) { throw 'Expected control file absent.' }
    $observer = Get-Content -LiteralPath (Join-Path $root 'observer.json') -Raw | ConvertFrom-Json
    if ($observer.id -cne $scope.id -or $observer.contract -cne $scope.contract -or $observer.scope -cne $root -or
        !$observer.accepted -or $observer.exit -ne 2 -or !$observer.backend_failure_accepted -or !$observer.backend_failure_sensitivity -or
        !$observer.exact_driver_exited -or !$observer.pipes_drained -or !$observer.owned_executables_stopped -or
        $observer.custody_pending -or $observer.retained_driver_handles -or $observer.parent_environment_changed -or
        $observer.allocated_runtime -cne $scope.runtime -or $observer.backend_failure_observed.evidence -cne $scope.evidence -or
        !(Test-Path -LiteralPath $scope.runtime -PathType Container)) { throw 'Control result or retained runtime changed.' }
    if ($scope.actors.Count -ne 2 -or $scope.actors[0].pid -ne $observer.driver_pid -or
        $scope.actors[0].creation -ne $observer.driver_creation -or
        $scope.actors[1].pid -ne $observer.backend_failure_observed.payload_pid -or
        $scope.actors[1].creation -ne $observer.backend_failure_observed.payload_creation) { throw 'Control actor identities changed.' }
    $roots += ,$root
    $actors += @($scope.actors)
}
if ($roots.Count -ne 2 -or ($roots | Sort-Object -Unique).Count -ne 2) { throw 'Exact two cleanup roots required.' }
$live = @(Get-CimInstance Win32_Process)
if ($live.Count -lt 1 -or @($live | Where-Object {$_.ProcessId -eq $PID}).Count -ne 1) { throw 'Current OS process census incomplete.' }
$actorChecks = @()
foreach ($actor in $actors) {
    $rows = @($live | Where-Object {$_.ProcessId -eq [int]$actor.pid})
    if ($rows.Count -gt 1) { throw 'Ambiguous current process generation.' }
    $creation = 0L
    if ($rows.Count -eq 1) {
        if ($null -eq $rows[0].CreationDate -or $rows[0].CreationDate -isnot [DateTime]) { throw 'Current process generation unavailable.' }
        $creation = $rows[0].CreationDate.ToUniversalTime().ToFileTimeUtc()
        if ([Math]::Abs([decimal]$creation-[decimal]$actor.creation) -le 10000000) { throw 'Original or indistinguishable actor remains live.' }
    }
    $actorChecks += ,@{pid=[int]$actor.pid;creation=[long]$actor.creation;current_creation=$creation;original_alive=$false}
}
foreach ($process in $live) {
    foreach ($root in $roots) {
        if (($process.ExecutablePath -and $process.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) -or
            ($process.CommandLine -and $process.CommandLine.IndexOf($root+'\',[StringComparison]::OrdinalIgnoreCase) -ge 0)) { throw 'Owned executable or argv still active.' }
    }
}
function Hash-Text([string]$Text) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
$actorJson = $actorChecks | ConvertTo-Json -Compress -Depth 5
$receipt = [ordered]@{nonce=$proof.nonce;manifest_sha256=$ManifestSha256;host_readback_sha256=$proof.host_readback_sha256;actor_checks_sha256=(Hash-Text $actorJson);actor_count=$actorChecks.Count;retired=@();all_scopes_absent=$false;retained_builds_verified=$false;foreign_resources_touched=$false;failure_sha256=('0'*64)}
$serial = [IO.Ports.SerialPort]::new('COM1',115200); $serial.WriteTimeout=2000
$failure = $null; $removed = @()
try {
    $serial.Open()
    $actorEncoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($actorJson))
    if ($actorEncoded.Length -gt 3500) { throw 'Actor receipt exceeds bounded serial frame; nothing deleted.' }
    $serial.WriteLine('RHAI_BACKEND_ACTORS '+$actorEncoded)
    try {
        foreach ($root in $roots) {
            Remove-Item -LiteralPath $root -Recurse -Force
            if (Test-Path -LiteralPath $root) { throw 'Exact own scope remains after removal.' }
            $removed += ,$root
        }
        Assert-RetainedBuilds
        $receipt.all_scopes_absent=$true; $receipt.retained_builds_verified=$true
    } catch { $failure=$_.Exception.ToString(); $receipt.failure_sha256=Hash-Text $failure }
    $receipt.retired=$removed
    $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt | ConvertTo-Json -Compress -Depth 5)))
    if ($encoded.Length -gt 3500) { throw 'Cleanup receipt exceeds bounded serial frame.' }
    $serial.WriteLine('RHAI_BACKEND_CLEANUP '+$encoded)
} finally { $serial.Dispose() }
$receipt | ConvertTo-Json -Compress -Depth 5
if ($failure) { throw $failure }
