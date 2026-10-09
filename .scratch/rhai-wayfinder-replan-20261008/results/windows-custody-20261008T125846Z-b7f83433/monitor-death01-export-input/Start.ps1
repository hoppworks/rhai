$ErrorActionPreference='Stop'
$id='rhai-monitor-death01-db023375475c485f8ed6ea9a8e8f3f6c'
$session=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\monitor-death-db023375475c485f8ed6ea9a8e8f3f6c'
$actors=@([pscustomobject]@{Role='target';Root=($session+'-target')},[pscustomobject]@{Role='sentinel';Root=($session+'-sentinel')})
$complete=$false;$status=2
$record=@{id=$id;scope=$session;accepted=$false;exit=2;export_only=$true;original_observer_retained=$true}
$files=@();$count=0;$total=0L
function NoReparse([string]$path){
 $cursor=[IO.Path]::GetFullPath($path)
 while($cursor){
  if((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Owned export reparse path refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($parent){$parent.FullName}else{$null}
 }
}
foreach($root in @($session,$actors[0].Root,$actors[1].Root)){
 NoReparse $root
 $stack=[Collections.Generic.Stack[string]]::new();$stack.Push($root)
 while($stack.Count){
  $path=$stack.Pop();NoReparse $path
  foreach($item in @(Get-ChildItem -LiteralPath $path -Force)){
   $count++;if($count -gt 64){throw 'Owned export exceeds 64 entries.'};NoReparse $item.FullName
   if($item.PSIsContainer){$stack.Push($item.FullName)}
   else{
    $total+=$item.Length
    if($item.Length -gt 4MB -or $total -gt 16MB){throw 'Owned export exceeds byte caps.'}
    $files+=,$item
   }
  }
 }
}
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
        $relative=$null
        if($file.FullName.StartsWith($session+'\',[StringComparison]::OrdinalIgnoreCase)){
            $relative=$file.FullName.Substring($session.Length+1).Replace('\','/')
        }else{
            foreach($actor in $actors){
                if($file.FullName.StartsWith($actor.Root+'\',[StringComparison]::OrdinalIgnoreCase)){
                    $relative=$actor.Role+'/'+$file.FullName.Substring($actor.Root.Length+1).Replace('\','/')
                    break
                }
            }
        }
        if(!$relative){throw 'Export source escaped its exact owned sessions.'}
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
    Emit-Frame 'END' @{id=$id;files=$files.Count;accepted=$complete;exit=$status;guest_evidence_retained=$true;driver_launched=$true}
} finally { $serial.Dispose() }
$record|ConvertTo-Json -Compress
exit 0
