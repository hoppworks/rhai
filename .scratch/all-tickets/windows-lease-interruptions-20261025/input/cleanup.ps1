# Consume the hash-pinned host validation report before retiring original evidence.
param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$HostReceiptSha256)
$ErrorActionPreference='Stop'
if((Get-FileHash -LiteralPath 'E:\bindings.json').Hash.ToLowerInvariant() -cne 'e9bdcbe82ea9ef2d9496e8252a5ffccaaff9cd2ea0eff454c9ee2bda0d45b363'){throw 'Cleanup binding differs.'}
if((Get-FileHash -LiteralPath 'E:\host-accepted-readback.json').Hash.ToLowerInvariant() -cne $HostReceiptSha256){throw 'Host validation receipt differs.'}
$b=Get-Content -LiteralPath 'E:\bindings.json' -Raw | ConvertFrom-Json
$hostProof=Get-Content -LiteralPath 'E:\host-accepted-readback.json' -Raw | ConvertFrom-Json
if(!$hostProof.semantic_accepted -or $hostProof.batch_id -cne $b.batch_id -or $hostProof.cases.Count -ne 3){throw 'Host validation is incomplete.'}
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong cleanup owner.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai';$scopes=@()
foreach($case in $b.cases){
 $scope=Join-Path $private $case.scope_leaf
 if([IO.Directory]::GetParent($scope).FullName -cne $private -or $case.scope_leaf -notmatch '^custody-(disconnect-alive|client-death|replay)-[0-9a-f]{12}$'){throw 'Foreign cleanup scope refused.'}
 $proofs=@($hostProof.cases|Where-Object {$_.id -ceq $case.id});if($proofs.Count -ne 1){throw 'Missing exact host case.'};$proof=$proofs[0]
 $allowed=@{};$dirs=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
 foreach($entry in $proof.files.PSObject.Properties){
  $relative=$entry.Name.Replace('/','\')
  if([IO.Path]::IsPathRooted($relative) -or $relative.Contains(':') -or $relative.Split([char[]]@('\','/')) -contains '..'){throw 'Invalid exported path.'}
  $full=[IO.Path]::GetFullPath((Join-Path $scope $relative));if(!$full.StartsWith($scope+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Foreign exported path.'}
  if($allowed.ContainsKey($full)){throw 'Ambiguous exported path.'};$allowed[$full]=$entry.Value.sha256
 }
 $allowed[(Join-Path $scope 'input\fixture.exe')]=$b.binaries.'PayloadFixture.exe'
 foreach($file in @($allowed.Keys)){$cursor=[IO.Path]::GetDirectoryName($file);while($cursor -and $cursor -cne $scope){$null=$dirs.Add($cursor);$cursor=[IO.Path]::GetDirectoryName($cursor)}}
 $cursor=$scope
 while($cursor){if((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse ancestor.'};$parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}}
 $entries=@(Get-ChildItem -LiteralPath $scope -Force -Recurse)
 if($entries.Count -gt 256 -or @($entries|Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count -ne 0){throw 'Unexpected cleanup inventory.'}
 foreach($entry in $entries){
  if($entry.PSIsContainer){if(!$dirs.Contains($entry.FullName)){throw 'Unexported directory; preserve it.'}}
  elseif(!$allowed.ContainsKey($entry.FullName) -or $entry.Length -gt 4MB -or (Get-FileHash -LiteralPath $entry.FullName).Hash.ToLowerInvariant() -cne $allowed[$entry.FullName]){throw 'Unexported/changed file; preserve it.'}
 }
 foreach($file in @($allowed.Keys)){if(!(Test-Path -LiteralPath $file -PathType Leaf)){throw 'Exported file absent.'}}
 if(($entries|Where-Object {!$_.PSIsContainer}|Measure-Object Length -Sum).Sum -gt 32MB){throw 'Unexpected cleanup size.'}
 $o=Get-Content -LiteralPath (Join-Path $scope 'observer.json') -Raw | ConvertFrom-Json
 if($o.id -cne $case.id -or $o.scope -cne $scope -or !$o.accepted -or $o.exit -ne 0 -or !$o.exact_driver_exited -or !$o.pipes_drained -or $o.retained_driver_handles -or !$o.fresh_host_record -or !$o.wrong_expectation_red -or !$o.payload_stopped_readback -or !$o.runtime_absent_readback -or !$o.runtime_absence_negative_control){throw 'Open/foreign/incomplete control custody.'}
 if([IO.Path]::GetDirectoryName($o.allocated_runtime) -cne (Join-Path $scope 'run') -or [IO.Path]::GetFileName($o.allocated_runtime) -notmatch '^scoped-[0-9a-f]{32}$' -or (Test-Path -LiteralPath $o.allocated_runtime)){throw 'Actual runtime remains.'}
 $process=$null;try{$process=[Diagnostics.Process]::GetProcessById([int]$o.payload_pid)}catch [ArgumentException]{}
 if($null -ne $process){try{if(!$process.HasExited -and $process.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$o.payload_creation){throw 'Original payload identity still live.'}}finally{$process.Dispose()}}
 $scopes+=,$scope
}
foreach($scope in $scopes){Remove-Item -LiteralPath $scope -Recurse -Force}
foreach($scope in $scopes){if(Test-Path -LiteralPath $scope){throw 'Control scope remains.'}}
$receipt=[ordered]@{batch=$b.batch_id;host_receipt_sha256=$HostReceiptSha256;retired=$scopes;retained_build_touched=$false;all_scopes_absent=$true}
$json=$receipt|ConvertTo-Json -Compress -Depth 4;$encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json));if($encoded.Length -gt 3500){throw 'Cleanup receipt too large.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000
try{$serial.Open();$serial.WriteLine('RHAI_CUSTODY_CLEANUP '+$encoded)}finally{$serial.Dispose()}
Write-Output $json
