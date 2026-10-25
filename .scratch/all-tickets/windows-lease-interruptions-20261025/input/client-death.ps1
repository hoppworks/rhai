$ErrorActionPreference = 'Stop'
$id = 'rhai-client-death-current-f9f42704c04c432e866e40380ec2da47'
$build = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\work-abort-build-4e92c3e57fa14837992fd1d20a3f2f8a\run\monitor-source-4e92c3e57fa14837992fd1d20a3f2f8a\build'
$payloadBuild = $build
$expected = @{
 'PayloadFixture.exe' = '8564df0bdf03e771c3cc27c7b1b01a77fe3184d44ef9e0a52e1053404a0a3058'
 'MonitorAcceptanceDriver.exe' = '27b1e6f380b5e75f425db2a993793f5a61f64be74827a8ba1957b0e18d5f059a'
 'ScopedRunner.exe' = '72b029407411bacf82c0451b1528ba2faa9644537d386e7b0ac4952c2a3986b2'
}
$cursor=[IO.Path]::GetFullPath($build)
while($cursor){
 if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse current build refused.'}
 $ancestor=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $ancestor){$null}else{$ancestor.FullName}
}
foreach ($name in $expected.Keys) {
 $file=Join-Path $build $name
 if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $expected[$name]){throw 'Current retained binary changed.'}
}
$runtime=$null;$runtimeAbsent=$false;$runtimeAbsenceRed=$false
$session = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\custody-client-death-f9f42704c04c'
$run = Join-Path $session 'run'; $input = Join-Path $session 'input'
if (Test-Path -LiteralPath $session) { throw 'Owned public session already exists; preserve it.' }
$cursor = [IO.Path]::GetFullPath($session)
while ($cursor) {
 if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse ancestor refused: $cursor" }
 $ancestor = [IO.Directory]::GetParent($cursor); $cursor = if ($null -eq $ancestor) { $null } else { $ancestor.FullName }
}
New-Item -ItemType Directory -Path $run,$input | Out-Null
Copy-Item -LiteralPath (Join-Path $payloadBuild 'PayloadFixture.exe') -Destination (Join-Path $input 'fixture.exe')
if ((Get-FileHash (Join-Path $input 'fixture.exe')).Hash.ToLowerInvariant() -cne $expected['PayloadFixture.exe']) { throw 'Copied immutable payload changed.' }
$stdout = Join-Path $session 'bootstrap.stdout'; $stderr = Join-Path $session 'bootstrap.stderr'
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $build 'MonitorAcceptanceDriver.exe'
$info.Arguments = '--mode client-death --source "' + $input + '" --exe fixture.exe --expected-payload-exit 0000007D -- payload-record.txt --hold'
$info.WorkingDirectory = $build; $info.UseShellExecute = $false; $info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
$info.EnvironmentVariables['AGENT_RUNTIME_DIR'] = $run
$process = [Diagnostics.Process]::new(); $process.StartInfo = $info
$status = -1; $complete = $false; $failure = ''; $hostRecord = $false
$assertionRed = $false; $payloadStoppedReadback = $false; $payloadPid = $null; $payloadCreation = $null
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
  if ($observerDeadline.Elapsed.TotalSeconds -ge 190) { throw 'Public fixture driver exceeded its independent 190-second observer bound.' }
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
  foreach ($line in @('CLIENT_EXIT=0x00000001','MODE=client-death;ACTION_CONFIRMED=True;','PAYLOAD_EXIT=0000007D','SUPERVISION=MonitorStopped','CLEANUP_CONFIRMED=True','RUNTIME_REMOVED=True','HOST_EXPORTED=False')) {
   if (!$output.Contains($line)) { throw "Missing exact native result: $line" }
  }
  $evidence = @(Get-ChildItem -LiteralPath $run -Directory -Filter '.scoped-evidence-*')
  if ($evidence.Count -ne 1) { throw 'Expected one invocation-owned evidence directory.' }
  $marker = Join-Path $evidence[0].FullName 'runtime\payload-record.txt'
  $markerBytes = [IO.File]::ReadAllText($marker)
  function Assert-ObservedPayload([string] $expectedRecord) {
   if ($markerBytes -cne $expectedRecord) { throw 'Fresh independent native payload-record mismatch.' }
  }
  $assertionRed = $false
  try { Assert-ObservedPayload 'wrong-payload-expectation' } catch {
   if ($_.Exception.Message -cne 'Fresh independent native payload-record mismatch.') { throw }
   $assertionRed = $true
  }
  if (!$assertionRed) { throw 'Wrong payload expectation was not rejected.' }
  Assert-ObservedPayload ("payload-started" + [char]13 + [char]10)
  $identityText = [IO.File]::ReadAllText($marker + '.identity')
  if ($identityText -cnotmatch '^pid=([0-9]+) creation=([0-9]+)\r\n$') { throw 'Fresh payload identity missing or malformed.' }
  $payloadPid = [int]$Matches[1]; $payloadCreation = [long]$Matches[2]
  $observedProcess = $null; $sameLiveIdentity = $false
  try { $observedProcess = [Diagnostics.Process]::GetProcessById($payloadPid) } catch [ArgumentException] {}
  if ($null -ne $observedProcess) {
   try { $sameLiveIdentity = !$observedProcess.HasExited -and $observedProcess.StartTime.ToUniversalTime().ToFileTimeUtc() -eq $payloadCreation } finally { $observedProcess.Dispose() }
  }
  if ($sameLiveIdentity) { throw 'Independently recorded payload identity remains live.' }
  $payloadStoppedReadback = $true
  $runtimeMatches=[regex]::Matches($output,'(?m)^RUNTIME=([^\r\n]+)\r?$')
  if($runtimeMatches.Count -ne 1){throw 'Expected one actual runtime report.'}
  $runtime=[IO.Path]::GetFullPath($runtimeMatches[0].Groups[1].Value)
  if([IO.Path]::GetDirectoryName($runtime) -cne $run -or [IO.Path]::GetFileName($runtime) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Runtime is not this exact owned allocation.'}
  function Assert-RuntimeAbsent([string]$Path){if(Test-Path -LiteralPath $Path){throw 'Runtime absence assertion failed.'}}
  try{Assert-RuntimeAbsent $evidence[0].FullName}catch{if($_.Exception.Message -cne 'Runtime absence assertion failed.'){throw};$runtimeAbsenceRed=$true}
  if(!$runtimeAbsenceRed){throw 'Runtime absence control did not reject the retained snapshot.'}
  Assert-RuntimeAbsent $runtime
  if(@(Get-ChildItem -LiteralPath $run -Force -Directory -Filter 'scoped-*').Count -ne 0){throw 'Unexpected live runtime remains.'}
  $runtimeAbsent=$true
  $hostRecord = $true; $complete = $true
 } catch { $failure = $_.Exception.ToString() }
}
$record = [ordered]@{id=$id;scope=$session;run=$run;exit=$status;accepted=$complete;failure=$failure;fresh_host_record=$hostRecord;wrong_expectation_red=$assertionRed;payload_stopped_readback=$payloadStoppedReadback;payload_pid=$payloadPid;payload_creation=$payloadCreation;allocated_runtime=$runtime;runtime_absent_readback=$runtimeAbsent;runtime_absence_negative_control=$runtimeAbsenceRed;parent_environment_changed=$false;driver_launched=$started;exact_driver_exited=$exited;pipes_drained=$pipesDrained;retained_driver_handles=($started -and (!$exited -or !$pipesDrained));retained_binaries=$expected;product_run=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 5),[Text.UTF8Encoding]::new($false))
$files = @(Get-Item -LiteralPath $stdout,$stderr,(Join-Path $session 'observer.json'))
# Enumerate runtime evidence only after the validated completion/removal receipt.
# On an observer/control failure export stable originals and preserve guest custody.
if ($complete) { $files += @(Get-ChildItem -LiteralPath $run -Recurse -File) }
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
