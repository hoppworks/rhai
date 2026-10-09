$ErrorActionPreference='Stop'
$observer=Join-Path $PSScriptRoot 'RunMonitorDeathControl.ps1'
if((Get-FileHash -LiteralPath $observer).Hash.ToLowerInvariant() -cne '3376a51edc79d520def97cdd32d298f83ac439cce348660c3cbf251522aece57'){throw 'Frozen observer hash mismatch.'}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($observer,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw ($errors|Out-String)}
& $observer -Action output-limit -FixturePath 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\monitor-fixture03-f60e80b2fd47\run\monitor-source-f60e80b2fd474b9ca0ed7d8678a13bb4\build\MonitorDeathFixture.exe' -FixtureSha256 '5e9d818d2e2e5a5adab0b32229f4b0e0cc390a4417231cd55dc5d7eb4d13386e' -DriverBuild 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build' -Session (Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\monitor-output-limit-b7fd2bab746b4f01b1b0431365d52bd4') -Id 'rhai-output-limit01-b7fd2bab746b4f01b1b0431365d52bd4'
exit $LASTEXITCODE
