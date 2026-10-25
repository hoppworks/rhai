# Continue the already completed native build; do not relaunch Start or Cargo.
$ErrorActionPreference = 'Stop'
$expectedRun = 'C:\Users\RhaiTest\.local\share\agent-builds\rhai\work-abort-build-4e92c3e57fa14837992fd1d20a3f2f8a\run\monitor-source-4e92c3e57fa14837992fd1d20a3f2f8a'
if ($run -cne $expectedRun -or !$complete -or !$processExitConfirmed -or $custodyIndeterminate) { throw 'Completed exact build custody is not available.' }
$receipt = Get-Content -LiteralPath $observerPath -Raw | ConvertFrom-Json
if (!$receipt.accepted -or !$receipt.native_started -or $receipt.custody_indeterminate -or $receipt.exit -ne 0 -or $receipt.run -cne $expectedRun) { throw 'Original build receipt is not accepted for this exact runtime.' }
if ((Get-FileHash -LiteralPath $control -Algorithm SHA256).Hash.ToLowerInvariant() -cne 'f313d83b470341adf4a60b9cb47b8005c6ff626f77fa77f384dd2b4b3877f135') { throw 'Frozen native control changed.' }
$manifestPath = Join-Path $run 'build-manifest.txt'
$oldHash = [regex]::Match([IO.File]::ReadAllText($manifestPath),'(?m)^([0-9a-f]{64})  build/PayloadFixture\.exe$').Groups[1].Value
if ($oldHash.Length -ne 0) { throw 'Original manifest parser failure was not reproduced.' }
$fixtureLines = @([IO.File]::ReadAllLines($manifestPath) | Where-Object { $_ -match '^[0-9a-f]{64}  build/PayloadFixture\.exe$' })
if ($fixtureLines.Count -ne 1) { throw 'Manifest must bind exactly one native payload fixture.' }
$fixtureHash = $fixtureLines[0].Substring(0,64)
if ((Get-FileHash -LiteralPath $fixturePath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $fixtureHash) { throw 'Native payload differs from its source-bound build receipt.' }
$global:RhaiPayloadControlExitCode = $null
& $control -FixturePath $fixturePath -FixtureSha256 $fixtureHash -Session $controlSession -Id $id -Phase RETIREMENT_ABORT -BuildRoot (Join-Path $run 'build') -ReturnStatusToCaller
if ($global:RhaiPayloadControlExitCode -ne 0) { throw 'Native retirement control failed; retain original evidence and custody.' }
