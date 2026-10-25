param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ManifestSha256)
# Read-only completed owned build export; no Driver/compiler/removal/reexecution.
$ErrorActionPreference='Stop'
$manifestPath='E:\cleanup-host-manifest.json'
if((Get-FileHash -LiteralPath $manifestPath).Hash.ToLowerInvariant() -cne $ManifestSha256){throw 'Readback manifest changed.'}
$m=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$session=[IO.Path]::GetFullPath($m.scope)
if($env:USERPROFILE -cne 'C:\Users\RhaiTest' -or $session -cne 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\memory-fixture-63a597390756484cbc31eb5c9bdeff3d' -or $m.original_case_id -cne 'rhai-memory-denial-63a597390756484cbc31eb5c9bdeff3d' -or !$m.readback_only -or $m.delete_allowed -or $m.native_reexecution){throw 'Wrong own completed build scope/mode.'}
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){if((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse readback path.'};$parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}}
}
No-Reparse $session
$buildObserver=Get-Content -LiteralPath (Join-Path $session 'build-observer.json') -Raw|ConvertFrom-Json
if(!$buildObserver.accepted -or $buildObserver.exit -ne 0 -or $buildObserver.custody_indeterminate -or $buildObserver.id -cne $m.original_case_id -or $buildObserver.input_manifest_sha256 -cne $m.input_manifest_sha256 -or $buildObserver.start_sha256 -cne $m.start_sha256){throw 'Completed build provenance/custody differs.'}
$liveProcesses=@(Get-CimInstance Win32_Process)
if($liveProcesses.Count -lt 1 -or @($liveProcesses|Where-Object{$_.ProcessId -eq $PID}).Count -ne 1){throw 'Current OS process census incomplete.'}
$ownerRows=@($liveProcesses|Where-Object{$_.ProcessId -eq [int]$buildObserver.process_id})
if($ownerRows.Count -gt 1){throw 'Ambiguous native build owner generation.'}
if($ownerRows.Count -eq 1){
 if($null -eq $ownerRows[0].CreationDate -or $ownerRows[0].CreationDate -isnot [DateTime]){throw 'Native build owner creation unavailable.'}
 $original=[DateTime]::Parse($buildObserver.process_start_utc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime().ToFileTimeUtc()
 $current=$ownerRows[0].CreationDate.ToUniversalTime().ToFileTimeUtc()
 if([Math]::Abs([decimal]$current-[decimal]$original) -le 10000000){throw 'Original or indistinguishable native build owner remains live.'}
}
foreach($entry in $m.files.PSObject.Properties){$file=Join-Path (Join-Path $session 'source-input') $entry.Name.Replace('/','\');No-Reparse $file;if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $entry.Value){throw 'Original build source changed.'}}
foreach($proc in @(Get-CimInstance Win32_Process)){if(($proc.ExecutablePath -and $proc.ExecutablePath.StartsWith($session+'\',[StringComparison]::OrdinalIgnoreCase)) -or ($proc.CommandLine -and $proc.CommandLine.IndexOf($session+'\',[StringComparison]::OrdinalIgnoreCase) -ge 0)){throw 'Completed build scope has an active executable; preserve it.'}}
$entries=@(Get-ChildItem -LiteralPath $session -Recurse -Force)
if($entries.Count -gt 256){throw 'Completed build inventory cap.'}
foreach($entry in $entries){if($entry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse entry.'}}
$files=@($entries|Where-Object{!$_.PSIsContainer});$dirs=@($entries|Where-Object{$_.PSIsContainer}|ForEach-Object{$_.FullName.Substring($session.Length+1).Replace('\','/')})
if($files.Count -gt 64 -or ($files|Measure-Object Length -Sum).Sum -gt 16MB){throw 'Completed build export caps.'}
foreach($file in $files){if($file.Length -gt 4MB){throw 'Completed build file cap.'}}
$id=$m.readback_id;$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000;$script:sequence=0;$deadline=[Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string]$Kind,[object]$Value){
 if($deadline.Elapsed.TotalSeconds -gt 180){throw 'Completed build export reached bound; preserve originals.'}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Depth 8 -Compress)))
 if($encoded.Length -gt 3500){throw 'Completed build export frame cap.'}
 $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded");$script:sequence++
}
try{
 $serial.Open();Emit-Frame BEGIN @{id=$id;exit=0;accepted=$false;readback_only=$true;original_id=$m.original_case_id;scope=$session;build_accepted=$true;directories=$dirs;observer_present=(Test-Path -LiteralPath (Join-Path $session 'build-observer.json'));native_reexecution=$false;native_removal_claimed=$false}
 foreach($file in $files){
  $stream=[IO.FileStream]::new($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
  try{
   if($stream.Length -ne $file.Length -or $stream.Length -gt 4MB){throw 'Completed build bytes changed.'}
   $bytes=New-Object byte[] ([int]$stream.Length);$read=0
   while($read -lt $bytes.Length){$n=$stream.Read($bytes,$read,$bytes.Length-$read);if($n -le 0){throw 'Completed build file truncated.'};$read+=$n}
   if($stream.ReadByte() -ne -1){throw 'Completed build file grew.'}
  }finally{$stream.Dispose()}
  $digest=[Security.Cryptography.SHA256]::Create();try{$hash=[BitConverter]::ToString($digest.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$digest.Dispose()}
  $relative=$file.FullName.Substring($session.Length+1).Replace('\','/')
  Emit-Frame FILE @{path=$relative;length=$bytes.Length;sha256=$hash}
  for($offset=0;$offset -lt $bytes.Length;$offset+=1024){$length=[Math]::Min(1024,$bytes.Length-$offset);Emit-Frame CHUNK @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}}
  Emit-Frame FILE_END @{path=$relative;length=$bytes.Length;sha256=$hash}
 }
 Emit-Frame END @{id=$id;exit=0;accepted=$false;files=$files.Count;readback_only=$true;guest_evidence_retained=$true;native_reexecution=$false;product_accepted=$false}
}finally{$serial.Dispose()}
