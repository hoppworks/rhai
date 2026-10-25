$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'RunPayloadEnvironmentControl.ps1'
if((Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant() -cne '4895b277961b3006ef23aaedee7d1517729f433f917a3eba33315dac3f421429'){throw 'Frozen environment observer mismatch.'}
$tokens=$null;$errors=$null
[void][Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count -ne 0){throw ($errors|Out-String)}
& $source -FixturePath 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\env-fixture01-33ae77140048\run\monitor-source-33ae77140048452c913934f8cecccf9f\build\PayloadFixture.exe' -FixtureSha256 'e663ad3f7acd1b2b170433e0335e5d29c499a80751f15eb077e7df8b51e498b2' -Session (Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai\env-control-1d8b0ab26dbc4516b26d7f23ec9e868a') -Id 'rhai-environment-red01-1d8b0ab26dbc4516b26d7f23ec9e868a' -Phase RED
exit $LASTEXITCODE
