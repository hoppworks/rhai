$ErrorActionPreference = 'Stop'
$id = 'rhai-public-loop01-20261008T125846Z-b7f83433'
$build = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\runtime-acl-green02-20261008-b7f83433\run\monitor-source-f5d92b7bceaa46e8b751d9359c3b0f6a\build'
$expected = @{
 'ScopedRunner.exe' = '4db31fded99370901f34af6c39661f73f712d8a7b6061678c1bcc4046d8a0a0d'
 'MonitorAcceptanceDriver.exe' = '67d6278249b229e94ebaf737816dcd7e00121dd30b0f03867ab2aedf05f864a1'
 'PayloadFixture.exe' = 'ffaad1a2194e9b1dd94a8880d734ec0b31ba3e43aca61eaad87cd8983b72449f'
}
foreach ($name in $expected.Keys) {
 $file = Join-Path $build $name
 if ((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $expected[$name]) { throw "Retained native binary changed: $name" }
}
if ((Get-FileHash 'C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe').Hash.ToLowerInvariant() -cne 'cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1') { throw 'Accepted compiler identity changed; preserve retained build.' }
$session = Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\custody-loop01-20261008-b7f83433'
$run = Join-Path $session 'run'; $input = Join-Path $session 'input'
if (Test-Path -LiteralPath $session) { throw 'Owned public session already exists; preserve it.' }
$cursor = [IO.Path]::GetFullPath($session)
while ($cursor) {
 if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse ancestor refused: $cursor" }
 $ancestor = [IO.Directory]::GetParent($cursor); $cursor = if ($null -eq $ancestor) { $null } else { $ancestor.FullName }
}
New-Item -ItemType Directory -Path $run,$input | Out-Null
Copy-Item -LiteralPath (Join-Path $build 'PayloadFixture.exe') -Destination (Join-Path $input 'fixture.exe')
if ((Get-FileHash (Join-Path $input 'fixture.exe')).Hash.ToLowerInvariant() -cne $expected['PayloadFixture.exe']) { throw 'Copied immutable payload changed.' }
$stdout = Join-Path $session 'bootstrap.stdout'; $stderr = Join-Path $session 'bootstrap.stderr'
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = Join-Path $build 'MonitorAcceptanceDriver.exe'
$info.Arguments = '--mode success --source "' + $input + '" --exe fixture.exe --expected-payload-exit 00000000 -- payload-record.txt'
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
  if ($observerDeadline.Elapsed.TotalSeconds -ge 10) { throw 'Public fixture driver exceeded its independent 10-second observer bound.' }
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
  foreach ($line in @('CLIENT_EXIT=0x0000004E','MODE=success;ACTION_CONFIRMED=True;','PAYLOAD_EXIT=00000000','SUPERVISION=PayloadExited','CLEANUP_CONFIRMED=True','RUNTIME_REMOVED=True','HOST_EXPORTED=False')) {
   if (!$output.Contains($line)) { throw "Missing exact native result: $line" }
  }
  $evidence = @(Get-ChildItem -LiteralPath $run -Directory -Filter '.scoped-evidence-*')
  if ($evidence.Count -ne 1) { throw 'Expected one invocation-owned evidence directory.' }
  $marker = Join-Path $evidence[0].FullName 'runtime\payload-record.txt'
  if ([IO.File]::ReadAllText($marker) -cne "payload-started`r`n") { throw 'Fresh independent native payload-record mismatch.' }
  if (@(Get-ChildItem -LiteralPath $run -Directory -Filter 'scoped-*').Count -ne 0) { throw 'Actual runtime presence contradicts cleanup receipt.' }
  $hostRecord = $true; $complete = $true
 } catch { $failure = $_.Exception.ToString() }
}
$record = [ordered]@{id=$id;scope=$session;run=$run;exit=$status;accepted=$complete;failure=$failure;fresh_host_record=$hostRecord;parent_environment_changed=$false;driver_launched=$started;exact_driver_exited=$exited;pipes_drained=$pipesDrained;retained_driver_handles=($started -and (!$exited -or !$pipesDrained));retained_binaries=$expected;product_run=$false}
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
