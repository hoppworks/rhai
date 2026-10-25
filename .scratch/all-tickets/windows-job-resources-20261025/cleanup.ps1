param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference='Stop'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong cleanup owner.'}
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Actual host-accepted manifest differs.'}
$proof=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if(!$proof.accepted_for_cleanup -or $proof.nonce -cne '4b6f1af18783499eba100bef0e0a4930' -or $proof.scopes.Count -ne 4){throw 'Incomplete host acceptance.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$expectedLeaves=@('job-resource-build-red-4b6f1af18783499eba100bef0e0a4930','env-control-4b6f1af18783499eba100bef0e0a4930','env-control-cdcd7eebb7ec4c89b8aa2f9e8f2054f4','env-control-3851f0f9a4274b59a0d9cb8fdb06c40b')
$roots=@();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
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
 if($scope.kind -ceq 'job-resources-control' -or $scope.kind -ceq 'environment-control'){
  $o=Get-Content -LiteralPath (Join-Path $root 'observer.json') -Raw|ConvertFrom-Json
  if(!$o.accepted -or $o.id -cne $scope.id -or $o.scope -cne $root -or !$o.exact_driver_exited -or !$o.pipes_drained -or $o.retained_driver_handles -or !$o.runtime_absent_readback -or !$o.runtime_absence_negative_control -or $o.parent_environment_changed -or $o.contract -cne $scope.contract -or $o.phase -cne $scope.phase){throw 'Incomplete native control closure.'}
  if($scope.kind -ceq 'job-resources-control'){
   if(!$o.job_actors_stopped -or $scope.identities.Count -lt 1 -or ($o.phase -ceq 'RED' -and !$o.job_resources_red) -or ($o.phase -ceq 'GREEN' -and (!$o.job_resources_green -or !$o.job_resources_sensitivity -or $scope.identities.Count -ne 2))){throw 'Native resource criterion/readback missing.'}
  }elseif(!$o.environment_contract_green){throw 'Environment criterion missing.'}
  if([IO.Path]::GetDirectoryName($scope.runtime) -cne (Join-Path $root 'run') -or [IO.Path]::GetFileName($scope.runtime) -notmatch '^scoped-[0-9a-f]{32}$' -or (Test-Path -LiteralPath $scope.runtime)){throw 'Actual runtime remains.'}
  foreach($identity in $scope.identities){
   $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById([int]$identity.pid)}catch [ArgumentException]{}
   if($null -ne $actor){try{if(!$actor.HasExited -and $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$identity.creation){throw 'Exact actor still live.'}}finally{$actor.Dispose()}}
  }
 }elseif($scope.kind -ceq 'completed-build'){
  $o=Get-Content -LiteralPath (Join-Path $root 'build-observer.json') -Raw|ConvertFrom-Json
  if(!$o.accepted -or !$o.native_started -or $o.custody_indeterminate -or $o.exit -ne 0){throw 'Original build custody incomplete.'}
 }else{throw 'Unknown scope kind.'}
 $roots+=,$root
}
# Read-only exact path matching. Do not kill or mutate any process found here.
foreach($process in @(Get-CimInstance Win32_Process)){
 foreach($root in $roots){if($process.ExecutablePath -and $process.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Owned binary still executing; preserve all scopes.'}}
}
$retained=[IO.Path]::GetFullPath($proof.retain.scope)
if($roots -contains $retained -or [IO.Path]::GetDirectoryName($retained) -cne $private -or [IO.Path]::GetFileName($retained) -cne 'job-resource-build-green-cdcd7eebb7ec4c89b8aa2f9e8f2054f4'){throw 'Retained current build must remain separate.'}
foreach($entry in $proof.retain.binaries.PSObject.Properties){$file=Join-Path $proof.retain.build $entry.Name;if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $entry.Value){throw 'Retained current binary changed.'}}
foreach($root in $roots){Remove-Item -LiteralPath $root -Recurse -Force}
foreach($root in $roots){if(Test-Path -LiteralPath $root){throw 'Owned scope remains.'}}
if(!(Test-Path -LiteralPath $retained -PathType Container)){throw 'Retained build absent.'}
$receipt=[ordered]@{nonce=$proof.nonce;host_manifest_sha256=$ManifestSha256;host_receipt_sha256=$proof.host_receipt_sha256;retained_build=$retained;retained_build_preserved=$true;retired=$roots;all_scopes_absent=$true;foreign_resources_touched=$false}
$encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress -Depth 5)))
if($encoded.Length -gt 3500){throw 'Cleanup receipt too large.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000
try{$serial.Open();$serial.WriteLine('RHAI_JOB_RESOURCE_CLEANUP '+$encoded)}finally{$serial.Dispose()}
$receipt|ConvertTo-Json -Compress -Depth 5
