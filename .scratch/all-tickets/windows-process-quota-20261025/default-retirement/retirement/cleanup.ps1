param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference='Stop'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong cleanup owner.'}
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Actual host-accepted manifest differs.'}
$proof=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
if(!$proof.accepted_for_cleanup -or $proof.nonce -cne '278b19c6e05ac1725763aa778e031945' -or $proof.scopes.Count -ne 1 -or !$proof.no_other_scopes -or !$proof.originals_exported -or $proof.native_reexecution){throw 'Incomplete host acceptance.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$expectedLeaves=@('quota-build-e6ce6222dba147a8b43b2c79187d3184')
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
 if($scope.kind -ceq 'completed-build'){
  $o=Get-Content -LiteralPath (Join-Path $root 'build-observer.json') -Raw|ConvertFrom-Json
  if($o.id -cne $scope.id -or $o.session -cne $root -or $o.input_manifest_sha256 -cne $scope.input_manifest_sha256 -or $o.start_sha256 -cne $scope.start_sha256 -or !$o.accepted -or !$o.native_started -or $o.custody_indeterminate -or $o.exit -ne 0){throw 'Native build custody/provenance incomplete.'}
  if((Get-FileHash -LiteralPath (Join-Path $o.run 'build-manifest.txt')).Hash.ToLowerInvariant() -cne $scope.build_manifest_sha256){throw 'Compiled manifest differs from exported source.'}
  foreach($pin in $scope.binary_pins.PSObject.Properties){if((Get-FileHash -LiteralPath (Join-Path (Join-Path $o.run 'build') $pin.Name)).Hash.ToLowerInvariant() -cne $pin.Value){throw 'Original public binary pin changed.'}}
  $creation=[DateTime]::Parse($o.process_start_utc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime().ToFileTimeUtc()
  $recordedActors+=,@{pid=[int]$o.process_id;creation=$creation}
 }else{throw 'Unknown own default-build scope kind.'}
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
function Hash-Text([string]$Text){$sha=[Security.Cryptography.SHA256]::Create();try{return [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}}
$actorJson=$actorChecks|ConvertTo-Json -Compress -Depth 5
$actorHash=Hash-Text $actorJson
$receipt=[ordered]@{nonce=$proof.nonce;manifest_sha256=$ManifestSha256;host_receipt_sha256=$proof.host_receipt_sha256;actor_check_count=$actorChecks.Count;actor_checks_sha256=$actorHash;retired=$roots;all_scopes_absent=$false;original_build_retired=$false;foreign_resources_touched=$false;failure_sha256=('0'*64)}
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
 for($index=0;$index -lt $chunks;$index++){$start=$index*3000;$length=[Math]::Min(3000,$actorEncoded.Length-$start);$serial.WriteLine('RHAI_DEFAULT_BUILD_ACTOR_CHECKS '+$index+' '+$chunks+' '+$actorEncoded.Substring($start,$length))}
 try{
  foreach($root in $roots){Remove-Item -LiteralPath $root -Recurse -Force;if(Test-Path -LiteralPath $root){throw 'Exact own scope remains.'};$removed+=,$root}
  $receipt.all_scopes_absent=$true;$receipt.original_build_retired=$true
 }catch{$failure=$_.Exception.ToString();$receipt.failure_sha256=Hash-Text $failure}
 $receipt.retired=$removed
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress -Depth 5)))
 if($encoded.Length -gt 3500){throw 'Cleanup receipt exceeded validated cap.'}
 $serial.WriteLine('RHAI_DEFAULT_BUILD_CLEANUP '+$encoded)
}finally{$serial.Dispose()}
$receipt|ConvertTo-Json -Compress -Depth 5
if($failure){throw $failure}
