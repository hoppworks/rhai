$ErrorActionPreference='Stop'
$observer=Join-Path $PSScriptRoot 'RunNestedRefusalControl.ps1'
if((Get-FileHash -LiteralPath $observer).Hash.ToLowerInvariant() -cne '50884e9ca927c3ac7fcf8962f9b0c0a1357735dda8f557a4803ee8de285ff39c'){throw 'Frozen observer hash mismatch.'}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($observer,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw ($errors|Out-String)}
& $observer -DriverBuild 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build' -Session (Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\nested-refusal-8eaf92ee5060484ab71ba657435578ea') -Id 'rhai-nested-refusal01-8eaf92ee5060484ab71ba657435578ea'
exit $LASTEXITCODE
