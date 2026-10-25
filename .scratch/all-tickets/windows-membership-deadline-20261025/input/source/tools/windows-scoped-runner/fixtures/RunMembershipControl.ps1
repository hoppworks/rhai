param(
 [Parameter(Mandatory=$true)][string]$FixturePath,
 [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$FixtureSha256,
 [Parameter(Mandatory=$true)][string]$DriverBuild,
 [Parameter(Mandatory=$true)][string]$SessionPath,
 [Parameter(Mandatory=$true)][string]$Id,
 [ValidateSet('membership','deadline')][string]$Mode='membership'
)
$ErrorActionPreference='Stop';$id=$Id;$build=[IO.Path]::GetFullPath($DriverBuild)
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
if([IO.Directory]::GetParent([IO.Path]::GetFullPath($SessionPath)).FullName -cne $private -or [IO.Path]::GetFileName($SessionPath) -notmatch '^membership-(membership|deadline)-[0-9a-f]{32}$'){throw 'Exact fresh owned control scope required.'}
$expected=@{'MonitorAcceptanceDriver.exe'='27b1e6f380b5e75f425db2a993793f5a61f64be74827a8ba1957b0e18d5f059a';'ScopedRunner.exe'='72b029407411bacf82c0451b1528ba2faa9644537d386e7b0ac4952c2a3986b2'}
foreach($file in @($FixturePath,(Join-Path $build 'MonitorAcceptanceDriver.exe'),(Join-Path $build 'ScopedRunner.exe'))){
 $cursor=[IO.Path]::GetFullPath($file)
 while($cursor){if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse input refused.'};$parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}}
}
foreach($name in $expected.Keys){if((Get-FileHash -LiteralPath (Join-Path $build $name)).Hash.ToLowerInvariant() -cne $expected[$name]){throw 'Current native binary changed.'}}
if((Get-FileHash -LiteralPath $FixturePath).Hash.ToLowerInvariant() -cne $FixtureSha256){throw 'Native source-bound fixture changed.'}
$runtime=$null;$runtimeAbsent=$false;$runtimeAbsenceRed=$false
$session = [IO.Path]::GetFullPath($SessionPath)
$run = Join-Path $session 'run'; $input = Join-Path $session 'input'
if (Test-Path -LiteralPath $session) { throw 'Owned public session already exists; preserve it.' }
$cursor = [IO.Path]::GetFullPath($session)
while ($cursor) {
 if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse ancestor refused: $cursor" }
 $ancestor = [IO.Directory]::GetParent($cursor); $cursor = if ($null -eq $ancestor) { $null } else { $ancestor.FullName }
}
New-Item -ItemType Directory -Path $run,$input | Out-Null
Copy-Item -LiteralPath $FixturePath -Destination (Join-Path $input 'fixture.exe')
if ((Get-FileHash (Join-Path $input 'fixture.exe')).Hash.ToLowerInvariant() -cne $FixtureSha256) { throw 'Copied immutable payload changed.' }
$stdout = Join-Path $session 'bootstrap.stdout'; $stderr = Join-Path $session 'bootstrap.stderr'
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $build 'MonitorAcceptanceDriver.exe'
$argument = if($Mode -eq 'membership'){'--membership'}else{'--membership-deadline'}
$info.Arguments = '--mode success --source "' + $input + '" --exe fixture.exe --expected-payload-exit 00000000 -- '+$argument+' pair'
$info.WorkingDirectory = $build; $info.UseShellExecute = $false; $info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true; $info.RedirectStandardError = $true
$info.EnvironmentVariables['AGENT_RUNTIME_DIR'] = $run
$process = [Diagnostics.Process]::new(); $process.StartInfo = $info
$status = -1; $complete = $false; $failure = ''; $hostRecord = $false
$assertionRed = $false; $payloadStoppedReadback = $false; $payloadPid = $null; $payloadCreation = $null
$started = $false; $exited = $false; $pipesDrained = $false; $readers = @()
$observerDeadline = [Diagnostics.Stopwatch]::StartNew()
$pairSeenLive=$false;$liveIdentities=@()
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
  if($Mode -eq 'deadline' -and !$pairSeenLive){
   $roots=@(Get-ChildItem -LiteralPath $run -Force -Directory -Filter 'scoped-*')
   if($roots.Count -eq 1 -and (Test-Path -LiteralPath (Join-Path $roots[0].FullName 'pair.ready'))){
    $liveIdentities=@()
    foreach($name in @('pair.identity','pair.child.identity')){
     $text=[IO.File]::ReadAllText((Join-Path $roots[0].FullName $name))
     if($text -cnotmatch '^pid=([0-9]+) creation=([0-9]+)\r\n$'){throw 'Live actor identity invalid.'}
     $actor=[Diagnostics.Process]::GetProcessById([int]$Matches[1])
     try {if($actor.HasExited -or $actor.StartTime.ToUniversalTime().ToFileTimeUtc() -ne [long]$Matches[2]){throw 'Exact membership actor not live.'};$liveIdentities+=@{pid=$actor.Id;creation=$Matches[2]}} finally {$actor.Dispose()}
    }
    $pairSeenLive=$true
   }
  }
  if ($observerDeadline.Elapsed.TotalSeconds -ge 240) { throw 'Public fixture driver exceeded its independent 240-second observer bound.' }
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
$actorsStopped=$false;$membershipRed=$false;$actors=@();$journalPath=$null
if ($started -and $exited -and $pipesDrained -and !$failure) {
 try {
  $output=[IO.File]::ReadAllText($stdout)
  if($Mode -eq 'membership'){
   if($status -ne 0 -or !$output.Contains('SUPERVISION=PayloadExited') -or !$output.Contains('PAYLOAD_EXIT=00000000') -or !$output.Contains('CLEANUP_CONFIRMED=True') -or !$output.Contains('RUNTIME_REMOVED=True')){throw 'Normal public Driver contract failed.'}
  } else {
   if($observerDeadline.Elapsed.TotalSeconds -lt 179 -or ($status -ne 124 -and !($status -eq 2 -and [IO.File]::ReadAllText($stderr).Contains('whole-driver deadline expired')))){throw 'Driver did not reach its deliberate180second deadline.'}
   if(!$pairSeenLive){throw 'Both deadline actors were not independently observed live.'}
  }
  $closure=[Diagnostics.Stopwatch]::StartNew()
  do {
   $evidence=@(Get-ChildItem -LiteralPath $run -Force -Directory -Filter '.scoped-evidence-*')
   $journals=@(Get-ChildItem -LiteralPath $run -Force -File -Filter '.scoped-run-*.journal')
   $roots=@(Get-ChildItem -LiteralPath $run -Force -Directory -Filter 'scoped-*')
   if($roots.Count -eq 0 -and $evidence.Count -eq 1 -and $journals.Count -eq 1){
    $lines=[IO.File]::ReadAllLines($journals[0].FullName)
    if($lines.Count -eq 8 -and $lines[-1].Contains(':REMOVED|')){break}
   }
   if($closure.Elapsed.TotalSeconds -ge 60){throw 'Independent exact closure did not complete within60seconds.'}
   [Threading.Thread]::Sleep(20)
  }while($true)
  $journalPath=$journals[0].FullName
  $parts=$lines[0].Split(':',3)[2].Split('|')
  if($parts[0] -cne 'INTENT'){throw 'Missing actual allocation intent.'}
  $runtime=[IO.Path]::GetFullPath($parts[2])
  if([IO.Path]::GetDirectoryName($runtime) -cne $run -or [IO.Path]::GetFileName($runtime) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Runtime outside exact control.'}
  function Assert-RuntimeAbsent([string]$Path){if(Test-Path -LiteralPath $Path){throw 'Runtime absence assertion failed.'}}
  try{Assert-RuntimeAbsent $evidence[0].FullName}catch{if($_.Exception.Message -cne 'Runtime absence assertion failed.'){throw};$runtimeAbsenceRed=$true}
  if(!$runtimeAbsenceRed){throw 'Runtime absence RED missing.'};Assert-RuntimeAbsent $runtime;$runtimeAbsent=$true
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
   $expectedMembership='self='+$identities[$index].text+';peer='+$identities[1-$index].text+';members='+($sorted -join ',')+';assigned=2;returned=2'
   $actual=[IO.File]::ReadAllText((Join-Path $snapshot ($name+'.membership')))
   function Assert-Membership([string]$Wanted){if($actual -cne $Wanted+[char]13+[char]10){throw 'Exact native Job membership mismatch.'}}
   if($index -eq 0){try{Assert-Membership 'wrong-pair'}catch{if($_.Exception.Message -cne 'Exact native Job membership mismatch.'){throw};$membershipRed=$true}}
   Assert-Membership $expectedMembership
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
  if($Mode -eq 'deadline'){
   for($index=0;$index -lt 2;$index++){if($actors[$index].pid -ne $liveIdentities[$index].pid -or $actors[$index].creation -ne [long]$liveIdentities[$index].creation){throw 'Live and stopped actor identities differ.'}}
  }
  $hostRecord=$true;$payloadStoppedReadback=$true;$complete=$true
 }catch{$failure=$_.Exception.ToString()}
}
$record=[ordered]@{id=$id;mode=$Mode;scope=$session;run=$run;exit=$status;accepted=$complete;failure=$failure;fresh_host_record=$hostRecord;wrong_expectation_red=$assertionRed;membership_negative_control=$membershipRed;actors=$actors;actors_stopped=$actorsStopped;pair_seen_live=$pairSeenLive;live_identities=$liveIdentities;allocated_runtime=$runtime;runtime_absent_readback=$runtimeAbsent;runtime_absence_negative_control=$runtimeAbsenceRed;journal=$journalPath;driver_launched=$started;exact_driver_exited=$exited;pipes_drained=$pipesDrained;retained_driver_handles=($started -and (!$exited -or !$pipesDrained));retained_binaries=$expected;fixture_sha256=$FixtureSha256;elapsed_seconds=$observerDeadline.Elapsed.TotalSeconds;product_run=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
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
