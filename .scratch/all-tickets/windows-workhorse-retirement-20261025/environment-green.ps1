# One affected environment GREEN on the same retained native C# build.
$ErrorActionPreference='Stop'
$private=Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai'
$buildRun=Join-Path $private 'work-abort-build-4e92c3e57fa14837992fd1d20a3f2f8a\run\monitor-source-4e92c3e57fa14837992fd1d20a3f2f8a'
$control=Join-Path $private 'work-abort-build-4e92c3e57fa14837992fd1d20a3f2f8a\source-input\tools\windows-scoped-runner\fixtures\RunPayloadEnvironmentControl.ps1'
if((Get-FileHash -LiteralPath $control).Hash.ToLowerInvariant() -cne 'f313d83b470341adf4a60b9cb47b8005c6ff626f77fa77f384dd2b4b3877f135'){throw 'Frozen control differs.'}
$text=Get-Content -LiteralPath $control -Raw
foreach($key in @('RUNTIME','JOURNAL')){
 $old='(?m)^'+$key+'=([^\r\n]+)$'
 $new='(?m)^'+$key+'=([^\r\n]+)\r?$'
 if(($text.Split([string[]]@($old),[StringSplitOptions]::None)).Count -ne 2){throw 'Expected exactly one known line-ending parser site.'}
 $text=$text.Replace($old,$new)
}
$fixture=Join-Path $buildRun 'build\PayloadFixture.exe'
$fixtureHash=(Get-FileHash -LiteralPath $fixture).Hash.ToLowerInvariant()
$global:RhaiPayloadControlExitCode=$null
& ([scriptblock]::Create($text)) -FixturePath $fixture -FixtureSha256 $fixtureHash -Session (Join-Path $private 'env-control-e527e19ef6234cc499498b967dbff2ee') -Id 'rhai-environment-retirement-20261025-e527e19ef6234cc499498b967dbff2ee' -Phase GREEN -BuildRoot (Join-Path $buildRun 'build') -ReturnStatusToCaller
if($global:RhaiPayloadControlExitCode -ne 0){throw 'Affected native environment GREEN failed; retain originals.'}
