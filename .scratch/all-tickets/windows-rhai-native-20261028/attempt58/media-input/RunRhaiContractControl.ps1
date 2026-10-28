param(
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][string]$SourceRoot,
 [Parameter(Mandatory=$true)][string]$BuildRoot,
 [Parameter(Mandatory=$true)][string]$Id,
 [Parameter(Mandatory=$true)][string]$CargoSha256
)
$ErrorActionPreference='Stop'
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$session=[IO.Path]::GetFullPath($Session)
if([IO.Directory]::GetParent($session).FullName -cne $private -or [IO.Path]::GetFileName($session) -cne 'n-0cea30ae') { throw 'Exact own project scope required.' }
$source=[IO.Path]::GetFullPath($SourceRoot)
if($source -cne (Join-Path $session 'source')){throw 'Project source differs from owned copy.'}
if((Get-FileHash -LiteralPath (Join-Path $source 'cargo.exe')).Hash.ToLowerInvariant() -cne $CargoSha256){throw 'Native Cargo proxy changed.'}
$build=[IO.Path]::GetFullPath($BuildRoot)
if($build -cne (Join-Path $private 'public-refresh-e2047d40e48afb4426d07e2a1e881f19\run\monitor-source-e2047d40e48afb4426d07e2a1e881f19\build')){throw 'Unexpected public native build.'}
$buildManifest=Join-Path ([IO.Directory]::GetParent($build).FullName) 'build-manifest.txt'
if((Get-FileHash -LiteralPath $buildManifest).Hash.ToLowerInvariant() -cne '8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1'){throw 'Public build manifest differs from accepted native readback.'}
$rows=[IO.File]::ReadAllLines($buildManifest)
$acceptedPins=@{'ScopedRunner.exe'='ff836aa0ce75807c817097327b60a2a9cd8741a0937cfb072bd17adefd994c7f';'MonitorAcceptanceDriver.exe'='090d29d3eb3642c6acb53f241c340cd7ef800f07977671039465ae140837e5a0'}
if($rows[0] -cne 'compiler_sha256=cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1'){throw 'Accepted native compiler pin differs.'}
Copy-Item -LiteralPath $buildManifest -Destination (Join-Path $session 'build-manifest.txt')
$bin=Join-Path $session 'bin';New-Item -ItemType Directory -Path $bin|Out-Null
foreach($name in @('ScopedRunner.exe','MonitorAcceptanceDriver.exe')){
 $matches=@($rows|Where-Object{$_ -cmatch ('^[0-9a-f]{64}  build/'+[regex]::Escape($name)+'$')})
 if($matches.Count -ne 1 -or $matches[0].Substring(0,64) -cne $acceptedPins[$name]){throw "Public build differs from accepted binary pin: $name"}
 $original=Join-Path $build $name
 if((Get-FileHash -LiteralPath $original).Hash.ToLowerInvariant() -cne $matches[0].Substring(0,64)){throw "Public build changed: $name"}
 Copy-Item -LiteralPath $original -Destination $bin
 if((Get-FileHash -LiteralPath (Join-Path $bin $name)).Hash.ToLowerInvariant() -cne $matches[0].Substring(0,64)){throw "Private public tool copy changed: $name"}
}
$run=Join-Path $session 'run';New-Item -ItemType Directory -Path $run|Out-Null
$stdout=Join-Path $session 'driver.stdout';$stderr=Join-Path $session 'driver.stderr'
$info=[Diagnostics.ProcessStartInfo]::new()
$info.FileName=Join-Path $bin 'MonitorAcceptanceDriver.exe'
$info.Arguments='--mode success --source "'+$source+'" --exe cmd.exe --expected-payload-exit 00000000 -- /D /C RunRhaiContract.cmd'
$info.WorkingDirectory=$bin;$info.UseShellExecute=$false;$info.CreateNoWindow=$true
$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
$info.EnvironmentVariables['AGENT_RUNTIME_DIR']=$run
if($null -ne $global:RhaiProjectCommandPendingCustody){throw 'Previous exact project custody unresolved.'}
$process=[Diagnostics.Process]::new();$process.StartInfo=$info
$readers=[Collections.Generic.List[object]]::new()
$global:RhaiProjectCommandPendingCustody=[pscustomobject]@{Process=$process;Readers=$readers;Scope=$session;ExactExitConfirmed=$false;PipesDrained=$false;ProcessDisposed=$false}
$status=-1;$complete=$false;$failure='';$started=$false;$exited=$false;$pipesDrained=$false;$processDisposed=$false;$observerKillUsed=$false
$driverPid=0;$driverCreation=0L;$driverElapsedSeconds=0.0;$runtimeObserved='';$wrongExpectationRejected=$false;$productTestRun=$false;$actualOutcome='unobserved'
$clock=[Diagnostics.Stopwatch]::StartNew()
function Save-Chunk([object]$Channel){
 if($null -eq $Channel.Task -or !$Channel.Task.IsCompleted){return}
 try{
  $task=$Channel.Task;$Channel.Task=$null;$count=$task.GetAwaiter().GetResult()
  if($count -eq 0){$Channel.Eof=$true;return}
  $Channel.Bytes+=[Text.Encoding]::UTF8.GetByteCount($Channel.Buffer,0,$count)
  if($Channel.Bytes -gt 4MB){throw 'Driver output exceeds4MiB; prefix preserved.'}
  $Channel.Writer.Write($Channel.Buffer,0,$count);$Channel.Writer.Flush()
  $Channel.Task=$Channel.Reader.ReadAsync($Channel.Buffer,0,$Channel.Buffer.Length)
 }catch{$Channel.Error=$_.Exception.ToString();throw}
}
try{
 if(!$process.Start()){throw 'Native Driver did not start.'};$started=$true
 $driverPid=$process.Id;$driverCreation=$process.StartTime.ToUniversalTime().ToFileTimeUtc()
 if($process.Handle -eq [IntPtr]::Zero){throw 'Exact Driver handle missing.'}
 foreach($definition in @(@{Output=$true;Path=$stdout},@{Output=$false;Path=$stderr})){
  $channel=[pscustomobject]@{Reader=$null;Writer=$null;Buffer=[char[]]::new(1024);Task=$null;Bytes=0;Eof=$false;Error='';WriterDisposed=$false;ReaderDisposed=$false}
  $readers.Add($channel);$channel.Reader=if($definition.Output){$process.StandardOutput}else{$process.StandardError}
  $channel.Writer=[IO.StreamWriter]::new($definition.Path,$false,[Text.UTF8Encoding]::new($false))
  $channel.Task=$channel.Reader.ReadAsync($channel.Buffer,0,$channel.Buffer.Length)
 }
 while(!$process.WaitForExit(20)){
  foreach($channel in $readers){Save-Chunk $channel}
  if($clock.Elapsed.TotalSeconds -ge 185){throw 'Native Rhai Driver exceeded independent185second bound.'}
 }
 $exited=$true;$driverElapsedSeconds=$clock.Elapsed.TotalSeconds;$process.Refresh();$status=[int]$process.ExitCode
}catch{$failure=$_.Exception.ToString()}
finally{
 if($started -and !$exited){
  try{
   if(!$process.HasExited){$observerKillUsed=$true;$process.Kill()}
   if(!$process.WaitForExit(10000)){throw 'Exact Driver exit remains unconfirmed after bounded termination.'}
   $exited=$true;$process.Refresh();$status=[int]$process.ExitCode
  }catch{$failure+="`nExact Driver cleanup failed: "+$_.Exception.ToString()}
 }
 $drain=[Diagnostics.Stopwatch]::StartNew()
 do{
  foreach($channel in $readers){try{Save-Chunk $channel}catch{$failure+="`nOriginal pipe read failed: "+$_.Exception.ToString()}}
  if(@($readers|Where-Object{$null -ne $_.Task}).Count -eq 0){break}
  [Threading.Thread]::Sleep(10)
 }while($drain.Elapsed.TotalSeconds -lt 10)
 $pipesDrained=$readers.Count -eq 2 -and @($readers|Where-Object{!$_.Eof -or $_.Error}).Count -eq 0
 $global:RhaiProjectCommandPendingCustody.ExactExitConfirmed=$exited
 $global:RhaiProjectCommandPendingCustody.PipesDrained=$pipesDrained
 foreach($channel in $readers){
  if($null -ne $channel.Writer){try{$channel.Writer.Flush();$channel.Writer.Dispose();$channel.WriterDisposed=$true}catch{$failure+="`nOriginal writer disposal failed: "+$_.Exception.ToString()}}
 }
 if($exited -and $pipesDrained){
  foreach($channel in $readers){if($null -ne $channel.Reader){try{$channel.Reader.Dispose();$channel.ReaderDisposed=$true}catch{$failure+="`nOriginal reader disposal failed: "+$_.Exception.ToString()}}}
  if(@($readers|Where-Object{!$_.WriterDisposed -or !$_.ReaderDisposed}).Count -eq 0){try{$process.Dispose();$global:RhaiProjectCommandPendingCustody.ProcessDisposed=$true}catch{$failure+="`nExact Process disposal failed: "+$_.Exception.ToString()}}
 }
 $processDisposed=$global:RhaiProjectCommandPendingCustody.ProcessDisposed
 if($exited -and $pipesDrained -and $processDisposed){$global:RhaiProjectCommandPendingCustody=$null}
}
$custodyPending=$null -ne $global:RhaiProjectCommandPendingCustody
$ownExecutablesStopped=$false
if($started -and $exited -and $pipesDrained -and !$custodyPending){
 $closure=[Diagnostics.Stopwatch]::StartNew()
 do{
  $active=@(Get-CimInstance Win32_Process|Where-Object{$_.ExecutablePath -and ($_.ExecutablePath.StartsWith($session+'\',[StringComparison]::OrdinalIgnoreCase) -or $_.ExecutablePath.StartsWith($run+'\',[StringComparison]::OrdinalIgnoreCase))})
  if($active.Count -eq 0){$ownExecutablesStopped=$true;break}
  if($closure.Elapsed.TotalSeconds -ge 60){$failure+="`nOwned project executables did not stop within60seconds.";break}
  [Threading.Thread]::Sleep(20)
 }while($true)
}
if($started -and $exited -and $pipesDrained -and !$custodyPending -and $ownExecutablesStopped -and !$failure){
 try{
  if($observerKillUsed -or $status -ne 0){throw "Native Driver failed or observer killed it: $status"}
  $output=[IO.File]::ReadAllText($stdout)
  foreach($line in @('CLIENT_EXIT=0x0000004E','MODE=success;ACTION_CONFIRMED=True;','PAYLOAD_EXIT=00000000','SUPERVISION=PayloadExited','CLEANUP_CONFIRMED=True','RUNTIME_REMOVED=True','HOST_EXPORTED=False')){if(!$output.Contains($line)){throw "Missing successful native Driver result: $line"}}
  $matches=[regex]::Matches($output,'(?m)^RUNTIME=([^\r\n]+)\r?$')
  if($matches.Count -ne 1){throw 'Exact runtime report missing.'};$runtimeObserved=$matches[0].Groups[1].Value
  if([IO.Path]::GetDirectoryName($runtimeObserved) -cne $run -or [IO.Path]::GetFileName($runtimeObserved) -notmatch '^scoped-[0-9a-f]{32}$'){throw 'Allocated project runtime outside exact owned run.'}
  if(Test-Path -LiteralPath $runtimeObserved){throw 'Native project runtime remains after completed receipt.'}
  $evidence=@(Get-ChildItem -LiteralPath $run -Directory -Filter '.scoped-evidence-*')
  if($evidence.Count -ne 1){throw 'Exact project evidence snapshot missing.'}
  $payloadOutput=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'stdout.log'))
  $compile=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\compile.log'))
  foreach($line in @('RHAI_READONLY_ALIAS_SCOPE_CONFIRMED','RHAI_WORK_READONLY_CLEARED','RHAI_MANAGED_CWD_CLEANED','RHAI_MANAGED_CWD_WRONG_EXIT=101','RHAI_MANAGED_CWD_GREEN_EXIT=0','RHAI_MANAGED_CWD_SUITE_EXIT=0','RHAI_MANAGED_CWD_CONTROL_PASS')){if(!$payloadOutput.Contains($line)){throw "Managed cwd marker missing: $line"}}
  if(!$compile.Contains('rhai')){throw 'Native process test compile evidence missing.'}
  $wrong=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\wrong.log'))
  $green=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\green.log'))
  $suite=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\suite.log'))
  foreach($line in @('windows_managed_cwd_readback','deliberately wrong Managed cwd executable expectation','test result: FAILED. 0 passed; 1 failed;')){if(!$wrong.Contains($line)){throw "Cwd wrong control missing: $line"}}
  foreach($line in @('windows_managed_cwd_readback','test result: ok. 1 passed; 0 failed;')){if(!$green.Contains($line)){throw "Cwd green proof missing: $line"}}
  if(!$suite.Contains('test result: ok. 31 passed; 0 failed;')){throw 'Windows process suite missing.'}
  $productTestRun=$true;$actualOutcome='pass';$wrongExpectationRejected=$true
  $journal=@(Get-ChildItem -LiteralPath $run -File -Filter '.scoped-run-*.journal')
  if($journal.Count -ne 1 -or [IO.File]::ReadAllLines($journal[0].FullName).Count -ne 8){throw 'Complete native journal record count missing.'}
  $complete=$true
 }catch{$failure=$_.Exception.ToString()}
}
$record=[ordered]@{id=$Id;scope=$session;source=$source;source_manifest_sha256='d65351e9855e5f4ac8f56626aa058abda34629c8a7c0eb8378e10ae0192d9abf';lock_sha256='12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802';public_build_manifest_sha256='8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1';public_binary_pins=$acceptedPins;cargo_proxy_sha256=$CargoSha256;driver_pid=$driverPid;driver_creation=$driverCreation;driver_elapsed_seconds=$driverElapsedSeconds;driver_exit=$status;driver_exited=$exited;pipes_drained=$pipesDrained;process_disposed=$processDisposed;custody_pending=$custodyPending;observer_kill_used=$observerKillUsed;owned_executables_stopped=$ownExecutablesStopped;runtime=$runtimeObserved;wrong_expectation_rejected=$wrongExpectationRejected;diagnostic_suites_complete=$false;accepted=$complete;failure=$failure;product_test_run=$productTestRun;actual_outcome=$actualOutcome;product_acceptance=$false}
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 6),[Text.UTF8Encoding]::new($false))
$files=@(Get-Item -LiteralPath (Join-Path $session 'observer.json'))
foreach($path in @($stdout,$stderr,(Join-Path $session 'source-manifest.json'),(Join-Path $session 'preflight.json'),(Join-Path $session 'build-manifest.txt'))){if(Test-Path -LiteralPath $path -PathType Leaf){$files+=@(Get-Item -LiteralPath $path)}}
if(!$custodyPending -and $ownExecutablesStopped){
 $files+=@(Get-ChildItem -LiteralPath $run -File -Force -Filter '.scoped-run-*.journal')
 $evidence=@(Get-ChildItem -LiteralPath $run -Directory -Force -Filter '.scoped-evidence-*')
 if($evidence.Count -eq 1){
  foreach($relative in @('stdout.log','stderr.log','manifest.txt','runtime\compile.log','runtime\wrong.log','runtime\green.log','runtime\suite.log')){
   $path=Join-Path $evidence[0].FullName $relative
   if(Test-Path -LiteralPath $path -PathType Leaf){$files+=@(Get-Item -LiteralPath $path)}
  }
 }
}
if($files.Count -gt 64 -or ($files|Measure-Object Length -Sum).Sum -gt 16MB){throw 'Bounded project export inventory exceeded; preserve guest originals.'}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000;$script:sequence=0;$exportDeadline=[Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string]$Kind,[object]$Value){
 if($exportDeadline.Elapsed.TotalSeconds -gt 180){throw 'Project export exceeded180seconds; retain guest evidence.'}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Compress -Depth 8)))
 if($encoded.Length -gt 3500){throw 'Project export frame exceeds bound.'}
 $serial.WriteLine("RHAI_BOOTSTRAP $Id $($script:sequence) $Kind $encoded");$script:sequence++
}
try{
 $serial.Open();Emit-Frame 'BEGIN' @{id=$Id;scope=$session;accepted=$complete;exit=$status;driver_pid=$driverPid;driver_creation=$driverCreation}
 foreach($file in $files){
  if($file.Length -gt 4MB -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Export file exceeds cap or is a reparse point.'}
  $relative=$file.FullName.Substring($session.Length+1).Replace('\','/');$bytes=[IO.File]::ReadAllBytes($file.FullName)
  $sha=[Security.Cryptography.SHA256]::Create();try{$hash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
  Emit-Frame 'FILE' @{path=$relative;length=$bytes.Length;sha256=$hash}
  for($offset=0;$offset -lt $bytes.Length;$offset+=1024){$length=[Math]::Min(1024,$bytes.Length-$offset);Emit-Frame 'CHUNK' @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}}
  Emit-Frame 'FILE_END' @{path=$relative;length=$bytes.Length;sha256=$hash}
 }
 Emit-Frame 'END' @{id=$Id;files=$files.Count;accepted=$complete;exit=$status;guest_evidence_retained=$true}
}finally{$serial.Dispose()}
$record|ConvertTo-Json -Compress -Depth 6
if(!$complete){throw 'Bounded native project command did not meet its exact contract; preserve guest originals.'}
