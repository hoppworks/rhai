param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference='Stop'
$nonce='49243ecf52d64c609a876e3c52409500'
$manifestPath='E:\cleanup-host-manifest.json'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest' -or $env:USERNAME -cne 'RhaiTest'){throw 'Wrong native cleanup owner.'}
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Host-accepted cleanup manifest changed.'}
$proof=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$root=Join-Path $private ('project-control-'+$nonce)
if(!$proof.accepted_for_cleanup -or $proof.nonce -cne $nonce -or
   $proof.id -cne ('rhai-project-command-'+$nonce) -or $proof.scope -cne $root -or
   $proof.independent_verification_sha256 -cne '81b0eb8227101350ac192ffc0cec3c315dbbbe9aba24b2be40d99049ff6587f1' -or
   $proof.export_readback_sha256 -cne 'b74df0b103e1c7103d12b5c0155acc323983096e5e18022c7d77b77d3b717f83' -or
   $proof.evidence_manifest_sha256 -cne '5e550ac07d19bccf6157fbc25eabc34a46da697f95c1bbaa059bf76787b17cfc' -or
   $proof.evidence_snapshot_files -ne 438 -or
   $proof.max_files -ne 888 -or $proof.max_entries -ne 1100 -or $proof.max_bytes -ne 67108864 -or
   @($proof.files.PSObject.Properties).Count -ne 888){throw 'Cleanup contract differs.'}
$cursor=[IO.Path]::GetFullPath($root)
while($cursor){
 if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse ancestor refused.'}
 $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
}
if(!(Test-Path -LiteralPath $root -PathType Container)){throw 'Exact own scope absent.'}
$observerPath=Join-Path $root 'observer.json'
if((Get-FileHash -LiteralPath $observerPath).Hash.ToLowerInvariant() -cne $proof.observer_sha256){throw 'Accepted original observer changed.'}
$observer=Get-Content -LiteralPath $observerPath -Raw|ConvertFrom-Json
if($observer.id -cne $proof.id -or !$observer.accepted -or $observer.driver_exit -ne 0 -or
   $observer.failure -or $observer.custody_pending -or !$observer.owned_executables_stopped -or
   !$observer.process_disposed -or !$observer.wrong_expectation_rejected -or
   $observer.runtime -cne $proof.runtime -or $observer.driver_pid -ne $proof.driver_pid -or
   $observer.driver_creation -ne $proof.driver_creation -or
   (Test-Path -LiteralPath $proof.runtime) -or
   (Get-FileHash -LiteralPath (Join-Path $root 'source-manifest.json')).Hash.ToLowerInvariant() -cne $proof.source_manifest_sha256){throw 'Original custody or runtime changed.'}
$allowed=[Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
$dirs=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($entry in $proof.files.PSObject.Properties){
 $relative=$entry.Name.Replace('/','\')
 if([IO.Path]::IsPathRooted($relative) -or $relative.Contains(':') -or
    $relative.Split([char[]]@('\','/')) -contains '..' -or
    $entry.Value -cnotmatch '^[0-9a-f]{64}$'){throw 'Unsafe expected original path or hash.'}
 $full=[IO.Path]::GetFullPath((Join-Path $root $relative))
 if(!$full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or $allowed.ContainsKey($full)){throw 'Duplicate or escaped original.'}
 $allowed.Add($full,[string]$entry.Value)
 $directory=[IO.Path]::GetDirectoryName($full)
 while($directory -cne $root){$null=$dirs.Add($directory);$directory=[IO.Path]::GetDirectoryName($directory)}
}
if($dirs.Count -ne 91 -or $proof.PSObject.Properties.Name -contains 'optional_empty_dirs'){
 throw 'Expected original directory inventory differs.'
}
$queue=[Collections.Generic.Queue[string]]::new();$queue.Enqueue($root)
$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$entries=0;$bytes=0L
while($queue.Count -gt 0){
 $current=$queue.Dequeue()
 foreach($item in @(Get-ChildItem -LiteralPath $current -Force)){
  $entries++
  if($entries -gt 1100 -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Original inventory bound or reparse violation.'}
  if($item.PSIsContainer){
   if(!$dirs.Contains($item.FullName)){throw ('Unknown original directory: '+$item.FullName)}
   $queue.Enqueue($item.FullName)
  }else{
   if(!$allowed.ContainsKey($item.FullName) -or !$seen.Add($item.FullName) -or
      $item.Length -gt 16MB -or
      (Get-FileHash -LiteralPath $item.FullName).Hash.ToLowerInvariant() -cne $allowed[$item.FullName]){throw ('Unknown or changed original file: '+$item.FullName)}
   $bytes+=$item.Length
   if($bytes -gt 67108864){throw 'Original bytes exceed cleanup bound.'}
  }
 }
}
if($seen.Count -ne 888){throw 'Original file count differs.'}
$live=@(Get-CimInstance Win32_Process)
if($live.Count -lt 1 -or @($live|Where-Object{$_.ProcessId -eq $PID}).Count -ne 1){throw 'Native process census incomplete.'}
$actor=@($live|Where-Object{$_.ProcessId -eq [int]$proof.driver_pid})
if($actor.Count -gt 1){throw 'Driver PID ambiguous.'}
if($actor.Count -eq 1){
 if($null -eq $actor[0].CreationDate -or $actor[0].CreationDate -isnot [DateTime]){throw 'Driver generation unavailable.'}
 $creation=$actor[0].CreationDate.ToUniversalTime().ToFileTimeUtc()
 if([Math]::Abs([decimal]$creation-[decimal]$proof.driver_creation) -le 10000000){throw 'Original Driver generation remains live.'}
}
foreach($process in $live){
 if(($process.ExecutablePath -and $process.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) -or
    ($process.CommandLine -and $process.CommandLine.IndexOf($root+'\',[StringComparison]::OrdinalIgnoreCase) -ge 0)){throw 'Owned executable or argument remains live.'}
}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000
try{
 $serial.Open()
 $prepare=@{id=$proof.id;manifest_sha256=$ManifestSha256;original_files=$seen.Count;original_bytes=$bytes;runtime_absent=$true;driver_generation_absent=$true}
 $serial.WriteLine('RHAI_PROJECT_RETIRE_PREPARED '+[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($prepare|ConvertTo-Json -Compress))))
 Remove-Item -LiteralPath $root -Recurse -Force
 if(Test-Path -LiteralPath $root){throw 'Exact own project scope remains.'}
 $done=@{id=$proof.id;manifest_sha256=$ManifestSha256;scope=$root;scope_absent=$true;original_files=$seen.Count;foreign_resources_touched=$false}
 $serial.WriteLine('RHAI_PROJECT_RETIRE_COMPLETE '+[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($done|ConvertTo-Json -Compress))))
}finally{$serial.Dispose()}
Write-Output "PROJECT_ORIGINAL_RETIREMENT_OK files=$($seen.Count) bytes=$bytes"
