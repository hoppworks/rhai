param(
 [Parameter(Mandatory=$true)][string]$BuildRoot,
 [Parameter(Mandatory=$true)][string]$RetainedBuild,
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9-]+$')][string]$Id,
 [Parameter(Mandatory=$true)][ValidateSet('ASSOCIATION_DENIED','POST_CREATE_ABORT')][string]$Profile
)
$ErrorActionPreference='Stop'
$id=$Id;$session=[IO.Path]::GetFullPath($Session)
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse creation-control path refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
 }
}
if([IO.Path]::GetDirectoryName($session) -cne $private -or [IO.Path]::GetFileName($session) -notmatch '^creation-control-[0-9a-f]{32}$'){throw 'Exact own private creation-control scope required.'}
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
$runnerName='ScopedRunner-'+$Profile+'.exe'
$runnerHash=Read-BinaryPin $BuildRoot $runnerName
$driverHash=Read-BinaryPin $RetainedBuild 'MonitorAcceptanceDriver.exe'
$fixtureHash=Read-BinaryPin $RetainedBuild 'PayloadFixture.exe'
if($driverHash -cne '531259b5a4003abbdab2eca4521da64c295563d33a7486c898645402e8e4ac76' -or $fixtureHash -cne '4ce2f3f13ab9ed2bef02a675fd607ca993e90488e1c8f48e4bc160881f137846'){throw 'Retained compatible component provenance changed.'}
$parentEnvironment=@{}
foreach($key in @('AGENT_RUNTIME_DIR','TMP','TEMP','CARGO_HOME','CARGO_TARGET_DIR')){$parentEnvironment[$key]=[Environment]::GetEnvironmentVariable($key)}
$parentCwd=[Environment]::CurrentDirectory
$run=Join-Path $session 'run';$input=Join-Path $session 'input';$bin=Join-Path $session 'bin'
New-Item -ItemType Directory -Path $run,$input,$bin|Out-Null
foreach($copy in @(@{from=(Join-Path $BuildRoot $runnerName);to=(Join-Path $bin 'ScopedRunner.exe');hash=$runnerHash},@{from=(Join-Path $RetainedBuild 'MonitorAcceptanceDriver.exe');to=(Join-Path $bin 'MonitorAcceptanceDriver.exe');hash=$driverHash},@{from=(Join-Path $RetainedBuild 'PayloadFixture.exe');to=(Join-Path $input 'fixture.exe');hash=$fixtureHash})){
 Copy-Item -LiteralPath $copy.from -Destination $copy.to
 if((Get-FileHash -LiteralPath $copy.to).Hash.ToLowerInvariant() -cne $copy.hash){throw 'Control component copy mismatch.'}
}
$buildReadback=Join-Path $session 'build-readback';New-Item -ItemType Directory -Path $buildReadback|Out-Null
$buildRun=[IO.Path]::GetDirectoryName($BuildRoot);$buildSession=[IO.Directory]::GetParent([IO.Path]::GetDirectoryName($buildRun)).FullName
foreach($name in @('build-manifest.txt','run-result.txt')){Copy-Item -LiteralPath (Join-Path $buildRun $name) -Destination $buildReadback}
foreach($name in @('build-observer.json','bootstrap.stdout','bootstrap.stderr')){Copy-Item -LiteralPath (Join-Path $buildSession $name) -Destination $buildReadback}
Copy-Item -LiteralPath (Join-Path $buildRun 'logs') -Destination $buildReadback -Recurse
$protected="protected-before-failed-association`r`n"
[IO.File]::WriteAllText((Join-Path $input 'must-not-run.txt'),$protected,[Text.UTF8Encoding]::new($false))
$stdout=Join-Path $session 'bootstrap.stdout';$stderr=Join-Path $session 'bootstrap.stderr'
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName=Join-Path $bin 'MonitorAcceptanceDriver.exe'
$info.Arguments='--mode success --source "'+$input+'" --exe fixture.exe --expected-payload-exit 00000000 -- must-not-run.txt'
$info.WorkingDirectory=$bin;$info.UseShellExecute=$false;$info.CreateNoWindow=$true
$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
$info.EnvironmentVariables['AGENT_RUNTIME_DIR']=$run
if($null -ne $global:RhaiCreationPendingCustody){throw 'Previous exact creation-control custody is unresolved; preserve it.'}
$process=[Diagnostics.Process]::new();$process.StartInfo=$info
$readers=[Collections.Generic.List[object]]::new()
# Publish stable owners before Start and before acquisition into each channel.
$global:RhaiCreationPendingCustody=[pscustomobject]@{Process=$process;Readers=$readers;Scope=$session;ExactExitConfirmed=$false;PipesDrained=$false;ProcessDisposed=$false}
$status=-1;$complete=$false;$failure='';$started=$false;$exited=$false;$pipesDrained=$false
$observerDeadline=[Diagnostics.Stopwatch]::StartNew()
$trace=@{};$runtimeObserved=$null;$journalPath=$null;$actorStopped=$false;$actorDisposition='unverified';$markerRed=$false;$parentChanged=$false;$ownExecutablesStopped=$false
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
  $driverBound=190
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
   if (!$process.HasExited) { $process.Kill() }
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
 $global:RhaiCreationPendingCustody.ExactExitConfirmed=$exited
 $global:RhaiCreationPendingCustody.PipesDrained=$pipesDrained
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
   try{$process.Dispose();$global:RhaiCreationPendingCustody.ProcessDisposed=$true}catch{$failure+="`nExact Process Dispose failed: "+$_.Exception.ToString()}
  }
 }
 $processDisposed=$global:RhaiCreationPendingCustody.ProcessDisposed
 if($exited -and $pipesDrained -and $processDisposed -and @($readers|Where-Object{!$_.WriterDisposed -or !$_.ReaderDisposed}).Count -eq 0){$global:RhaiCreationPendingCustody=$null}
}
$custodyPending=$null -ne $global:RhaiCreationPendingCustody
$channelClosure=@($readers|ForEach-Object{@{reader_acquired=($null -ne $_.Reader);reader_disposed=$_.ReaderDisposed;writer_acquired=($null -ne $_.Writer);writer_disposed=$_.WriterDisposed;eof=$_.Eof;error=$_.Error;pending_task=($null -ne $_.Task)}})

if($started -and $exited -and $pipesDrained -and !$custodyPending -and !$failure){
 try{
  # The regular success parser intentionally rejects retained four-record failure
  # journals. Do not turn that into a successful eight-record removal receipt.
  $closureWait=[Diagnostics.Stopwatch]::StartNew()
  do{
   $active=@(Get-CimInstance Win32_Process|Where-Object{$_.ExecutablePath -and $_.ExecutablePath.StartsWith($bin+'\',[StringComparison]::OrdinalIgnoreCase)})
   if($active.Count -eq 0){$ownExecutablesStopped=$true;break}
   if($closureWait.Elapsed.TotalSeconds -ge 60){throw 'Owned monitor/client executable remains live.'}
   [Threading.Thread]::Sleep(20)
  }while($true)
  $journals=@(Get-ChildItem -LiteralPath $run -File -Force -Filter '.scoped-run-*')
  if($journals.Count -ne 1){throw 'Expected one exact original journal.'}
  $journalPath=$journals[0].FullName;No-Reparse $journalPath
  $stream=[IO.File]::Open($journalPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
  try{
   if($stream.Length -gt 65536){throw 'Journal exceeds failure-control bound.'}
   $bytes=[byte[]]::new([int]$stream.Length);$at=0
   while($at -lt $bytes.Length){$count=$stream.Read($bytes,$at,$bytes.Length-$at);if($count -eq 0){throw 'Short original journal read.'};$at+=$count}
  }finally{$stream.Dispose()}
  $text=[Text.Encoding]::ASCII.GetString($bytes);$rows=@($text.Split([char]10)|Where-Object{$_ -ne ''})
  if($rows.Count -ne 4){throw 'Failure journal is not the exact four-record grammar.'}
  $decoded=@();$types=@('INTENT','IDENTITY','STAGED','LIFECYCLE')
  for($index=0;$index -lt $rows.Count;$index++){
   $row=$rows[$index]
   if($row -cnotmatch '^[0-9A-F]{4}:[0-9A-F]{8}:[ -~]+$'){throw 'Failure journal framing invalid.'}
   $body=$row.Substring(14);if([Convert]::ToInt32($row.Substring(0,4),16) -ne $body.Length){throw 'Failure journal length mismatch.'}
   # CRCs are independently verified by the host decoder before acceptance.
   $fields=$body.Split('|');if($fields[0] -cne $types[$index]){throw 'Failure journal order invalid.'};$decoded+=,$fields
  }
  $intent=$decoded[0];$identity=$decoded[1];$lifecycle=$decoded[3]
  if($intent.Count -ne 6 -or $intent[1] -cnotmatch '^[0-9a-f]{32}$' -or $intent[3] -cne $journalPath){throw 'Failure INTENT invalid.'}
  $runtimeObserved=[IO.Path]::GetFullPath($intent[2]);No-Reparse $runtimeObserved
  if([IO.Path]::GetDirectoryName($runtimeObserved) -cne $run -or [IO.Path]::GetFileName($runtimeObserved) -cne ('scoped-'+$intent[1])){throw 'Failed runtime not an exact owned child.'}
  for($index=1;$index -lt 4;$index++){if($decoded[$index][1] -cne $intent[1]){throw 'Failure invocation mismatch.'}}
  if($identity.Count -ne 5 -or $identity[2] -cnotmatch '^[0-9A-F]{16}:[0-9a-f]{32}$' -or $identity[3] -cne $intent[4] -or $identity[4] -cne $intent[5]){throw 'Failure identity binding invalid.'}
  if($lifecycle.Count -ne 7 -or $lifecycle[2] -cne $identity[2] -or $lifecycle[5] -cne 'cleanup=NONE' -or $lifecycle[6] -cne 'cleanup_confirmed=0' -or $lifecycle[4] -ceq 'operation=NONE'){throw 'Failure lifecycle was overstated or invalid.'}
  $tracePath=Join-Path $runtimeObserved 'native-creation-control.txt';No-Reparse $tracePath
  foreach($line in [IO.File]::ReadAllLines($tracePath)){
   $pair=$line.Split([char]'=',2);if($pair.Count -ne 2 -or $trace.ContainsKey($pair[0])){throw 'Native control trace malformed.'};$trace[$pair[0]]=$pair[1]
  }
  foreach($key in @('create_called','job_empty','process_closed_or_absent','thread_closed_or_absent','job_closed')){if($trace[$key] -cne 'True'){throw ('Native unwind did not prove '+$key)}}
  if($trace.transferred -cne 'False' -or $trace.cleanup_error -cne 'False'){throw 'Native creation cleanup did not complete cleanly; preserve diagnostics.'}
  if($Profile -ceq 'ASSOCIATION_DENIED'){
   if($trace.profile -cne 'association-denied' -or $trace.create_succeeded -cne 'False' -or $trace.create_error -cne '5' -or $trace.process_returned -cne 'False' -or $trace.thread_returned -cne 'False' -or $trace.process_id -cne '0' -or $trace.query_duplicate_closed -cne 'True' -or !$lifecycle[4].Contains('CreateProcessW(CREATE_SUSPENDED, JOB_LIST)')){throw 'Actual atomic association denial/error/returned handles mismatch.'}
   $actorDisposition='no_handles_returned_job_empty'
  }else{
   if($trace.root_termination_failed -cne 'True' -or $trace.root_signaled_after_termination_failure -cne 'True' -or $trace.profile -cne 'post-create-abort' -or $trace.create_succeeded -cne 'True' -or $trace.create_error -cne '0' -or $trace.process_returned -cne 'True' -or $trace.thread_returned -cne 'True' -or $trace.process_id -cnotmatch '^[1-9][0-9]*$' -or $trace.creation -cnotmatch '^[1-9][0-9]*$' -or !$lifecycle[4].Contains('CONTROL_ABORT_AFTER_REAL_SUSPENDED_CREATE')){throw 'Actual returned suspended-root control mismatch.'}
   $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById([int]$trace.process_id)}catch [ArgumentException]{}
   if($null -ne $actor){try{if(!$actor.HasExited -and $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$trace.creation){throw 'Exact suspended control root remains live.'}}finally{$actor.Dispose()}}
   $actorStopped=$true;$actorDisposition='exact_pid_start_stopped'
  }
  $marker=Join-Path $runtimeObserved 'must-not-run.txt';No-Reparse $marker
  function Assert-Protected([string]$Path,[string]$Expected){if([IO.File]::ReadAllText($Path) -cne $Expected){throw 'Protected marker mismatch.'}}
  try{Assert-Protected $marker "payload-started`r`n"}catch{if($_.Exception.Message -cne 'Protected marker mismatch.'){throw};$markerRed=$true}
  if(!$markerRed){throw 'Protected-state negative expectation was not rejected.'}
  Assert-Protected $marker $protected;Assert-Protected (Join-Path $input 'must-not-run.txt') $protected
  foreach($key in $parentEnvironment.Keys){if([Environment]::GetEnvironmentVariable($key) -cne $parentEnvironment[$key]){$parentChanged=$true}}
  if([Environment]::CurrentDirectory -cne $parentCwd){$parentChanged=$true}
  if($parentChanged){throw 'Observer parent environment/cwd changed.'}
  if($status -ne 2 -or ![IO.File]::ReadAllText($stderr).Contains('journal must contain the exact eight-record completion grammar')){throw 'Expected failed-creation Driver result not reached.'}
  $complete=$true
 }catch{$failure=$_.Exception.ToString()}
}
$record=[ordered]@{id=$id;scope=$session;run=$run;profile=$Profile;exit=$status;accepted=$complete;failure=$failure;driver_launched=$started;exact_driver_exited=$exited;pipes_drained=$pipesDrained;retained_driver_handles=(!$processDisposed);custody_pending=$custodyPending;process_disposed=$processDisposed;channel_closure=$channelClosure;retained_log_resources=(@($readers|Where-Object{($null -ne $_.Reader -and !$_.ReaderDisposed) -or ($null -ne $_.Writer -and !$_.WriterDisposed)}).Count -gt 0);allocated_runtime=$runtimeObserved;journal=$journalPath;runtime_retained=$true;automatic_removal_claimed=$false;native_trace=$trace;protected_marker_sensitivity=$markerRed;actor_stopped=$actorStopped;actor_disposition=$actorDisposition;owned_executables_stopped=$ownExecutablesStopped;parent_environment_changed=$parentChanged;binaries=@{runner=$runnerHash;driver=$driverHash;fixture=$fixtureHash};product_run=$false;elapsed_seconds=$observerDeadline.Elapsed.TotalSeconds}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
$files=@(Get-Item -LiteralPath (Join-Path $session 'observer.json'))
if(!$custodyPending){
 foreach($path in @($stdout,$stderr)){if(Test-Path -LiteralPath $path -PathType Leaf){$files+=@(Get-Item -LiteralPath $path)}}
 if($ownExecutablesStopped){$files+=@(Get-ChildItem -LiteralPath $run -Recurse -File)}
 $files+=@(Get-ChildItem -LiteralPath $buildReadback -Recurse -File)
 $files+=@(Get-ChildItem -LiteralPath $bin -File)
 $files+=@(Get-ChildItem -LiteralPath $input -File)
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
$record | ConvertTo-Json -Compress -Depth 8
if(!$complete){throw 'Native creation control incomplete; preserve original evidence and custody.'}
