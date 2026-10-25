# Read/export only the completed native run; never launches a Driver or compiler.
$ErrorActionPreference='Stop'
$session='C:\Users\RhaiTest\.local\share\agent-builds\rhai\env-control-4e92c3e57fa14837992fd1d20a3f2f8a'
$run=Join-Path $session 'run'
$id='rhai-work-aborted-retirement-20261009-4e92c3e57fa14837992fd1d20a3f2f8a-readback01'
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse environment-control path refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
 }
}
No-Reparse $session
$original=Get-Content -LiteralPath (Join-Path $session 'observer.json') -Raw | ConvertFrom-Json
if($original.id -cne 'rhai-work-aborted-retirement-20261009-4e92c3e57fa14837992fd1d20a3f2f8a' -or $original.exit -ne 0 -or !$original.driver_launched -or !$original.exact_driver_exited -or !$original.pipes_drained -or $original.retained_driver_handles -or $original.failure -cne 'System.Management.Automation.RuntimeException: Exact allocated runtime report unavailable.') {throw 'Original terminal run is not the expected parser-only failure.'}
$output=[IO.File]::ReadAllText((Join-Path $session 'bootstrap.stdout'))
foreach($marker in @('PAYLOAD_EXIT=0000002A','SUPERVISION=PayloadExited','CLEANUP_CONFIRMED=True','RUNTIME_REMOVED=True')){if(!$output.Contains($marker)){throw 'Native closure output is incomplete.'}}
$old=[regex]::Matches($output,'(?m)^RUNTIME=([^\r\n]+)$')
$paths=[regex]::Matches($output,'(?m)^RUNTIME=([^\r\n]+)\r?$')
if($old.Count -ne 0 -or $paths.Count -ne 1){throw 'Saved-output parser RED/GREEN binding failed.'}
$runtime=[IO.Path]::GetFullPath($paths[0].Groups[1].Value)
if([IO.Path]::GetDirectoryName($runtime) -cne $run -or [IO.Path]::GetFileName($runtime) -notmatch '^scoped-[0-9a-f]{32}$' -or (Test-Path -LiteralPath $runtime)){throw 'Native runtime absence does not match this owned run.'}
$files=@(Get-Item -LiteralPath (Join-Path $session 'bootstrap.stdout'),(Join-Path $session 'bootstrap.stderr'),(Join-Path $session 'observer.json'))
$files+=@(Get-ChildItem -LiteralPath $run -Recurse -File)
$files+=@(Get-ChildItem -LiteralPath (Join-Path $session 'build-readback') -Recurse -File)
if($files.Count -gt 64 -or ($files|Measure-Object Length -Sum).Sum -gt 16MB){throw 'Recovery export exceeds original finite caps.'}
foreach($file in $files){No-Reparse $file.FullName;if($file.Length -gt 4MB){throw 'Recovery file exceeds cap.'}}
$complete=$false;$started=$false;$status=0
$record=[ordered]@{id=$id;exit=0;accepted=$false;readback_only=$true;native_reexecution=$false;original_driver_launched=$original.driver_launched;original_id=$original.id;original_observer_accepted=$original.accepted;runtime_absent=$true;original_runtime=$runtime;old_runtime_parser_matches=$old.Count;fixed_runtime_parser_matches=$paths.Count;os_version=([Environment]::OSVersion.Version.ToString());powershell=$PSVersionTable.PSVersion.ToString();parent_environment_preservation_not_reproved=$true}
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
