$ErrorActionPreference='Stop'
$observer=Join-Path $PSScriptRoot 'RunMonitorDeathControl.ps1'
if((Get-FileHash -LiteralPath $observer).Hash.ToLowerInvariant() -cne '612a613fbba4c51b2b993646b19f1b46223dd5d14647c53a8e3b49fbc535d081'){throw 'Frozen observer hash mismatch.'}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($observer,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw ($errors|Out-String)}
& $observer -Action parent-exit -FixturePath 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\monitor-fixture02-120ba26aa981\run\monitor-source-120ba26aa9814b8bac58fad709eaf1ed\build\MonitorDeathFixture.exe' -FixtureSha256 'b1c3b284dc443eb187166a52412ce068c981a55e41a970903d9ba8ed58643680' -DriverBuild 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build' -Session (Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\monitor-parent-exit-2a34e9b8f16543bca8ed6fd6d5e93fd7') -Id 'rhai-parent-exit01-2a34e9b8f16543bca8ed6fd6d5e93fd7'
exit $LASTEXITCODE
