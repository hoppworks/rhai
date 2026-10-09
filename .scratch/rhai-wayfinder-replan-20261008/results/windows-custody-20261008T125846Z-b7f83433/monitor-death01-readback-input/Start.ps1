$ErrorActionPreference='Stop'
$id='rhai-monitor-readback-3e39cbc7bc1a4710a2d6f1acdf83b61c'
$session=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\monitor-readback-3e39cbc7bc1a4710a2d6f1acdf83b61c'
$original=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\monitor-death-db023375475c485f8ed6ea9a8e8f3f6c'
function NoReparse([string]$path){
 $cursor=[IO.Path]::GetFullPath($path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Readback reparse refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($parent){$parent.FullName}else{$null}
 }
}
NoReparse $session
if(Test-Path -LiteralPath $session){throw 'Readback scope exists; preserve it.'}
$manifest=Join-Path $PSScriptRoot 'originals.json'
if((Get-FileHash -LiteralPath $manifest).Hash.ToLowerInvariant() -cne 'd5321c04971fea173afcf4ca0120320205b1d820bf9b02535ecbbe5228d56ac7'){throw 'Frozen originals inventory changed.'}
$data=Get-Content -LiteralPath $manifest -Raw|ConvertFrom-Json
$checked=@{}
foreach($property in $data.files.PSObject.Properties){
 $relative=$property.Name;$item=$property.Value
 if($relative.StartsWith('target/')){$path=Join-Path ($original+'-target') $relative.Substring(7)}
 elseif($relative.StartsWith('sentinel/')){$path=Join-Path ($original+'-sentinel') $relative.Substring(9)}
 else{$path=Join-Path $original $relative}
 NoReparse $path
 if((Get-Item -LiteralPath $path).Length -ne $item.length -or (Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $item.sha256){throw 'Original saved file changed.'}
 $checked[$relative]=$item.sha256
}
$identities=[ordered]@{}
foreach($property in $data.identities.PSObject.Properties){
 $identity=$property.Value;$process=$null
 try{$process=[Diagnostics.Process]::GetProcessById([int]$identity.pid)}
 catch [ArgumentException]{$identities[$property.Name]=@{pid=$identity.pid;creation=$identity.creation;original_stopped=$true;pid_absent=$true};continue}
 try{
  $creation=$process.StartTime.ToUniversalTime().ToFileTimeUtc()
  if($creation -eq [long]$identity.creation -and !$process.HasExited){throw 'Exact original process is still live; preserve all resources.'}
  $identities[$property.Name]=@{pid=$identity.pid;creation=$identity.creation;original_stopped=$true;pid_absent=$false;current_creation=$creation}
 }finally{$process.Dispose()}
}
$targetRuntime=Join-Path ($original+'-target\run') 'scoped-cbccb01bc01346cd8a66654e193371be'
$sentinelRuntime=Join-Path ($original+'-sentinel\run') 'scoped-d26b448913c244c695b90aef14ec097c'
if(Test-Path -LiteralPath $sentinelRuntime){throw 'Independent sentinel runtime remains.'}
NoReparse $targetRuntime
$actual=@(Get-ChildItem -LiteralPath $targetRuntime -Force)
if($actual.Count -ne 8){throw 'Target cleanup inventory changed.'}
foreach($item in $actual){
 if($item.PSIsContainer){throw 'Unexpected target subdirectory.'}
 NoReparse $item.FullName
 $key='target/run/scoped-cbccb01bc01346cd8a66654e193371be/'+$item.Name
 if(!$checked.ContainsKey($key)){throw 'Unexported target file; preserve it.'}
}
New-Item -ItemType Directory -Path $session | Out-Null
$record=[ordered]@{id=$id;scope=$session;exit=0;accepted=$false;readback_only=$true;identities=$identities;originals_verified=$checked.Count;manifest_sha256='d5321c04971fea173afcf4ca0120320205b1d820bf9b02535ecbbe5228d56ac7';sentinel_runtime_absent=$true;monitor_cleanup_receipt_claimed=$false}
[IO.File]::WriteAllText((Join-Path $session 'before-cleanup.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
Remove-Item -LiteralPath $targetRuntime -Recurse -Force
if(Test-Path -LiteralPath $targetRuntime){throw 'Exact own target runtime removal failed.'}
$record['observer_runtime_removed']=$true
[IO.File]::WriteAllText((Join-Path $session 'after-cleanup.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
$files=@(Get-ChildItem -LiteralPath $session -File)
$actors=@();$status=0;$complete=$false
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
    $serial.Open(); Emit-Frame 'BEGIN' @{id=$id;scope=$session;exit=0;accepted=$false;readback_only=$true}
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
