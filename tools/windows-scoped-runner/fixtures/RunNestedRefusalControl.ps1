param(
 [Parameter(Mandatory=$true)][string]$DriverBuild,
 [Parameter(Mandatory=$true)][string]$Session,
 [Parameter(Mandatory=$true)][string]$Id
)
$ErrorActionPreference='Stop'
function No-Reparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse path refused.'}
  $parent=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $parent){$null}else{$parent.FullName}
 }
}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$session=[IO.Path]::GetFullPath($Session)
if([IO.Directory]::GetParent($session).FullName -cne $private -or [IO.Path]::GetFileName($session) -cnotmatch '^nested-refusal-[0-9a-f]{32}$'){throw 'Exact fresh own nested-refusal root required.'}
No-Reparse $session;No-Reparse $DriverBuild
if(Test-Path -LiteralPath $session){throw 'Own scope exists; preserve it.'}
$driver=Join-Path $DriverBuild 'MonitorAcceptanceDriver.exe'
$runner=Join-Path $DriverBuild 'ScopedRunner.exe'
foreach($item in @(@{path=$driver;sha='caf4afaa2f604fb47fc554c82d9493854be0959c8d329bff7a88fd7fe9e827cb'},@{path=$runner;sha='c3d91a8bcf550ef8087b7c057455ac876fe0a958b4e22de816b55daa659cb486'})){
 No-Reparse $item.path
 if((Get-FileHash -LiteralPath $item.path).Hash.ToLowerInvariant() -cne $item.sha){throw 'Accepted native artifact changed.'}
}
$assembly=[Reflection.Assembly]::LoadFile($driver)
$type=$assembly.GetType('MonitorAcceptanceDriver',$true)
$flags=[Reflection.BindingFlags]'Static,NonPublic'
function Native([string]$Name,[object[]]$Arguments){
 $method=$type.GetMethod($Name,$flags)
 if(!$method){throw ('Existing native method unavailable: '+$Name)}
 return $method.Invoke($null,$Arguments)
}
function Native-Size([object]$Value){
 $method=[Runtime.InteropServices.Marshal].GetMethod('SizeOf',[Type[]]@([Type]))
 if(!$method -or $method.ReturnType -ne [int]){throw 'Exact Marshal.SizeOf(Type) metadata unavailable.'}
 return [int]$method.Invoke($null,[object[]]@($Value.GetType()))
}
$self=[Diagnostics.Process]::GetCurrentProcess()
$membership=[object[]]@($self.Handle,[IntPtr]::Zero,$false)
if(!(Native 'IsProcessInJob' $membership) -or $membership[2]){throw 'Fresh observer must be uncontained; preserve any ambient job.'}
New-Item -ItemType Directory -Path $session | Out-Null
$input=Join-Path $session 'input';New-Item -ItemType Directory -Path $input | Out-Null
$parentEnvironment=@{}
foreach($key in @('AGENT_RUNTIME_DIR','TMP','TEMP','CARGO_HOME','CARGO_TARGET_DIR')){$parentEnvironment[$key]=[Environment]::GetEnvironmentVariable($key)}
$parentCwd=[Environment]::CurrentDirectory
$run=Join-Path $session 'run'
if(Test-Path -LiteralPath $run){throw 'Fresh runtime candidate already exists.'}
$deadline=[Diagnostics.Stopwatch]::StartNew()
$job=[IntPtr]::Zero;$child=$null;$childStarted=$false;$childWaited=$false
$record=[ordered]@{id=$Id;accepted=$false;failure='';driver_sha256='caf4afaa2f604fb47fc554c82d9493854be0959c8d329bff7a88fd7fe9e827cb';driver_exit=$null;wrong_success_red=$false;observer_identity=@{pid=$self.Id;creation=$self.StartTime.ToUniversalTime().ToFileTimeUtc()};observer_initially_uncontained=$true;observer_in_owned_job=$false;driver_identity=$null;driver_in_owned_job=$false;owner_only_before_release=$false;job_released=$false;payload_started=$false;parent_environment_changed=$false;parent_cwd_changed=$false}
function Bound {if($deadline.Elapsed.TotalSeconds -gt 30){throw 'Nested refusal observer exceeded30seconds.'}}
$channels=@();$status=2
try{
 $job=Native 'CreateJobObjectW' ([object[]]@([IntPtr]::Zero,$null))
 if($job -eq [IntPtr]::Zero){throw 'Owned native job creation failed.'}
 $limits=Native 'CreateLimits' ([object[]]@($true))
 $size=[uint32](Native-Size $limits)
 if(!(Native 'SetInformationJobObject' ([object[]]@($job,9,$limits,$size)))){throw 'Owned finite kill-on-close limits failed.'}
 if(!(Native 'AssignProcessToJobObject' ([object[]]@($job,$self.Handle)))){throw 'Own observer assignment failed.'}
 $membership=[object[]]@($self.Handle,$job,$false)
 if(!(Native 'IsProcessInJob' $membership) -or !$membership[2]){throw 'Fresh own job membership absent.'}
 $record.observer_in_owned_job=$true
 $info=[Diagnostics.ProcessStartInfo]::new()
 $info.FileName=$driver;$info.Arguments='--mode success --source "'+$input+'" --exe never-created.exe --expected-payload-exit 00000000 --'
 $info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.WorkingDirectory=$DriverBuild
 $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
 $info.EnvironmentVariables['AGENT_RUNTIME_DIR']=$run
 $child=[Diagnostics.Process]::new();$child.StartInfo=$info
 if(!$child.Start()){throw 'Exact native driver launch failed.'};$childStarted=$true
 $handle=$child.Handle
 $record.driver_identity=@{pid=$child.Id;creation=$child.StartTime.ToUniversalTime().ToFileTimeUtc()}
 $membership=[object[]]@($handle,$job,$false)
 if(!(Native 'IsProcessInJob' $membership) -or !$membership[2]){throw 'Actual child membership not independently proven; keep criterion open.'}
 $record.driver_in_owned_job=$true
 $channels=@()
 foreach($reader in @($child.StandardOutput,$child.StandardError)){
  $buffer=[char[]]::new(512)
  $channels+=,[pscustomobject]@{Reader=$reader;Buffer=$buffer;Task=$reader.ReadAsync($buffer,0,512);Text=[Text.StringBuilder]::new();Eof=$false;Faulted=$false}
 }
 while(!($child.HasExited -and @($channels|Where-Object {!$_.Eof}).Count -eq 0)){
  Bound
  foreach($ch in $channels){
   if(!$ch.Eof -and $ch.Task.IsCompleted){
    $count=$ch.Task.GetAwaiter().GetResult()
    if($count -eq 0){$ch.Eof=$true}
    else{
     if($ch.Text.Length+$count -gt 16384){
      $keep=[Math]::Max(0,16384-$ch.Text.Length)
      if($keep -gt 0){[void]$ch.Text.Append($ch.Buffer,0,$keep)}
      $record.diagnostic_truncated=$true
      throw 'Exact native diagnostic channel exceeds16384characters; bounded prefix retained.'
     }
     [void]$ch.Text.Append($ch.Buffer,0,$count);$ch.Task=$ch.Reader.ReadAsync($ch.Buffer,0,512)
    }
   }
  }
  [Threading.Thread]::Sleep(5)
 }
 if(!$child.WaitForExit(1000)){throw 'Exact child exit wait failed.'};$childWaited=$true
 $record.driver_exit=$child.ExitCode
 [IO.File]::WriteAllText((Join-Path $session 'driver.stdout'),$channels[0].Text.ToString(),[Text.UTF8Encoding]::new($false))
 [IO.File]::WriteAllText((Join-Path $session 'driver.stderr'),$channels[1].Text.ToString(),[Text.UTF8Encoding]::new($false))
 $diagnostic=$channels[1].Text.ToString()
 try{if($child.ExitCode -ne 0){throw 'Wrong expected successful driver exit.'}}catch{$record.wrong_success_red=$true}
 if($child.ExitCode -ne 2 -or $diagnostic -cnotmatch '^driver failure: InvalidOperationException: driver requires an uncontained parent; refusing ambient job membership\r?\n$' -or $channels[0].Text.Length -ne 0){throw 'Expected real nested admission refusal not proven.'}
 if(@(Get-ChildItem -LiteralPath $input -Force).Count -ne 0 -or (Test-Path -LiteralPath $run)){throw 'Admission refusal mutated input or created private runtime.'}
 foreach($key in $parentEnvironment.Keys){if([Environment]::GetEnvironmentVariable($key) -cne $parentEnvironment[$key]){$record.parent_environment_changed=$true;throw 'Parent environment changed.'}}
 if([Environment]::CurrentDirectory -cne $parentCwd){$record.parent_cwd_changed=$true;throw 'Parent cwd changed.'}
 $accountingType=$type.GetNestedType('JobBasicAccountingInformation',[Reflection.BindingFlags]'NonPublic')
 $accounting=[Activator]::CreateInstance($accountingType)
 $argsQuery=[object[]]@($job,1,$accounting,[uint32](Native-Size $accounting),[IntPtr]::Zero)
 if(!(Native 'QueryInformationJobObject' $argsQuery) -or $argsQuery[2].ActiveProcesses -ne 1){throw 'Exact owned job is not owner-only after refused driver exit.'}
 $record.owner_only_before_release=$true
 $releasedLimits=Native 'CreateLimits' ([object[]]@($false))
 if(!(Native 'SetInformationJobObject' ([object[]]@($job,9,$releasedLimits,$size)))){throw 'Could not clear owned kill-on-close after exact accounting.'}
 if(!(Native 'CloseHandle' ([object[]]@($job)))){throw 'Exact owned job handle close failed.'}
 $job=[IntPtr]::Zero;$record.job_released=$true
 $record.accepted=$true;$status=0
}catch{$record.failure=$_.Exception.ToString()}
finally{
 if($childStarted -and !$childWaited){
  try{if(!$child.HasExited){$child.Kill()};if($child.WaitForExit(1000)){$childWaited=$true}}catch{}
 }
 # A failed assertion/read/timeout still preserves completed native diagnostic prefixes.
 $drain=[Diagnostics.Stopwatch]::StartNew()
 while(@($channels|Where-Object {!$_.Eof -and !$_.Faulted}).Count -gt 0 -and $drain.ElapsedMilliseconds -lt 1000){
  foreach($ch in $channels){
   if(!$ch.Eof -and !$ch.Faulted -and $ch.Task.IsCompleted){
    try{
     $count=$ch.Task.GetAwaiter().GetResult()
     if($count -eq 0){$ch.Eof=$true}
     else{
      $keep=[Math]::Min($count,[Math]::Max(0,16384-$ch.Text.Length))
      if($keep -gt 0){[void]$ch.Text.Append($ch.Buffer,0,$keep)}
      if($keep -ne $count){$record.diagnostic_truncated=$true}
      $ch.Task=$ch.Reader.ReadAsync($ch.Buffer,0,512)
     }
    }catch{
     $ch.Faulted=$true
     $record.failure+=[Environment]::NewLine+'Final diagnostic drain: '+$_.Exception.ToString()
     $record.accepted=$false;$status=2;break
    }
   }
  }
  [Threading.Thread]::Sleep(5)
 }
 $record.child_exit_confirmed=$childWaited
 $record.diagnostic_channels_drained=($channels.Count -eq 2 -and @($channels|Where-Object {!$_.Eof}).Count -eq 0)
 $record.pending_diagnostic_workers_retained=@($channels|Where-Object {!$_.Eof -and !$_.Task.IsCompleted}).Count
 $record.diagnostic_read_faults=@($channels|Where-Object {$_.Faulted}).Count
 for($index=0;$index -lt $channels.Count;$index++){
  try{
   $name=if($index -eq 0){'driver.stdout'}else{'driver.stderr'}
   [IO.File]::WriteAllText((Join-Path $session $name),$channels[$index].Text.ToString(),[Text.UTF8Encoding]::new($false))
   if($channels[$index].Eof){$channels[$index].Reader.Dispose()}
  }catch{
   $record.failure+=[Environment]::NewLine+'Original diagnostic save/close: '+$_.Exception.ToString()
   $record.accepted=$false;$status=2
  }
 }
 if($childWaited -and $record.diagnostic_channels_drained){$child.Dispose()}
 # Never clear kill-on-close after an unknown or nonempty accounting result.
 # Failure retains the owned job until this observer exits; no clean receipt.
 $self.Dispose()
}
$record.elapsed_seconds=$deadline.Elapsed.TotalSeconds
[IO.File]::WriteAllText((Join-Path $session 'observer.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
$complete=$record.accepted;$driverWasStarted=$childStarted;$actors=@()
$files=@(Get-Item -LiteralPath (Join-Path $session 'observer.json'))
foreach($name in @('driver.stdout','driver.stderr')){
 $path=Join-Path $session $name
 if(Test-Path -LiteralPath $path){$files+=Get-Item -LiteralPath $path}
}
if($files.Count -gt 3 -or ($files|Measure-Object Length -Sum).Sum -gt 65536){throw 'Bounded refusal export inventory exceeded; preserve it.'}
$serial = [IO.Ports.SerialPort]::new('COM1',115200); $serial.WriteTimeout = 2000; $script:sequence = 0
$exportDeadline = [Diagnostics.Stopwatch]::StartNew()
function Emit-Frame([string] $Kind, [object] $Value) {
    if ($exportDeadline.Elapsed.TotalSeconds -gt 30) { throw 'Serial export exceeded its 30-second bound; guest evidence retained.' }
    $json = $Value | ConvertTo-Json -Compress -Depth 8
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    if ($encoded.Length -gt 3500) { throw 'Export frame exceeds its declared bound.' }
    $serial.WriteLine("RHAI_BOOTSTRAP $id $($script:sequence) $Kind $encoded")
    $script:sequence++
}
try {
    $serial.Open(); Emit-Frame 'BEGIN' @{id=$id;scope=$session;exit=$status;accepted=$complete;full_record='observer.json'}
    foreach ($file in $files) {
        if ($file.Length -gt 65536 -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Export file exceeds cap or is a reparse point.' }
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
$record|ConvertTo-Json -Compress -Depth 8
exit $status
