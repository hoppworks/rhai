$ErrorActionPreference='Stop'
$id='rhai-output-retire01-31b4968cac024f8a8714ea203aa8aa5d'
$expectedPath=Join-Path $PSScriptRoot 'expected.json'
if((Get-FileHash -LiteralPath $expectedPath).Hash.ToLowerInvariant() -cne '01261345c76f10cd22c030a79975954d3a2a9463f63e6d9a52b6829b43c4cbf8'){throw 'Frozen retirement inventory changed.'}
$expected=Get-Content -LiteralPath $expectedPath -Raw | ConvertFrom-Json
$deadline=[Diagnostics.Stopwatch]::StartNew()
function Bound { if($deadline.Elapsed.TotalSeconds -gt 120){throw 'Owned retirement exceeded120seconds.'} }
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse retirement path refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
 }
}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$case=Join-Path $private 'monitor-output-limit-b7fd2bab746b4f01b1b0431365d52bd4'
$target=$case+'-target'
$receiptRoot=Join-Path $private ('output-limit-retire-'+$id.Substring($id.Length-32))
No-Reparse $receiptRoot
if(Test-Path -LiteralPath $receiptRoot){throw 'Owned retirement receipt root exists; preserve it.'}
New-Item -ItemType Directory -Path $receiptRoot | Out-Null
$record=[ordered]@{id=$id;accepted=$false;failure='';observer_owned_reset=$true;backend_cleanup_receipt_claimed=$false;original_case_exit=0;original_driver_exit=2;source_review='d16ff487f42ef109b8794d8d65ac1068e5920a02e888ebbc81b224a2ae88437e';identities=@();inventory=@();roots=@();removed=@()}
$status=2
try{
 $runner='C:\Users\RhaiTest\.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build\ScopedRunner.exe'
 No-Reparse $runner
 if((Get-FileHash -LiteralPath $runner).Hash.ToLowerInvariant() -cne 'c3d91a8bcf550ef8087b7c057455ac876fe0a958b4e22de816b55daa659cb486'){throw 'Retained identity reader image changed.'}
 $assembly=[Reflection.Assembly]::LoadFile($runner);$type=$assembly.GetType('WindowsCustodyBackend',$true)
 $flags=[Reflection.BindingFlags]'Static,NonPublic'
 $open=$type.GetMethod('OpenDirectory',$flags);$read=$type.GetMethod('ReadIdentity',$flags);$format=$type.GetMethod('FormatIdentity',$flags)
 if(!$open -or !$read -or !$format){throw 'Existing read-only native identity methods unavailable.'}
 function Directory-Identity([string]$Path){
  Bound;No-Reparse $Path
  $handle=$open.Invoke($null,[object[]]@($Path,$false,$false))
  try{
   $identity=$read.Invoke($null,[object[]]@($handle))
   return $format.Invoke($null,[object[]]@($identity))
  }finally{$handle.Dispose()}
 }
 foreach($item in $expected.identities){
  Bound;$process=$null;$identityAbsent=$false
  try{$process=[Diagnostics.Process]::GetProcessById([int]$item.pid)}
  catch [ArgumentException]{$identityAbsent=$true}
  try{
   if($process){
    $current=$process.StartTime.ToUniversalTime().ToFileTimeUtc()
    if($current -ne [long]$item.creation){$identityAbsent=$true}
    elseif($process.HasExited){$identityAbsent=$true}
    else{throw 'A matching native actor is still live; no retirement authorized.'}
   }
   $record.identities+=,[ordered]@{pid=$item.pid;creation=$item.creation;exact_identity_absent=$identityAbsent}
  }finally{if($process){$process.Dispose()}}
 }
 foreach($binding in $expected.directory_bindings){
  $path=Join-Path $target $binding.relative
  $actual=Directory-Identity $path
  if($actual -cne $binding.identity){throw 'Original native directory identity changed.'}
  $record.roots+=,[ordered]@{path=$path;identity=$actual;original_binding=$true}
 }
 foreach($root in @($case,$target)){
  Bound
  if([IO.Directory]::GetParent($root).FullName -cne $private){throw 'Retirement root outside exact private parent.'}
  $rootIdentity=Directory-Identity $root
  $wanted=@($expected.files|Where-Object {$_.root -ceq $root})
  $expectedDirs=@{};$expectedDirs[$root]=$true
  foreach($item in $wanted){
   $parent=[IO.Path]::GetDirectoryName((Join-Path $root $item.relative))
   while($parent -cne $root){
    if(!$parent.StartsWith($root+'\',[StringComparison]::Ordinal)){throw 'Inventory path escaped root.'}
    $expectedDirs[$parent]=$true;$parent=[IO.Path]::GetDirectoryName($parent)
   }
  }
  $seen=@{};$pending=[Collections.Generic.Stack[string]]::new();$pending.Push($root);$count=0
  while($pending.Count){
   Bound;$dir=$pending.Pop();No-Reparse $dir
   foreach($entry in @(Get-ChildItem -LiteralPath $dir -Force)){
    Bound;$count++;if($count -gt 64){throw 'Retirement inventory exceeds64entries.'}
    No-Reparse $entry.FullName
    if($entry.PSIsContainer){
     if(!$expectedDirs.ContainsKey($entry.FullName)){throw 'Unexpected directory; preserve owned and foreign data.'}
     $pending.Push($entry.FullName)
    }else{
     $relative=$entry.FullName.Substring($root.Length+1)
     $match=@($wanted|Where-Object {$_.relative -ceq $relative})
     if($match.Count -ne 1 -or $seen.ContainsKey($relative)){throw 'Unexpected or duplicate file; preserve it.'}
     if($entry.Length -ne [long]$match[0].length -or $entry.Length -gt 67108864){throw 'Original file length changed.'}
     $hash=(Get-FileHash -LiteralPath $entry.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
     if($hash -cne $match[0].sha256){throw 'Original file hash changed; preserve runtime.'}
     $seen[$relative]=$true
     $record.inventory+=,[ordered]@{root=$root;relative=$relative;length=$entry.Length;sha256=$hash}
    }
   }
  }
  if($seen.Count -ne $wanted.Count){throw 'Original file inventory incomplete.'}
  if((Directory-Identity $root) -cne $rootIdentity){throw 'Root changed during bounded inventory.'}
  $record.roots+=,[ordered]@{path=$root;identity=$rootIdentity;original_binding=$false}
 }
 # Both exact inventories and native actors are checked before either removal.
 foreach($root in @($case,$target)){
  Bound;No-Reparse $root
  $bound=@($record.roots|Where-Object {$_.path -ceq $root})
  if($bound.Count -ne 1 -or (Directory-Identity $root) -cne $bound[0].identity){throw 'Retirement root identity changed.'}
  Remove-Item -LiteralPath $root -Recurse -Force
  if(Test-Path -LiteralPath $root){throw 'Exact own root retirement incomplete.'}
  $record.removed+=,$root
 }
 $record.accepted=$true;$status=0
}catch{$record.failure=$_.Exception.ToString()}
$record.elapsed_seconds=$deadline.Elapsed.TotalSeconds
$file=Join-Path $receiptRoot 'retirement.json'
[IO.File]::WriteAllText($file,($record|ConvertTo-Json -Compress -Depth 10),[Text.UTF8Encoding]::new($false))
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000;$script:sequence=0
$export=[Diagnostics.Stopwatch]::StartNew()
function Emit([string]$Kind,[object]$Value){
 if($export.Elapsed.TotalSeconds -gt 30){throw 'Retirement proof export exceeded30seconds.'}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Compress -Depth 10)))
 if($encoded.Length -gt 3500){throw 'Retirement proof frame exceeds cap.'}
 $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded");$script:sequence++
}
try{
 $serial.Open();Emit 'BEGIN' @{id=$id;scope=$receiptRoot;accepted=$record.accepted;exit=$status;full_record='retirement.json'}
 $bytes=[IO.File]::ReadAllBytes($file);if($bytes.Length -gt 65536){throw 'Retirement proof exceeds64KiB.'}
 $hash=(Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant()
 $header=@{path='retirement.json';length=$bytes.Length;sha256=$hash};Emit 'FILE' $header
 for($offset=0;$offset -lt $bytes.Length;$offset+=1024){
  $count=[Math]::Min(1024,$bytes.Length-$offset)
  Emit 'CHUNK' @{path='retirement.json';offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$count)}
 }
 Emit 'FILE_END' $header
 Emit 'END' @{id=$id;files=1;accepted=$record.accepted;exit=$status;driver_launched=$false;guest_evidence_retained=$true}
}finally{$serial.Dispose()}
$record|ConvertTo-Json -Compress -Depth 10
exit $status
