# Current-binary lease controls, existing accepted bodies; no compilation.
$ErrorActionPreference='Stop'
$media='E:\'
$bindingPath=Join-Path $media 'bindings.json'
if((Get-FileHash -LiteralPath $bindingPath).Hash.ToLowerInvariant() -cne 'e9bdcbe82ea9ef2d9496e8252a5ffccaaff9cd2ea0eff454c9ee2bda0d45b363'){throw 'Frozen binding changed.'}
$b=Get-Content -LiteralPath $bindingPath -Raw | ConvertFrom-Json
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong guest owner.'}
function Assert-NoReparse([string]$Path){
 $cursor=[IO.Path]::GetFullPath($Path)
 while($cursor){
  if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Reparse input refused.'}
  $ancestor=[IO.Directory]::GetParent($cursor);$cursor=if($null -eq $ancestor){$null}else{$ancestor.FullName}
 }
}
$build=Join-Path $env:USERPROFILE $b.build_relative
$buildRun=Split-Path -Parent $build
$buildSession=Split-Path -Parent (Split-Path -Parent $buildRun)
Assert-NoReparse $build
$receipt=Get-Content -LiteralPath (Join-Path $buildSession 'build-observer.json') -Raw | ConvertFrom-Json
if(!$receipt.accepted -or !$receipt.native_started -or $receipt.custody_indeterminate -or $receipt.exit -ne 0 -or $receipt.run -cne $buildRun){throw 'Retained native build custody receipt differs.'}
$manifestLines=[IO.File]::ReadAllLines((Join-Path $buildRun 'build-manifest.txt'))
foreach($entry in $b.source_pins.PSObject.Properties){
 $file=Join-Path (Join-Path $buildRun 'input') ($entry.Name.Replace('/','\'))
 Assert-NoReparse $file
 if((Get-Item -LiteralPath $file).Length -gt 2MB -or (Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $entry.Value){throw 'Retained source differs.'}
 if(@($manifestLines | Where-Object {$_ -ceq ($entry.Value+'  '+$entry.Name)}).Count -ne 1){throw 'Native manifest does not bind this source.'}
}
foreach($entry in $b.binaries.PSObject.Properties){
 $file=Join-Path $build $entry.Name;Assert-NoReparse $file
 if((Get-Item -LiteralPath $file).Length -gt 4MB -or (Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $entry.Value){throw 'Retained binary differs.'}
 if(@($manifestLines | Where-Object {$_ -ceq ($entry.Value+'  build/'+$entry.Name)}).Count -ne 1){throw 'Native manifest does not bind this binary.'}
}
if((Get-FileHash -LiteralPath 'C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe').Hash.ToLowerInvariant() -cne $b.compiler_sha256){throw 'Compiler identity changed.'}
if([IO.DriveInfo]::new('C:\').AvailableFreeSpace -lt 2GB){throw 'Insufficient guest disk headroom.'}
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
foreach($case in $b.cases){
 $file=Join-Path $media $case.file
 if((Get-FileHash -LiteralPath $file).Hash.ToLowerInvariant() -cne $case.sha256){throw 'Frozen case differs.'}
 $tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
 if($errors.Count -ne 0){throw ($errors|Out-String)}
 $scope=Join-Path $private $case.scope_leaf;Assert-NoReparse $scope
 if(Test-Path -LiteralPath $scope){throw 'Fresh control scope already exists; preserve it.'}
}
$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $media 'cleanup.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw ($errors|Out-String)}
$clock=[Diagnostics.Stopwatch]::StartNew()
foreach($case in $b.cases){
 if($clock.Elapsed.TotalSeconds -ge 1170){throw 'Batch budget exhausted before next case.'}
 $text=[IO.File]::ReadAllText((Join-Path $media $case.file))
 $observed=& ([scriptblock]::Create($text))
 $record=($observed -join [Environment]::NewLine)|ConvertFrom-Json
 if($record.id -cne $case.id -or !$record.accepted -or $record.exit -ne 0 -or !$record.exact_driver_exited -or !$record.pipes_drained -or $record.retained_driver_handles){throw 'Case incomplete: originals retained, no next case.'}
 Write-Output ('CASE_PASS='+$case.mode)
}
Write-Output ('BATCH_PASS='+$b.batch_id)
