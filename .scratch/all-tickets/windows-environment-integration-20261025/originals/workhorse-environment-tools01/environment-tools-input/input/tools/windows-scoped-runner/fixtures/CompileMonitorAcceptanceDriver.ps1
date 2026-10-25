param(
    [Parameter(Mandatory = $true)] [string] $SourceRoot,
    [Parameter(Mandatory = $true)] [string] $RunnerPath,
    [Parameter(Mandatory = $true)] [ValidatePattern('^[0-9a-f]{64}$')] [string] $ExpectedRunnerSha256,
    [Parameter(Mandatory = $true)] [string] $RunRoot
)

# Compile-only preparation for the real-client acceptance driver. This script
# may run the pure parser/control fixture; it never launches the native driver.
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ne 5 -or [IntPtr]::Size -ne 8) {
    throw 'Use the reviewed 64-bit Windows PowerShell 5.1 host.'
}

$productionExpected = @{
    'tools/windows-scoped-runner/LaunchSpecification.cs' = 'e08957b13d5ed5f86cb37d0545aa876aac50e507692d112b39882f465fff8f2b'
    'tools/windows-scoped-runner/LeaseMonitor.cs' = '72c79f18c96e28f27cd1b7b39b1025da9a250e0608885de7dc48934512a46bfc'
    'tools/windows-scoped-runner/MonitorPayloadJob.cs' = 'ac5c62bdcd4402b1f103131e082ab6e35a6d979b80629ea6ffef82b386f2353b'
    'tools/windows-scoped-runner/MonitorSpecificationIntake.cs' = '0f0a71563e6c3d99f0c643644d4b56951f6c69ceb3b10b03157f68dc37bb8412'
    'tools/windows-scoped-runner/MonitorStagingHandoff.cs' = 'c541f7d885d032c074461a5a0173b9ae6291ef7d8cd1b9fd2ce4a4f56d1e0e6e'
    'tools/windows-scoped-runner/MonitorTransport.cs' = 'ed23c8615af7d8c1b545d3108342640c46f7e245b4e6a83a7c98bf1720a74de8'
    'tools/windows-scoped-runner/ScopedRunner.cs' = 'd3a77f0daeebd5beed2b277fae9dc6a522acf1454bb5d8d776d84e1dc8e896c8'
    'tools/windows-scoped-runner/SpecificationTransfer.cs' = '7a9edfe98d84868b55146280bd5ed29576ee0c8725cf9f6c785b784bc0ad25c2'
    'tools/windows-scoped-runner/WindowsCustodyBackend.cs' = 'ba8c3a97fb07e424f18db33bfe814f00f9d9034a6de39094235dc7429b8724a2'
}
$expected = @{} + $productionExpected
$expected['tools/windows-scoped-runner/MonitorAcceptanceDriver.cs'] = 'dae12f910058773b16eb0eb48ad47ef94edb413aa812d640435a564bc1d31bad'
$expected['tools/windows-scoped-runner/fixtures/MonitorAcceptanceDriverFixture.cs'] = 'e27fa58588b1988ec0085ac4ec0379f686e5dd48254cd559f5278c057851f054'
$MaximumLogBytes = 4MB
$OverallLimitMs = 3600000
$CompilerLimitSeconds = 180
$FixtureLimitSeconds = 180
$privateBuildRoot = [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.local\share\agent-builds\rhai')).TrimEnd('\')
$privatePrefix = $privateBuildRoot + '\'
$allowedParent = Split-Path -Parent ([IO.Path]::GetFullPath($RunRoot))
function Assert-NoReparsePath([string] $Path) {
    $full = [IO.Path]::GetFullPath($Path)
    $current = [IO.Path]::GetPathRoot($full)
    $parts = $full.Substring($current.Length).Split([char[]]@('\'), [StringSplitOptions]::RemoveEmptyEntries)
    foreach ($part in $parts) {
        $current = Join-Path $current $part
        if (Test-Path -LiteralPath $current) {
            if (((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Reparse point rejected in owned input path: $current"
            }
        }
    }
}
$run = [IO.Path]::GetFullPath($RunRoot)
if (!$run.StartsWith($privatePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'RunRoot must be under the current user private agent-builds/rhai tree.'
}
$relativeRun = $run.Substring($privatePrefix.Length)
if ($relativeRun -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,95}\\run\\monitor-driver-[0-9a-f]{32}$') {
    throw 'RunRoot must be <private-session-root>\run\monitor-driver-GUID.'
}
Assert-NoReparsePath $allowedParent
if (!(Test-Path -LiteralPath $allowedParent -PathType Container)) { throw "Approved run ancestor absent: $allowedParent" }
if (Test-Path -LiteralPath $run) { throw "RunRoot already exists; preserve and inspect it: $run" }
if ([IO.DriveInfo]::new([IO.Path]::GetPathRoot($run)).AvailableFreeSpace -lt 2GB) { throw 'At least 2 GiB free on the private runtime volume is required.' }

$sourceCandidate = [IO.Path]::GetFullPath($SourceRoot)
Assert-NoReparsePath $sourceCandidate
$source = (Resolve-Path -LiteralPath $SourceRoot).Path
$runnerCandidate = [IO.Path]::GetFullPath($RunnerPath)
Assert-NoReparsePath $runnerCandidate
$RunnerPath = (Resolve-Path -LiteralPath $RunnerPath).Path
$sourceRun = Split-Path -Parent (Split-Path -Parent $RunnerPath)
if ((Split-Path -Leaf $sourceRun) -notmatch '^monitor-source-[0-9a-f]{32}$' -or
    (Split-Path -Leaf (Split-Path -Parent $RunnerPath)) -ne 'build') {
    throw 'RunnerPath must be build\ScopedRunner.exe under a retained monitor-source-GUID run.'
}
$sourceInput = Join-Path $sourceRun 'input'
foreach ($path in @($sourceRun, (Join-Path $sourceRun 'build'), $sourceInput)) {
    if (!(Test-Path -LiteralPath $path -PathType Container)) { throw "Retained source fixture path absent: $path" }
    if (((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Retained source fixture path is a reparse point: $path" }
}
Assert-NoReparsePath $sourceRun
Assert-NoReparsePath (Join-Path $sourceRun 'build')
Assert-NoReparsePath $sourceInput
if (!(Test-Path -LiteralPath $RunnerPath -PathType Leaf) -or (Split-Path -Leaf $RunnerPath) -ne 'ScopedRunner.exe') {
    throw 'RunnerPath must identify the retained ScopedRunner.exe.'
}

$runInput = Join-Path $run 'input'
$buildRoot = Join-Path $run 'build'
$logRoot = Join-Path $run 'logs'
$tempRoot = Join-Path $run 'temp'
# Reflection.Emit is used only to bind native APIs. Resolve GetProcAddress via
# a runtime P/Invoke type; MethodInfo.Invoke receives exact CLR argument types.
$script:delegateAssembly = [Reflection.Emit.AssemblyBuilder]::DefineDynamicAssembly(
    [Reflection.AssemblyName]::new('RhaiDriverCompileBindings'), [Reflection.Emit.AssemblyBuilderAccess]::Run)
$script:delegateModule = $script:delegateAssembly.DefineDynamicModule('Bindings')
function New-NativeDelegateType([string] $Name, [Type] $ReturnType, [Type[]] $ParameterTypes) {
    $builder = $script:delegateModule.DefineType($Name,
        [Reflection.TypeAttributes]::Public -bor [Reflection.TypeAttributes]::Sealed -bor [Reflection.TypeAttributes]::Class,
        [MulticastDelegate])
    $ctor = $builder.DefineConstructor([Reflection.MethodAttributes]::Public -bor [Reflection.MethodAttributes]::HideBySig -bor [Reflection.MethodAttributes]::SpecialName -bor [Reflection.MethodAttributes]::RTSpecialName,
        [Reflection.CallingConventions]::Standard, [Type[]]@([Object], [IntPtr]))
    $ctor.SetImplementationFlags([Reflection.MethodImplAttributes]::Runtime -bor [Reflection.MethodImplAttributes]::Managed)
    $invoke = $builder.DefineMethod('Invoke', [Reflection.MethodAttributes]::Public -bor [Reflection.MethodAttributes]::HideBySig -bor [Reflection.MethodAttributes]::NewSlot -bor [Reflection.MethodAttributes]::Virtual,
        $ReturnType, $ParameterTypes)
    $invoke.SetImplementationFlags([Reflection.MethodImplAttributes]::Runtime -bor [Reflection.MethodImplAttributes]::Managed)
    $attributeCtor = [Runtime.InteropServices.UnmanagedFunctionPointerAttribute].GetConstructor([Type[]]@([Runtime.InteropServices.CallingConvention]))
    $attributeFields = [Reflection.FieldInfo[]]@([Runtime.InteropServices.UnmanagedFunctionPointerAttribute].GetField('SetLastError'))
    $attribute = [Reflection.Emit.CustomAttributeBuilder]::new($attributeCtor,
        [Object[]]@([Runtime.InteropServices.CallingConvention]::Winapi), $attributeFields, [Object[]]@($true))
    $builder.SetCustomAttribute($attribute)
    return $builder.CreateTypeInfo().AsType()
}
$script:kernel32 = [Diagnostics.Process]::GetCurrentProcess().Modules |
    Where-Object { $_.ModuleName -ieq 'kernel32.dll' } | Select-Object -First 1 -ExpandProperty BaseAddress
$resolverBuilder = $script:delegateModule.DefineType('Kernel32ExportResolver',
    [Reflection.TypeAttributes]::Public -bor [Reflection.TypeAttributes]::Abstract -bor [Reflection.TypeAttributes]::Sealed)
$resolverMethod = $resolverBuilder.DefinePInvokeMethod('GetProcAddress', 'kernel32.dll',
    [Reflection.MethodAttributes]::Public -bor [Reflection.MethodAttributes]::Static -bor [Reflection.MethodAttributes]::PinvokeImpl,
    [Reflection.CallingConventions]::Standard, [IntPtr], [Type[]]@([IntPtr], [string]),
    [Runtime.InteropServices.CallingConvention]::Winapi, [Runtime.InteropServices.CharSet]::Ansi)
$resolverMethod.SetImplementationFlags([Reflection.MethodImplAttributes]::PreserveSig)
$script:kernel32Resolver = $resolverBuilder.CreateTypeInfo().AsType()
function Get-KernelDelegate([string] $Export, [Type] $DelegateType) {
    $moduleHandle = [System.Management.Automation.PSObject]::AsPSObject($script:kernel32).BaseObject
    if ($moduleHandle -isnot [IntPtr] -or $moduleHandle -eq [IntPtr]::Zero) { throw 'kernel32 is not a nonzero CLR IntPtr.' }
    if ([string]::IsNullOrWhiteSpace($Export)) { throw 'Kernel32 export name is empty.' }
    $arguments = [object[]]::new(2)
    $arguments.SetValue([System.Management.Automation.PSObject]::AsPSObject($script:kernel32).BaseObject, 0)
    $arguments.SetValue([string]$Export, 1)
    if ($arguments[0].GetType() -ne [IntPtr] -or $arguments[0] -eq [IntPtr]::Zero -or $arguments[1].GetType() -ne [string]) {
        throw 'GetProcAddress arguments have unexpected CLR types.'
    }
    $address = [IntPtr]$script:kernel32Resolver.GetMethod('GetProcAddress').Invoke($null, $arguments)
    if ($address -eq [IntPtr]::Zero) { throw "GetProcAddress($Export) failed." }
    return [Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($address, $DelegateType)
}
$script:createJob = Get-KernelDelegate 'CreateJobObjectW' (New-NativeDelegateType 'CreateJobObjectDelegate' ([IntPtr]) ([Type[]]@([IntPtr], [IntPtr])))
$script:setJobInfo = Get-KernelDelegate 'SetInformationJobObject' (New-NativeDelegateType 'SetInformationJobObjectDelegate' ([bool]) ([Type[]]@([IntPtr], [int], [IntPtr], [uint32])))
$script:assignJob = Get-KernelDelegate 'AssignProcessToJobObject' (New-NativeDelegateType 'AssignProcessToJobObjectDelegate' ([bool]) ([Type[]]@([IntPtr], [IntPtr])))
$script:terminateJob = Get-KernelDelegate 'TerminateJobObject' (New-NativeDelegateType 'TerminateJobObjectDelegate' ([bool]) ([Type[]]@([IntPtr], [uint32])))
$script:terminateProcess = Get-KernelDelegate 'TerminateProcess' (New-NativeDelegateType 'TerminateProcessDelegate' ([bool]) ([Type[]]@([IntPtr], [uint32])))
$script:terminateProcessType = $script:terminateProcess.GetType()
$script:queryJobInfo = Get-KernelDelegate 'QueryInformationJobObject' (New-NativeDelegateType 'QueryInformationJobObjectDelegate' ([bool]) ([Type[]]@([IntPtr], [int], [IntPtr], [uint32], [IntPtr])))
$script:closeHandle = Get-KernelDelegate 'CloseHandle' (New-NativeDelegateType 'CloseHandleDelegate' ([bool]) ([Type[]]@([IntPtr])))
$script:jobHandle = $script:createJob.Invoke([IntPtr]::Zero, [IntPtr]::Zero)
if ($script:jobHandle -eq [IntPtr]::Zero) { throw "CreateJobObjectW failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
$jobInfo = [Runtime.InteropServices.Marshal]::AllocHGlobal(144)
try {
    [Runtime.InteropServices.Marshal]::Copy([byte[]]::new(144), 0, $jobInfo, 144)
    [Runtime.InteropServices.Marshal]::WriteInt32($jobInfo, 16, 0x2308)
    [Runtime.InteropServices.Marshal]::WriteInt32($jobInfo, 40, 16)
    [Runtime.InteropServices.Marshal]::WriteInt64($jobInfo, 112, 1GB)
    [Runtime.InteropServices.Marshal]::WriteInt64($jobInfo, 120, 2GB)
    if (!$script:setJobInfo.Invoke($script:jobHandle, 9, $jobInfo, 144)) { throw 'SetInformationJobObject failed.' }
} finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($jobInfo) }
$currentProcess = [Diagnostics.Process]::GetCurrentProcess()
if (!$script:assignJob.Invoke($script:jobHandle, $currentProcess.Handle)) { throw 'Could not assign exact compiler controller to its kill-on-close job.' }

# One-shot exact-process watchdog; no callback touches the job handle. The
# retained Process and drain event live until Timer.Dispose(waitHandle) signals.
$watchdogType = $script:delegateModule.DefineType('RhaiCompileWallDeadline',
    [Reflection.TypeAttributes]::Public -bor [Reflection.TypeAttributes]::Sealed -bor [Reflection.TypeAttributes]::Abstract)
$fire = $watchdogType.DefineMethod('Fire', [Reflection.MethodAttributes]::Public -bor [Reflection.MethodAttributes]::Static, [void], [Type[]]@([Object]))
$il = $fire.GetILGenerator(); $stateLocal = $il.DeclareLocal([Object[]])
$il.Emit([Reflection.Emit.OpCodes]::Ldarg_0); $il.Emit([Reflection.Emit.OpCodes]::Castclass, [Object[]]); $il.Emit([Reflection.Emit.OpCodes]::Stloc, $stateLocal)
$il.Emit([Reflection.Emit.OpCodes]::Ldloc, $stateLocal); $il.Emit([Reflection.Emit.OpCodes]::Ldc_I4_1); $il.Emit([Reflection.Emit.OpCodes]::Ldelem_Ref); $il.Emit([Reflection.Emit.OpCodes]::Castclass, $script:terminateProcessType)
$il.Emit([Reflection.Emit.OpCodes]::Ldloc, $stateLocal); $il.Emit([Reflection.Emit.OpCodes]::Ldc_I4_0); $il.Emit([Reflection.Emit.OpCodes]::Ldelem_Ref); $il.Emit([Reflection.Emit.OpCodes]::Unbox_Any, [IntPtr])
$il.Emit([Reflection.Emit.OpCodes]::Ldloc, $stateLocal); $il.Emit([Reflection.Emit.OpCodes]::Ldc_I4_2); $il.Emit([Reflection.Emit.OpCodes]::Ldelem_Ref); $il.Emit([Reflection.Emit.OpCodes]::Unbox_Any, [uint32])
$il.Emit([Reflection.Emit.OpCodes]::Callvirt, $script:terminateProcessType.GetMethod('Invoke'))
$deadlineOk = $il.DefineLabel(); $il.Emit([Reflection.Emit.OpCodes]::Brtrue_S, $deadlineOk)
$il.Emit([Reflection.Emit.OpCodes]::Ldstr, 'Exact compiler-controller watchdog could not terminate itself.')
$il.Emit([Reflection.Emit.OpCodes]::Call, [Environment].GetMethod('FailFast', [Type[]]@([string])))
$il.MarkLabel($deadlineOk); $il.Emit([Reflection.Emit.OpCodes]::Ret)
$watchdog = $watchdogType.CreateTypeInfo().AsType()
$timerState = [Object[]]::new(3); $timerState[0] = $currentProcess.Handle; $timerState[1] = $script:terminateProcess; $timerState[2] = [uint32]0xE0000002
$watchdogDelegate = $watchdog.GetMethod('Fire').CreateDelegate([Threading.TimerCallback])
$drained = [Threading.ManualResetEvent]::new($false)
$script:wallTimer = [Threading.Timer]::new($watchdogDelegate, $timerState, $OverallLimitMs, [Threading.Timeout]::Infinite)
$runwatch = [Diagnostics.Stopwatch]::StartNew()
$workSucceeded = $false
try {

# Hashing the retained binary is under the exact-controller deadline too.
$runnerSourceHash = (Get-FileHash -LiteralPath $RunnerPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($runnerSourceHash -cne $ExpectedRunnerSha256) {
    throw 'Retained runner differs from the independently accepted build SHA-256.'
}

# Run-root creation, temp redirection, input copies and hashes all happen under
# the retained exact-owner watchdog and the already-configured controller job.
if (Test-Path -LiteralPath $run) { throw "RunRoot appeared during preflight; preserve and inspect it: $run" }
New-Item -ItemType Directory -Path $run | Out-Null
foreach ($directory in @($runInput, $buildRoot, $logRoot, $tempRoot)) { New-Item -ItemType Directory -Path $directory | Out-Null }
foreach ($directory in @($run, $runInput, $buildRoot, $logRoot, $tempRoot)) { Assert-NoReparsePath $directory }
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
foreach ($relative in ($expected.Keys | Sort-Object)) {
    $baselineRoot = if ($productionExpected.ContainsKey($relative)) { $sourceInput } else { $source }
    $baseline = Join-Path $baselineRoot $relative
    if (!(Test-Path -LiteralPath $baseline -PathType Leaf)) { throw "Frozen input absent: $relative" }
    Assert-NoReparsePath $baseline
    if ($productionExpected.ContainsKey($relative) -and
        (Get-FileHash -LiteralPath $baseline -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected[$relative]) {
        throw "Retained source fixture input differs from reviewed pin: $relative"
    }
    $destination = Join-Path $runInput $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $baseline -Destination $destination
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected[$relative]) {
        throw "Fresh immutable input hash mismatch: $relative"
    }
}
$runnerCopy = Join-Path $buildRoot 'ScopedRunner.exe'
Copy-Item -LiteralPath $RunnerPath -Destination $runnerCopy
$runnerHash = (Get-FileHash -LiteralPath $runnerCopy -Algorithm SHA256).Hash.ToLowerInvariant()
if ($runnerHash -cne $ExpectedRunnerSha256 -or $runnerHash -cne $runnerSourceHash) { throw 'Retained runner copy differs from the independently accepted build SHA-256.' }
$manifest = @("runner_sha256=$runnerHash") + @($expected.Keys | Sort-Object | ForEach-Object { "$($expected[$_])  $_" })
[IO.File]::WriteAllLines((Join-Path $run 'input-manifest.txt'), [string[]]$manifest, [Text.Encoding]::ASCII)

function Quote-ProcessArgument([string] $value) {
    $builder = New-Object System.Text.StringBuilder; [void]$builder.Append('"'); $slashes = 0
    foreach ($character in $value.ToCharArray()) {
        if ($character -eq '\') { $slashes++; continue }
        if ($character -eq '"') { [void]$builder.Append(('\' * (2 * $slashes + 1))).Append('"'); $slashes = 0; continue }
        [void]$builder.Append(('\' * $slashes)).Append($character); $slashes = 0
    }
    [void]$builder.Append(('\' * (2 * $slashes))).Append('"'); return $builder.ToString()
}
function Stop-OwnedJob([int] $code) {
    if (!$script:terminateJob.Invoke($script:jobHandle, [uint32]$code)) { [Environment]::FailFast('TerminateJobObject failed; retain exact controller/job cleanup by process teardown.') }
}
function Invoke-OwnedProcess([string] $path, [string[]] $arguments, [string] $name, [int] $limitSeconds, [int] $expectedExit = 0, [string] $expectedOutput = '', [string] $expectedError = '') {
    $stdout = Join-Path $logRoot ($name + '.stdout.txt'); $stderr = Join-Path $logRoot ($name + '.stderr.txt')
    $line = (($arguments | ForEach-Object { Quote-ProcessArgument ([string]$_) }) -join ' ')
    $remainingMs = [Math]::Min($limitSeconds * 1000, $OverallLimitMs - [int]$runwatch.Elapsed.TotalMilliseconds)
    if ($remainingMs -le 0) { throw 'Overall compile-only deadline expired.' }
    $process = Start-Process -FilePath $path -ArgumentList $line -WorkingDirectory $buildRoot -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -NoNewWindow
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        while (!$process.HasExited -and $watch.ElapsedMilliseconds -lt $remainingMs) {
            foreach ($log in @($stdout, $stderr)) {
                if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt $MaximumLogBytes) {
                    Stop-OwnedJob 0xE0000001
                    if (!$process.WaitForExit(5000)) { [Environment]::FailFast('Log cap exceeded and exact child did not exit after job termination.') }
                    throw "$name exceeded the per-log $MaximumLogBytes-byte cap."
                }
            }
            [void]$process.WaitForExit(100)
        }
        if (!$process.HasExited) {
            Stop-OwnedJob 0xE0000001
            if (!$process.WaitForExit(5000)) { [Environment]::FailFast('Timed-out child did not exit after exact controller-job termination.') }
            throw "$name exceeded its bounded timeout."
        }
        $process.Refresh()
        if ($process.ExitCode -ne $expectedExit) { throw "$name exit was $($process.ExitCode), expected $expectedExit; retained logs: $stdout $stderr" }
        foreach ($log in @($stdout, $stderr)) { if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt $MaximumLogBytes) { throw "$name log exceeded cap at exit." } }
        if ($expectedError) {
            $diagnostics = [IO.File]::ReadAllText($stderr) + [IO.File]::ReadAllText($stdout)
            if (!$diagnostics.Contains($expectedError)) { throw "$name did not emit its expected diagnostic $expectedError." }
        }
        if ($expectedOutput) {
            $actual = [IO.File]::ReadAllText($stdout).Trim()
            if ($actual -ne $expectedOutput) { throw "$name output did not equal its frozen acceptance line; got: $actual" }
        }
    } finally { $process.Dispose() }
}

    $production = @('LaunchSpecification','LeaseMonitor','MonitorPayloadJob','MonitorSpecificationIntake','MonitorStagingHandoff','MonitorTransport','ScopedRunner','SpecificationTransfer','WindowsCustodyBackend') | ForEach-Object { Join-Path $runInput ('tools/windows-scoped-runner/' + $_ + '.cs') }
    $driver = Join-Path $runInput 'tools/windows-scoped-runner/MonitorAcceptanceDriver.cs'
    $fixture = Join-Path $runInput 'tools/windows-scoped-runner/fixtures/MonitorAcceptanceDriverFixture.cs'
    $compiler = 'C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
    if (!(Test-Path -LiteralPath $compiler -PathType Leaf)) { throw "Existing reviewed compiler missing; install is out of scope: $compiler" }
    Invoke-OwnedProcess $compiler (@('/target:exe','/main:MonitorAcceptanceDriver',('/out:'+(Join-Path $buildRoot 'MonitorAcceptanceDriver.exe'))) + $production + @($driver)) 'compile-driver' $CompilerLimitSeconds
    Invoke-OwnedProcess $compiler (@('/target:exe','/define:SCOPED_RUNNER_TESTING','/main:MonitorAcceptanceDriverFixture',('/out:'+(Join-Path $buildRoot 'MonitorAcceptanceDriverFixture.exe'))) + $production + @($driver,$fixture)) 'compile-fixture' $CompilerLimitSeconds
    # A deliberate missing-input control proves the compiler's nonzero exit is
    # observed and classified; it is an expected failure, never a success build.
    $missing = Join-Path $runInput 'intentional-missing-control.cs'
    Invoke-OwnedProcess $compiler @('/target:library',$missing) 'expected-compiler-failure' $CompilerLimitSeconds 1 '' 'error CS2001'
    Invoke-OwnedProcess (Join-Path $buildRoot 'MonitorAcceptanceDriverFixture.exe') @() 'run-fixture' $FixtureLimitSeconds 0 'MonitorAcceptanceDriverFixture assertions=27'
    $workSucceeded = $true
    [IO.File]::WriteAllText((Join-Path $run 'run-result.txt'), "COMPILE AND FIXTURE PASS; job disposition pending.`r`n", [Text.Encoding]::ASCII)
} catch {
    if (Test-Path -LiteralPath $run -PathType Container) {
        [IO.File]::WriteAllText((Join-Path $run 'run-result.txt'), ("FAILED: " + $_.Exception.Message + [Environment]::NewLine), [Text.Encoding]::UTF8)
    }
    throw
} finally {
    if ($script:jobHandle -ne [IntPtr]::Zero) {
        try {
            if ($workSucceeded) {
                $accounting = [Runtime.InteropServices.Marshal]::AllocHGlobal(48)
                try {
                    if (!$script:queryJobInfo.Invoke($script:jobHandle, 1, $accounting, 48, [IntPtr]::Zero)) { throw 'QueryInformationJobObject(accounting) failed.' }
                    if ([Runtime.InteropServices.Marshal]::ReadInt32($accounting, 40) -ne 1) { throw 'Successful disposition requires exactly the controller process in the owned job.' }
                } finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($accounting) }
                $jobInfo = [Runtime.InteropServices.Marshal]::AllocHGlobal(144)
                try {
                    [Runtime.InteropServices.Marshal]::Copy([byte[]]::new(144), 0, $jobInfo, 144)
                    if (!$script:setJobInfo.Invoke($script:jobHandle, 9, $jobInfo, 144)) { throw 'Could not clear kill-on-close after exact accounting.' }
                } finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($jobInfo) }
            }
            if (!$script:closeHandle.Invoke($script:jobHandle)) {
                $closeError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
                # If KILL_ON_JOB_CLOSE was already cleared, terminate the
                # exactly-accounted job explicitly before failing the controller.
                if ($workSucceeded -and !$script:terminateJob.Invoke($script:jobHandle, [uint32]0xE0000003)) {
                    [Environment]::FailFast("CloseHandle(job) and recovery TerminateJobObject failed ($closeError / $([Runtime.InteropServices.Marshal]::GetLastWin32Error())); retain watchdog and owner through process teardown.")
                }
                [Environment]::FailFast("CloseHandle(job) failed ($closeError); retain watchdog and owner through process teardown.")
            }
            $script:jobHandle = [IntPtr]::Zero
        } catch {
            # Never unwind into the timer-disposal path with an owned job handle.
            # FailFast tears down this exact controller; the still-armed watchdog,
            # retained Process handle, and kill-on-close job remain live until then.
            [Environment]::FailFast("Job disposition failed; preserving watchdog and owner through controller teardown: $($_.Exception.Message)")
        }
    }
    # Only reached after the owned job handle was closed successfully. Keep the
    # timer and exact Process owner alive until callback drain is confirmed.
    if ($script:wallTimer) {
        if (!$script:wallTimer.Dispose($drained)) { [Environment]::FailFast('Watchdog timer refused disposal; preserving owner state through process teardown.') }
        if (!$drained.WaitOne(5000)) { [Environment]::FailFast('Watchdog callback did not drain; preserving owner state through process teardown.') }
        $script:wallTimer = $null
    }
    $drained.Dispose(); $currentProcess.Dispose()
}
if ($workSucceeded) {
    $summary = "COMPILE-ONLY PASS; native driver was not launched; job accounting and disposition passed. Retained run root: $run"
    [IO.File]::WriteAllText((Join-Path $run 'run-result.txt'), $summary + [Environment]::NewLine, [Text.Encoding]::ASCII)
    Write-Output $summary
}
