param(
 [Parameter(Mandatory=$true)][string]$BuildRoot,
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][ValidateLength(1,96)][ValidatePattern('^[a-z0-9-]+$')][string]$Id,
 [Parameter(Mandatory=$true)][ValidateSet('watchdog','absolute')][string]$Mode
)
$ErrorActionPreference='Stop'
$id=$Id;$session=[IO.Path]::GetFullPath($Session)
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse deadline-control path refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
 }
}
if([IO.Path]::GetDirectoryName($session) -cne $private -or [IO.Path]::GetFileName($session) -notmatch '^deadline-control-[0-9a-f]{32}$'){throw 'Exact own private deadline-control scope required.'}
No-Reparse $session
if(Test-Path -LiteralPath $session){throw 'Owned scope exists; preserve it.'}
function Read-BinaryPin([string]$Build,[string]$Name){
 $Build=[IO.Path]::GetFullPath($Build);No-Reparse $Build
 $canonical='^'+[regex]::Escape($private)+'\\[A-Za-z0-9][A-Za-z0-9._-]{0,95}\\run\\monitor-source-[0-9a-f]{32}\\build$'
 if($Build -cnotmatch $canonical){throw 'Noncanonical owned build path.'}
 $manifest=Join-Path ([IO.Path]::GetDirectoryName($Build)) 'build-manifest.txt';No-Reparse $manifest
 $rows=@([IO.File]::ReadAllLines($manifest)|Where-Object{$_ -cmatch ('^[0-9a-f]{64}  build/'+[regex]::Escape($Name)+'$')})
 if($rows.Count -ne 1){throw 'One manifest-bound binary required.'}
 $file=Join-Path $Build $Name;No-Reparse $file;$hash=$rows[0].Substring(0,64)
 if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $hash){throw 'Manifest-bound binary changed.'}
 return $hash
}
$runnerName='ScopedRunnerDeadlineControl.exe'
$driverName=if($Mode -ceq 'watchdog'){'MonitorWATCHDOGDriver.exe'}else{'MonitorABSOLUTEDriver.exe'}
$fixtureName='MonitorDeadlineFixture.exe'
$runnerHash=Read-BinaryPin $BuildRoot $runnerName
$driverHash=Read-BinaryPin $BuildRoot $driverName
$fixtureHash=Read-BinaryPin $BuildRoot $fixtureName
$parentEnvironment=@{}
foreach($key in @('AGENT_RUNTIME_DIR','TMP','TEMP','CARGO_HOME','CARGO_TARGET_DIR')){$parentEnvironment[$key]=[Environment]::GetEnvironmentVariable($key)}
$parentCwd=[Environment]::CurrentDirectory
$run=Join-Path $session 'run';$input=Join-Path $session 'input';$bin=Join-Path $session 'bin'
New-Item -ItemType Directory -Path $run,$input,$bin|Out-Null
foreach($copy in @(@{name=$runnerName;to=(Join-Path $bin 'ScopedRunner.exe');hash=$runnerHash},@{name=$driverName;to=(Join-Path $bin 'MonitorAcceptanceDriver.exe');hash=$driverHash},@{name=$fixtureName;to=(Join-Path $input 'fixture.exe');hash=$fixtureHash})){
 Copy-Item -LiteralPath (Join-Path $BuildRoot $copy.name) -Destination $copy.to
 if((Get-FileHash -LiteralPath $copy.to).Hash.ToLowerInvariant() -cne $copy.hash){throw 'Deadline component copy mismatch.'}
}
$buildReadback=Join-Path $session 'build-readback';New-Item -ItemType Directory -Path $buildReadback|Out-Null
$buildRun=[IO.Path]::GetDirectoryName($BuildRoot);$buildSession=[IO.Directory]::GetParent([IO.Path]::GetDirectoryName($buildRun)).FullName
foreach($name in @('build-manifest.txt','run-result.txt')){Copy-Item -LiteralPath (Join-Path $buildRun $name) -Destination $buildReadback}
foreach($name in @('build-observer.json','bootstrap.stdout','bootstrap.stderr')){Copy-Item -LiteralPath (Join-Path $buildSession $name) -Destination $buildReadback}
Copy-Item -LiteralPath (Join-Path $buildRun 'logs') -Destination $buildReadback -Recurse
$stdout=Join-Path $session 'bootstrap.stdout';$stderr=Join-Path $session 'bootstrap.stderr'
$info=[Diagnostics.ProcessStartInfo]::new();$info.FileName=Join-Path $bin 'MonitorAcceptanceDriver.exe'
$driverMode=if($Mode -ceq 'absolute'){'absolute-deadline'}else{'success'}
$expectedPayload=if($Mode -ceq 'absolute'){'0000007D'}else{'00000000'}
$payloadArgument=if($Mode -ceq 'absolute'){'--membership-absolute'}else{'--membership-deadline'}
$info.Arguments='--mode '+$driverMode+' --source "'+$input+'" --exe fixture.exe --expected-payload-exit '+$expectedPayload+' -- '+$payloadArgument+' pair'
$info.WorkingDirectory=$bin;$info.UseShellExecute=$false;$info.CreateNoWindow=$true
$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
$info.EnvironmentVariables['AGENT_RUNTIME_DIR']=$run
$driverBound=if($Mode -ceq 'absolute'){1950}else{200}
$pairSeenLive=$false;$liveIdentities=@();$lastLiveElapsed=0.0;$lastProbe=-1.0;$lastHeartbeat=-30.0
$heartbeatCount=0;$driverPid=0;$driverCreation=0L;$observerKillUsed=$false
function Observe-LivePair {
 $roots=@(Get-ChildItem -LiteralPath $run -Force -Directory -Filter 'scoped-*')
 if(!$script:pairSeenLive){
  if($roots.Count -gt 1){throw 'Multiple owned deadline runtimes.'}
  if($roots.Count -ne 1 -or !(Test-Path -LiteralPath (Join-Path $roots[0].FullName 'pair.ready'))){return}
  if([IO.File]::ReadAllText((Join-Path $roots[0].FullName 'pair.ready')) -cne "both-membership-and-work-confirmed`r`n"){throw 'Independent pair readiness differs.'}
  $script:liveIdentities=@()
  foreach($name in @('pair.identity','pair.child.identity')){
   $text=[IO.File]::ReadAllText((Join-Path $roots[0].FullName $name))
   if($text -cnotmatch '^pid=([1-9][0-9]*) creation=([1-9][0-9]*)\r\n$'){throw 'Live deadline actor identity invalid.'}
   $script:liveIdentities+=@{pid=[int]$Matches[1];creation=[long]$Matches[2]}
  }
 }
 $allLive=$true
 foreach($identity in $script:liveIdentities){
  $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById($identity.pid)}catch [ArgumentException]{$allLive=$false}
  if($null -ne $actor){try{if($actor.HasExited -or $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -ne $identity.creation){$allLive=$false}}finally{$actor.Dispose()}}
 }
 if($allLive){$script:pairSeenLive=$true;$script:lastLiveElapsed=$observerDeadline.Elapsed.TotalSeconds}
}
function Emit-LiveDriver {
 # A fresh native Process/retained handle observation, never a stored PID alone.
 if($process.HasExited){return}
 $value=@{id=$id;mode=$Mode;scope=$session;pid=$driverPid;creation=$driverCreation;driver_exited=$false;exact_handle_owned=(!$processDisposed);elapsed_seconds=$observerDeadline.Elapsed.TotalSeconds;pair_seen_live=$script:pairSeenLive;last_pair_live_seconds=$script:lastLiveElapsed}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($value|ConvertTo-Json -Compress)))
 if($encoded.Length -gt 3500){throw 'Live-driver frame exceeds cap.'}
 $port=[IO.Ports.SerialPort]::new('COM1',115200);$port.WriteTimeout=2000
 try{$port.Open();$port.WriteLine('RHAI_DEADLINE_LIVE '+$encoded)}finally{$port.Dispose()}
 $script:heartbeatCount++
}
if($null -ne $global:RhaiDeadlinePendingCustody){throw 'Previous exact deadline-control custody is unresolved; preserve it.'}
$process=[Diagnostics.Process]::new();$process.StartInfo=$info
$readers=[Collections.Generic.List[object]]::new()
# Publish stable owners before Start and before acquisition into each channel.
$global:RhaiDeadlinePendingCustody=[pscustomobject]@{Process=$process;Readers=$readers;Scope=$session;ExactExitConfirmed=$false;PipesDrained=$false;ProcessDisposed=$false}
$script:pairSeenLive=$false;$script:liveIdentities=@();$script:lastLiveElapsed=0.0;$script:heartbeatCount=0
$status=-1;$complete=$false;$failure='';$started=$false;$exited=$false;$pipesDrained=$false
$observerDeadline=[Diagnostics.Stopwatch]::StartNew()
$runtime=$null;$journalPath=$null;$parentChanged=$false;$ownExecutablesStopped=$false;$monitorTrace=@{};$actors=@();$actorsStopped=$false;$runtimeAbsent=$false;$runtimeAbsenceRed=$false;$membershipRed=$false;$assertionRed=$false;$deadlineRed=$false;$processDisposed=$false
function Save-CompletedChunk([object] $Channel) {
 if ($null -eq $Channel.Task -or !$Channel.Task.IsCompleted) { return }
 try {
  $task=$Channel.Task;$Channel.Task=$null
  $count=$task.GetAwaiter().GetResult()
  if($count -eq 0){$Channel.Eof=$true;return}
  $Channel.Bytes += [Text.Encoding]::UTF8.GetByteCount($Channel.Buffer,0,$count)
  if($Channel.Bytes -gt 4MB){throw 'Driver log exceeded4MiB; bounded original prefix retained.'}
  $Channel.Writer.Write($Channel.Buffer,0,$count);$Channel.Writer.Flush()
  $Channel.Task=$Channel.Reader.ReadAsync($Channel.Buffer,0,$Channel.Buffer.Length)
 }catch{$Channel.Error=$_.Exception.ToString();throw}
}
try {
 if (!$process.Start()) { throw 'Native driver did not start.' }; $started = $true
 $driverPid=$process.Id;$driverCreation=$process.StartTime.ToUniversalTime().ToFileTimeUtc()
 $handle = $process.Handle
 if ($handle -eq [IntPtr]::Zero) { throw 'Exact retained driver handle missing.' }
 # A single async chunk per stream is in flight. Save each original chunk to its
 # bounded durable file immediately; no ReadToEnd result is lost on later failure.
 foreach ($definition in @(@{Output=$true;Path=$stdout},@{Output=$false;Path=$stderr})) {
  $channel=[pscustomobject]@{Reader=$null;Writer=$null;Buffer=[char[]]::new(1024);Task=$null;Bytes=0;Eof=$false;Error='';WriterDisposed=$false;ReaderDisposed=$false}
  $readers.Add($channel)
  $channel.Reader=if($definition.Output){$process.StandardOutput}else{$process.StandardError}
  $channel.Writer=[IO.StreamWriter]::new($definition.Path,$false,[Text.UTF8Encoding]::new($false))
  $channel.Task=$channel.Reader.ReadAsync($channel.Buffer,0,$channel.Buffer.Length)
 }
 while (!$process.WaitForExit(20)) {
  foreach ($channel in $readers) { Save-CompletedChunk $channel }
  if($observerDeadline.Elapsed.TotalSeconds-$lastProbe -ge 1){Observe-LivePair;$lastProbe=$observerDeadline.Elapsed.TotalSeconds}
  if($observerDeadline.Elapsed.TotalSeconds-$lastHeartbeat -ge 30){Emit-LiveDriver;$lastHeartbeat=$observerDeadline.Elapsed.TotalSeconds}
  if ($observerDeadline.Elapsed.TotalSeconds -ge $driverBound) { throw ('Public fixture driver exceeded its independent '+$driverBound.ToString()+'-second observer bound.') }
 }
 $exited = $true
 $process.Refresh(); if ($null -eq $process.ExitCode) { throw 'Driver exit unavailable.' }; $status = [int]$process.ExitCode
} catch { $failure = $_.Exception.ToString() }
finally {
 # Any failure after Start uses the same retained Process object. Never dispose
 # it or enumerate mutable runtime evidence while exact exit remains unconfirmed.
 if ($started -and !$exited) {
  try {
   if (!$process.HasExited) { $observerKillUsed=$true;$process.Kill() }
   if (!$process.WaitForExit(10000)) { throw 'Exact driver did not exit after observer cleanup.' }
   $exited = $true; $process.Refresh(); $status = [int]$process.ExitCode
  } catch { $failure += "`nExact driver cleanup failed: " + $_.Exception.ToString() }
 }
 $drainDeadline = [Diagnostics.Stopwatch]::StartNew()
 do {
  foreach ($channel in $readers) {
   try { Save-CompletedChunk $channel } catch { $failure += "`nOriginal pipe read failed: " + $_.Exception.ToString() }
  }
  $pending = @($readers | Where-Object { $null -ne $_.Task })
  if ($pending.Count -eq 0) { break }
  # This finite wait yields to both actual pipe readers, without a readiness claim.
  [Threading.Thread]::Sleep(10)
 } while ($drainDeadline.Elapsed.TotalSeconds -lt 10)
 $pipesDrained = $readers.Count -eq 2 -and @($readers | Where-Object { !$_.Eof -or $_.Error }).Count -eq 0
 $global:RhaiDeadlinePendingCustody.ExactExitConfirmed=$exited
 $global:RhaiDeadlinePendingCustody.PipesDrained=$pipesDrained
 foreach($channel in $readers){
  if($null -ne $channel.Writer){
   try{$channel.Writer.Flush()}catch{$failure+="`nOriginal log Flush failed: "+$_.Exception.ToString()}
   finally{try{$channel.Writer.Dispose();$channel.WriterDisposed=$true}catch{$failure+="`nOriginal log Dispose failed: "+$_.Exception.ToString()}}
  }
 }
 if($started -and !$pipesDrained){$failure+="`nOriginal pipe drain incomplete; retain exact owners and guest runtime."}
 if($exited -and $pipesDrained){
  foreach($channel in $readers){
   if($null -ne $channel.Reader){try{$channel.Reader.Dispose();$channel.ReaderDisposed=$true}catch{$failure+="`nOriginal reader Dispose failed: "+$_.Exception.ToString()}}
  }
  if(@($readers|Where-Object{!$_.WriterDisposed -or !$_.ReaderDisposed}).Count -eq 0){
   try{$process.Dispose();$global:RhaiDeadlinePendingCustody.ProcessDisposed=$true}catch{$failure+="`nExact Process Dispose failed: "+$_.Exception.ToString()}
  }
 }
 $processDisposed=$global:RhaiDeadlinePendingCustody.ProcessDisposed
 if($exited -and $pipesDrained -and $processDisposed -and @($readers|Where-Object{!$_.WriterDisposed -or !$_.ReaderDisposed}).Count -eq 0){$global:RhaiDeadlinePendingCustody=$null}
}
$custodyPending=$null -ne $global:RhaiDeadlinePendingCustody
$channelClosure=@($readers|ForEach-Object{@{reader_acquired=($null -ne $_.Reader);reader_disposed=$_.ReaderDisposed;writer_acquired=($null -ne $_.Writer);writer_disposed=$_.WriterDisposed;eof=$_.Eof;error=$_.Error;pending_task=($null -ne $_.Task)}})


if($started -and $exited -and $pipesDrained -and !$custodyPending -and !$failure){
 try{
  $output=[IO.File]::ReadAllText($stdout)
  if($observerKillUsed -or !$script:pairSeenLive){throw 'Independent live/deadline observation missing or observer killed the driver.'}
  if($Mode -ceq 'watchdog'){
   function Assert-WatchdogExit([int]$Expected){if($status -ne $Expected){throw 'Independent watchdog exit mismatch.'}}
   try{Assert-WatchdogExit 125}catch{if($_.Exception.Message -cne 'Independent watchdog exit mismatch.'){throw};$deadlineRed=$true}
   if(!$deadlineRed){throw 'Watchdog exit sensitivity missing.'};Assert-WatchdogExit 124
   if($status -ne 124 -or $observerDeadline.Elapsed.TotalSeconds -lt 179 -or $script:lastLiveElapsed -lt 178 -or !$output.Contains('WATCHDOG_CONTROL_MAIN_STALLED;BOUND_MS=180000')){throw 'Real independent WatchDeadline124 branch was not established.'}
  }else{
   foreach($line in @('CLIENT_EXIT=0x0000004E','MODE=absolute-deadline;ACTION_CONFIRMED=True;','PAYLOAD_EXIT=0000007D','SUPERVISION=MonitorStopped','CLEANUP_CONFIRMED=True','RUNTIME_REMOVED=True')){if(!$output.Contains($line)){throw 'Real monitor absolute-deadline report missing.'}}
   if($status -ne 0 -or $observerDeadline.Elapsed.TotalSeconds -lt 1799 -or $script:lastLiveElapsed -lt 1798){throw 'Monitor deadline ended before the real30minute interval.'}
  }
  $closure=[Diagnostics.Stopwatch]::StartNew()
  do{
   $evidence=@(Get-ChildItem -LiteralPath $run -Force -Directory -Filter '.scoped-evidence-*')
   $journals=@(Get-ChildItem -LiteralPath $run -Force -File -Filter '.scoped-run-*.journal')
   $roots=@(Get-ChildItem -LiteralPath $run -Force -Directory -Filter 'scoped-*')
   if($roots.Count -eq 0 -and $evidence.Count -eq 1 -and $journals.Count -eq 1){
    $stream=$null
    try{
     $stream=[IO.File]::Open($journals[0].FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
     if($stream.Length -gt 65536){throw 'Deadline journal exceeds native bound.'}
     $reader=[IO.StreamReader]::new($stream,[Text.Encoding]::ASCII);$stream=$null
     try{$text=$reader.ReadToEnd()}finally{$reader.Dispose()}
     $lines=@($text.Split([char]10)|Where-Object{$_ -ne ''})
     if($lines.Count -eq 8 -and $lines[-1].Contains(':REMOVED|')){break}
    }catch [IO.IOException]{if(($_.Exception.HResult -band 65535) -ne 32){throw}}finally{if($null -ne $stream){$stream.Dispose()}}
   }
   if($closure.Elapsed.TotalSeconds -ge 60){throw 'Exact deadline journal/runtime closure did not finish within60seconds.'}
   [Threading.Thread]::Sleep(20)
  }while($true)
  $journalPath=$journals[0].FullName;$parts=$lines[0].Split(':',3)[2].Split('|')
  if($parts[0] -cne 'INTENT'){throw 'Missing allocation intent.'};$runtime=[IO.Path]::GetFullPath($parts[2]);No-Reparse $runtime
  if([IO.Path]::GetDirectoryName($runtime) -cne $run -or [IO.Path]::GetFileName($runtime) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Deadline runtime outside exact owned control.'}
  function Assert-RuntimeAbsent([string]$Path){if(Test-Path -LiteralPath $Path){throw 'Runtime absence assertion failed.'}}
  try{Assert-RuntimeAbsent $evidence[0].FullName}catch{if($_.Exception.Message -cne 'Runtime absence assertion failed.'){throw};$runtimeAbsenceRed=$true}
  if(!$runtimeAbsenceRed){throw 'Runtime absence sensitivity missing.'};Assert-RuntimeAbsent $runtime;$runtimeAbsent=$true
  $snapshot=Join-Path $evidence[0].FullName 'runtime'
  $identities=@()
  foreach($name in @('pair','pair.child')){
   $identity=[IO.File]::ReadAllText((Join-Path $snapshot ($name+'.identity')))
   if($identity -cnotmatch '^pid=([0-9]+) creation=([0-9]+)\r\n$'){throw 'Exact actor identity invalid.'}
   $identities+=@{pid=[int]$Matches[1];creation=[long]$Matches[2];text=$identity.TrimEnd([char[]]@(13,10))}
  }
  if($identities[0].pid -eq $identities[1].pid){throw 'Distinct exact actors required.'}
  $sorted=@($identities.pid|Sort-Object)
  for($index=0;$index -lt 2;$index++){
   $name=if($index -eq 0){'pair'}else{'pair.child'}
   $actual=[IO.File]::ReadAllText((Join-Path $snapshot ($name+'.membership')))
   function Assert-Membership([int]$WantedSelf,[int]$WantedPeer){
    if($actual -cnotmatch '^self=pid=([0-9]+) creation=([0-9]+);peer=pid=([0-9]+) creation=([0-9]+);members=([0-9,]+);assigned=([0-9]+);returned=([0-9]+)\r\n$'){throw 'Exact native Job membership mismatch.'}
    $m=$Matches;$members=@($m[5].Split(',')|ForEach-Object{[int]$_});$ordered=@($members|Sort-Object -Unique)
    if([int]$m[1] -ne $WantedSelf -or [int]$m[3] -ne $WantedPeer -or [long]$m[2] -ne $identities[$index].creation -or [long]$m[4] -ne $identities[1-$index].creation -or $members.Count -lt 2 -or $members.Count -gt 16 -or $members.Count -ne [int]$m[6] -or $members.Count -ne [int]$m[7] -or ($members -join ',') -cne ($ordered -join ',') -or $members -contains 0 -or $members -notcontains $WantedSelf -or $members -notcontains $WantedPeer){throw 'Exact native Job membership mismatch.'}
   }
   if($index -eq 0){try{Assert-Membership 0 $identities[1].pid}catch{if($_.Exception.Message -cne 'Exact native Job membership mismatch.'){throw};$membershipRed=$true}}
   Assert-Membership $identities[$index].pid $identities[1-$index].pid
   $actor=$null
   try{$actor=[Diagnostics.Process]::GetProcessById($identities[$index].pid)}catch [ArgumentException]{}
   if($null -ne $actor){try{if(!$actor.HasExited -and $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq $identities[$index].creation){throw 'Exact actor remains live.'}}finally{$actor.Dispose()}}
  }
  $actors=$identities;$actorsStopped=$true
  $parentWork=[IO.File]::ReadAllText((Join-Path $snapshot 'pair.work'))
  $childWork=[IO.File]::ReadAllText((Join-Path $snapshot 'pair.child.work'))
  function Assert-Work([string]$Wanted){if($childWork -cne $Wanted+[char]13+[char]10){throw 'Independent child work mismatch.'}}
  try{Assert-Work 'wrong-child-work'}catch{if($_.Exception.Message -cne 'Independent child work mismatch.'){throw};$assertionRed=$true}
  Assert-Work 'child-work-after-both-membership'
  if($parentWork -cne "parent-work-after-both-membership`r`n" -or !$membershipRed -or !$assertionRed){throw 'Work/order control missing.'}
  for($index=0;$index -lt 2;$index++){if($actors[$index].pid -ne $script:liveIdentities[$index].pid -or $actors[$index].creation -ne [long]$script:liveIdentities[$index].creation){throw 'Live and stopped actor identities differ.'}}

  $traces=@(Get-ChildItem -LiteralPath $run -File -Filter 'monitor-deadline-*.txt')
  if($traces.Count -ne 1){throw 'One exact native monitor deadline trace required.'}
  foreach($line in [IO.File]::ReadAllLines($traces[0].FullName)){$pair=$line.Split([char]'=',2);if($pair.Count -ne 2 -or $monitorTrace.ContainsKey($pair[0])){throw 'Native monitor trace invalid.'};$monitorTrace[$pair[0]]=$pair[1]}
  foreach($key in @('started','absolute_ms','expired_at','lease_at_expiry','loop_stopped_at')){if($monitorTrace[$key] -notmatch '^(0|[1-9][0-9]*)$'){throw 'Monitor monotonic field invalid.'}}
  if($monitorTrace.absolute_ms -cne '1800000' -or [long]$monitorTrace.started -le 0){throw 'Production monitor bound was changed.'}
  if($Mode -ceq 'absolute'){
   function Assert-Absolute([long]$Expected){
    $delta=[long]$monitorTrace.expired_at-[long]$monitorTrace.started
    if($monitorTrace.expiry -cne 'AbsoluteDeadline' -or $delta -lt $Expected -or $delta -gt $Expected+30000 -or [long]$monitorTrace.lease_at_expiry -ne ([long]$monitorTrace.started+$Expected) -or $monitorTrace.client_signaled -cne 'False'){throw 'Independent native absolute deadline mismatch.'}
   }
   try{Assert-Absolute 1700000}catch{if($_.Exception.Message -cne 'Independent native absolute deadline mismatch.'){throw};$deadlineRed=$true}
   # The wrong bound lies outside the entire elapsed tolerance and exact lease clamp.
   if(!$deadlineRed){throw 'Absolute deadline negative expectation was not rejected.'}
   Assert-Absolute 1800000
  }elseif($monitorTrace.expiry -cne 'None' -or $monitorTrace.expired_at -cne '0' -or ([long]$monitorTrace.loop_stopped_at-[long]$monitorTrace.started) -lt 179000){throw 'A policy expiry, rather than actual driver death, ended watchdog control.'}
  $wait=[Diagnostics.Stopwatch]::StartNew()
  do{
   $active=@(Get-CimInstance Win32_Process|Where-Object{$_.ExecutablePath -and $_.ExecutablePath.StartsWith($bin+'\',[StringComparison]::OrdinalIgnoreCase)})
   if($active.Count -eq 0){$ownExecutablesStopped=$true;break}
   if($wait.Elapsed.TotalSeconds -ge 60){throw 'Owned deadline client/monitor still live.'};[Threading.Thread]::Sleep(20)
  }while($true)
  foreach($key in $parentEnvironment.Keys){if([Environment]::GetEnvironmentVariable($key) -cne $parentEnvironment[$key]){$parentChanged=$true}}
  if([Environment]::CurrentDirectory -cne $parentCwd){$parentChanged=$true};if($parentChanged){throw 'Observer parent environment/cwd changed.'}
  $complete=$true
 }catch{$failure=$_.Exception.ToString()}
}
$failureSummary=$failure;if($failureSummary.Length -gt 512){$failureSummary=$failureSummary.Substring(0,512)+' [original retained]'}
$record=[ordered]@{id=$id;mode=$Mode;scope=$session;run=$run;exit=$status;accepted=$complete;failure=$failureSummary;driver_pid=$driverPid;driver_creation=$driverCreation;observer_kill_used=$observerKillUsed;driver_launched=$started;exact_driver_exited=$exited;pipes_drained=$pipesDrained;process_disposed=$processDisposed;custody_pending=$custodyPending;channel_closure=$channelClosure;retained_driver_handles=(!$processDisposed);allocated_runtime=$runtime;runtime_absent_readback=$runtimeAbsent;runtime_absence_negative_control=$runtimeAbsenceRed;actors=$actors;actors_stopped=$actorsStopped;pair_seen_live=$script:pairSeenLive;last_pair_live_seconds=$script:lastLiveElapsed;heartbeat_count=$script:heartbeatCount;membership_negative_control=$membershipRed;wrong_expectation_red=$assertionRed;deadline_negative_control=$deadlineRed;monitor_trace=$monitorTrace;owned_executables_stopped=$ownExecutablesStopped;parent_environment_changed=$parentChanged;binaries=@{runner=$runnerHash;driver=$driverHash;fixture=$fixtureHash};elapsed_seconds=$observerDeadline.Elapsed.TotalSeconds;product_run=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
$files=@(Get-Item -LiteralPath (Join-Path $session 'observer.json'))
if(!$custodyPending){
 foreach($path in @($stdout,$stderr)){if(Test-Path -LiteralPath $path -PathType Leaf){$files+=@(Get-Item -LiteralPath $path)}}
 if($failure){$failurePath=Join-Path $session 'failure-original.txt';[IO.File]::WriteAllText($failurePath,$failure,[Text.UTF8Encoding]::new($false));$files+=@(Get-Item -LiteralPath $failurePath)}
 if($ownExecutablesStopped){$files+=@(Get-ChildItem -LiteralPath $run -Recurse -File)}
 $files+=@(Get-ChildItem -LiteralPath $buildReadback -Recurse -File);$files+=@(Get-ChildItem -LiteralPath $bin -File);$files+=@(Get-ChildItem -LiteralPath $input -File)
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
    $serial.Open(); Emit-Frame 'BEGIN' @{id=$id;scope=$session;mode=$Mode;accepted=$complete;exit=$status;driver_pid=$driverPid;driver_creation=$driverCreation}
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
$record | ConvertTo-Json -Compress -Depth 8
if(!$complete){throw 'Native deadline control incomplete; preserve original evidence and custody.'}
