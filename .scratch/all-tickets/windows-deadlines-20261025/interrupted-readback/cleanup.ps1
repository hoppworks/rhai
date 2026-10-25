param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
# Read-only export of the interrupted case; no Driver/compiler/removal/reexecution.
$ErrorActionPreference='Stop'
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Readback manifest changed.'}
$m=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$session=[IO.Path]::GetFullPath($m.scope)
if($env:USERPROFILE -cne 'C:\Users\RhaiTest' -or $session -cne 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\deadline-control-e8b0c81f1f9448d78dae7dd0bfd96b4a' -or $m.original_case_id -cne 'rhai-deadline-absolute-e8b0c81f1f9448d78dae7dd0bfd96b4a'){throw 'Wrong interrupted owner/scope.'}
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){if((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse readback path.'};$parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}}
}
No-Reparse $session
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToFileTimeUtc()
if($boot -lt [long]$m.minimum_new_boot_filetime -or [long]$m.old_driver_creation -ge $boot){throw 'New kernel boot has not closed the original process lifetime.'}
foreach($proc in @(Get-CimInstance Win32_Process)){if($proc.ExecutablePath -and $proc.ExecutablePath.StartsWith($session+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Interrupted scope has an active executable; preserve it.'}}
$entries=@(Get-ChildItem -LiteralPath $session -Recurse -Force)
if($entries.Count -gt 256){throw 'Interrupted inventory cap.'}
foreach($entry in $entries){if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse entry.'}}
$files=@($entries|Where-Object{!$_.PSIsContainer});$dirs=@($entries|Where-Object{$_.PSIsContainer}|ForEach-Object{$_.FullName.Substring($session.Length+1).Replace('\','/')})
if($files.Count -gt 64 -or ($files|Measure-Object Length -Sum).Sum -gt 16MB){throw 'Interrupted export caps.'}
foreach($file in $files){if($file.Length -gt 4MB){throw 'Interrupted file cap.'}}
$id=$m.readback_id;$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000;$script:sequence=0;$deadline=[Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string]$Kind,[object]$Value){
 if($deadline.Elapsed.TotalSeconds -gt 180){throw 'Interrupted export reached bound; preserve originals.'}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 8 -Compress)))
 if($encoded.Length -gt 3500){throw 'Interrupted export frame cap.'}
 $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded");$script:sequence++
}
try{
 $serial.Open();Emit-Frame BEGIN @{id=$id;exit=0;accepted=$false;readback_only=$true;original_id=$m.original_case_id;scope=$session;boot_filetime=$boot;directories=$dirs;observer_present=(Test-Path -LiteralPath (Join-Path $session 'observer.json'));native_reexecution=$false;native_removal_claimed=$false}
 foreach($file in $files){
  $stream=[IO.FileStream]::new($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
  try{
   if($stream.Length -ne $file.Length -or $stream.Length -gt 4MB){throw 'Interrupted bytes changed.'}
   $bytes=New-Object byte[] ([int]$stream.Length);$read=0
   while($read -lt $bytes.Length){$n=$stream.Read($bytes,$read,$bytes.Length-$read);if($n -le 0){throw 'Interrupted file truncated.'};$read+=$n}
   if($stream.ReadByte() -ne -1){throw 'Interrupted file grew.'}
  }finally{$stream.Dispose()}
  $digest=[Security.Cryptography.SHA256]::Create();try{$hash=[BitConverter]::ToString($digest.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$digest.Dispose()}
  $relative=$file.FullName.Substring($session.Length+1).Replace('\','/')
  Emit-Frame FILE @{path=$relative;length=$bytes.Length;sha256=$hash}
  for($offset=0;$offset -lt $bytes.Length;$offset+=1024){$length=[Math]::Min(1024,$bytes.Length-$offset);Emit-Frame CHUNK @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}}
  Emit-Frame FILE_END @{path=$relative;length=$bytes.Length;sha256=$hash}
 }
 Emit-Frame END @{id=$id;exit=0;accepted=$false;files=$files.Count;readback_only=$true;guest_evidence_retained=$true;native_reexecution=$false;product_accepted=$false}
}finally{$serial.Dispose()}
