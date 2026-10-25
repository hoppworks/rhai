param([ValidateSet('build','membership','deadline')][string]$Phase='build')
# Compile only the changed finite fixture; public runner and Driver are reused unchanged.
$ErrorActionPreference='Stop'
$media='E:\'
$bindingPath=Join-Path $media 'bindings.json'
if((Get-FileHash -LiteralPath $bindingPath).Hash.ToLowerInvariant() -cne '7d8d95a5677c0a3474549774a8f4e5f9255e35f1a5751b365b80287da7b9621f'){throw 'Frozen binding changed.'}
$b=Get-Content -LiteralPath $bindingPath -Raw | ConvertFrom-Json
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong guest owner.'}
function Assert-NoReparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse input refused.'}
  $ancestor=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $ancestor){$null}else{$ancestor.FullName}
 }
}
$build=Join-Path $env:USERPROFILE $b.old_build.build_relative
$buildRun=Split-Path -Parent $build
$buildSession=Split-Path -Parent (Split-Path -Parent $buildRun)
Assert-NoReparse $build
$receipt=Get-Content -LiteralPath (Join-Path $buildSession 'build-observer.json') -Raw | ConvertFrom-Json
if(!$receipt.accepted -or !$receipt.native_started -or $receipt.custody_indeterminate -or $receipt.exit -ne 0 -or $receipt.run -cne $buildRun){throw 'Retained native build custody receipt differs.'}
$manifestLines=[IO.File]::ReadAllLines((Join-Path $buildRun 'build-manifest.txt'))
foreach($entry in $b.old_build.source_pins.PSObject.Properties){
 $file=Join-Path (Join-Path $buildRun 'input') ($entry.Name.Replace('/','\'))
 Assert-NoReparse $file
 if((Get-Item -LiteralPath $file).Length -gt 2MB -or (Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $entry.Value){throw 'Retained source differs.'}
 if(@($manifestLines | Where-Object {$_ -ceq ($entry.Value+'  '+$entry.Name)}).Count -ne 1){throw 'Native manifest does not bind this source.'}
}
foreach($entry in $b.old_build.binaries.PSObject.Properties){
 $file=Join-Path $build $entry.Name;Assert-NoReparse $file
 if((Get-Item -LiteralPath $file).Length -gt 4MB -or (Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $entry.Value){throw 'Retained binary differs.'}
 if(@($manifestLines | Where-Object {$_ -ceq ($entry.Value+'  build/'+$entry.Name)}).Count -ne 1){throw 'Native manifest does not bind this binary.'}
}
if((Get-FileHash -LiteralPath 'C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe').Hash.ToLowerInvariant() -cne $b.old_build.compiler_sha256){throw 'Compiler identity changed.'}
if([IO.DriveInfo]::new('C:\').AvailableFreeSpace -lt 2GB){throw 'Insufficient guest disk headroom.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
# Verify complete new compile/observer source inputs before creating a scope.
$mediaSource=Join-Path $media 'source'
foreach($pin in $b.new_source_pins.PSObject.Properties){
 $file=Join-Path $mediaSource $pin.Name
 if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $pin.Value){throw 'Reviewed new source changed.'}
 if($file.EndsWith('.ps1')){$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors);if($errors.Count -ne 0){throw ($errors|Out-String)}}
}
$session=Join-Path $private $b.build_session_leaf
$source=Join-Path $session 'source-input';$parent=Join-Path $session 'run';$run=Join-Path $parent ('monitor-source-'+$b.nonce)
if($Phase -ne 'build'){
 Assert-NoReparse $session
 $r=Get-Content -LiteralPath (Join-Path $session 'build-observer.json') -Raw|ConvertFrom-Json
 if(!$r.accepted -or !$r.exact_build_exited -or $r.exit -ne 0 -or $r.run -cne $run){throw 'Exact successful compile-only receipt missing.'}
 $fixture=Join-Path $run 'build\MonitorDeathFixture.exe';$fixtureHash=$r.fixture_sha256
 if((Get-FileHash -LiteralPath $fixture).Hash.ToLowerInvariant() -cne $fixtureHash){throw 'Source-bound native fixture changed.'}
 $manifest=[IO.File]::ReadAllLines((Join-Path $run 'build-manifest.txt'))
 if(@($manifest|Where-Object{$_ -ceq ($fixtureHash+'  build/MonitorDeathFixture.exe')}).Count -ne 1){throw 'Fixture native manifest differs.'}
 foreach($pin in $b.new_source_pins.PSObject.Properties){
  if($r.source_pins.($pin.Name) -cne $pin.Value){throw 'Native build source binding differs.'}
  $file=Join-Path $source $pin.Name;Assert-NoReparse $file
  if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $pin.Value){throw 'Reviewed native source or control changed.'}
 }
 $case=@($b.cases|Where-Object{$_.mode -ceq $Phase});if($case.Count -ne 1){throw 'Expected one bounded phase.'}
 $control=Join-Path $source 'tools\windows-scoped-runner\fixtures\RunMembershipControl.ps1'
 & ([scriptblock]::Create([IO.File]::ReadAllText($control))) -FixturePath $fixture -FixtureSha256 $fixtureHash -DriverBuild $build -SessionPath (Join-Path $private $case[0].scope_leaf) -Id $case[0].id -Mode $Phase
 return
}
foreach($path in @($session)+@($b.cases|ForEach-Object{Join-Path $private $_.scope_leaf})){Assert-NoReparse $path;if(Test-Path -LiteralPath $path){throw 'Owned new scope exists; preserve it.'}}
New-Item -ItemType Directory -Path $source,$parent|Out-Null
foreach($entry in @(Get-ChildItem -LiteralPath $mediaSource -Force)){Copy-Item -LiteralPath $entry.FullName -Destination $source -Recurse}
foreach($pin in $b.new_source_pins.PSObject.Properties){$file=Join-Path $source $pin.Name;Assert-NoReparse $file;if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $pin.Value){throw 'Private source readback changed.'}}
$bootstrap=Join-Path $source 'tools\windows-scoped-runner\fixtures\RunSourceFixtures.ps1'
$arguments=@('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$bootstrap,'-SourceRoot',$source,'-RunRoot',$run,'-BuildOnly','-MonitorDeathFixtureOnly')
$line=($arguments|ForEach-Object{'"'+$_+'"'}) -join ' '
$stdout=Join-Path $session 'bootstrap.stdout';$stderr=Join-Path $session 'bootstrap.stderr'
$process=$null;$exited=$false;$status=-1;$failure='';$accepted=$false;$fixture=$null;$fixtureHash=$null
$watch=[Diagnostics.Stopwatch]::StartNew()
try{
 $process=Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -ArgumentList $line -WorkingDirectory $source -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -PassThru
 $handle=$process.Handle;if($handle -eq [IntPtr]::Zero){throw 'Build exact retained handle missing.'}
 if(!$process.WaitForExit(270000)){throw 'Build exceeded independent270second bound.'}
 $exited=$true;$process.Refresh();if($null -eq $process.ExitCode){throw 'Build exit unavailable.'};$status=[int]$process.ExitCode
 if($status -ne 0){throw 'Native fixture compile failed; no public Driver permitted.'}
 if(![IO.File]::ReadAllText((Join-Path $run 'run-result.txt')).StartsWith('BUILD_ONLY_PASS:')){throw 'Post-disposition build receipt missing.'}
 $buildFiles=@(Get-ChildItem -LiteralPath (Join-Path $run 'build') -File)
 if($buildFiles.Count -ne 1 -or $buildFiles[0].Name -cne 'MonitorDeathFixture.exe'){throw 'Compile-only selection produced unexpected binaries.'}
 $fixture=$buildFiles[0].FullName;$fixtureHash=(Get-FileHash -LiteralPath $fixture).Hash.ToLowerInvariant()
 $lines=[IO.File]::ReadAllLines((Join-Path $run 'build-manifest.txt'))
 if(@($lines|Where-Object{$_ -ceq ($fixtureHash+'  build/MonitorDeathFixture.exe')}).Count -ne 1){throw 'Native fixture manifest binding missing.'}
 foreach($pin in $b.new_source_pins.PSObject.Properties){
  if(!$pin.Name.EndsWith('.ps1')){
   if(@($lines|Where-Object{$_ -ceq ($pin.Value+'  '+$pin.Name)}).Count -ne 1){throw 'Manifest source differs.'}
  }
 }
 $accepted=$true
}catch{$failure=$_.Exception.ToString()}
finally{
 if($null -ne $process){
  if(!$exited){try{if(!$process.HasExited){$process.Kill()};if(!$process.WaitForExit(30000)){throw 'Exact compiler owner exit unconfirmed.'};$exited=$true}catch{$failure+="`n"+$_.Exception.ToString()}}
  if($exited){$process.Dispose()}else{$global:RhaiMembershipPendingBuild=$process}
 }
}
$record=[ordered]@{id=$b.build_id;scope=$session;run=$run;accepted=$accepted;failure=$failure;exit=$status;exact_build_exited=$exited;fixture_path=$fixture;fixture_sha256=$fixtureHash;compiler_sha256=$b.old_build.compiler_sha256;source_pins=$b.new_source_pins;elapsed_seconds=$watch.Elapsed.TotalSeconds;public_drivers=0}
# The original observer file holds the full pin map; the serial BEGIN stays small.
[IO.File]::WriteAllText((Join-Path $session 'build-observer.json'),($record|ConvertTo-Json -Compress -Depth 8),[Text.UTF8Encoding]::new($false))
$files=@(Get-Item -LiteralPath $stdout,$stderr,(Join-Path $session 'build-observer.json'))
if($exited){$files+=@(Get-ChildItem -LiteralPath $run -File -Recurse|Where-Object{$_.FullName -notlike ($run+'\input\*')})}
$id=$b.build_id;$begin=[ordered]@{id=$id;accepted=$accepted;exit=$status;exact_build_exited=$exited;fixture_sha256=$fixtureHash;driver_launched=$false}
$serial=[IO.Ports.SerialPort]::new('COM1',115200);$serial.WriteTimeout=2000;$script:sequence=0;$exportWatch=[Diagnostics.Stopwatch]::StartNew()
function Emit([string]$Kind,[object]$Value){
 if($exportWatch.Elapsed.TotalSeconds -ge 180){throw 'Build export exceeded180seconds.'}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Value|ConvertTo-Json -Compress -Depth 8)))
 if($encoded.Length -gt 3500){throw 'Build export frame exceeded3500characters.'}
 $serial.WriteLine("RHAI_BOOTSTRAP $id $script:sequence $Kind $encoded");$script:sequence++
}
if($files.Count -gt 64 -or ($files|Measure-Object Length -Sum).Sum -gt 16MB){throw 'Build export inventory exceeded bounds.'}
try{
 $serial.Open();Emit 'BEGIN' $begin
 foreach($file in $files){
  Assert-NoReparse $file.FullName;if($file.Length -gt 4MB){throw 'Build export file too large.'}
  $relative=$file.FullName.Substring($session.Length+1).Replace('\','/');$bytes=[IO.File]::ReadAllBytes($file.FullName)
  $hash=(Get-FileHash -LiteralPath $file.FullName).Hash.ToLowerInvariant()
  Emit 'FILE' @{path=$relative;length=$bytes.Length;sha256=$hash}
  for($offset=0;$offset -lt $bytes.Length;$offset+=1024){$length=[Math]::Min(1024,$bytes.Length-$offset);Emit 'CHUNK' @{path=$relative;offset=$offset;data=[Convert]::ToBase64String($bytes,$offset,$length)}}
  Emit 'FILE_END' @{path=$relative;length=$bytes.Length;sha256=$hash}
 }
 Emit 'END' @{id=$id;accepted=$accepted;exit=$status;files=$files.Count;driver_launched=$false;guest_evidence_retained=$true}
}finally{$serial.Dispose()}
if(!$accepted -or !$exited){throw 'Build incomplete: no control launch, preserve exact scope.'}
Write-Output ('BUILD_PASS='+$b.nonce)
