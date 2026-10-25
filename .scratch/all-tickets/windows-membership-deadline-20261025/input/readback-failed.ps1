# Read/export only the completed native run; never launches a Driver or compiler.
$ErrorActionPreference='Stop'
$session='C:\Users\RhaiTest\.local\share\agent-builds\rhai\membership-membership-7756151b9a8b488ea7df3c92b5a04494'
$run=Join-Path $session 'run'
$id='rhai-membership-7756151b9a8b488ea7df3c92b5a04494-readback'
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse environment-control path refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
 }
}
No-Reparse $session
$original=Get-Content -LiteralPath (Join-Path $session 'observer.json') -Raw|ConvertFrom-Json
if($original.id -cne 'rhai-membership-7756151b9a8b488ea7df3c92b5a04494' -or $original.accepted -or $original.exit -ne 2 -or !$original.driver_launched -or !$original.exact_driver_exited -or !$original.pipes_drained -or $original.retained_driver_handles){throw 'Expected exact terminal failed Driver required.'}
if($original.scope -cne $session -or $original.run -cne $run -or $original.mode -cne 'membership'){throw 'Original observer scope/mode differs.'}
$journals=@(Get-ChildItem -LiteralPath $run -Force -File -Filter '.scoped-run-*.journal')
if($journals.Count -ne 1){throw 'One original journal required.'}
$rows=[IO.File]::ReadAllLines($journals[0].FullName)
if($rows.Count -ne 8 -or !$rows[-1].Contains(':REMOVED|')){throw 'Original closure incomplete; no runtime export.'}
$parts=$rows[0].Split(':',3)[2].Split('|')
if($parts[0] -cne 'INTENT'){throw 'Original intent missing.'}
$runtime=[IO.Path]::GetFullPath($parts[2])
if([IO.Path]::GetDirectoryName($runtime) -cne $run -or [IO.Path]::GetFileName($runtime) -notmatch '^scoped-[0-9a-f]{32}$' -or (Test-Path -LiteralPath $runtime)){throw 'Exact original runtime still exists.'}
# The failure occurred before observer allocation parsing; null is preserved truth.
if($null -ne $original.allocated_runtime -and $original.allocated_runtime -cne $runtime){throw 'Original allocated runtime contradicts journal.'}
$files=@(Get-Item -LiteralPath (Join-Path $session 'bootstrap.stdout'),(Join-Path $session 'bootstrap.stderr'),(Join-Path $session 'observer.json'))
$files+=@(Get-ChildItem -LiteralPath $run -Recurse -File -Force)
if($files.Count -gt 64 -or ($files|Measure-Object Length -Sum).Sum -gt 16MB){throw 'Readback inventory exceeds cap.'}
foreach($file in $files){No-Reparse $file.FullName;if($file.Length -gt 4MB){throw 'Readback file exceeds cap.'}}
$complete=$false;$started=$false;$status=0
$record=[ordered]@{id=$id;exit=0;accepted=$false;readback_only=$true;native_reexecution=$false;original_id=$original.id;original_observer_accepted=$original.accepted;runtime_absent=$true;original_runtime=$runtime}
$serial = [IO.Ports.SerialPort]::new('COM1',115200); $serial.WriteTimeout = 2000; $script:sequence = 0
$exportDeadline = [Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string] $Kind, [object] $Value) {
    if ($exportDeadline.Elapsed.TotalSeconds -gt 180) { throw 'Serial export exceeded its 180-second bound; guest evidence retained.' }
    $json = $Value | ConvertTo-Json -Compress -Depth 8
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    if ($encoded.Length -gt 3500) { throw 'Export frame exceeds its declared bound.' }
    $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded")
    $script:sequence++
}
try {
    $serial.Open(); Emit-Frame 'BEGIN' $record
    foreach ($file in $files) {
        if ($file.Length -gt 4MB -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Export file exceeds cap or is a reparse point.' }
        $relative = $file.FullName.Substring($session.Length + 1).Replace('\','/')
        $bytes = [IO.File]::ReadAllBytes($file.FullName)
        $digest = [Security.Cryptography.SHA256]::Create()
        try { $hash = [BitConverter]::ToString($digest.ComputeHash($bytes)).Replace('-','').ToLowerInvariant() } finally { $digest.Dispose() }
        Emit-Frame 'FILE' @{path=$relative;length=$bytes.Length;sha256=$hash}
        for ($offset=0; $offset -lt $bytes.Length; $offset+=1024) {
            $length = [Math]::Min(1024,$bytes.Length-$offset)
            Emit-Frame 'CHUNK' @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}
        }
        Emit-Frame 'FILE_END' @{path=$relative;length=$bytes.Length;sha256=$hash}
    }
    Emit-Frame 'END' @{id=$id;files=$files.Count;accepted=$complete;exit=$status;guest_evidence_retained=$true;driver_launched=$started}
} finally { $serial.Dispose() }
