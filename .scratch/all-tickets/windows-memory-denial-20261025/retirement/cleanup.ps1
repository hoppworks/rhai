param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference='Stop'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong cleanup owner.'}
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Actual host-accepted manifest differs.'}
$proof=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if(!$proof.accepted_for_cleanup -or $proof.nonce -cne '197434e7a73dd8d7f20fd2f296895dce' -or $proof.scopes.Count -ne 2){throw 'Incomplete host acceptance.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$expectedLeaves=@('env-control-b6391212cbfa4d38a24bc8bb3b3583ac','memory-fixture-63a597390756484cbc31eb5c9bdeff3d')
$actorChecks=@();$recordedActors=@();$roots=@();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($scope in $proof.scopes){
 $root=[IO.Path]::GetFullPath($scope.scope)
 if([IO.Path]::GetDirectoryName($root) -cne $private -or $expectedLeaves -cnotcontains [IO.Path]::GetFileName($root) -or !$seen.Add($root)){throw 'Unexpected/duplicate cleanup root.'}
 $cursor=$root
 while($cursor){if((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse ancestor.'};$parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}}
 $allowed=@{};$dirs=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
 foreach($entry in $scope.files.PSObject.Properties){
  $relative=$entry.Name.Replace('/','\')
  if([IO.Path]::IsPathRooted($relative) -or $relative.Contains(':') -or $relative.Split([char[]]@('\','/')) -contains '..' -or $entry.Value -cnotmatch '^[0-9a-f]{64}$'){throw 'Invalid expected disposable file.'}
  $full=[IO.Path]::GetFullPath((Join-Path $root $relative))
  if(!$full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or $allowed.ContainsKey($full)){throw 'Foreign/ambiguous file.'}
  $allowed[$full]=$entry.Value
  $cursor=[IO.Path]::GetDirectoryName($full);while($cursor -cne $root){$null=$dirs.Add($cursor);$cursor=[IO.Path]::GetDirectoryName($cursor)}
 }
 foreach($relative in $scope.empty_dirs){$full=[IO.Path]::GetFullPath((Join-Path $root $relative));if(!$full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid owned empty directory.'};$null=$dirs.Add($full)}
 $entries=@(Get-ChildItem -LiteralPath $root -Recurse -Force)
 if($entries.Count -gt 256 -or @($entries|Where-Object{$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count -ne 0){throw 'Unexpected scope inventory.'}
 foreach($entry in $entries){
  if($entry.PSIsContainer){if(!$dirs.Contains($entry.FullName)){throw 'Unexported directory; preserve it.'}}
  elseif(!$allowed.ContainsKey($entry.FullName) -or $entry.Length -gt 4MB -or (Get-FileHash -LiteralPath $entry.FullName).Hash.ToLowerInvariant() -cne $allowed[$entry.FullName]){throw 'Unknown/changed file; preserve it.'}
 }
 foreach($file in @($allowed.Keys)){if(!(Test-Path -LiteralPath $file -PathType Leaf)){throw 'Expected disposable file absent.'}}
 if(($entries|Where-Object{!$_.PSIsContainer}|Measure-Object Length -Sum).Sum -gt 32MB){throw 'Unexpected cleanup bytes.'}
 if($scope.kind -ceq 'completed-control'){
  $o=Get-Content -LiteralPath (Join-Path $root 'observer.json') -Raw|ConvertFrom-Json
  if($o.id -cne $scope.id -or $o.scope -cne $root -or $o.contract -cne $scope.contract -or $o.accepted -ne $scope.expected_accepted -or !$o.exact_driver_exited -or !$o.pipes_drained -or $o.retained_driver_handles -or $o.custody_pending -or !$o.process_disposed -or !$o.owned_executables_stopped -or $o.parent_environment_changed -or !$o.memory_actors_stopped -or !$o.job_memory_green -or !$o.job_memory_sensitivity){throw 'Completed control custody/provenance differs.'}
  if((Test-Path -LiteralPath $scope.runtime) -or [IO.Path]::GetDirectoryName($scope.runtime) -cne (Join-Path $root 'run') -or [IO.Path]::GetFileName($scope.runtime) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Exact completed runtime absence changed.'}
  $recordedActors+=@($scope.actors)
 }elseif($scope.kind -ceq 'completed-build'){
  $o=Get-Content -LiteralPath (Join-Path $root 'build-observer.json') -Raw|ConvertFrom-Json
  if($o.id -cne $scope.id -or !$o.accepted -or !$o.native_started -or $o.custody_indeterminate -or $o.exit -ne 0){throw 'Native build custody/provenance incomplete.'}
  $creation=[DateTime]::Parse($o.process_start_utc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime().ToFileTimeUtc()
  $recordedActors+=,@{pid=[int]$o.process_id;creation=$creation}
 }else{throw 'Unknown own memory scope kind.'}
 $roots+=,$root
}
# Query the supported OS process census once. PowerShell property adapters can
# return null for Process.StartTime; null/unknown metadata is never stopped proof.
$liveProcesses=@(Get-CimInstance Win32_Process)
if($liveProcesses.Count -lt 1 -or @($liveProcesses|Where-Object{$_.ProcessId -eq $PID}).Count -ne 1){throw 'OS process census is incomplete.'}
foreach($pair in $recordedActors){
 $rows=@($liveProcesses|Where-Object{$_.ProcessId -eq [int]$pair.pid})
 if($rows.Count -gt 1){throw 'Ambiguous current process generation.'}
 $observedCreation=0L;$recycled=$false
 if($rows.Count -eq 1){
  if($null -eq $rows[0].CreationDate -or $rows[0].CreationDate -isnot [DateTime]){throw 'Current process creation unavailable; preserve all roots.'}
  $observedCreation=$rows[0].CreationDate.ToUniversalTime().ToFileTimeUtc()
  # CIM datetime precision need not preserve the original 100ns remainder.
  # A full-second ambiguity window is conservative: near matches fail closed.
  if([Math]::Abs([decimal]$observedCreation-[decimal]$pair.creation) -le 10000000){throw 'Original or indistinguishable actor generation still present.'}
  $recycled=$true
 }
 $actorChecks+=,@{pid=[int]$pair.pid;creation=[long]$pair.creation;observed_creation=$observedCreation;original_alive=$false;pid_recycled=$recycled;source='Win32_Process current census'}
}
foreach($process in $liveProcesses){
 foreach($root in $roots){if(($process.ExecutablePath -and $process.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) -or ($process.CommandLine -and $process.CommandLine.IndexOf($root+'\',[StringComparison]::OrdinalIgnoreCase) -ge 0)){throw 'Owned executable/argv still active; preserve all scopes.'}}
}
# Retained compatible tools are siblings, never deletion targets.
$retained=$proof.retained
if($retained.scope -cne 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\quota-build-e6ce6222dba147a8b43b2c79187d3184' -or $roots -contains $retained.scope){throw 'Wrong retained default scope.'}
$retainedManifest=Join-Path ([IO.Directory]::GetParent($retained.build).FullName) 'build-manifest.txt'
function Assert-RetainedTools {
 $cursor=$retainedManifest
 while($cursor){if((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Retained path became a reparse point.'};$parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}}
 if((Get-FileHash -LiteralPath $retainedManifest).Hash.ToLowerInvariant() -cne $proof.retained_manifest_sha256){throw 'Retained manifest changed.'}
 $lines=[IO.File]::ReadAllLines($retainedManifest);$pins=@($retained.binaries.PSObject.Properties)
 if($pins.Count -ne 3 -or (($pins.Name|Sort-Object)-join ',') -cne 'MonitorAcceptanceDriver.exe,PayloadFixture.exe,ScopedRunner.exe'){throw 'Unexpected retained binary inventory.'}
 foreach($pin in $pins){
  $file=[IO.Path]::GetFullPath((Join-Path $retained.build $pin.Name))
  if([IO.Path]::GetDirectoryName($file) -cne [IO.Path]::GetFullPath($retained.build) -or $pin.Value -cnotmatch '^[0-9a-f]{64}$' -or @($lines|Where-Object{$_ -ceq ($pin.Value+'  build/'+$pin.Name)}).Count -ne 1 -or ((Get-Item -LiteralPath $file -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -or (Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $pin.Value){throw 'Retained binary path/pin differs from exact build.'}
 }
}
Assert-RetainedTools
function Hash-Text([string]$Text){$sha=[Security.Cryptography.SHA256]::Create();try{return [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}}
$actorJson=$actorChecks|ConvertTo-Json -Compress -Depth 5
$actorHash=Hash-Text $actorJson
$receipt=[ordered]@{nonce=$proof.nonce;manifest_sha256=$ManifestSha256;host_receipt_sha256=$proof.host_receipt_sha256;actor_check_count=$actorChecks.Count;actor_checks_sha256=$actorHash;retired=$roots;all_scopes_absent=$false;retained_scope_leaf=[IO.Path]::GetFileName($retained.scope);retained_manifest_sha256=$proof.retained_manifest_sha256;retained_verified=$false;foreign_resources_touched=$false;failure_sha256=('0'*64)}
$preview=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress -Depth 5)))
if($preview.Length -gt 3500 -or [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($actorJson)).Length -gt 96000){throw 'Cleanup metadata would exceed cap; nothing deleted.'}
$actorEncoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($actorJson));$chunks=[int][Math]::Ceiling($actorEncoded.Length/3000.0)
if($chunks -gt 32){throw 'Actor metadata export exceeds bound; nothing deleted.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000
$removed=@();$failure=$null
try{
 # Export fresh identity proof before any removal. Open/write failure leaves
 # every validated root intact; the final receipt follows actual deletion.
 $serial.Open()
 for($index=0;$index -lt $chunks;$index++){$start=$index*3000;$length=[Math]::Min(3000,$actorEncoded.Length-$start);$serial.WriteLine('RHAI_MEMORY_ACTOR_CHECKS '+$index+' '+$chunks+' '+$actorEncoded.Substring($start,$length))}
 try{
  foreach($root in $roots){Remove-Item -LiteralPath $root -Recurse -Force;if(Test-Path -LiteralPath $root){throw 'Exact own scope remains.'};$removed+=,$root}
  Assert-RetainedTools
  $receipt.all_scopes_absent=$true;$receipt.retained_verified=$true
 }catch{$failure=$_.Exception.ToString();$receipt.failure_sha256=Hash-Text $failure}
 $receipt.retired=$removed
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress -Depth 5)))
 if($encoded.Length -gt 3500){throw 'Cleanup receipt exceeded validated cap.'}
 $serial.WriteLine('RHAI_MEMORY_CLEANUP '+$encoded)
}finally{$serial.Dispose()}
$receipt|ConvertTo-Json -Compress -Depth 5
if($failure){throw $failure}
