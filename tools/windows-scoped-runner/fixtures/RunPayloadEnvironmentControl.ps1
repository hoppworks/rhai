param(
 [Parameter(Mandatory=$true)][string]$FixturePath,
 [Parameter(Mandatory=$true)][string]$FixtureSha256,
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][string]$Id,
 [ValidateSet('RED','GREEN','RETIREMENT_ABORT')][string]$Phase='RED',
 [string]$BuildRoot,
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
if($BuildRoot){
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
}else{
 $build=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build'
 $expected=@{'ScopedRunner.exe'='c3d91a8bcf550ef8087b7c057455ac876fe0a958b4e22de816b55daa659cb486';'MonitorAcceptanceDriver.exe'='caf4afaa2f604fb47fc554c82d9493854be0959c8d329bff7a88fd7fe9e827cb'}
 foreach($name in $expected.Keys){$file=Join-Path $build $name;No-Reparse $file;if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $expected[$name]){throw 'Retained production binary changed.'}}
}
if($Phase -ceq 'RETIREMENT_ABORT' -and !$BuildRoot){throw 'The retirement-abort phase requires the current source-bound build.'}
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
$expectedPayload=if($Phase -ceq 'GREEN'){'00000000'}else{'0000002A'}
$environmentObserved=@{};$environmentMismatches=@();$runtimeObserved=$null
$environmentRed=$false;$environmentGreen=$false;$workRetirementRed=$false;$workRetirementGreen=$false;$parentChanged=$false
$stdout = Join-Path $session 'bootstrap.stdout'; $stderr = Join-Path $session 'bootstrap.stderr'
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $build 'MonitorAcceptanceDriver.exe'
$payloadArguments=if($Phase -ceq 'RETIREMENT_ABORT'){'--retirement-abort'}else{'payload-environment.txt --environment'}
$info.Arguments = '--mode success --source "'+$input+'" --exe fixture.exe --expected-payload-exit '+$expectedPayload+' -- '+$payloadArguments
$info.WorkingDirectory = $build; $info.UseShellExecute = $false; $info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
$info.EnvironmentVariables['AGENT_RUNTIME_DIR'] = $run
$process = [Diagnostics.Process]::new(); $process.StartInfo = $info
$status = -1; $complete = $false; $failure = ''; $hostRecord = $false
$started = $false; $exited = $false; $pipesDrained = $false; $readers = @()
$observerDeadline = [Diagnostics.Stopwatch]::StartNew()
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
try {
 if (!$process.Start()) { throw 'Native driver did not start.' }; $started = $true
 $handle = $process.Handle
 if ($handle -eq [IntPtr]::Zero) { throw 'Exact retained driver handle missing.' }
 # A single async chunk per stream is in flight. Save each original chunk to its
 # bounded durable file immediately; no ReadToEnd result is lost on later failure.
 foreach ($definition in @(@{Reader=$process.StandardOutput;Path=$stdout},@{Reader=$process.StandardError;Path=$stderr})) {
  $channel = [pscustomobject]@{Reader=$definition.Reader;Writer=[IO.StreamWriter]::new($definition.Path,$false,[Text.UTF8Encoding]::new($false));Buffer=[char[]]::new(1024);Task=$null;Bytes=0;Eof=$false;Error=''}
  $readers += $channel; $channel.Task = $channel.Reader.ReadAsync($channel.Buffer,0,$channel.Buffer.Length)
 }
 while (!$process.WaitForExit(20)) {
  foreach ($channel in $readers) { Save-CompletedChunk $channel }
  $driverBound=if($Phase -ceq 'RETIREMENT_ABORT'){180}else{10}
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
 foreach ($channel in $readers) { $channel.Writer.Flush(); $channel.Writer.Dispose() }
 if ($started -and !$pipesDrained) { $failure += "`nOriginal pipe drain incomplete; retained tasks/handles and guest runtime are not retired." }
 if (!(Test-Path -LiteralPath $stdout)) { [IO.File]::WriteAllText($stdout,'',[Text.UTF8Encoding]::new($false)) }
 if (!(Test-Path -LiteralPath $stderr)) { [IO.File]::WriteAllText($stderr,'',[Text.UTF8Encoding]::new($false)) }
 if ($exited -and $pipesDrained) { foreach ($channel in $readers) { $channel.Reader.Dispose() }; $process.Dispose() }
}
if ($started -and $exited -and $pipesDrained -and !$failure) {
 try {
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
  if (@(Get-ChildItem -LiteralPath $run -Directory -Filter 'scoped-*').Count -ne 0) { throw 'Actual runtime presence contradicts cleanup receipt.' }
  $hostRecord = $true; $complete = $true
 } catch { $failure = $_.Exception.ToString() }
}
$record = [ordered]@{id=$id;scope=$session;run=$run;exit=$status;accepted=$complete;failure=$failure;fresh_host_record=$hostRecord;phase=$Phase;expected_payload_exit=$expectedPayload;work_retirement_red=$workRetirementRed;work_retirement_green=$workRetirementGreen;environment_contract_red=$environmentRed;environment_contract_green=$environmentGreen;allocated_runtime=$runtimeObserved;environment_observed=$environmentObserved;environment_mismatches=$environmentMismatches;parent_environment_changed=$parentChanged;fixture_sha256=$FixtureSha256;driver_launched=$started;exact_driver_exited=$exited;pipes_drained=$pipesDrained;retained_driver_handles=($started -and (!$exited -or !$pipesDrained));retained_binaries=$expected;product_run=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 5),[Text.UTF8Encoding]::new($false))
$files = @(Get-Item -LiteralPath $stdout,$stderr,(Join-Path $session 'observer.json'))
# Enumerate runtime evidence only after the validated completion/removal receipt.
# On an observer/control failure export stable originals and preserve guest custody.
if ($complete) { $files += @(Get-ChildItem -LiteralPath $run -Recurse -File) }
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
$record | ConvertTo-Json -Compress
$controlExitCode=if($complete){0}else{2}
if($ReturnStatusToCaller){$global:RhaiPayloadControlExitCode=$controlExitCode;return}
exit $controlExitCode
