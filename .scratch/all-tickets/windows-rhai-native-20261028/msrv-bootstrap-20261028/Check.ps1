$ErrorActionPreference = 'Stop'
$path = Join-Path $PSScriptRoot 'Start.ps1'
$tokens = $null
$errors = $null
$null = [Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors)
if ($errors.Count -ne 0) { throw ($errors | Out-String) }
Write-Output ('MSRV_BOOTSTRAP_SYNTAX_OK ' + (Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant())
