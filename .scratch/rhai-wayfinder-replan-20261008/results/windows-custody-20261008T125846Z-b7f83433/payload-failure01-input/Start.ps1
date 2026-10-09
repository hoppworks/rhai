$ErrorActionPreference='Stop'
$observer=Join-Path $PSScriptRoot 'RunMonitorDeathControl.ps1'
if((Get-FileHash -LiteralPath $observer).Hash.ToLowerInvariant() -cne '2c62af542a5a30b62577d24ae1d8e04452e88b18afc7b90322ab4746003ca112'){throw 'Frozen observer hash mismatch.'}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($observer,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw ($errors|Out-String)}
& $observer -Action payload-failure -FixturePath 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\monitor-fixture02-120ba26aa981\run\monitor-source-120ba26aa9814b8bac58fad709eaf1ed\build\MonitorDeathFixture.exe' -FixtureSha256 'b1c3b284dc443eb187166a52412ce068c981a55e41a970903d9ba8ed58643680' -DriverBuild 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build' -Session (Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\monitor-payload-failure-d2882f5c40e244ef8bfc3a94c6c8db76') -Id 'rhai-payload-failure01-d2882f5c40e244ef8bfc3a94c6c8db76'
exit $LASTEXITCODE
