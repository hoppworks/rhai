param(
 [Parameter(Mandatory=$true)][string]$FixturePath,
 [Parameter(Mandatory=$true)][string]$FixtureSha256,
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][ValidateLength(1,96)][ValidatePattern('^[a-z0-9-]+$')][string]$Id,
 [ValidateSet('RED','GREEN','RETIREMENT_ABORT')][string]$Phase='RED',
 [ValidateSet('environment','job-resources','job-quota')][string]$Contract='environment',
 [Parameter(Mandatory=$true)][string]$BuildRoot,
 [switch]$ReturnStatusToCaller
)
$ErrorActionPreference='Stop'
$id=$Id;$session=[IO.Path]::GetFullPath($Session)
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
if([IO.Directory]::GetParent($session).FullName -cne $private -or [IO.Path]::GetFileName($session) -notmatch '^env-control-[0-9a-f]{32}$'){throw 'Exact own private environment scope required.'}
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse environment-control path refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
 }
}
$expected=@{}
 $build=[IO.Path]::GetFullPath($BuildRoot);No-Reparse $build
 if([IO.Path]::GetFileName($build) -cne 'build'){throw 'BuildRoot must be the exact compiled build directory.'}
 $buildRun=[IO.Directory]::GetParent($build).FullName
 if([IO.Path]::GetFileName($buildRun) -notmatch '^monitor-source-[0-9a-f]{32}$'){throw 'BuildRoot must belong to a canonical monitor-source run.'}
 $buildParent=[IO.Directory]::GetParent($buildRun).FullName
 if([IO.Path]::GetFileName($buildParent) -cne 'run' -or [IO.Directory]::GetParent($buildParent).Parent.FullName -cne $private){throw 'BuildRoot must be inside its own canonical private session scope.'}
 $buildManifest=Join-Path $buildRun 'build-manifest.txt';No-Reparse $buildManifest
 if(!(Test-Path -LiteralPath $buildManifest -PathType Leaf)){throw 'Retained build manifest is missing.'}
 $buildManifestLines=[IO.File]::ReadAllLines($buildManifest)
 foreach($name in @('ScopedRunner.exe','MonitorAcceptanceDriver.exe','PayloadFixture.exe')){
  $matches=@($buildManifestLines | Where-Object {$_ -match ('^(?<hash>[0-9a-f]{64})  build/'+[regex]::Escape($name)+'$')})
  if($matches.Count -ne 1){throw 'Build manifest does not bind exactly one required binary.'}
  $hash=[regex]::Match($matches[0],'^([0-9a-f]{64})  ').Groups[1].Value
  $expected[$name]=$hash
  $file=Join-Path $build $name;No-Reparse $file
  if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $hash){throw 'Compiled binary differs from its retained build manifest.'}
 }
if($Contract -ceq 'job-quota' -and $Phase -cne 'GREEN'){throw 'Actual quota denial uses current bounded production tools and GREEN phase.'}

No-Reparse $session;No-Reparse $FixturePath
if((Get-FileHash -LiteralPath $FixturePath).Hash.ToLowerInvariant() -cne $FixtureSha256){throw 'Native environment fixture changed.'}
if(Test-Path -LiteralPath $session){throw 'Own environment scope exists; preserve it.'}
$parentEnvironment=@{}
foreach($key in @('AGENT_RUNTIME_DIR','TMP','TEMP','CARGO_HOME','CARGO_TARGET_DIR')){$parentEnvironment[$key]=[Environment]::GetEnvironmentVariable($key)}
$parentCwd=[Environment]::CurrentDirectory
$run=Join-Path $session 'run';$input=Join-Path $session 'input'
New-Item -ItemType Directory -Path $run,$input | Out-Null
$buildReadback=$null
if($BuildRoot){
 $buildReadback=Join-Path $session 'build-readback';New-Item -ItemType Directory -Path $buildReadback | Out-Null
 Copy-Item -LiteralPath $buildManifest -Destination $buildReadback
 Copy-Item -LiteralPath (Join-Path $buildRun 'run-result.txt') -Destination $buildReadback
 $buildSession=[IO.Directory]::GetParent($buildParent).FullName
 foreach($outerName in @('build-observer.json','bootstrap.stdout','bootstrap.stderr')){
  $outerPath=Join-Path $buildSession $outerName;No-Reparse $outerPath
  if(!(Test-Path -LiteralPath $outerPath -PathType Leaf)){throw ('Required outer build readback is missing: '+$outerName)}
  Copy-Item -LiteralPath $outerPath -Destination $buildReadback
 }
 $buildLogs=Join-Path $buildRun 'logs'
 if(Test-Path -LiteralPath $buildLogs -PathType Container){Copy-Item -LiteralPath $buildLogs -Destination $buildReadback -Recurse}
 foreach($readbackFile in (Get-ChildItem -LiteralPath $buildReadback -Recurse -File)){
  No-Reparse $readbackFile.FullName
  if($readbackFile.Length -gt 4MB){throw 'A build diagnostic exceeds the bounded export file cap.'}
 }
}
Copy-Item -LiteralPath $FixturePath -Destination (Join-Path $input 'fixture.exe')
if((Get-FileHash -LiteralPath (Join-Path $input 'fixture.exe')).Hash.ToLowerInvariant() -cne $FixtureSha256){throw 'Fixture copy mismatch.'}
$bin=Join-Path $session 'bin';New-Item -ItemType Directory -Path $bin|Out-Null
foreach($name in @('ScopedRunner.exe','MonitorAcceptanceDriver.exe')){
 $sourceBinary=Join-Path $build $name;No-Reparse $sourceBinary
 Copy-Item -LiteralPath $sourceBinary -Destination (Join-Path $bin $name)
 if((Get-FileHash -LiteralPath (Join-Path $bin $name)).Hash.ToLowerInvariant() -cne $expected[$name]){throw 'Owned public tool copy differs from source-bound build.'}
}
$jobQuotaObserved=@{};$jobQuotaGreen=$false;$jobQuotaSensitivity=$false;$quotaProtectedSensitivity=$false;$quotaActorsStopped=$false
$expectedPayload=if($Phase -ceq 'GREEN'){'00000000'}else{'0000002A'}
$runtimeAbsenceRed=$false;$runtimeAbsent=$false;
$jobResourcesObserved=@{};$jobResourcesRed=$false;$jobResourcesGreen=$false;$jobResourcesSensitivity=$false;$jobActorsStopped=$false
$environmentObserved=@{};$environmentMismatches=@();$runtimeObserved=$null
$environmentRed=$false;$environmentGreen=$false;$workRetirementRed=$false;$workRetirementGreen=$false;$parentChanged=$false
$stdout = Join-Path $session 'bootstrap.stdout'; $stderr = Join-Path $session 'bootstrap.stderr'
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $bin 'MonitorAcceptanceDriver.exe'
$payloadArguments=if($Phase -ceq 'RETIREMENT_ABORT'){'--retirement-abort'}elseif($Contract -ceq 'job-resources'){'payload-job-resources.txt --job-resources'}elseif($Contract -ceq 'job-quota'){'payload-job-quota.txt --job-quota'}else{'payload-environment.txt --environment'}
$info.Arguments = '--mode success --source "'+$input+'" --exe fixture.exe --expected-payload-exit '+$expectedPayload+' -- '+$payloadArguments
$info.WorkingDirectory = $bin; $info.UseShellExecute = $false; $info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
$info.EnvironmentVariables['AGENT_RUNTIME_DIR'] = $run
if($null -ne $global:RhaiPayloadPendingCustody){throw 'Previous exact public-payload custody is unresolved; preserve it.'}
$process=[Diagnostics.Process]::new();$process.StartInfo=$info
$readers=[Collections.Generic.List[object]]::new()
# Publish stable owners before Start and before acquisition into each channel.
$global:RhaiPayloadPendingCustody=[pscustomobject]@{Process=$process;Readers=$readers;Scope=$session;ExactExitConfirmed=$false;PipesDrained=$false;ProcessDisposed=$false}
$status=-1;$complete=$false;$failure='';$started=$false;$exited=$false;$pipesDrained=$false
$observerDeadline=[Diagnostics.Stopwatch]::StartNew()
$hostRecord=$false;$processDisposed=$false;$observerKillUsed=$false;$driverElapsedSeconds=0.0;$driverPid=0;$driverCreation=0L;$ownExecutablesStopped=$false
$driverBound=if($Contract -ceq 'job-quota'){190}elseif($Phase -ceq 'RETIREMENT_ABORT'){180}else{10}
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
  if ($observerDeadline.Elapsed.TotalSeconds -ge $driverBound) { throw ('Public fixture driver exceeded its independent '+$driverBound.ToString()+'-second observer bound.') }
 }
 $exited = $true;$driverElapsedSeconds=$observerDeadline.Elapsed.TotalSeconds
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
 $global:RhaiPayloadPendingCustody.ExactExitConfirmed=$exited
 $global:RhaiPayloadPendingCustody.PipesDrained=$pipesDrained
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
   try{$process.Dispose();$global:RhaiPayloadPendingCustody.ProcessDisposed=$true}catch{$failure+="`nExact Process Dispose failed: "+$_.Exception.ToString()}
  }
 }
 $processDisposed=$global:RhaiPayloadPendingCustody.ProcessDisposed
 if($exited -and $pipesDrained -and $processDisposed -and @($readers|Where-Object{!$_.WriterDisposed -or !$_.ReaderDisposed}).Count -eq 0){$global:RhaiPayloadPendingCustody=$null}
}
$custodyPending=$null -ne $global:RhaiPayloadPendingCustody
$channelClosure=@($readers|ForEach-Object{@{reader_acquired=($null -ne $_.Reader);reader_disposed=$_.ReaderDisposed;writer_acquired=($null -ne $_.Writer);writer_disposed=$_.WriterDisposed;eof=$_.Eof;error=$_.Error;pending_task=($null -ne $_.Task)}})


if($started -and $exited -and $pipesDrained -and !$custodyPending){
 $closure=[Diagnostics.Stopwatch]::StartNew()
 do{
  $active=@(Get-CimInstance Win32_Process|Where-Object{$_.ExecutablePath -and $_.ExecutablePath.StartsWith($session+'\',[StringComparison]::OrdinalIgnoreCase)})
  if($active.Count -eq 0){$ownExecutablesStopped=$true;break}
  if($closure.Elapsed.TotalSeconds -ge 60){$failure+="`nOwned public payload executables did not stop within60seconds.";break}
  [Threading.Thread]::Sleep(20)
 }while($true)
}
if ($started -and $exited -and $pipesDrained -and !$custodyPending -and $ownExecutablesStopped -and !$failure) {
 try {
  if($observerKillUsed){throw 'Observer termination cannot certify public payload acceptance.'}
  $output = [IO.File]::ReadAllText($stdout)
  if ($status -ne 0) { throw "Public native driver exited $status; preserve exact original logs and session." }
  foreach ($line in @('CLIENT_EXIT=0x0000004E','MODE=success;ACTION_CONFIRMED=True;',('PAYLOAD_EXIT='+$expectedPayload),'SUPERVISION=PayloadExited','CLEANUP_CONFIRMED=True','RUNTIME_REMOVED=True','HOST_EXPORTED=False')) {
   if (!$output.Contains($line)) { throw "Missing exact native result: $line" }
  }
  $evidence = @(Get-ChildItem -LiteralPath $run -Directory -Filter '.scoped-evidence-*')
  if ($evidence.Count -ne 1) { throw 'Expected one invocation-owned evidence directory.' }
  $runtimeMatches=[regex]::Matches($output,'(?m)^RUNTIME=([^\r\n]+)\r?$')
  if($runtimeMatches.Count -ne 1){throw 'Exact allocated runtime report unavailable.'}
  $runtimeObserved=$runtimeMatches[0].Groups[1].Value
  if($Phase -ceq 'RETIREMENT_ABORT'){
   $payloadOutput=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'stdout.log'))
   if(!$payloadOutput.Contains('INTENTIONAL_ASSERTION_FAILURE: retirement abort after bounded-work fixture')){throw 'The real payload did not reach its intentional failing assertion.'}
   if(!$payloadOutput.Contains('WORK_RETIREMENT_LONG_RELATIVE_PATH:265') -or !$payloadOutput.Contains('WORK_RETIREMENT_EXPECTED_BYTES:613419011')){throw 'The payload work fixture did not reach its independent size/path controls.'}
   if(Test-Path -LiteralPath (Join-Path $runtimeObserved 'work')){throw 'Exact payload runtime still contains private work after retirement.'}
   $evidenceManifest=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'manifest.txt'))
   if($evidenceManifest -match '(?im)(^|[\\/])work([\\/]|$)'){throw 'Bounded snapshot still contains a work subtree.'}
   $journalMatches=[regex]::Matches($output,'(?m)^JOURNAL=([^\r\n]+)\r?$')
   if($journalMatches.Count -ne 1){throw 'Exact local outcome journal path unavailable.'}
   $journalPath=$journalMatches[0].Groups[1].Value;No-Reparse $journalPath
   $journalLines=[IO.File]::ReadAllLines($journalPath);$decoded=@()
   foreach($recordLine in $journalLines){$parts=$recordLine -split ':',3;if($parts.Length -ne 3){throw 'Outcome journal framing is malformed.'};$decoded+=,$parts[2]}
   $evidenceRecords=@($decoded | Where-Object {$_.StartsWith('EVIDENCE|')})
   if($evidenceRecords.Count -ne 1 -or @($decoded | Where-Object {$_.StartsWith('OUTCOME|')}).Count -ne 1 -or @($decoded | Where-Object {$_.StartsWith('REMOVED|')}).Count -ne 1){throw 'Aborted payload journal lacks one exact EVIDENCE/OUTCOME/REMOVED sequence.'}
   $fields=@{};foreach($field in $evidenceRecords[0].Split('|')){if($field -match '^([^=]+)=(.*)$'){$fields[$Matches[1]]=$Matches[2]}}
   function Assert-WorkRetirementReadback([hashtable]$Fields,[int]$MinimumEntries,[long]$ExpectedBytes){
    $entries=0;$bytes=0L
    if($Fields['work_identity'] -notmatch '^[0-9A-F]{16}:[0-9a-f]{32}$'){throw 'Retired work identity is not independently recorded.'}
    if(![int]::TryParse($Fields['work_entries'],[ref]$entries) -or $entries -lt $MinimumEntries){throw 'Retired work entry count is below the independent minimum.'}
    if(![long]::TryParse($Fields['work_bytes'],[ref]$bytes) -or $bytes -ne $ExpectedBytes){throw 'Retired work byte count differs from independent fixture truth.'}
   }
   $wrongExpectationRejected=$false
   try{Assert-WorkRetirementReadback $fields 99999 613419011}catch{$wrongExpectationRejected=$_.Exception.Message -like '*entry count*'}
   if(!$wrongExpectationRejected){throw 'Negative control accepted an impossible work-entry expectation.'}
   Assert-WorkRetirementReadback $fields 2060 613419011
   $workRetirementRed=$wrongExpectationRejected;$workRetirementGreen=$true
  }elseif($Contract -ceq 'job-quota'){
   $snapshotRoot=Join-Path $evidence[0].FullName 'runtime'
   if($driverElapsedSeconds -ge 110){throw 'Quota closure did not precede the120second natural leaf expiry.'}
   $quotaText=[IO.File]::ReadAllText((Join-Path $snapshotRoot 'payload-job-quota.txt'))
   if($quotaText.Length -gt 4096){throw 'Actual quota record exceeds its bounded schema.'}
   if($quotaText -cnotmatch '^pid=([1-9][0-9]*);creation=([1-9][0-9]*);active_limit=16;members=([0-9,]+);members_after=([0-9,]+);spawned=([1-9][0-9]*);denied_native_error=([1-9][0-9]*);excess_started=False;protected_unchanged=True;contract=PASS\r\n$'){throw 'Actual quota record/schema incomplete.'}
   $q=$Matches.Clone();$members=@($q[3].Split(',')|ForEach-Object{[int]$_});$after=@($q[4].Split(',')|ForEach-Object{[int]$_});$spawned=[int]$q[5]
   if($spawned -lt 1 -or $spawned -gt 15){throw 'Actual quota descendant count outside1..15.'}
   $actors=@(@{pid=[int]$q[1];creation=[long]$q[2]})
   for($index=0;$index -lt $spawned;$index++){
    $childName='quota-child-'+$index.ToString('D2',[Globalization.CultureInfo]::InvariantCulture)+'.txt'
    $child=[IO.File]::ReadAllText((Join-Path $snapshotRoot $childName))
    if($child -cnotmatch '^pid=([1-9][0-9]*);creation=([1-9][0-9]*);job_member=True\r\n$'){throw 'Exact quota leaf record invalid.'}
    $actors+=@{pid=[int]$Matches[1];creation=[long]$Matches[2]}
   }
   $fixtureActors=$actors;$allMembers=@()
   $memberRows=[IO.File]::ReadAllLines((Join-Path $snapshotRoot 'quota-members.txt'))
   if($memberRows.Count -ne 16){throw 'All16quota member identities are required.'}
   foreach($row in $memberRows){
    if($row -cnotmatch '^pid=([1-9][0-9]*);creation=([1-9][0-9]*)$'){throw 'Full quota member identity malformed.'}
    $allMembers+=@{pid=[int]$Matches[1];creation=[long]$Matches[2]}
   }
   function Assert-QuotaProof([int]$ExpectedCount){
    if($members.Count -ne $ExpectedCount -or ($members -join ',') -cne ($after -join ',') -or ($members -join ',') -cne (@($members|Sort-Object -Unique)-join ',') -or $members -contains 0 -or $spawned -gt 15 -or @($fixtureActors|ForEach-Object{$_.pid}|Sort-Object -Unique).Count -ne $fixtureActors.Count -or (($allMembers|ForEach-Object{$_.pid})-join ',') -cne ($members-join ',')){throw 'Native quota proof mismatch.'}
    foreach($actor in $fixtureActors){if(@($allMembers|Where-Object{$_.pid -eq $actor.pid -and $_.creation -eq $actor.creation}).Count -ne 1){throw 'Native quota proof mismatch.'}}
   }
   try{Assert-QuotaProof 17}catch{if($_.Exception.Message -cne 'Native quota proof mismatch.'){throw};$jobQuotaSensitivity=$true}
   if(!$jobQuotaSensitivity){throw 'Wrong quota-count expectation was not rejected.'};Assert-QuotaProof 16
   function Assert-ProtectedQuota([string]$Expected){if([IO.File]::ReadAllText((Join-Path $snapshotRoot 'quota-protected.txt')) -cne $Expected -or (Test-Path -LiteralPath (Join-Path $snapshotRoot 'quota-excess.txt'))){throw 'Protected quota state mismatch.'}}
   try{Assert-ProtectedQuota "WRONG_PROTECTED_QUOTA_EXPECTATION`r`n"}catch{if($_.Exception.Message -cne 'Protected quota state mismatch.'){throw};$quotaProtectedSensitivity=$true}
   if(!$quotaProtectedSensitivity){throw 'Protected quota sensitivity missing.'};Assert-ProtectedQuota "protected-before-quota`r`n"
   foreach($identity in $allMembers){
    $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById($identity.pid)}catch [ArgumentException]{}
    if($null -ne $actor){try{if(!$actor.HasExited -and $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq $identity.creation){throw 'Exact quota actor remains live.'}}finally{$actor.Dispose()}}
   }
   $jobQuotaObserved=@{root=$fixtureActors[0];actors=$allMembers;fixture_actors=$fixtureActors;members=$members;members_after=$after;spawned=$spawned;denied_native_error=[int]$q[6];excess_started=$false;protected_unchanged=$true}
   $quotaActorsStopped=$true;$jobQuotaGreen=$true
  }elseif($Contract -ceq 'job-resources'){
   function Read-JobResourceRecord([string]$Path){
    $rows=[IO.File]::ReadAllLines($Path);$keys=@('pid','creation','flags','active_process_limit','process_memory_bytes','job_memory_bytes','contract');$values=@{}
    if($rows.Count -ne 7){throw 'Actual Job resource record incomplete.'}
    for($index=0;$index -lt $keys.Count;$index++){$prefix=$keys[$index]+'=';if(!$rows[$index].StartsWith($prefix)){throw 'Job resource key/order invalid.'};$values[$keys[$index]]=$rows[$index].Substring($prefix.Length)}
    if($values.pid -notmatch '^[1-9][0-9]*$' -or $values.creation -notmatch '^[1-9][0-9]*$' -or $values.flags -cnotmatch '^[0-9A-F]{8}$'){throw 'Job resource identity/flags invalid.'}
    foreach($key in @('active_process_limit','process_memory_bytes','job_memory_bytes')){if($values[$key] -notmatch '^(0|[1-9][0-9]*)$'){throw 'Job resource bound invalid.'}}
    return $values
   }
   function Assert-JobResources([object]$Values,[string]$ExpectedFlags='00002308'){
    if($Values.flags -cne $ExpectedFlags -or $Values.active_process_limit -cne '16' -or $Values.process_memory_bytes -cne '1073741824' -or $Values.job_memory_bytes -cne '2147483648' -or $Values.contract -cne 'PASS'){throw 'Actual payload Job resource contract mismatch.'}
   }
   function Assert-ActorStopped([object]$Values){
    $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById([int]$Values.pid)}catch [ArgumentException]{}
    if($null -ne $actor){try{if(!$actor.HasExited -and $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$Values.creation){throw 'Exact resource actor remains live.'}}finally{$actor.Dispose()}}
   }
   $recordPath=Join-Path $evidence[0].FullName 'runtime\payload-job-resources.txt'
   $rootValues=Read-JobResourceRecord $recordPath;$jobResourcesObserved.root=$rootValues
   if($Phase -ceq 'RED'){
    $rejected=$false;try{Assert-JobResources $rootValues}catch{if($_.Exception.Message -cne 'Actual payload Job resource contract mismatch.'){throw};$rejected=$true}
    $diagnostic=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'stderr.log'))
    if(!$rejected -or $rootValues.contract -cne 'FAIL' -or !$diagnostic.Contains('FAIL native payload Job resource contract')){throw 'Expected real Job resource RED was not reached.'}
    $jobResourcesRed=$true
   }else{
    try{Assert-JobResources $rootValues '00002309'}catch{if($_.Exception.Message -cne 'Actual payload Job resource contract mismatch.'){throw};$jobResourcesSensitivity=$true}
    if(!$jobResourcesSensitivity){throw 'Wrong Job flag expectation was not rejected.'}
    Assert-JobResources $rootValues
    $childValues=Read-JobResourceRecord ($recordPath+'.child');$jobResourcesObserved.child=$childValues
    Assert-JobResources $childValues
    if($childValues.pid -ceq $rootValues.pid -or [IO.File]::ReadAllText($recordPath+'.work') -cne "both-actors-resource-bounded`r`n"){throw 'Distinct child/useful-work readback missing.'}
    Assert-ActorStopped $childValues
    $jobResourcesGreen=$true
   }
   Assert-ActorStopped $rootValues;$jobActorsStopped=$true
  }else{
   $marker=Join-Path $evidence[0].FullName 'runtime\payload-environment.txt'
   $lines=[IO.File]::ReadAllLines($marker)
   if($lines.Count -ne 7 -or !$lines[0].StartsWith('cwd=')){throw 'Exact fresh environment record incomplete.'}
   $childCwd=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($lines[0].Substring(4)))
   if($childCwd -cne $runtimeObserved){throw 'Child cwd differs from independently reported allocated runtime.'}
   $work=Join-Path $runtimeObserved 'work'
   $values=@{AGENT_RUNTIME_DIR=$runtimeObserved;TMP=(Join-Path $work 'temp');TEMP=(Join-Path $work 'temp');CARGO_HOME=(Join-Path $work 'cargo-home');CARGO_TARGET_DIR=(Join-Path $work 'target')}
   $keys=@('AGENT_RUNTIME_DIR','TMP','TEMP','CARGO_HOME','CARGO_TARGET_DIR')
   $diagnostic=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'stderr.log'))
   for($index=0;$index -lt $keys.Count;$index++){
    $key=$keys[$index];$prefix=$key+'='
    if(!$lines[$index+1].StartsWith($prefix)){throw 'Wrong environment record key/order.'}
    $actual=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($lines[$index+1].Substring($prefix.Length)))
    $environmentObserved[$key]=$actual
    if(![string]::Equals($actual,$values[$key],[StringComparison]::OrdinalIgnoreCase)){
     $environmentMismatches+=,$key
     if(!$diagnostic.Contains('FAIL native payload private environment '+$key)){throw 'Mismatch did not reach its intended assertion.'}
    }
   }
   if($Phase -ceq 'RED'){
    if(!$environmentMismatches.Count -or $lines[6] -cne 'contract=FAIL'){throw 'Expected actual environment contract RED was not observed.'}
    $environmentRed=$true
   }else{
    if($environmentMismatches.Count -or $lines[6] -cne 'contract=PASS' -or $diagnostic.Contains('FAIL native payload private environment')){throw 'Native environment contract remains failing.'}
    $environmentGreen=$true
   }
  }
  foreach($key in $parentEnvironment.Keys){if([Environment]::GetEnvironmentVariable($key) -cne $parentEnvironment[$key]){$parentChanged=$true}}
  if([Environment]::CurrentDirectory -cne $parentCwd){$parentChanged=$true}
  if($parentChanged){throw 'Observer parent environment/cwd changed.'}
  $actualRuntime=[IO.Path]::GetFullPath($runtimeObserved)
  if([IO.Path]::GetDirectoryName($actualRuntime) -cne $run -or [IO.Path]::GetFileName($actualRuntime) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Actual runtime is outside this exact control.'}
  function Assert-RuntimeAbsent([string]$Path){if(Test-Path -LiteralPath $Path){throw 'Actual runtime absence mismatch.'}}
  try{Assert-RuntimeAbsent $evidence[0].FullName}catch{if($_.Exception.Message -cne 'Actual runtime absence mismatch.'){throw};$runtimeAbsenceRed=$true}
  if(!$runtimeAbsenceRed){throw 'Runtime absence negative control missing.'}
  Assert-RuntimeAbsent $actualRuntime;$runtimeAbsent=$true
  if (@(Get-ChildItem -LiteralPath $run -Force -Directory -Filter 'scoped-*').Count -ne 0) { throw 'Actual runtime presence contradicts cleanup receipt.' }
  $hostRecord = $true; $complete = $true
 } catch { $failure = $_.Exception.ToString() }
}
$record = [ordered]@{id=$id;scope=$session;run=$run;exit=$status;accepted=$complete;failure=$failure;fresh_host_record=$hostRecord;phase=$Phase;contract=$Contract;driver_elapsed_seconds=$driverElapsedSeconds;driver_pid=$driverPid;driver_creation=$driverCreation;observer_kill_used=$observerKillUsed;process_disposed=$processDisposed;custody_pending=$custodyPending;channel_closure=$channelClosure;owned_executables_stopped=$ownExecutablesStopped;job_quota_observed=$jobQuotaObserved;job_quota_green=$jobQuotaGreen;job_quota_sensitivity=$jobQuotaSensitivity;quota_protected_sensitivity=$quotaProtectedSensitivity;quota_actors_stopped=$quotaActorsStopped;job_resources_observed=$jobResourcesObserved;job_resources_red=$jobResourcesRed;job_resources_green=$jobResourcesGreen;job_resources_sensitivity=$jobResourcesSensitivity;job_actors_stopped=$jobActorsStopped;expected_payload_exit=$expectedPayload;work_retirement_red=$workRetirementRed;work_retirement_green=$workRetirementGreen;environment_contract_red=$environmentRed;environment_contract_green=$environmentGreen;allocated_runtime=$runtimeObserved;runtime_absent_readback=$runtimeAbsent;runtime_absence_negative_control=$runtimeAbsenceRed;environment_observed=$environmentObserved;environment_mismatches=$environmentMismatches;parent_environment_changed=$parentChanged;fixture_sha256=$FixtureSha256;driver_launched=$started;exact_driver_exited=$exited;pipes_drained=$pipesDrained;retained_driver_handles=$custodyPending;retained_binaries=$expected;product_run=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 5),[Text.UTF8Encoding]::new($false))
$files=@(Get-Item -LiteralPath (Join-Path $session 'observer.json'))
foreach($path in @($stdout,$stderr)){if(Test-Path -LiteralPath $path -PathType Leaf){$files+=@(Get-Item -LiteralPath $path)}}
# Enumerate runtime evidence only after the validated completion/removal receipt.
# On an observer/control failure export stable originals and preserve guest custody.
if (!$custodyPending -and $ownExecutablesStopped) { $files += @(Get-ChildItem -LiteralPath $run -Recurse -File) }
$files+=@(Get-ChildItem -LiteralPath $bin -File);$files+=@(Get-ChildItem -LiteralPath $input -File)
if ($buildReadback -and (Test-Path -LiteralPath $buildReadback -PathType Container)) {
 $files += @(Get-ChildItem -LiteralPath $buildReadback -Recurse -File)
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
    $serial.Open(); Emit-Frame 'BEGIN' @{id=$id;scope=$session;phase=$Phase;contract=$Contract;accepted=$complete;exit=$status;driver_pid=$driverPid;driver_creation=$driverCreation}
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
$record | ConvertTo-Json -Compress
$controlExitCode=if($complete){0}else{2}
if($ReturnStatusToCaller){$global:RhaiPayloadControlExitCode=$controlExitCode;return}
exit $controlExitCode
