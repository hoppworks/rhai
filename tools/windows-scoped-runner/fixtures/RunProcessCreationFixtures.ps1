param(
    [Parameter(Mandatory = $true)]
    [string] $RunnerBinary,
    [Parameter(Mandatory = $true)]
    [string] $PayloadBinary
)

$ErrorActionPreference = 'Stop'
$privateRoot = Join-Path ([IO.Path]::GetTempPath()) ('rhai-job-list-fixture-' + [Guid]::NewGuid().ToString('N'))
$runnerExe = (Resolve-Path -LiteralPath $RunnerBinary).Path
$payloadExe = (Resolve-Path -LiteralPath $PayloadBinary).Path
$sourceRoot = Join-Path $privateRoot 'payload-source'
$allCasesPassed = $false

function Invoke-RunnerCase([string] $CaseName, [string] $FaultOption) {
    $caseRoot = Join-Path $privateRoot $CaseName
    $runtimeRoot = Join-Path $caseRoot 'runtime'
    $marker = Join-Path $caseRoot 'payload-started.txt'
    $stdoutPath = Join-Path $caseRoot 'runner.stdout.log'
    $stderrPath = Join-Path $caseRoot 'runner.stderr.log'
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    $hadPreviousRoot = Test-Path Env:RHAI_SCOPED_RUNNER_TEST_ROOT
    $previousRoot = $env:RHAI_SCOPED_RUNNER_TEST_ROOT
    $env:RHAI_SCOPED_RUNNER_TEST_ROOT = $runtimeRoot
    try {
        & $runnerExe '--source' $sourceRoot '--exe' 'PayloadFixture.exe' $FaultOption '--' $marker 1> $stdoutPath 2> $stderrPath
        $exitCode = $LASTEXITCODE
    } finally {
        if ($hadPreviousRoot) { $env:RHAI_SCOPED_RUNNER_TEST_ROOT = $previousRoot }
        else { Remove-Item Env:RHAI_SCOPED_RUNNER_TEST_ROOT -ErrorAction SilentlyContinue }
    }

    if ($exitCode -eq 0) { throw "$CaseName unexpectedly reported success; artifacts: $caseRoot" }
    if (Test-Path -LiteralPath $marker) { throw "$CaseName allowed the payload to execute" }
    $diagnostics = (Get-Content -LiteralPath $stdoutPath -Raw) + (Get-Content -LiteralPath $stderrPath -Raw)
    $expectedDiagnostic = if ($CaseName -eq 'pre-resume') { 'injected fixture failure before ResumeThread' } else { 'CreateProcessW(creation-time job assignment)' }
    if ($diagnostics -notmatch [regex]::Escape($expectedDiagnostic)) {
        throw "$CaseName did not report its expected failure '$expectedDiagnostic'; artifacts: $caseRoot"
    }

    if ($CaseName -eq 'pre-resume') {
        $receipts = @(Get-ChildItem -LiteralPath $runtimeRoot -Filter 'fixture-cleanup-receipt.txt' -Recurse -File)
        if ($receipts.Count -ne 1) { throw "pre-resume cleanup receipt missing; artifacts: $caseRoot" }
        $receipt = Get-Content -LiteralPath $receipts[0].FullName -Raw
        if ($receipt -notmatch '(?m)^root_process_signaled=true\s*$' -or
            $receipt -notmatch '(?m)^job_active_processes=0\s*$') {
            throw "pre-resume receipt did not confirm process signaling and an empty job; artifacts: $caseRoot"
        }
    }
}

try {
    New-Item -ItemType Directory -Path $privateRoot, $sourceRoot -Force | Out-Null
    Copy-Item -LiteralPath $payloadExe -Destination (Join-Path $sourceRoot 'PayloadFixture.exe')

    Invoke-RunnerCase 'job-list-failure' '--test-inject-job-list-failure'
    Invoke-RunnerCase 'pre-resume' '--test-fail-before-resume'
    $allCasesPassed = $true
    Write-Output "PASS: source fixture assertions completed under $privateRoot"
    Write-Warning 'This harness receipt and marker check are not independent job/process read-back or native acceptance.'
} finally {
    if ($allCasesPassed) { Remove-Item -LiteralPath $privateRoot -Recurse -Force -ErrorAction SilentlyContinue }
    else { Write-Warning "Fixture artifacts retained for exact inspection: $privateRoot" }
}
