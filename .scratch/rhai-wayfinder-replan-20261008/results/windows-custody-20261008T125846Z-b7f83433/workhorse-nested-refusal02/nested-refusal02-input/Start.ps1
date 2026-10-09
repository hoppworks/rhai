$ErrorActionPreference='Stop'
$observer=Join-Path $PSScriptRoot 'RunNestedRefusalControl.ps1'
if((Get-FileHash -LiteralPath $observer).Hash.ToLowerInvariant() -cne 'ae32883d25de43797d048258b3bc836d80b47f182383af99063358e90ba211e8'){throw 'Frozen observer hash mismatch.'}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($observer,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw ($errors|Out-String)}
& $observer -DriverBuild 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\driver-wh02-af46729dd10c\run\monitor-source-af46729dd10c4493afc2264f240c8992\build' -Session (Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\nested-refusal-33b851a725484c8bb830280181963963') -Id 'rhai-nested-refusal02-33b851a725484c8bb830280181963963'
exit $LASTEXITCODE
