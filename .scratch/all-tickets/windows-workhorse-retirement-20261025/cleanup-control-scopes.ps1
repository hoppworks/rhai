$ErrorActionPreference='Stop'
if($env:USERPROFILE -cne 'C:\Users\RhaiTest'){throw 'Wrong fixture owner'}
$p=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$roots=@((Join-Path $p 'env-control-4e92c3e57fa14837992fd1d20a3f2f8a'),(Join-Path $p 'env-control-e527e19ef6234cc499498b967dbff2ee'))
foreach($q in $roots){
 if((Get-Item -LiteralPath $q -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse scope'}
 $o=Get-Content -LiteralPath (Join-Path $q 'observer.json') -Raw | ConvertFrom-Json
 if($o.scope -cne $q -or $o.exit -ne 0 -or !$o.driver_launched -or !$o.exact_driver_exited -or !$o.pipes_drained -or $o.retained_driver_handles){throw 'Open or foreign custody'}
 $entries=@(Get-ChildItem -LiteralPath $q -Force -Recurse)
 if($entries.Count -gt 256 -or @($entries | Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}).Count -ne 0){throw 'Unexpected fixture tree'}
 $bytes=($entries | Where-Object {!$_.PSIsContainer} | Measure-Object Length -Sum).Sum
 if($bytes -gt 32MB){throw 'Unexpected fixture size'}
 if(@(Get-ChildItem -LiteralPath (Join-Path $q 'run') -Directory -Filter 'scoped-*').Count -ne 0){throw 'Live runtime remains'}
}
foreach($q in $roots){Remove-Item -LiteralPath $q -Recurse -Force}
foreach($q in $roots){if(Test-Path -LiteralPath $q){throw 'Fixture scope remains'}}
'OWN_CONTROL_SCOPES_RETIRED=True'
'RETAINED_BUILD_UNTOUCHED=True'
Get-Date -Format o
