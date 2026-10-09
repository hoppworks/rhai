param(
 [Parameter(Mandatory=$true)][string]$FixturePath,
 [Parameter(Mandatory=$true)][string]$FixtureSha256,
 [Parameter(Mandatory=$true)][string]$DriverBuild,
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][string]$Id,
 [ValidateSet('monitor-death','parent-exit')][string]$Action='monitor-death'
)
$ErrorActionPreference='Stop'
$id=$Id;$session=[IO.Path]::GetFullPath($Session)
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
if([IO.Directory]::GetParent($session).FullName -cne $private -or
 [IO.Path]::GetFileName($session) -notmatch '^monitor-(death|parent-exit)-[0-9a-f]{32}$'){
 throw 'Monitor-death requires its exact fresh private session root.'
}
if(Test-Path -LiteralPath $session){throw 'Owned monitor-death session exists; preserve it.'}
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and
   ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){
   throw "Reparse path refused: $cursor"
  }
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
 }
}
No-Reparse $session;No-Reparse $FixturePath;No-Reparse $DriverBuild
$driver=Join-Path $DriverBuild 'MonitorAcceptanceDriver.exe'
$runner=Join-Path $DriverBuild 'ScopedRunner.exe'
$expected=@{$FixturePath=$FixtureSha256;$driver='caf4afaa2f604fb47fc554c82d9493854be0959c8d329bff7a88fd7fe9e827cb';$runner='c3d91a8bcf550ef8087b7c057455ac876fe0a958b4e22de816b55daa659cb486'}
foreach($path in $expected.Keys){
 No-Reparse $path
 if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne $expected[$path]){throw "Retained artifact changed: $path"}
}
$roles=if($Action -eq 'parent-exit'){@('target')}else{@('target','sentinel')}
foreach($role in $roles){
 $root=$session+'-'+$role;No-Reparse $root
 if(Test-Path -LiteralPath $root){throw 'Owned actor session exists; preserve it.'}
}
New-Item -ItemType Directory -Path $session | Out-Null
$deadline=[Diagnostics.Stopwatch]::StartNew()
$actors=@();$handles=@();$failure='';$complete=$false;$status=-1
$monitorKilled=$false;$wrongExpectationRed=$false;$sentinelSurvived=$false
$targetStopped=$false;$observerRemoved=$false;$sentinelCompleted=$false;$targetRuntime=$null
$observations=[ordered]@{}
$targetCustodyValidated=$false;$monitor=$null
$parentReleaseRequested=$false;$targetExitCodes=$null;$normalClosure=$false
function Bound{
 if($deadline.Elapsed.TotalSeconds -ge 190){throw 'Monitor-death observer exceeded its 190-second bound.'}
}
function Start-Driver([string]$role,[string]$payloadExit,[string]$fixtureArgs){
 $root=$session+'-'+$role;$input=Join-Path $root 'input';$run=Join-Path $root 'run'
 New-Item -ItemType Directory -Path $input,$run | Out-Null
 $copy=Join-Path $input 'fixture.exe';Copy-Item -LiteralPath $FixturePath -Destination $copy
 if((Get-FileHash -LiteralPath $copy).Hash.ToLowerInvariant() -cne $FixtureSha256){throw 'Immutable fixture copy mismatch.'}
 $info=[Diagnostics.ProcessStartInfo]::new();$info.FileName=$driver
 $info.Arguments='--mode success --source "'+$input+'" --exe fixture.exe --expected-payload-exit '+$payloadExit+' -- '+$fixtureArgs
 $info.WorkingDirectory=$DriverBuild;$info.UseShellExecute=$false;$info.CreateNoWindow=$true
 $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
 $info.EnvironmentVariables['AGENT_RUNTIME_DIR']=$run
 $process=[Diagnostics.Process]::new();$process.StartInfo=$info
 $actor=[pscustomobject]@{Role=$role;Root=$root;Run=$run;Process=$process;Started=$false;Exited=$false;Drained=$false;Status=$null;Readers=@()}
 $script:actors+=,$actor
 if(!$process.Start()){throw "Native $role driver did not start."};$actor.Started=$true
 if($process.Handle -eq [IntPtr]::Zero){throw 'Exact native driver handle missing.'}
 foreach($def in @(@{Reader=$process.StandardOutput;Path=(Join-Path $root 'bootstrap.stdout')},@{Reader=$process.StandardError;Path=(Join-Path $root 'bootstrap.stderr')})){
  $channel=[pscustomobject]@{Reader=$def.Reader;Writer=[IO.StreamWriter]::new($def.Path,$false,[Text.UTF8Encoding]::new($false));Buffer=[char[]]::new(1024);Task=$null;Bytes=0;Eof=$false;Error='';Closed=$false}
  $actor.Readers+=,$channel;$channel.Task=$channel.Reader.ReadAsync($channel.Buffer,0,$channel.Buffer.Length)
 }
 return $actor
}
function Poll-Drivers{
 Bound
 foreach($actor in $actors){
  foreach($channel in $actor.Readers){Save-CompletedChunk $channel}
  if($actor.Started -and $actor.Process.HasExited){
   $actor.Exited=$true;$actor.Process.Refresh();$actor.Status=[int]$actor.Process.ExitCode
  }
 }
}
function Runtime-Ready($actor,[string]$prefix,[string]$marker){
 $dirs=@(Get-ChildItem -LiteralPath $actor.Run -Directory -Filter 'scoped-*')
 if($dirs.Count -eq 0){return $null}
 if($dirs.Count -ne 1){throw 'Ambiguous owned runtime inventory.'}
 $path=Join-Path $dirs[0].FullName ($prefix+'.ready');No-Reparse $path
 if(!(Test-Path -LiteralPath $path)){return $null}
 if([IO.File]::ReadAllText($path) -cne ($marker+[char]13+[char]10)){throw 'Fresh runtime readiness mismatch.'}
 return $dirs[0].FullName
}
function Identity-Handle([string]$path,[string]$role){
 No-Reparse $path;$text=[IO.File]::ReadAllText($path)
 if($text -cnotmatch '^pid=([0-9]+) creation=([0-9]+)\r\n$'){throw 'Malformed fresh identity.'}
 $pidValue=[int]$Matches[1];$creation=[long]$Matches[2]
 $process=[Diagnostics.Process]::GetProcessById($pidValue);$script:handles+=,$process
 if($process.Handle -eq [IntPtr]::Zero -or $process.HasExited -or
  $process.StartTime.ToUniversalTime().ToFileTimeUtc() -ne $creation){throw 'Fresh identity is not the exact live process.'}
 $script:observations[$role]=[ordered]@{pid=$pidValue;creation=$creation}
 return $process
}
function Assert-TargetStopped([bool]$expected){
 $actual=$monitor.HasExited -and $client.HasExited -and $payload.HasExited -and $grandchild.HasExited
 if($actual -ne $expected){throw 'Monitor-death exact target termination assertion mismatch.'}
}
function Snapshot-Target([string]$root,[string]$destination){
 New-Item -ItemType Directory -Path $destination | Out-Null
 $pending=[Collections.Generic.Stack[string]]::new();$pending.Push($root);$count=0;$bytes=0L
 while($pending.Count -gt 0){
  Bound;$dir=$pending.Pop();No-Reparse $dir
  foreach($item in @(Get-ChildItem -LiteralPath $dir -Force)){
   $count++;if($count -gt 64){throw 'Owned snapshot exceeds 64 entries.'}
   No-Reparse $item.FullName
   $copy=Join-Path $destination ($item.FullName.Substring($root.Length+1))
   if($item.PSIsContainer){New-Item -ItemType Directory -Path $copy | Out-Null;$pending.Push($item.FullName)}
   else{
    $bytes+=$item.Length
    if($item.Length -gt 4MB -or $bytes -gt 16MB){throw 'Owned snapshot exceeds byte limits.'}
    Copy-Item -LiteralPath $item.FullName -Destination $copy
    if((Get-FileHash -LiteralPath $copy).Hash -cne (Get-FileHash -LiteralPath $item.FullName).Hash){throw 'Fresh snapshot copy mismatch.'}
   }
  }
 }
}
function Save-CompletedChunk([object] $Channel) {
 if ($null -eq $Channel.Task -or !$Channel.Task.IsCompleted) { return }
 $task = $Channel.Task; $Channel.Task = $null
 try { $count = $task.GetAwaiter().GetResult() } catch { $Channel.Error = $_.Exception.ToString(); throw }
 if ($count -eq 0) { $Channel.Eof = $true; return }
 $bytes = [Text.Encoding]::UTF8.GetByteCount($Channel.Buffer,0,$count)
 $Channel.Bytes += $bytes
 if ($Channel.Bytes -gt 4MB) { $Channel.Error = 'Driver log exceeded 4MiB; only bounded original prefix retained.'; throw $Channel.Error }
 $Channel.Writer.Write($Channel.Buffer,0,$count); $Channel.Writer.Flush()
 $Channel.Task = $Channel.Reader.ReadAsync($Channel.Buffer,0,$Channel.Buffer.Length)
}
try{
 if($Action -eq 'monitor-death'){
 $sentinelActor=Start-Driver 'sentinel' '0000007E' '--leaf sentinel'
 $sentinelRuntime=$null
 while(!$sentinelRuntime){
  Poll-Drivers;if($sentinelActor.Exited){throw 'Sentinel driver exited before readiness.'}
  $sentinelRuntime=Runtime-Ready $sentinelActor 'sentinel' 'leaf-ready'
  if(!$sentinelRuntime){[Threading.Thread]::Sleep(10)}
 }
 $sentinel=Identity-Handle (Join-Path $sentinelRuntime 'sentinel.identity') 'sentinel'
 }
 $fixtureArgs=if($Action -eq 'parent-exit'){'--parent-exit monitor-witness'}else{'--parent monitor-witness'}
 $targetActor=Start-Driver 'target' '00000000' $fixtureArgs
 while(!$targetRuntime){
  Poll-Drivers;if($targetActor.Exited){throw 'Target driver exited before parent/child readiness.'}
  $targetRuntime=Runtime-Ready $targetActor 'monitor-witness' 'parent-and-child-ready'
  if(!$targetRuntime){[Threading.Thread]::Sleep(10)}
 }
 $prefix=Join-Path $targetRuntime 'monitor-witness'
 $observedDriver=Identity-Handle ($prefix+'.driver') 'driver'
 if($observedDriver.Id -ne $targetActor.Process.Id -or
  $observedDriver.StartTime.ToUniversalTime().ToFileTimeUtc() -ne $targetActor.Process.StartTime.ToUniversalTime().ToFileTimeUtc()){
  throw 'Witness chain is not our exact target driver.'
 }
 $client=Identity-Handle ($prefix+'.client') 'client';$monitor=Identity-Handle ($prefix+'.monitor') 'monitor'
 $payload=Identity-Handle ($prefix+'.identity') 'payload';$grandchild=Identity-Handle ($prefix+'.child.identity') 'grandchild'
 foreach($process in @($client,$monitor)){
  if(!$process.MainModule.FileName.Equals($runner,[StringComparison]::OrdinalIgnoreCase)){throw 'Witness runner image path mismatch.'}
 }
 foreach($process in @($payload,$grandchild)){
  if(!$process.MainModule.FileName.Equals((Join-Path $targetRuntime 'fixture.exe'),[StringComparison]::OrdinalIgnoreCase)){throw 'Witness payload image path mismatch.'}
 }
 $targetCustodyValidated=$true
 if($Action -eq 'monitor-death' -and $sentinel.HasExited){throw 'Independent sentinel already stopped before target action.'}
 try{Assert-TargetStopped $true}catch{
  if($_.Exception.Message -cne 'Monitor-death exact target termination assertion mismatch.'){throw}
  $wrongExpectationRed=$true
 }
 if(!$wrongExpectationRed){throw 'Live-target wrong expectation did not fail.'}
 # Terminate only the validated retained monitor Process, never an enumerated PID.
 if($Action -eq 'monitor-death'){$monitor.Kill();$monitorKilled=$true}
 else{
  $release=$prefix+'.release';No-Reparse $release;No-Reparse ($release+'.pending')
  if((Test-Path -LiteralPath $release) -or (Test-Path -LiteralPath ($release+'.pending'))){throw 'Parent release input already exists.'}
  $stream=[IO.FileStream]::new(($release+'.pending'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
  try{
   $bytes=[Text.Encoding]::UTF8.GetBytes('exit-parent'+[char]13+[char]10)
   $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)
  }finally{$stream.Dispose()}
  [IO.File]::Move(($release+'.pending'),$release);$parentReleaseRequested=$true
 }
 foreach($process in @($monitor,$client,$payload,$grandchild)){
  Poll-Drivers;if(!$process.WaitForExit(10000)){throw 'Exact target process did not stop after monitor death.'}
 }
 Assert-TargetStopped $true;$targetStopped=$true
 if($payload.ExitCode -eq 126 -or $grandchild.ExitCode -eq 126){throw 'Natural expiry cannot prove monitor-death termination.'}
 $targetExitCodes=[ordered]@{payload=[int]$payload.ExitCode;grandchild=[int]$grandchild.ExitCode;client=[int]$client.ExitCode;monitor=[int]$monitor.ExitCode}
 if($Action -eq 'parent-exit'){
  if($payload.ExitCode -ne 0 -or $grandchild.ExitCode -ne 125){throw 'Ordinary parent exit must be0 and exact residual-child termination125.'}
 }else{
  $sentinelSurvived=!$sentinel.HasExited
  if(!$sentinelSurvived){throw 'Independent sentinel did not survive target monitor death.'}
 }
 do{
  Poll-Drivers
  $waiting=@($actors|Where-Object {!$_.Exited -or @($_.Readers|Where-Object {!$_.Eof}).Count -ne 0})
  if($waiting.Count -gt 0){[Threading.Thread]::Sleep(10)}
 }while($waiting.Count -gt 0)
 # Close completed log writers before a fresh read opens with FileShare.Read.
 foreach($actor in $actors){
  foreach($channel in $actor.Readers){
   $channel.Writer.Flush();$channel.Writer.Dispose();$channel.Closed=$true
  }
 }
 if($Action -eq 'monitor-death'){
 # Strict completion parsing must reject this deliberately interrupted journal.
 $errorText=[IO.File]::ReadAllText((Join-Path $targetActor.Root 'bootstrap.stderr'))
 if($targetActor.Status -ne 2 -or !$errorText.Contains('journal must contain the exact eight-record completion grammar')){
  throw 'Expected strict incomplete-journal rejection is missing.'
 }
 if($sentinelActor.Status -ne 0 -or !$sentinel.WaitForExit(10000)){throw 'Sentinel normal completion failed.'}
 $sentinelOutput=[IO.File]::ReadAllText((Join-Path $sentinelActor.Root 'bootstrap.stdout'))
 foreach($line in @('CLIENT_EXIT=0x0000004E','PAYLOAD_EXIT=0000007E','SUPERVISION=PayloadExited','CLEANUP_CONFIRMED=True','RUNTIME_REMOVED=True')){
  if(!$sentinelOutput.Contains($line)){throw "Missing sentinel completion: $line"}
 }
 if(Test-Path -LiteralPath $sentinelRuntime){throw 'Sentinel runtime remains after removal receipt.'}
 $sentinelCompleted=$true
 # Secure original interrupted files before observer-owned reset; no monitor
 # cleanup or complete eight-record receipt is fabricated.
 $snapshot=Join-Path $session 'monitor-death-evidence';New-Item -ItemType Directory -Path $snapshot | Out-Null
 Snapshot-Target $targetRuntime (Join-Path $snapshot 'runtime')
 $journals=@(Get-ChildItem -LiteralPath $targetActor.Run -File -Filter '.scoped-run-*.journal')
 if($journals.Count -ne 1){throw 'Expected one exact interrupted journal.'}
 foreach($journal in $journals){
  No-Reparse $journal.FullName
  if($journal.Length -gt 4MB){throw 'Interrupted journal exceeds its bound.'}
  Copy-Item -LiteralPath $journal.FullName -Destination (Join-Path $snapshot $journal.Name)
 }
 No-Reparse $targetRuntime
 Remove-Item -LiteralPath $targetRuntime -Recurse -Force
 if(Test-Path -LiteralPath $targetRuntime){throw 'Exact observer runtime retirement failed.'}
 $observerRemoved=$true;$complete=$true;$status=0
 }else{
  if($targetActor.Status -ne 0){throw 'Ordinary parent-exit driver failed.'}
  $output=[IO.File]::ReadAllText((Join-Path $targetActor.Root 'bootstrap.stdout'))
  foreach($line in @('CLIENT_EXIT=0x0000004E','PAYLOAD_EXIT=00000000','SUPERVISION=PayloadExited','CLEANUP_CONFIRMED=True','RUNTIME_REMOVED=True')){
   if(!$output.Contains($line)){throw 'Ordinary parent-exit completion receipt missing.'}
  }
  if(Test-Path -LiteralPath $targetRuntime){throw 'Ordinary parent-exit runtime remains.'}
  $snapshot=Join-Path $session 'monitor-death-evidence'
  Snapshot-Target $targetActor.Run $snapshot
  $witness=@(Get-ChildItem -LiteralPath $snapshot -Recurse -File -Filter 'monitor-witness.child.identity')
  if($witness.Count -ne 1){throw 'Independent residual-child witness inventory mismatch.'}
  No-Reparse $witness[0].FullName
  $identity=$observations['grandchild']
  $expected='pid='+$identity.pid+' creation='+$identity.creation+[char]13+[char]10
  if([IO.File]::ReadAllText($witness[0].FullName) -cne $expected){throw 'Independent residual-child snapshot identity mismatch.'}
  $normalClosure=$true;$complete=$true;$status=0
 }
}catch{$failure=$_.Exception.ToString()}
finally{
 # Exceptional cleanup may touch only the completely validated target chain.
 # Before that binding exists, driver death triggers its established lease cleanup;
 # unknown identities and unfinished runtimes remain evidence, never reset targets.
 if(!$complete -and $targetCustodyValidated){
  foreach($process in @($monitor,$client,$payload,$grandchild)){
   try{
    if(!$process.HasExited){$process.Kill()}
    if(!$process.WaitForExit(10000)){throw 'Validated target cleanup exit unconfirmed.'}
   }catch{$failure+=[Environment]::NewLine+'Validated target cleanup: '+$_.Exception.ToString()}
  }
 }
 foreach($actor in $actors){
  if($actor.Started -and !$actor.Exited){
   try{
    if(!$actor.Process.HasExited){$actor.Process.Kill()}
    if(!$actor.Process.WaitForExit(10000)){throw 'Exact driver cleanup exit unconfirmed.'}
    $actor.Exited=$true;$actor.Process.Refresh();$actor.Status=[int]$actor.Process.ExitCode
   }catch{$failure+=[Environment]::NewLine+'Exact driver cleanup: '+$_.Exception.ToString();$complete=$false}
  }
  $drain=[Diagnostics.Stopwatch]::StartNew()
  do{
   foreach($channel in $actor.Readers){
    try{Save-CompletedChunk $channel}catch{$failure+=[Environment]::NewLine+'Original pipe read: '+$_.Exception.ToString();$complete=$false}
   }
   $pending=@($actor.Readers|Where-Object {$null -ne $_.Task})
   if($pending.Count -eq 0){break};[Threading.Thread]::Sleep(10)
  }while($drain.ElapsedMilliseconds -lt 10000)
  $actor.Drained=$actor.Readers.Count -eq 2 -and @($actor.Readers|Where-Object {!$_.Eof -or $_.Error}).Count -eq 0
  foreach($channel in $actor.Readers){
   if($channel.Closed){continue}
   try{$channel.Writer.Flush()}
   catch{$failure+=[Environment]::NewLine+'Original writer flush: '+$_.Exception.ToString();$complete=$false}
   try{$channel.Writer.Dispose();$channel.Closed=$true}
   catch{$failure+=[Environment]::NewLine+'Original writer close: '+$_.Exception.ToString();$complete=$false}
  }
  if(!$actor.Drained){$failure+=[Environment]::NewLine+'Original driver pipes not drained; retain resources.';$complete=$false}
  if($actor.Exited -and $actor.Drained){
   foreach($channel in $actor.Readers){
    try{$channel.Reader.Dispose()}
    catch{$failure+=[Environment]::NewLine+'Original reader close: '+$_.Exception.ToString();$complete=$false}
   }
   try{$actor.Process.Dispose()}
   catch{$failure+=[Environment]::NewLine+'Exact driver handle close: '+$_.Exception.ToString();$complete=$false}
  }
 }
 foreach($process in $handles){
  try{if($process.HasExited){$process.Dispose()}}
  catch{$failure+=[Environment]::NewLine+'Identity handle retained: '+$_.Exception.ToString();$complete=$false}
 }
}
if(!$complete){$status=2}
$driverWasStarted=@($actors|Where-Object {$_.Started}).Count -gt 0
$record=[ordered]@{id=$id;scope=$session;exit=$status;accepted=$complete;failure=$failure;driver_launched=$driverWasStarted;
 action=$Action;parent_release_requested=$parentReleaseRequested;target_exit_codes=$targetExitCodes;
 monitor_killed=$monitorKilled;wrong_expectation_red=$wrongExpectationRed;target_stopped=$targetStopped;
 sentinel_survived=$sentinelSurvived;sentinel_completed=$sentinelCompleted;observer_runtime_removed=$observerRemoved;
 monitor_cleanup_receipt_claimed=$normalClosure;target_custody_validated=$targetCustodyValidated;identities=$observations;fixture_sha256=$FixtureSha256;
 parent_environment_changed=$false;product_run=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
$files=@(Get-Item -LiteralPath (Join-Path $session 'observer.json'))
foreach($actor in $actors){
 foreach($name in @('bootstrap.stdout','bootstrap.stderr')){
  $path=Join-Path $actor.Root $name
  if(Test-Path -LiteralPath $path){$files+=Get-Item -LiteralPath $path}
 }
}
if($complete){
 $files+=@(Get-ChildItem -LiteralPath (Join-Path $session 'monitor-death-evidence') -Recurse -File)
 if($Action -eq 'monitor-death'){$files+=@(Get-ChildItem -LiteralPath $sentinelActor.Run -Recurse -File)}
}
if ($files.Count -gt 64 -or ($files | Measure-Object Length -Sum).Sum -gt 16MB) { throw 'Export inventory exceeds the declared bounds; preserve all guest evidence.' }
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
    $serial.Open(); Emit-Frame 'BEGIN' @{id=$id;scope=$session;exit=$status;accepted=$complete;full_record='observer.json'}
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
    Emit-Frame 'END' @{id=$id;files=$files.Count;accepted=$complete;exit=$status;guest_evidence_retained=$true;driver_launched=$driverWasStarted}
} finally { $serial.Dispose() }
$record | ConvertTo-Json -Compress
exit $status
