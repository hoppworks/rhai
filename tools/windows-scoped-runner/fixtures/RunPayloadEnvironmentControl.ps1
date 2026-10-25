param(
 [Parameter(Mandatory=$true)][string]$FixturePath,
 [Parameter(Mandatory=$true)][string]$FixtureSha256,
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][ValidateLength(1,96)][ValidatePattern('^[a-z0-9-]+$')][string]$Id,
 [ValidateSet('RED','GREEN','RETIREMENT_ABORT')][string]$Phase='RED',
 [ValidateSet('environment','job-resources','job-quota','job-memory','backend-evidence-hardlink','backend-cleanup-readonly')][string]$Contract='environment',
 [Parameter(Mandatory=$true)][string]$BuildRoot,
 [string]$FixtureBuildRoot,
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
function Read-CompiledBuild([string]$Directory,[string[]]$Names){
 $build=[IO.Path]::GetFullPath($Directory);No-Reparse $build
 if([IO.Path]::GetFileName($build) -cne 'build'){throw 'Compiled build directory basename invalid.'}
 $buildRun=[IO.Directory]::GetParent($build).FullName;$buildParent=[IO.Directory]::GetParent($buildRun).FullName
 if([IO.Path]::GetFileName($buildRun) -notmatch '^monitor-source-[0-9a-f]{32}$' -or [IO.Path]::GetFileName($buildParent) -cne 'run' -or [IO.Directory]::GetParent($buildParent).Parent.FullName -cne $private){throw 'Compiled build must be inside canonical own private scope.'}
 $manifest=Join-Path $buildRun 'build-manifest.txt';No-Reparse $manifest;$rows=[IO.File]::ReadAllLines($manifest);$pins=@{}
 foreach($name in $Names){
  $matches=@($rows|Where-Object{$_ -cmatch ('^[0-9a-f]{64}  build/'+[regex]::Escape($name)+'$')})
  if($matches.Count -ne 1){throw 'Compiled build must bind each requested binary exactly once.'}
  $pins[$name]=$matches[0].Substring(0,64);$file=Join-Path $build $name;No-Reparse $file
  if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $pins[$name]){throw 'Compiled binary differs from manifest.'}
 }
 return @{build=$build;run=$buildRun;session=([IO.Directory]::GetParent($buildParent).FullName);manifest=$manifest;pins=$pins}
}
$publicBuild=Read-CompiledBuild $BuildRoot @('ScopedRunner.exe','MonitorAcceptanceDriver.exe')
if(!$FixtureBuildRoot){$FixtureBuildRoot=$BuildRoot}
$fixtureBuild=Read-CompiledBuild $FixtureBuildRoot @('PayloadFixture.exe')
$build=$publicBuild.build;$buildManifest=$publicBuild.manifest;$expected=$publicBuild.pins
if([IO.Path]::GetFullPath($FixturePath) -cne (Join-Path $fixtureBuild.build 'PayloadFixture.exe') -or $FixtureSha256 -cne $fixtureBuild.pins['PayloadFixture.exe']){throw 'Fixture path/hash differs from its actual compiled component.'}
if($Contract -cin @('job-quota','job-memory') -and $Phase -cne 'GREEN'){throw 'Actual Job limit denials use current bounded production tools and GREEN phase.'}
if($Contract -cin @('backend-evidence-hardlink','backend-cleanup-readonly') -and $Phase -cne 'GREEN'){throw 'Native backend failure controls require the current GREEN fixture input.'}

No-Reparse $session;No-Reparse $FixturePath
if((Get-FileHash -LiteralPath $FixturePath).Hash.ToLowerInvariant() -cne $FixtureSha256){throw 'Native environment fixture changed.'}
if(Test-Path -LiteralPath $session){throw 'Own environment scope exists; preserve it.'}
$parentEnvironment=@{}
foreach($key in @('AGENT_RUNTIME_DIR','TMP','TEMP','CARGO_HOME','CARGO_TARGET_DIR')){$parentEnvironment[$key]=[Environment]::GetEnvironmentVariable($key)}
$parentCwd=[Environment]::CurrentDirectory
$run=Join-Path $session 'run';$input=Join-Path $session 'input'
New-Item -ItemType Directory -Path $run,$input | Out-Null
function Copy-CompiledReadback([object]$Component,[string]$Destination,[bool]$FixtureCompilerOnly=$false){
 New-Item -ItemType Directory -Path $Destination|Out-Null
 foreach($name in @('build-manifest.txt','run-result.txt')){Copy-Item -LiteralPath (Join-Path $Component.run $name) -Destination $Destination}
 foreach($name in @('build-observer.json','bootstrap.stdout','bootstrap.stderr')){Copy-Item -LiteralPath (Join-Path $Component.session $name) -Destination $Destination}
 $logs=Join-Path $Component.run 'logs'
 if($FixtureCompilerOnly){
  $selected=Join-Path $Destination 'logs';New-Item -ItemType Directory -Path $selected|Out-Null
  # Earlier full exports retain the unchanged harness controls. This component
  # needs its exact compile result and before/after native owner accounting.
  foreach($name in @('compile-PayloadFixture.stdout.txt','compile-PayloadFixture.stderr.txt','job-members.jsonl')){Copy-Item -LiteralPath (Join-Path $logs $name) -Destination $selected}
 }elseif(Test-Path -LiteralPath $logs -PathType Container){
  $selected=Join-Path $Destination 'logs';New-Item -ItemType Directory -Path $selected|Out-Null
  foreach($file in @(Get-ChildItem -LiteralPath $logs -File | Where-Object{$_.Name -like 'compile-*.stdout.txt' -or $_.Name -like 'compile-*.stderr.txt' -or $_.Name -ceq 'job-members.jsonl'})){Copy-Item -LiteralPath $file.FullName -Destination $selected}
 }
 foreach($file in @(Get-ChildItem -LiteralPath $Destination -File -Recurse)){No-Reparse $file.FullName;if($file.Length -gt 4MB){throw 'Build component diagnostic exceeds4MiB.'}}
}
$buildReadback=Join-Path $session 'build-readback';Copy-CompiledReadback $publicBuild $buildReadback
$fixtureReadback=$null
if($fixtureBuild.build -cne $publicBuild.build){$fixtureReadback=Join-Path $session 'fixture-build-readback';Copy-CompiledReadback $fixtureBuild $fixtureReadback $true}
Copy-Item -LiteralPath $FixturePath -Destination (Join-Path $input 'fixture.exe')
if((Get-FileHash -LiteralPath (Join-Path $input 'fixture.exe')).Hash.ToLowerInvariant() -cne $FixtureSha256){throw 'Fixture copy mismatch.'}
$bin=Join-Path $session 'bin';New-Item -ItemType Directory -Path $bin|Out-Null
foreach($name in @('ScopedRunner.exe','MonitorAcceptanceDriver.exe')){
 $sourceBinary=Join-Path $build $name;No-Reparse $sourceBinary
 Copy-Item -LiteralPath $sourceBinary -Destination (Join-Path $bin $name)
 if((Get-FileHash -LiteralPath (Join-Path $bin $name)).Hash.ToLowerInvariant() -cne $expected[$name]){throw 'Owned public tool copy differs from source-bound build.'}
}
$jobQuotaObserved=@{};$jobQuotaGreen=$false;$jobQuotaSensitivity=$false;$quotaProtectedSensitivity=$false;$quotaActorsStopped=$false
$jobMemoryObserved=@{};$jobMemoryGreen=$false;$jobMemorySensitivity=$false;$memoryActorsStopped=$false
$expectedPayload=if($Phase -ceq 'GREEN'){'00000000'}else{'0000002A'}
$runtimeAbsenceRed=$false;$runtimeAbsent=$false;
$jobResourcesObserved=@{};$jobResourcesRed=$false;$jobResourcesGreen=$false;$jobResourcesSensitivity=$false;$jobActorsStopped=$false
$environmentObserved=@{};$environmentMismatches=@();$runtimeObserved=$null
$environmentRed=$false;$environmentGreen=$false;$workRetirementRed=$false;$workRetirementGreen=$false;$parentChanged=$false
$backendFailureObserved=@{};$backendFailureSensitivity=$false;$backendFailureAccepted=$false
$stdout = Join-Path $session 'bootstrap.stdout'; $stderr = Join-Path $session 'bootstrap.stderr'
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $bin 'MonitorAcceptanceDriver.exe'
$payloadArguments=if($Phase -ceq 'RETIREMENT_ABORT'){'--retirement-abort'}elseif($Contract -ceq 'job-resources'){'payload-job-resources.txt --job-resources'}elseif($Contract -ceq 'job-quota'){'payload-job-quota.txt --job-quota'}elseif($Contract -ceq 'job-memory'){'payload-job-memory.txt --job-memory'}elseif($Contract -ceq 'backend-evidence-hardlink'){('"'+(Join-Path $session 'payload-record.txt')+'" --backend-evidence-hardlink')}elseif($Contract -ceq 'backend-cleanup-readonly'){('"'+(Join-Path $session 'payload-record.txt')+'" --backend-cleanup-readonly')}else{'payload-environment.txt --environment'}
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
$driverBound=if($Contract -cin @('job-quota','job-memory')){190}elseif($Phase -ceq 'RETIREMENT_ABORT'){180}elseif($Contract -like 'backend-*'){30}else{10}
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
if ($Contract -notlike 'backend-*' -and $started -and $exited -and $pipesDrained -and !$custodyPending -and $ownExecutablesStopped -and !$failure) {
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
  }elseif($Contract -ceq 'job-memory'){
   $snapshotRoot=Join-Path $evidence[0].FullName 'runtime'
   if($driverElapsedSeconds -ge 110){throw 'Memory closure did not precede the120second natural leaf expiry.'}
   function Read-MemoryLine([string]$Name,[string]$Pattern){
    $text=[IO.File]::ReadAllText((Join-Path $snapshotRoot $Name))
    if($text.Length -gt 4096){throw ('Actual memory record exceeds bound: '+$Name)}
    if($text -cmatch $Pattern){return $Matches}
    throw ('Actual memory record invalid: '+$Name)
   }
   $root=Read-MemoryLine 'payload-job-memory.txt.root' '^pid=([1-9][0-9]*);creation=([1-9][0-9]*);job_member=True;flags=([0-9A-F]{8});process_limit=([1-9][0-9]*);job_limit=([1-9][0-9]*);global_available_commit=([1-9][0-9]*);private_bytes=([1-9][0-9]*)\r\n$'
   if([long]$root[6] -lt 3221225472 -or [long]$root[7] -ge 536870912){throw 'Global or process commit headroom did not separate Job limits from system exhaustion.'}
   $processDenial=Read-MemoryLine 'payload-job-memory.txt.process-denial' '^bytes=1073741824;returned=False;native_error=([1-9][0-9]*);protected_unchanged=True\r\n$'
   $job=Read-MemoryLine 'payload-job-memory.txt.job-denial' '^bytes=536870912;returned=False;native_error=([1-9][0-9]*);root_private_before=([1-9][0-9]*);global_available_commit_before=([1-9][0-9]*);protected_unchanged=True\r\n$'
   $leaf0=Read-MemoryLine 'payload-job-memory.txt.leaf-0' '^pid=([1-9][0-9]*);creation=([1-9][0-9]*);job_member=True;committed_bytes=805306368;private_bytes=([1-9][0-9]*)\r\n$'
   $leaf1=Read-MemoryLine 'payload-job-memory.txt.leaf-1' '^pid=([1-9][0-9]*);creation=([1-9][0-9]*);job_member=True;committed_bytes=805306368;private_bytes=([1-9][0-9]*)\r\n$'
   if([long]$job[2] -ge 536870912 -or [long]$job[3] -lt 1073741824 -or [long]$leaf0[3] -lt 805306368 -or [long]$leaf1[3] -lt 805306368){throw 'Actual committed-memory headroom or leaf charges do not separate per-process and Job denials.'}
   $outcome=Read-MemoryLine 'payload-job-memory.txt' '^pid=([1-9][0-9]*);creation=([1-9][0-9]*);job_member=True;process_error=([1-9][0-9]*);job_error=([1-9][0-9]*);released_leaf=([1-9][0-9]*);retained_leaf=([1-9][0-9]*);retries=(0|[1-9][0-9]*);contract=PASS\r\n$'
   if($root[1] -cne $outcome[1] -or $root[2] -cne $outcome[2] -or $processDenial[1] -cne $outcome[3] -or $job[1] -cne $outcome[4] -or $leaf0[1] -cne $outcome[5] -or $leaf1[1] -cne $outcome[6] -or $root[1] -ceq $leaf0[1] -or $root[1] -ceq $leaf1[1] -or $leaf0[1] -ceq $leaf1[1]){throw 'Memory root, leaves or native denials are not bound to the final result.'}
   function Assert-MemoryLimits([long]$ExpectedProcess,[long]$ExpectedJob){
    if($root[3] -cne '00002308' -or [long]$root[4] -ne $ExpectedProcess -or [long]$root[5] -ne $ExpectedJob){throw 'Actual memory limit expectation mismatch.'}
   }
   try{Assert-MemoryLimits 1073741825 2147483648}catch{if($_.Exception.Message -cne 'Actual memory limit expectation mismatch.'){throw};$jobMemorySensitivity=$true}
   if(!$jobMemorySensitivity){throw 'Memory wrong-limit expectation did not fail.'}
   Assert-MemoryLimits 1073741824 2147483648
   if([IO.File]::ReadAllText((Join-Path $snapshotRoot 'payload-job-memory.txt.protected')) -cne "same-allocation-succeeded-after-exact-leaf-exit`r`n"){throw 'Memory countercase did not produce the independently read protected marker.'}
   $memoryDiagnostic=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'stderr.log'))
   if($memoryDiagnostic -match '(?i)memory (child cleanup failed|child wait incomplete|root VirtualFree failed|leaf VirtualFree failed)'){throw 'Memory actor cleanup reported an incomplete native operation.'}
   $jobMemoryObserved=@{root=@{pid=[int]$root[1];creation=[long]$root[2];private_before=[long]$root[7]};released_leaf=@{pid=[int]$leaf0[1];creation=[long]$leaf0[2];private_bytes=[long]$leaf0[3]};retained_leaf=@{pid=[int]$leaf1[1];creation=[long]$leaf1[2];private_bytes=[long]$leaf1[3]};process_native_error=[int]$processDenial[1];job_native_error=[int]$job[1];root_private_before_job_denial=[long]$job[2];global_available_commit=[long]$root[6];global_available_commit_before_job_denial=[long]$job[3];recovery_attempts=[int]$outcome[7]}
   $liveProcesses=@(Get-CimInstance Win32_Process)
   if($liveProcesses.Count -lt 1 -or @($liveProcesses|Where-Object{$_.ProcessId -eq $PID}).Count -ne 1){throw 'Current OS process census is incomplete.'}
   foreach($actor in @($jobMemoryObserved.root,$jobMemoryObserved.released_leaf,$jobMemoryObserved.retained_leaf)){
    $rows=@($liveProcesses|Where-Object{$_.ProcessId -eq $actor.pid})
    if($rows.Count -gt 1){throw 'Memory actor process generation is ambiguous.'}
    if($rows.Count -eq 1){
     if($null -eq $rows[0].CreationDate -or $rows[0].CreationDate -isnot [DateTime]){throw 'Current memory actor creation data unavailable.'}
     $observedCreation=$rows[0].CreationDate.ToUniversalTime().ToFileTimeUtc()
     if([Math]::Abs([decimal]$observedCreation-[decimal]$actor.creation) -le 10000000){throw 'Original or indistinguishable memory actor generation remains live.'}
    }
   }
   $memoryActorsStopped=$true;$jobMemoryGreen=$true
  }elseif($Contract -ceq 'job-quota'){
   $snapshotRoot=Join-Path $evidence[0].FullName 'runtime'
   if($driverElapsedSeconds -ge 110){throw 'Quota closure did not precede the120second natural leaf expiry.'}
   $quotaText=[IO.File]::ReadAllText((Join-Path $snapshotRoot 'payload-job-quota.txt'))
   if($quotaText.Length -gt 4096 -or !$quotaText.EndsWith("`r`n")){throw 'Quota record size/terminator invalid.'}
   $keys=@('pid','creation','active_limit','payload_count','accounting_full','accounting_after','accounting_recovered','members','members_after','spawned','api_create_returned','api_error','excess_pid','excess_creation','excess_exit','excess_wait_confirmed','released_fixture_children','recovered_members','recovery_pid','recovery_creation','excess_user_code','protected_unchanged_at_denial','countercase_user_code','contract')
   $rows=$quotaText.Substring(0,$quotaText.Length-2).Split(';');$q=@{}
   if($rows.Count -ne $keys.Count){throw 'Quota record field count invalid.'}
   for($index=0;$index -lt $keys.Count;$index++){$prefix=$keys[$index]+'=';if(!$rows[$index].StartsWith($prefix)){throw 'Quota field order invalid.'};$q[$keys[$index]]=$rows[$index].Substring($prefix.Length)}
   foreach($key in @('pid','creation','spawned','accounting_full','accounting_after','accounting_recovered','recovery_pid','recovery_creation')){if($q[$key] -cnotmatch '^[1-9][0-9]*$'){throw 'Quota identity/count format invalid.'}}
   foreach($key in @('api_error','excess_pid','excess_creation')){if($q[$key] -cnotmatch '^(0|[1-9][0-9]*)$'){throw 'Quota admission numeric field invalid.'}}
   $members=@($q.members.Split(',')|ForEach-Object{[int]$_});$after=@($q.members_after.Split(',')|ForEach-Object{[int]$_});$recovered=@($q.recovered_members.Split(',')|ForEach-Object{[int]$_});$spawned=[int]$q.spawned
   if($spawned -ne 15 -or $q.payload_count -cne '16' -or $q.active_limit -cne '16' -or $q.released_fixture_children -cne '2' -or $q.excess_user_code -cne 'False' -or $q.protected_unchanged_at_denial -cne 'True' -or $q.countercase_user_code -cne 'True' -or $q.contract -cne 'PASS'){throw 'Quota outcome contract invalid.'}
   if($q.api_create_returned -ceq 'True'){
    if($q.excess_wait_confirmed -cne 'True' -or $q.api_error -cne '0' -or $q.excess_exit -cnotmatch '^[0-9A-F]{8}$' -or $q.excess_exit -ceq '00000000' -or [int]$q.excess_pid -le 0 -or [long]$q.excess_creation -le 0){throw 'Returned excess process lacks exact stopped nonzero startup disposition.'}
   }elseif($q.api_create_returned -ceq 'False'){
    if([int]$q.api_error -le 0 -or $q.excess_pid -cne '0' -or $q.excess_creation -cne '0' -or $q.excess_exit -cne 'NONE' -or $q.excess_wait_confirmed -cne 'False'){throw 'Native API denial disposition invalid.'}
   }else{throw 'Quota API result invalid.'}
   $admissionText=[IO.File]::ReadAllText((Join-Path $snapshotRoot 'payload-job-quota.txt.admission'))
   $expectedAdmission='create_returned='+$q.api_create_returned+';api_error='+$q.api_error+';pid='+$q.excess_pid+';creation='+$q.excess_creation+';wait_confirmed='+$q.excess_wait_confirmed+';exit='+$q.excess_exit+';before='+$q.members+"`r`n"
   if($admissionText -cne $expectedAdmission){throw 'Durable exact admission differs from final quota result.'}
   $diagnostic=[IO.File]::ReadAllText((Join-Path $snapshotRoot 'quota-observation.log'))
   if($diagnostic.Length -gt 262144 -or !$diagnostic.Contains('phase=before-start;before='+$q.members+"`r`n") -or !$diagnostic.Contains('phase=start-result;create_returned='+$q.api_create_returned+';native_error='+$q.api_error+"`r`n") -or !$diagnostic.Contains(';phase=settled-denial;class=3;capacity=64;bytes=520;success=True;native_error=0;') -or $diagnostic.Contains('phase=failure')){throw 'Bounded phase/query diagnostics do not bind the actual denial.'}
   $fixtureActors=@(@{pid=[int]$q.pid;creation=[long]$q.creation})
   for($index=0;$index -lt $spawned;$index++){
    $file='quota-child-'+$index.ToString('D2',[Globalization.CultureInfo]::InvariantCulture)+'.txt'
    $text=[IO.File]::ReadAllText((Join-Path $snapshotRoot $file))
    if($text -cnotmatch '^pid=([1-9][0-9]*);creation=([1-9][0-9]*);job_member=True\r\n$'){throw 'Exact quota fixture child record invalid.'}
    $fixtureActors+=@{pid=[int]$Matches[1];creation=[long]$Matches[2]}
   }
   function Read-QuotaMembers([string]$Name){
    $values=@();foreach($row in [IO.File]::ReadAllLines((Join-Path $snapshotRoot $Name))){
     if($row -cnotmatch '^pid=([1-9][0-9]*);creation=([1-9][0-9]*)$'){throw 'Full quota member identity invalid.'}
     $values+=@{pid=[int]$Matches[1];creation=[long]$Matches[2]}
    };return $values
   }
   $allMembers=@(Read-QuotaMembers 'quota-members.txt');$recoveredMembers=@(Read-QuotaMembers 'quota-recovered-members.txt')
   function Assert-QuotaProof([int]$Wanted){
    if($fixtureActors.Count -ne $Wanted -or $members.Count -lt $Wanted -or $members.Count -gt 32 -or $allMembers.Count -ne $members.Count -or ($members-join ',') -cne ($after-join ',') -or ($members-join ',') -cne (@($members|Sort-Object -Unique)-join ',') -or $members -contains 0 -or (($allMembers|ForEach-Object{$_.pid})-join ',') -cne ($members-join ',')){throw 'Native quota proof mismatch.'}
    foreach($actor in $fixtureActors){if(@($allMembers|Where-Object{$_.pid -eq $actor.pid -and $_.creation -eq $actor.creation}).Count -ne 1){throw 'Native quota proof mismatch.'}}
   }
   try{Assert-QuotaProof 17}catch{if($_.Exception.Message -cne 'Native quota proof mismatch.'){throw};$jobQuotaSensitivity=$true};if(!$jobQuotaSensitivity){throw 'Quota wrong-count control missing.'};Assert-QuotaProof 16
   if($recovered.Count -lt 1 -or $recovered.Count -gt 32 -or ($recovered-join ',') -cne (@($recovered|Sort-Object -Unique)-join ',') -or (($recoveredMembers|ForEach-Object{$_.pid})-join ',') -cne ($recovered-join ',')){throw 'Countercase complete Job identity binding invalid.'}
   $recovery=@{pid=[int]$q.recovery_pid;creation=[long]$q.recovery_creation}
   if(@($recoveredMembers|Where-Object{$_.pid -eq $recovery.pid -and $_.creation -eq $recovery.creation}).Count -ne 1){throw 'Countercase actor not in its real bounded Job.'}
   if([IO.File]::ReadAllText((Join-Path $snapshotRoot 'quota-excess.txt')) -cne ('pid='+$recovery.pid+';creation='+$recovery.creation+";job_member=True`r`n")){throw 'Countercase fresh user-code record invalid.'}
   function Assert-ProtectedQuota([string]$Expected){if([IO.File]::ReadAllText((Join-Path $snapshotRoot 'quota-protected-after-denial.txt')) -cne $Expected){throw 'Protected quota state mismatch.'}}
   try{Assert-ProtectedQuota "WRONG_PROTECTED_QUOTA_EXPECTATION`r`n"}catch{if($_.Exception.Message -cne 'Protected quota state mismatch.'){throw};$quotaProtectedSensitivity=$true};if(!$quotaProtectedSensitivity){throw 'Protected quota sensitivity missing.'};Assert-ProtectedQuota "protected-before-quota`r`n"
   if([IO.File]::ReadAllText((Join-Path $snapshotRoot 'quota-protected.txt')) -cne "protected-before-quota`r`nEXCESS_PROCESS_RAN`r`n"){throw 'Allowed countercase effect missing.'}
   function Assert-QuotaImages([string]$Name,[object[]]$Census,[object[]]$Fixtures){
    $rows=[IO.File]::ReadAllLines((Join-Path $snapshotRoot $Name));if($rows.Count -ne $Census.Count){throw 'Quota image census is incomplete.'}
    $seen=@();$imageObservations=@()
    foreach($row in $rows){
     if($row -cnotmatch '^pid=([1-9][0-9]*);creation=([1-9][0-9]*);image_b64=([A-Za-z0-9+/]+={0,2})$'){throw 'Quota image record format invalid.'}
     $pidValue=[int]$Matches[1];$creation=[long]$Matches[2];$image=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Matches[3]))
     if($seen -contains $pidValue -or @($Census|Where-Object{$_.pid -eq $pidValue -and $_.creation -eq $creation}).Count -ne 1){throw 'Quota image identity differs from complete Job census.'};$seen+=,$pidValue
     $isFixture=@($Fixtures|Where-Object{$_.pid -eq $pidValue -and $_.creation -eq $creation}).Count -eq 1
     $expectedImage=if($isFixture){Join-Path $runtimeObserved 'fixture.exe'}else{Join-Path ([Environment]::SystemDirectory) 'conhost.exe'}
     if(![string]::Equals($image,$expectedImage,[StringComparison]::OrdinalIgnoreCase)){throw 'Unclassified quota member image.'}
     $imageObservations+=@{pid=$pidValue;creation=$creation;image=$image;fixture=$isFixture}
    };return $imageObservations
   }
   $fullImages=@(Assert-QuotaImages 'quota-member-images.txt' $allMembers $fixtureActors)
   $recoveredFixtures=@($fixtureActors[0])+@($fixtureActors|Select-Object -Skip 3)+@($recovery)
   foreach($actor in $recoveredFixtures){if(@($recoveredMembers|Where-Object{$_.pid -eq $actor.pid -and $_.creation -eq $actor.creation}).Count -ne 1){throw 'Recovered fixture actor absent from full census.'}}
   $recoveredImages=@(Assert-QuotaImages 'quota-recovered-images.txt' $recoveredMembers $recoveredFixtures)
   foreach($entry in @(@{phase='before-admission';field='accounting_full'},@{phase='settled-denial';field='accounting_after'},@{phase='recovered-countercase';field='accounting_recovered'})){
    $pattern='(?m)^accounting;phase='+$entry.phase+';success=True;native_error=0;total=([0-9]+);active=([0-9]+);terminated=([0-9]+)\r?$'
    $matched=[regex]::Matches($diagnostic,$pattern)
    if($matched.Count -ne 1 -or $matched[0].Groups[2].Value -cne $q[$entry.field] -or [int]$q[$entry.field] -lt 1 -or [int]$q[$entry.field] -gt 64){throw 'Quota accounting diagnostics differ from recorded actual counts.'}
   }
   $allObserved=@($allMembers)+@($recoveredMembers)
   if($q.api_create_returned -ceq 'True'){$allObserved+=@{pid=[int]$q.excess_pid;creation=[long]$q.excess_creation}}
   foreach($identity in $allObserved){
    $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById($identity.pid)}catch [ArgumentException]{}
    if($null -ne $actor){try{if(!$actor.HasExited -and $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq $identity.creation){throw 'Exact quota identity remains live.'}}finally{$actor.Dispose()}}
   }
   $jobQuotaObserved=@{root=$fixtureActors[0];actors=$allMembers;fixture_actors=$fixtureActors;recovered_actors=$recoveredMembers;recovery=$recovery;members=$members;members_after=$after;recovered_members=$recovered;spawned=$spawned;admission=$q;full_images=$fullImages;recovered_images=$recoveredImages;ordinary_payload_limit=16;physical_os_actor_limit_claimed=$false}
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
if ($Contract -like 'backend-*' -and $started -and $exited -and $pipesDrained -and !$custodyPending -and $ownExecutablesStopped -and !$failure) {
 try {
  if($observerKillUsed -or $status -ne 2){throw 'Expected negative public Driver result 2 was not observed.'}
  $recordPath=Join-Path $session 'payload-record.txt'
  $recordLines=[IO.File]::ReadAllLines($recordPath)
  if($recordLines.Count -ne 7){throw 'Independent payload failure-input record is incomplete.'}
  $values=@{}
  foreach($line in $recordLines){if($line -cnotmatch '^([a-z_]+)=(.*)$' -or $values.ContainsKey($Matches[1])){throw 'Payload failure-input record is malformed.'};$values[$Matches[1]]=$Matches[2]}
  $expectedMode=if($Contract -ceq 'backend-evidence-hardlink'){'evidence-hardlink'}else{'cleanup-readonly'}
  if($values.mode -cne $expectedMode -or $values.job_member -cne 'True' -or $values.pid -cnotmatch '^[1-9][0-9]*$' -or $values.creation_filetime_utc -cnotmatch '^[1-9][0-9]*$'){throw 'Native Job payload did not create the selected failure input.'}
  $runtimes=@(Get-ChildItem -LiteralPath $run -Directory -Force -Filter 'scoped-*')
  $journals=@(Get-ChildItem -LiteralPath $run -File -Force -Filter '.scoped-run-*.journal')
  $evidenceRoots=@(Get-ChildItem -LiteralPath $run -Directory -Force -Filter '.scoped-evidence-*')
  if($runtimes.Count -ne 1 -or $journals.Count -ne 1 -or $evidenceRoots.Count -ne 1){throw 'Exact negative runtime/journal/evidence inventory is incomplete.'}
  $runtimeObserved=$runtimes[0].FullName
  if(![string]::Equals($values.runtime,$runtimeObserved,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetDirectoryName($runtimeObserved) -cne $run -or [IO.Path]::GetFileName($runtimeObserved) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Payload runtime differs from exact monitor allocation.'}
  $selectedName=if($Contract -ceq 'backend-evidence-hardlink'){'evidence-hardlink-primary.txt'}else{'cleanup-readonly.txt'}
  $selectedFile=Join-Path $runtimeObserved $selectedName
  $selectedLink=if($Contract -ceq 'backend-evidence-hardlink'){Join-Path $runtimeObserved 'evidence-hardlink-alias.txt'}else{''}
  if(![string]::Equals($values.file,$selectedFile,[StringComparison]::OrdinalIgnoreCase) -or ![string]::Equals($values.link,$selectedLink,[StringComparison]::OrdinalIgnoreCase) -or !(Test-Path -LiteralPath $selectedFile -PathType Leaf)){throw 'Exact failure input was not retained.'}
  if($selectedLink){if(!(Test-Path -LiteralPath $selectedLink -PathType Leaf) -or [IO.File]::ReadAllText($selectedFile) -cne [IO.File]::ReadAllText($selectedLink)){throw 'Hardlink input is incomplete.'}}
  else{if((([IO.File]::GetAttributes($selectedFile)) -band [IO.FileAttributes]::ReadOnly) -eq 0){throw 'Real read-only cleanup input is missing.'}}
  $actor=$null;try{$actor=[Diagnostics.Process]::GetProcessById([int]$values.pid)}catch [ArgumentException]{}
  if($null -ne $actor){try{if(!$actor.HasExited -and $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -eq [long]$values.creation_filetime_utc){throw 'Exact failure-input payload actor remains live.'}}finally{$actor.Dispose()}}
  $journalLines=[IO.File]::ReadAllLines($journals[0].FullName);$decoded=@()
  foreach($line in $journalLines){if($line -cnotmatch '^[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8}:(.+)$'){throw 'Original journal framing is malformed.'};$decoded+=,$Matches[1]}
  $lifecycle=@($decoded|Where-Object{$_.StartsWith('LIFECYCLE|')})
  $evidence=@($decoded|Where-Object{$_.StartsWith('EVIDENCE|')})
  $outcome=@($decoded|Where-Object{$_.StartsWith('OUTCOME|')})
  $intent=@($decoded|Where-Object{$_.StartsWith('REMOVE_INTENT|')})
  $removed=@($decoded|Where-Object{$_.StartsWith('REMOVED|')})
  if($lifecycle.Count -ne 1 -or !$lifecycle[0].Contains('cleanup_confirmed=1') -or $removed.Count -ne 0){throw 'Negative backend journal falsely claims completion or lacks real Job closure.'}
  function Assert-BackendFailureCounts([int]$ExpectedEvidence,[int]$ExpectedOutcome,[int]$ExpectedIntent){
   if($evidence.Count -ne $ExpectedEvidence -or $outcome.Count -ne $ExpectedOutcome -or $intent.Count -ne $ExpectedIntent){throw 'Backend failure record counts differ from expectation.'}
  }
  $wanted=if($Contract -ceq 'backend-evidence-hardlink'){@(0,0,0)}else{@(1,1,1)}
  try{Assert-BackendFailureCounts (1-$wanted[0]) $wanted[1] $wanted[2]}catch{if($_.Exception.Message -cne 'Backend failure record counts differ from expectation.'){throw};$backendFailureSensitivity=$true}
  if(!$backendFailureSensitivity){throw 'Wrong backend outcome expectation did not fail.'}
  Assert-BackendFailureCounts $wanted[0] $wanted[1] $wanted[2]
  if($outcome.Count -eq 1 -and (!$outcome[0].Contains('host_exported=0') -or !$outcome[0].Contains('runtime_removed=0'))){throw 'Partial outcome falsely claims host export or runtime removal.'}
  foreach($key in $parentEnvironment.Keys){if([Environment]::GetEnvironmentVariable($key) -cne $parentEnvironment[$key]){$parentChanged=$true}}
  if([Environment]::CurrentDirectory -cne $parentCwd){$parentChanged=$true}
  if($parentChanged){throw 'Observer parent environment/cwd changed.'}
  $backendFailureObserved=@{mode=$expectedMode;runtime=$runtimeObserved;journal=$journals[0].FullName;evidence=$evidenceRoots[0].FullName;payload_pid=[int]$values.pid;payload_creation=[long]$values.creation_filetime_utc;original_records=$decoded.Count;payload_actor_stopped=$true;runtime_retained=$true}
  $backendFailureAccepted=$true;$hostRecord=$true;$complete=$true
 } catch {$failure=$_.Exception.ToString()}
}
$record = [ordered]@{id=$id;scope=$session;run=$run;exit=$status;accepted=$complete;failure=$failure;fresh_host_record=$hostRecord;phase=$Phase;contract=$Contract;driver_elapsed_seconds=$driverElapsedSeconds;driver_pid=$driverPid;driver_creation=$driverCreation;observer_kill_used=$observerKillUsed;process_disposed=$processDisposed;custody_pending=$custodyPending;channel_closure=$channelClosure;owned_executables_stopped=$ownExecutablesStopped;backend_failure_observed=$backendFailureObserved;backend_failure_sensitivity=$backendFailureSensitivity;backend_failure_accepted=$backendFailureAccepted;job_memory_observed=$jobMemoryObserved;job_memory_green=$jobMemoryGreen;job_memory_sensitivity=$jobMemorySensitivity;memory_actors_stopped=$memoryActorsStopped;job_quota_observed=$jobQuotaObserved;job_quota_green=$jobQuotaGreen;job_quota_sensitivity=$jobQuotaSensitivity;quota_protected_sensitivity=$quotaProtectedSensitivity;quota_actors_stopped=$quotaActorsStopped;job_resources_observed=$jobResourcesObserved;job_resources_red=$jobResourcesRed;job_resources_green=$jobResourcesGreen;job_resources_sensitivity=$jobResourcesSensitivity;job_actors_stopped=$jobActorsStopped;expected_payload_exit=$expectedPayload;work_retirement_red=$workRetirementRed;work_retirement_green=$workRetirementGreen;environment_contract_red=$environmentRed;environment_contract_green=$environmentGreen;allocated_runtime=$runtimeObserved;runtime_absent_readback=$runtimeAbsent;runtime_absence_negative_control=$runtimeAbsenceRed;environment_observed=$environmentObserved;environment_mismatches=$environmentMismatches;parent_environment_changed=$parentChanged;fixture_sha256=$FixtureSha256;fixture_build_manifest_sha256=((Get-FileHash -LiteralPath $fixtureBuild.manifest).Hash.ToLowerInvariant());fixture_build=$fixtureBuild.build;driver_launched=$started;exact_driver_exited=$exited;pipes_drained=$pipesDrained;retained_driver_handles=$custodyPending;retained_binaries=$expected;product_run=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
$files=@(Get-Item -LiteralPath (Join-Path $session 'observer.json'))
foreach($path in @($stdout,$stderr)){if(Test-Path -LiteralPath $path -PathType Leaf){$files+=@(Get-Item -LiteralPath $path)}}
if(Test-Path -LiteralPath (Join-Path $session 'payload-record.txt') -PathType Leaf){$files+=@(Get-Item -LiteralPath (Join-Path $session 'payload-record.txt'))}
# Enumerate runtime evidence only after the validated completion/removal receipt.
# On an observer/control failure export stable originals and preserve guest custody.
if (!$custodyPending -and $ownExecutablesStopped) { $files += @(Get-ChildItem -LiteralPath $run -Recurse -File) }
$files+=@(Get-ChildItem -LiteralPath $bin -File);$files+=@(Get-ChildItem -LiteralPath $input -File)
if($fixtureReadback){$files+=@(Get-ChildItem -LiteralPath $fixtureReadback -Recurse -File)}
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
