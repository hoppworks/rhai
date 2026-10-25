param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference='Stop'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong cleanup owner.'}
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Actual host-accepted manifest differs.'}
$proof=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if(!$proof.accepted_for_cleanup -or $proof.nonce -cne '48d19d95797f4b4f84f6962bac3f955c' -or $proof.scopes.Count -ne 9){throw 'Incomplete host acceptance.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$expectedLeaves=@('env-control-911a10854db94505b29817e3720d551f','env-control-50a587ef233d4b54a1586bf029a426e9','env-control-b8761d9bb62643179a967b942e6bc3a3','env-control-45c8571772d5463eb5e4ca442df4b979','env-control-1ad6339a9548413db5ce9f948ff63aaa','env-control-55e61c971bf447f7a2e1332a66375ca3','quota-fixture-c8d7629099fd47d1b6f10ef65649db5e','quota-fixture-61233f37b1ce4ddc847ba9b8ff2a14ed','quota-fixture-48d19d95797f4b4f84f6962bac3f955c')
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
 if($scope.kind -ceq 'completed-control'){
  $o=Get-Content -LiteralPath (Join-Path $root 'observer.json') -Raw|ConvertFrom-Json
  if($o.id -cne $scope.id -or $o.scope -cne $root -or $o.contract -cne $scope.contract -or $o.accepted -ne $scope.expected_accepted -or !$o.exact_driver_exited -or !$o.pipes_drained -or $o.retained_driver_handles -or $o.custody_pending -or !$o.process_disposed -or !$o.owned_executables_stopped -or $o.parent_environment_changed){throw 'Completed control custody/provenance differs.'}
  if((Test-Path -LiteralPath $scope.runtime) -or [IO.Path]::GetDirectoryName($scope.runtime) -cne (Join-Path $root 'run') -or [IO.Path]::GetFileName($scope.runtime) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Exact completed runtime absence changed.'}
  foreach($pair in @($scope.actors)){
   $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById([int]$pair.pid)}catch [ArgumentException]{}
   $recycled=$false
   if($null -ne $actor){try{if(!$actor.HasExited){if($actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$pair.creation){throw 'Exact recorded own actor still live.'};$recycled=$true}}finally{$actor.Dispose()}}
   $actorChecks+=,@{pid=$pair.pid;creation=$pair.creation;original_alive=$false;pid_recycled=$recycled}
  }
 }elseif($scope.kind -ceq 'completed-build'){
  $o=Get-Content -LiteralPath (Join-Path $root 'build-observer.json') -Raw|ConvertFrom-Json
  if($o.id -cne $scope.id -or !$o.accepted -or !$o.native_started -or $o.custody_indeterminate -or $o.exit -ne 0){throw 'Native build custody/provenance incomplete.'}
  $owner=$null;try{$owner=[Diagnostics.Process]::GetProcessById([int]$o.process_id)}catch [ArgumentException]{}
  if($null -ne $owner){try{if(!$owner.HasExited -and $owner.StartTime.ToUniversalTime().ToString('o') -ceq $o.process_start_utc){throw 'Exact native build owner still live.'}}finally{$owner.Dispose()}}
 }else{throw 'Unknown own quota scope kind.'}
 $roots+=,$root
}
foreach($process in @(Get-CimInstance Win32_Process)){
 foreach($root in $roots){if(($process.ExecutablePath -and $process.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) -or ($process.CommandLine -and $process.CommandLine.IndexOf($root+'\',[StringComparison]::OrdinalIgnoreCase) -ge 0)){throw 'Owned binary still executing; preserve all scopes.'}}
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
$actorHash=Hash-Text ($actorChecks|ConvertTo-Json -Compress -Depth 5)
$receipt=[ordered]@{nonce=$proof.nonce;manifest_sha256=$ManifestSha256;host_receipt_sha256=$proof.host_receipt_sha256;actor_check_count=$actorChecks.Count;actor_checks_sha256=$actorHash;retired=$roots;all_scopes_absent=$false;retained_scope_leaf=[IO.Path]::GetFileName($retained.scope);retained_manifest_sha256=$proof.retained_manifest_sha256;retained_verified=$false;foreign_resources_touched=$false;failure_sha256=('0'*64)}
$preview=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress -Depth 5)))
if($preview.Length -gt 3500){throw 'Cleanup receipt would exceed cap; nothing deleted.'}
$removed=@();$failure=$null
try{
 foreach($root in $roots){Remove-Item -LiteralPath $root -Recurse -Force;if(Test-Path -LiteralPath $root){throw 'Exact own scope remains.'};$removed+=,$root}
 Assert-RetainedTools
 $receipt.all_scopes_absent=$true;$receipt.retained_verified=$true
}catch{$failure=$_.Exception.ToString();$receipt.failure_sha256=Hash-Text $failure}
$receipt.retired=$removed
$encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress -Depth 5)))
if($encoded.Length -gt 3500){throw 'Cleanup receipt exceeded validated cap.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000
try{$serial.Open();$serial.WriteLine('RHAI_QUOTA_CLEANUP '+$encoded)}finally{$serial.Dispose()}
$receipt|ConvertTo-Json -Compress -Depth 5
if($failure){throw $failure}
