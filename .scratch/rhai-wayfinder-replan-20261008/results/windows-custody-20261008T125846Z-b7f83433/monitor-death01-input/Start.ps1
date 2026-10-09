$ErrorActionPreference='Stop'
$observer=Join-Path $PSScriptRoot 'RunMonitorDeathControl.ps1'
if((Get-FileHash -LiteralPath $observer).Hash.ToLowerInvariant() -cne '83d87c752338585a51db453712ab4eb918b216405ee6b2dad6c618fb3003ec0a'){throw 'Frozen observer hash mismatch.'}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($observer,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw ($errors|Out-String)}
& $observer -FixturePath 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\monitor-fixture01-7204331df099\run\monitor-source-7204331df0994553a1d4278556ab3210\build\MonitorDeathFixture.exe' -FixtureSha256 'b82e73f128b024cd0f4bb4bd5eb866456e55963eabe5d30cfdbea8b773d81c65' -DriverBuild 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build' -Session (Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\monitor-death-db023375475c485f8ed6ea9a8e8f3f6c') -Id 'rhai-monitor-death01-db023375475c485f8ed6ea9a8e8f3f6c'
exit $LASTEXITCODE
