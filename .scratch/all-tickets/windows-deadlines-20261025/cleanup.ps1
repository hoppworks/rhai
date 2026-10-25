param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference='Stop'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong cleanup owner.'}
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Actual host-accepted manifest differs.'}
$proof=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if(!$proof.accepted_for_cleanup -or $proof.nonce -cne '4c3d5d7636d642529e5c02ecd3d6c188' -or $proof.scopes.Count -ne 4){throw 'Incomplete host acceptance.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$expectedLeaves=@('deadline-build-4c3d5d7636d642529e5c02ecd3d6c188','deadline-control-f11d200d497f4cafbf61eaa88701819c','deadline-control-e8b0c81f1f9448d78dae7dd0bfd96b4a','deadline-control-2b784c5369ce4e2d8b51391433fd0d7e')
$actorChecks=@();$roots=@();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
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
 if($scope.kind -ceq 'accepted-control'){
  $o=Get-Content -LiteralPath (Join-Path $root 'observer.json') -Raw|ConvertFrom-Json
  if($o.id -cne $scope.id -or $o.scope -cne $root -or $o.mode -cne $scope.mode -or !$o.accepted -or !$o.exact_driver_exited -or !$o.pipes_drained -or $o.retained_driver_handles -or $o.custody_pending -or !$o.process_disposed -or !$o.owned_executables_stopped -or !$o.actors_stopped -or !$o.runtime_absent_readback -or $o.parent_environment_changed){throw 'Incomplete accepted native deadline observer.'}
  if((Test-Path -LiteralPath $o.allocated_runtime) -or [IO.Path]::GetDirectoryName($o.allocated_runtime) -cne (Join-Path $root 'run') -or [IO.Path]::GetFileName($o.allocated_runtime) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Accepted exact runtime absence changed.'}
  foreach($pair in @($scope.actors)){
   $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById([int]$pair.pid)}catch [ArgumentException]{}
   $recycled=$false
   if($null -ne $actor){try{if(!$actor.HasExited){if($actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$pair.creation){throw 'Accepted exact actor still live.'};$recycled=$true}}finally{$actor.Dispose()}}
   $actorChecks+=,@{pid=$pair.pid;creation=$pair.creation;original_alive=$false;pid_recycled=$recycled}
  }
 }elseif($scope.kind -ceq 'completed-build'){
  $o=Get-Content -LiteralPath (Join-Path $root 'build-observer.json') -Raw|ConvertFrom-Json
  if(!$o.accepted -or !$o.native_started -or $o.custody_indeterminate -or $o.exit -ne 0){throw 'Original native build custody incomplete.'}
 }elseif($scope.kind -ceq 'interrupted-control'){
  $boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToFileTimeUtc()
  if($scope.native_removal_claimed -or $boot -lt [long]$scope.boot_filetime -or [long]$scope.old_driver_creation -ge [long]$scope.boot_filetime){throw 'Interrupted original must predate the proven new kernel lifetime.'}
  $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById([int]$scope.old_driver_pid)}catch [ArgumentException]{}
  if($null -ne $actor){try{if(!$actor.HasExited -and $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$scope.old_driver_creation){throw 'Exact interrupted driver still live.'}}finally{$actor.Dispose()}}
 }else{throw 'Unknown deadline scope kind.'}
 $roots+=,$root
}
foreach($process in @(Get-CimInstance Win32_Process)){
 foreach($root in $roots){if($process.ExecutablePath -and $process.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Owned binary still executing; preserve all scopes.'}}
}
foreach($root in $roots){Remove-Item -LiteralPath $root -Recurse -Force}
foreach($root in $roots){if(Test-Path -LiteralPath $root){throw 'Owned deadline scope remains.'}}
$receipt=[ordered]@{nonce=$proof.nonce;host_manifest_sha256=$ManifestSha256;host_receipt_sha256=$proof.host_receipt_sha256;interrupted_originals_sha256=$proof.interrupted_originals_sha256;actor_checks=$actorChecks;interrupted_originals_exported=$true;retired=$roots;all_scopes_absent=$true;foreign_resources_touched=$false;interrupted_runtime_retirement='observer retirement after boot, not native automatic cleanup acceptance'}
$encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress -Depth 5)))
if($encoded.Length -gt 3500){throw 'Deadline cleanup receipt too large.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000
try{$serial.Open();$serial.WriteLine('RHAI_DEADLINE_CLEANUP '+$encoded)}finally{$serial.Dispose()}
$receipt|ConvertTo-Json -Compress -Depth 5
