param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
$ErrorActionPreference='Stop'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong cache owner.'}
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Cache retirement manifest changed.'}
$proof=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$roots=@();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($scope in @($proof)){
 $root=[IO.Path]::GetFullPath($scope.scope)
 if([IO.Path]::GetDirectoryName($root) -cne $private -or [IO.Path]::GetFileName($root) -cne 'job-resource-build-green-cdcd7eebb7ec4c89b8aa2f9e8f2054f4' -or !$seen.Add($root)){throw 'Unexpected/duplicate cleanup root.'}
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

 $bo=Get-Content -LiteralPath (Join-Path $root 'build-observer.json') -Raw|ConvertFrom-Json
 if(!$bo.accepted -or !$bo.native_started -or $bo.custody_indeterminate -or $bo.exit -ne 0){throw 'Original native build ownership not closed.'}
 $roots+=,$root
}
foreach($process in @(Get-CimInstance Win32_Process)){
 foreach($root in $roots){if($process.ExecutablePath -and $process.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Cache binary remains active; preserve it.'}}
}
foreach($root in $roots){Remove-Item -LiteralPath $root -Recurse -Force;if(Test-Path -LiteralPath $root){throw 'Exact cache scope remains.'}}
$receipt=@{scope=$proof.scope;all_scopes_absent=$true;manifest_sha256=$ManifestSha256;original_accepted_proof_sha256=$proof.original_accepted_proof_sha256;file_count=@($proof.files.PSObject.Properties).Count;foreign_resources_touched=$false;reason='ended compatible reuse before original expiry'}
$encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($receipt|ConvertTo-Json -Compress)))
if($encoded.Length -gt 3500){throw 'Cache receipt exceeds cap.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000
try{$serial.Open();$serial.WriteLine('RHAI_DEADLINE_BASELINE_RETIRED '+$encoded)}finally{$serial.Dispose()}
$receipt|ConvertTo-Json -Compress
