param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference='Stop'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong cleanup owner.'}
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Actual host-accepted manifest differs.'}
$proof=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if(!$proof.accepted_for_cleanup -or $proof.nonce -cne '5fa1dfcc5d504bafa9f2219bf0f0fbca' -or $proof.scopes.Count -ne 7){throw 'Incomplete host acceptance.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$expectedLeaves=@('creation-build-5fa1dfcc5d504bafa9f2219bf0f0fbca','creation-control-0c8fb9dbbefb4d89a8988cc4803eef12','creation-control-4761e32fc7d04d779133ce983943dc52','creation-build-b72d8e60d49e490d9355925e9b379158','creation-control-92daebd4d1444f3087da0597e0791145','creation-build-50629a73efc34ced96046d9a8044fe40','creation-control-9d5034e5056b4d2ab163d43a31714868')
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
 if($scope.kind -ceq 'creation-control' -or $scope.kind -ceq 'failed-creation-control'){
  $o=Get-Content -LiteralPath (Join-Path $root 'observer.json') -Raw|ConvertFrom-Json
  if($o.id -cne $scope.id -or $o.scope -cne $root -or $o.profile -cne $scope.profile -or !$o.exact_driver_exited -or !$o.pipes_drained -or $o.retained_driver_handles -or $o.custody_pending -or $o.retained_log_resources -or !$o.process_disposed -or !$o.owned_executables_stopped -or !$o.runtime_retained -or $o.automatic_removal_claimed -or $o.parent_environment_changed){throw 'Incomplete native observer custody.'}
  if($scope.kind -ceq 'creation-control'){
   if(!$o.accepted -or !$scope.original_accepted -or !$o.protected_marker_sensitivity -or $o.native_trace.cleanup_error -cne 'False'){throw 'Accepted criterion not bound.'}
  }elseif($o.accepted -or $scope.original_accepted -or $o.native_trace.cleanup_error -cne 'True'){
   throw 'Failed-original classification changed; do not claim acceptance.'
  }
  if([IO.Path]::GetDirectoryName($scope.runtime) -cne (Join-Path $root 'run') -or [IO.Path]::GetFileName($scope.runtime) -notmatch '^scoped-[0-9a-f]{32}$' -or $o.allocated_runtime -cne $scope.runtime -or !(Test-Path -LiteralPath $scope.runtime -PathType Container)){throw 'Exact retained failed runtime changed.'}
  foreach($key in @('create_called','job_empty','process_closed_or_absent','thread_closed_or_absent','job_closed')){if($o.native_trace.$key -cne 'True'){throw 'Exact native unwind incomplete.'}}
  if($o.native_trace.transferred -cne 'False'){throw 'Native ownership was transferred.'}
  if([IO.File]::ReadAllText((Join-Path $scope.runtime 'must-not-run.txt')) -cne "protected-before-failed-association`r`n"){throw 'Protected original changed.'}
  if($scope.profile -ceq 'ASSOCIATION_DENIED'){
   if(!$o.accepted -or $o.actor_stopped -or $o.actor_disposition -cne 'no_handles_returned_job_empty' -or $o.native_trace.create_succeeded -cne 'False' -or $o.native_trace.create_error -cne '5' -or $o.native_trace.process_returned -cne 'False' -or $o.native_trace.thread_returned -cne 'False' -or $o.native_trace.query_duplicate_closed -cne 'True'){throw 'Native failed-association disposition invalid.'}
  }elseif($scope.profile -ceq 'POST_CREATE_ABORT'){
   if($o.native_trace.create_succeeded -cne 'True' -or $o.native_trace.process_returned -cne 'True' -or $o.native_trace.thread_returned -cne 'True' -or $o.native_trace.process_id -cne $scope.trace.process_id -or $o.native_trace.creation -cne $scope.trace.creation -or $scope.trace.process_id -notmatch '^[1-9][0-9]*$' -or $scope.trace.creation -notmatch '^[1-9][0-9]*$'){throw 'Exact returned-root identity invalid.'}
   if($o.accepted -and (!$o.actor_stopped -or $o.actor_disposition -cne 'exact_pid_start_stopped' -or $o.native_trace.root_termination_failed -cne 'True' -or $o.native_trace.root_signaled_after_termination_failure -cne 'True')){throw 'Accepted stopped-root branch missing.'}
   $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById([int]$scope.trace.process_id)}catch [ArgumentException]{}
   $recycled=$false
   if($null -ne $actor){try{if(!$actor.HasExited){if($actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$scope.trace.creation){throw 'Exact original root remains live.'};$recycled=$true}}finally{$actor.Dispose()}}
   $actorChecks+=,@{pid=$scope.trace.process_id;creation=$scope.trace.creation;original_alive=$false;pid_recycled=$recycled}
  }else{throw 'Unknown failure profile.'}
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
$receipt=[ordered]@{nonce=$proof.nonce;host_manifest_sha256=$ManifestSha256;host_receipt_sha256=$proof.host_receipt_sha256;retained_build=$retained;retained_build_preserved=$true;actor_checks=$actorChecks;failed_originals_exported=$true;retired=$roots;all_scopes_absent=$true;foreign_resources_touched=$false}
$encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress -Depth 5)))
if($encoded.Length -gt 3500){throw 'Cleanup receipt too large.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000
try{$serial.Open();$serial.WriteLine('RHAI_CREATION_CLEANUP '+$encoded)}finally{$serial.Dispose()}
$receipt|ConvertTo-Json -Compress -Depth 5
