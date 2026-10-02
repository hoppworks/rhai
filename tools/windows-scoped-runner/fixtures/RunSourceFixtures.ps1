param(
    [Parameter(Mandatory = $true)] [string] $SourceRoot,
    [Parameter(Mandatory = $true)] [string] $RunRoot,
    [switch] $SetupFailureControl
)

$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSVersion -lt [version]'5.1') {
    throw 'PowerShell 5.1 or later is required; the guest preflight established Windows PowerShell 5.1.'
}
if ([IntPtr]::Size -ne 8) { throw 'The accepted Windows guest and job layout require a 64-bit PowerShell process.' }

# Source hashes bind this harness to the source checkpoint reviewed on
# 2026-10-01. Update them only with a separately reviewed source change.
$expected = @{
    'tools/windows-scoped-runner/LaunchSpecification.cs' = 'e08957b13d5ed5f86cb37d0545aa876aac50e507692d112b39882f465fff8f2b'
    'tools/windows-scoped-runner/LeaseMonitor.cs' = '72c79f18c96e28f27cd1b7b39b1025da9a250e0608885de7dc48934512a46bfc'
    'tools/windows-scoped-runner/MonitorPayloadJob.cs' = 'da9297e44a3c9fc208571038a3b6874cb62d3b67948102d60b98f03c6c4dac70'
    'tools/windows-scoped-runner/MonitorSpecificationIntake.cs' = '0f0a71563e6c3d99f0c643644d4b56951f6c69ceb3b10b03157f68dc37bb8412'
    'tools/windows-scoped-runner/MonitorStagingHandoff.cs' = 'c541f7d885d032c074461a5a0173b9ae6291ef7d8cd1b9fd2ce4a4f56d1e0e6e'
    'tools/windows-scoped-runner/MonitorTransport.cs' = '4a307370af955b49bae50b86fec5be9039db392c730897a3c87111e0191b89a7'
    'tools/windows-scoped-runner/ScopedRunner.cs' = '60c7998b834e87815092fc9003cad27812094028201906ec6e6dc05ea2b85695'
    'tools/windows-scoped-runner/SpecificationTransfer.cs' = '7a9edfe98d84868b55146280bd5ed29576ee0c8725cf9f6c785b784bc0ad25c2'
    'tools/windows-scoped-runner/WindowsCustodyBackend.cs' = '664f4d61edc078ef711cfe439090f0acb94d32737b9b1eb3bbb6737caa40d30a'
    'tools/windows-scoped-runner/fixtures/CustodyBackendFixture.cs' = '9600120c2c64df5362b4fdd7b64c781683c289ebab13c7ccf0490b06740cd38f'
    'tools/windows-scoped-runner/fixtures/LaunchSpecificationFixture.cs' = '5acc9ddd831fef39bdcd5c540a5404c5dd077abda731a67d16ecd4d92c82313e'
    'tools/windows-scoped-runner/fixtures/LeaseProtocolFixture.cs' = 'c466da5498e6908f273158384c73d58b055f083930bc9fac7c7af2a7dbf12251'
    'tools/windows-scoped-runner/fixtures/MonitorPayloadJobFixture.cs' = 'd9aae76fd68a2cb52721618cd0746af36892a7951c9d0c4d11867a05e11ca7c0'
    'tools/windows-scoped-runner/fixtures/MonitorSpecificationIntakeFixture.cs' = '3e774455bc25a3f0fa40162e4ca3f5d59f35270d27b41c3e2aceb0f144f73d8d'
    'tools/windows-scoped-runner/fixtures/MonitorStagingHandoffFixture.cs' = '463273337d01e64b4285031858188b5ef886bb5cf150f6dabe2ac637bca999d5'
    'tools/windows-scoped-runner/fixtures/PayloadFixture.cs' = 'e806b393f9f7fe24d349879e70ff247479592373831a1eb30f55e5950d341676'
    'tools/windows-scoped-runner/fixtures/SpecificationTransferFixture.cs' = 'a6b901d0a9cf59faba2d5f056d983ef627b92b2e9535277b60a1e2e75541e504'
}

$source = (Resolve-Path -LiteralPath $SourceRoot).Path
$run = [IO.Path]::GetFullPath($RunRoot)
$allowedParent = 'C:\RhaiQuality\runs'
$allowedRoot = $allowedParent + '\'
if ($run -notmatch '^C:\\RhaiQuality\\runs\\monitor-source-[0-9a-f]{32}$') {
    throw "RunRoot must be a direct, unique monitor-source-GUID child of $allowedParent"
}
foreach ($trustedDirectory in @('C:\RhaiQuality', $allowedParent)) {
    if (!(Test-Path -LiteralPath $trustedDirectory -PathType Container)) { throw "Approved run ancestor is absent: $trustedDirectory" }
    $directoryInfo = Get-Item -LiteralPath $trustedDirectory -Force
    if (($directoryInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Approved run ancestor is a reparse point: $trustedDirectory" }
}
if ($SetupFailureControl) {
    if (!(Test-Path -LiteralPath $run -PathType Container)) { throw "SetupFailureControl requires the existing owner run root: $run" }
}
elseif (Test-Path -LiteralPath $run) { throw "RunRoot already exists; preserve and inspect it: $run" }
$drive = [IO.DriveInfo]::new('C:')
if ($drive.AvailableFreeSpace -lt 2GB) { throw 'At least 2 GiB free on C: is required by the fixed fixture storage plan' }

$expectedRoot = Join-Path $run 'input'
$buildRoot = Join-Path $run 'build'
$logRoot = Join-Path $run 'logs'
$tempRoot = Join-Path $run 'temp'
if ($SetupFailureControl) {
    foreach ($directory in @($expectedRoot, $buildRoot, $logRoot, $tempRoot)) {
        if (!(Test-Path -LiteralPath $directory -PathType Container)) { throw "SetupFailureControl owner directory is absent: $directory" }
    }
}
else {
    New-Item -ItemType Directory -Path $run | Out-Null
    foreach ($directory in @($expectedRoot, $buildRoot, $logRoot, $tempRoot)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
}
$env:TEMP = $tempRoot
$env:TMP = $tempRoot

# Bind kernel32 exports through runtime-generated delegates. This emits managed
# metadata only; no C# compiler or other child is started before ownership.
$assemblyName = [Reflection.AssemblyName]::new('RhaiFixtureNativeBindings')
$assemblyAccess = [Reflection.Emit.AssemblyBuilderAccess]::Run
if ($PSVersionTable.PSEdition -eq 'Desktop') {
    $script:delegateAssembly = [AppDomain]::CurrentDomain.DefineDynamicAssembly($assemblyName, $assemblyAccess)
}
else {
    $script:delegateAssembly = [Reflection.Emit.AssemblyBuilder]::DefineDynamicAssembly($assemblyName, $assemblyAccess)
}
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
    $attributeValues = [Object[]]@($true)
    $attribute = [Reflection.Emit.CustomAttributeBuilder]::new($attributeCtor,
        [Object[]]@([Runtime.InteropServices.CallingConvention]::Winapi), $attributeFields, $attributeValues)
    $builder.SetCustomAttribute($attribute)
    return $builder.CreateTypeInfo().AsType()
}
$currentProcessModules = [Diagnostics.Process]::GetCurrentProcess().Modules
$kernel32Module = $null
foreach ($module in $currentProcessModules) {
    if ($module.ModuleName -ieq 'kernel32.dll') { $kernel32Module = $module; break }
}
if ($null -eq $kernel32Module) { throw 'kernel32 module was not present in the current process module list.' }
# Desktop PowerShell wraps values emitted from a collection pipeline in PSObject.
# Use a typed assignment from the concrete ProcessModule property before any
# reflection call; the resolver below requires a CLR IntPtr, not that wrapper.
[IntPtr]$script:kernel32 = $kernel32Module.BaseAddress
if ($script:kernel32.GetType() -ne [IntPtr] -or $script:kernel32 -eq [IntPtr]::Zero) {
    throw 'kernel32 module handle was not a nonzero CLR IntPtr after explicit conversion.'
}
$resolverBuilder = $script:delegateModule.DefineType('Kernel32ExportResolver',
    [Reflection.TypeAttributes]::Public -bor [Reflection.TypeAttributes]::Abstract -bor [Reflection.TypeAttributes]::Sealed)
$resolverMethod = $resolverBuilder.DefinePInvokeMethod('GetProcAddress', 'kernel32.dll',
    [Reflection.MethodAttributes]::Public -bor [Reflection.MethodAttributes]::Static -bor [Reflection.MethodAttributes]::PinvokeImpl,
    [Reflection.CallingConventions]::Standard, [IntPtr], [Type[]]@([IntPtr], [string]),
    [Runtime.InteropServices.CallingConvention]::Winapi, [Runtime.InteropServices.CharSet]::Ansi)
$resolverMethod.SetImplementationFlags([Reflection.MethodImplAttributes]::PreserveSig)
$script:kernel32Resolver = $resolverBuilder.CreateTypeInfo().AsType()
function Get-KernelDelegate([string] $Export, [Type] $DelegateType) {
    # Read the handle from the explicitly typed owner field. MethodInfo.Invoke
    # requires a CLR IntPtr in its argument array, not a PowerShell wrapper.
    [IntPtr]$moduleHandle = $script:kernel32
    if ($moduleHandle -isnot [IntPtr] -or $moduleHandle -eq [IntPtr]::Zero) {
        throw 'kernel32 module handle was not a nonzero CLR IntPtr.'
    }
    if ([string]::IsNullOrWhiteSpace($Export)) { throw 'Kernel32 export name is empty.' }
    $arguments = [object[]]::new(2)
    $arguments.SetValue($moduleHandle, 0)
    $arguments.SetValue([string]$Export, 1)
    if ($arguments[0].GetType() -ne [IntPtr] -or $arguments[0] -eq [IntPtr]::Zero) {
        throw 'GetProcAddress argument 0 is not a nonzero CLR IntPtr.'
    }
    if ($arguments[1].GetType() -ne [string]) { throw 'GetProcAddress argument 1 is not a CLR String.' }
    $address = [IntPtr]$script:kernel32Resolver.GetMethod('GetProcAddress').Invoke($null, $arguments)
    if ($address -eq [IntPtr]::Zero) { throw "GetProcAddress($Export) failed." }
    return [Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer($address, $DelegateType)
}
$script:createJob = Get-KernelDelegate 'CreateJobObjectW' (New-NativeDelegateType 'CreateJobObjectDelegate' ([IntPtr]) ([Type[]]@([IntPtr], [IntPtr])))
$script:setJobInfo = Get-KernelDelegate 'SetInformationJobObject' (New-NativeDelegateType 'SetInformationJobObjectDelegate' ([bool]) ([Type[]]@([IntPtr], [int], [IntPtr], [uint32])))
$script:assignJob = Get-KernelDelegate 'AssignProcessToJobObject' (New-NativeDelegateType 'AssignProcessToJobObjectDelegate' ([bool]) ([Type[]]@([IntPtr], [IntPtr])))
$script:terminateJob = Get-KernelDelegate 'TerminateJobObject' (New-NativeDelegateType 'TerminateJobObjectDelegate' ([bool]) ([Type[]]@([IntPtr], [uint32])))
$script:terminateProcess = Get-KernelDelegate 'TerminateProcess' (New-NativeDelegateType 'TerminateProcessDelegate' ([bool]) ([Type[]]@([IntPtr], [uint32])))
$script:terminateProcessDelegateType = $script:terminateProcess.GetType()
$script:closeHandle = Get-KernelDelegate 'CloseHandle' (New-NativeDelegateType 'CloseHandleDelegate' ([bool]) ([Type[]]@([IntPtr])))
$script:queryJobInfo = Get-KernelDelegate 'QueryInformationJobObject' (New-NativeDelegateType 'QueryInformationJobObjectDelegate' ([bool]) ([Type[]]@([IntPtr], [int], [IntPtr], [uint32], [IntPtr])))

# Initialize every owner before acquiring the first native handle. The encompassing
# try/finally below covers job creation, assignment, watchdog setup and execution.
$script:jobHandle = [IntPtr]::Zero
$script:jobInfo = [IntPtr]::Zero
$script:wallTimer = $null
$script:setupFailureChild = $null
$currentProcess = $null
$drained = $null
$success = $false
try {
$script:jobHandle = $script:createJob.Invoke([IntPtr]::Zero, [IntPtr]::Zero)
if ($script:jobHandle -eq [IntPtr]::Zero) { throw "CreateJobObjectW failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
$script:jobInfo = [Runtime.InteropServices.Marshal]::AllocHGlobal(144)
try {
    [Runtime.InteropServices.Marshal]::Copy([byte[]]::new(144), 0, $script:jobInfo, 144)
    [Runtime.InteropServices.Marshal]::WriteInt32($script:jobInfo, 16, 0x2308) # kill-on-close + process/job memory and active-count caps; no breakaway
    [Runtime.InteropServices.Marshal]::WriteInt32($script:jobInfo, 40, 16) # PowerShell + bounded compiler/fixture descendants
    [Runtime.InteropServices.Marshal]::WriteInt64($script:jobInfo, 112, 1GB) # process memory cap
    [Runtime.InteropServices.Marshal]::WriteInt64($script:jobInfo, 120, 2GB) # total job memory cap
    if (!$script:setJobInfo.Invoke($script:jobHandle, 9, $script:jobInfo, 144)) {
        throw "SetInformationJobObject failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
    }
}
finally {
    [Runtime.InteropServices.Marshal]::FreeHGlobal($script:jobInfo)
    $script:jobInfo = [IntPtr]::Zero
}
$currentProcess = [Diagnostics.Process]::GetCurrentProcess()
if (!$script:assignJob.Invoke($script:jobHandle, $currentProcess.Handle)) {
    $failure = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    # Keep the exact handle in its initialized owner; the encompassing finally
    # performs the only close attempt and preserves it on failure.
    throw "AssignProcessToJobObject(current PowerShell process) failed before any child was launched: $failure"
}
if ($SetupFailureControl) {
    $controlOutput = Join-Path $logRoot 'setup-failure-child.stdout.txt'
    $controlError = Join-Path $logRoot 'setup-failure-child.stderr.txt'
    $script:setupFailureChild = Start-Process -FilePath 'C:\Windows\System32\PING.EXE' `
        -ArgumentList @('-n', '60', '127.0.0.1') -RedirectStandardOutput $controlOutput `
        -RedirectStandardError $controlError -PassThru -NoNewWindow
    throw 'Injected setup failure after job assignment and before watchdog construction.'
}

# A one-hour timer runs on the .NET timer thread. On expiry it terminates the
# exact PowerShell process. Process teardown closes its exact job handle, whose
# KILL_ON_JOB_CLOSE limit then terminates compiler/fixture descendants. The
# process handle remains valid through job accounting and exact job disposition.
$watchdogType = $script:delegateModule.DefineType('RhaiFixtureWallDeadline',
    [Reflection.TypeAttributes]::Public -bor [Reflection.TypeAttributes]::Sealed -bor [Reflection.TypeAttributes]::Abstract)
$fire = $watchdogType.DefineMethod('Fire', [Reflection.MethodAttributes]::Public -bor [Reflection.MethodAttributes]::Static,
    [void], [Type[]]@([Object]))
$il = $fire.GetILGenerator()
$stateLocal = $il.DeclareLocal([Object[]])
$il.Emit([Reflection.Emit.OpCodes]::Ldarg_0)
$il.Emit([Reflection.Emit.OpCodes]::Castclass, [Object[]])
$il.Emit([Reflection.Emit.OpCodes]::Stloc, $stateLocal)
$il.Emit([Reflection.Emit.OpCodes]::Ldloc, $stateLocal)
$il.Emit([Reflection.Emit.OpCodes]::Ldc_I4_1)
$il.Emit([Reflection.Emit.OpCodes]::Ldelem_Ref)
$il.Emit([Reflection.Emit.OpCodes]::Castclass, $script:terminateProcessDelegateType)
$il.Emit([Reflection.Emit.OpCodes]::Ldloc, $stateLocal)
$il.Emit([Reflection.Emit.OpCodes]::Ldc_I4_0)
$il.Emit([Reflection.Emit.OpCodes]::Ldelem_Ref)
$il.Emit([Reflection.Emit.OpCodes]::Unbox_Any, [IntPtr])
$il.Emit([Reflection.Emit.OpCodes]::Ldloc, $stateLocal)
$il.Emit([Reflection.Emit.OpCodes]::Ldc_I4_2)
$il.Emit([Reflection.Emit.OpCodes]::Ldelem_Ref)
$il.Emit([Reflection.Emit.OpCodes]::Unbox_Any, [uint32])
$il.Emit([Reflection.Emit.OpCodes]::Callvirt, $script:terminateProcessDelegateType.GetMethod('Invoke'))
$il.Emit([Reflection.Emit.OpCodes]::Pop)
$il.Emit([Reflection.Emit.OpCodes]::Ret)
$script:wallWatchdogType = $watchdogType.CreateTypeInfo().AsType()
$timerState = [Object[]]::new(3)
$timerState[0] = $currentProcess.Handle
$timerState[1] = $script:terminateProcess
$timerState[2] = [uint32]3758096386 # 0xE0000002, represented as positive UInt32 for Windows PowerShell 5.1
$watchdogDelegate = $script:wallWatchdogType.GetMethod('Fire').CreateDelegate([Threading.TimerCallback])
$drained = [Threading.ManualResetEvent]::new($false)
$script:wallTimer = [Threading.Timer]::new($watchdogDelegate, $timerState, 3600000, [System.Threading.Timeout]::Infinite)

$runwatch = [Diagnostics.Stopwatch]::StartNew()
$totalRunLimitSeconds = 3600

function Quote-ProcessArgument([string] $value) {
    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append('"')
    $slashes = 0
    foreach ($character in $value.ToCharArray()) {
        if ($character -eq '\') { $slashes++; continue }
        if ($character -eq '"') { [void]$builder.Append(('\' * (2 * $slashes + 1))).Append('"'); $slashes = 0; continue }
        [void]$builder.Append(('\' * $slashes)).Append($character); $slashes = 0
    }
    [void]$builder.Append(('\' * (2 * $slashes))).Append('"')
    return $builder.ToString()
}

function Invoke-OwnedProcess([string] $Path, [string[]] $Arguments, [string] $Name, [int] $TimeoutSeconds) {
    $stdout = Join-Path $logRoot ($Name + '.stdout.txt')
    $stderr = Join-Path $logRoot ($Name + '.stderr.txt')
    $argumentLine = (($Arguments | ForEach-Object { Quote-ProcessArgument ([string]$_) }) -join ' ')
    $remaining = [Math]::Min($TimeoutSeconds, $totalRunLimitSeconds - [int]$runwatch.Elapsed.TotalSeconds)
    if ($remaining -le 0) { throw 'One-hour overall source-fixture limit elapsed.' }
    $process = Start-Process -FilePath $Path -ArgumentList $argumentLine -WorkingDirectory $buildRoot `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -NoNewWindow
    # The PowerShell parent is already in a KILL_ON_JOB_CLOSE job. Windows
    # places this child in that job at creation, before it can execute.
    if (!$process.WaitForExit($remaining * 1000)) {
        [void]$script:terminateJob.Invoke($script:jobHandle, [uint32]3758096385) # 0xE0000001
        [void]$process.WaitForExit(5000)
        throw "$Name exceeded its bounded timeout; inherited job was terminated"
    }
    $process.Refresh()
    if ($process.ExitCode -ne 0) { throw "$Name exited $($process.ExitCode); inspect $stdout and $stderr" }
    Write-Output "PASS $Name"
}

if (!$SetupFailureControl) {
    $controlMarker = Join-Path $logRoot 'setup-failure-control.txt'
    if (Test-Path -LiteralPath $controlMarker) { throw "Setup-failure control marker already exists: $controlMarker" }
    $childPowerShell = Join-Path $PSHOME 'powershell.exe'
    $controlStdout = Join-Path $logRoot 'setup-failure-control.stdout.txt'
    $controlStderr = Join-Path $logRoot 'setup-failure-control.stderr.txt'
    $controlArguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath,
        '-SourceRoot', $source, '-RunRoot', $run, '-SetupFailureControl')
    $controlArgumentLine = (($controlArguments | ForEach-Object { Quote-ProcessArgument ([string]$_) }) -join ' ')
    $controlDeadline = [Diagnostics.Stopwatch]::StartNew()
    $controlProcess = $null
    try {
        $controlProcess = Start-Process -FilePath $childPowerShell -ArgumentList $controlArgumentLine `
            -WorkingDirectory $source -RedirectStandardOutput $controlStdout -RedirectStandardError $controlStderr `
            -PassThru -NoNewWindow
        $remainingMilliseconds = [Math]::Max(0, 30000 - [int]$controlDeadline.ElapsedMilliseconds)
        if (!$controlProcess.WaitForExit($remainingMilliseconds)) {
            [void]$script:terminateJob.Invoke($script:jobHandle, [uint32]3758096385)
            throw 'Setup-failure control exceeded its shared 30-second deadline; the exact outer job was terminated.'
        }
        $controlProcess.Refresh()
        if ($controlProcess.ExitCode -eq 0) { throw 'Setup-failure control unexpectedly succeeded.' }
        if (!(Test-Path -LiteralPath $controlMarker -PathType Leaf)) { throw 'Setup-failure control did not preserve its primary setup exception.' }
        $controlRecord = Get-Content -LiteralPath $controlMarker -Raw
        if ($controlRecord -notmatch 'CONTROL_INJECTED_AFTER_JOB_ASSIGNMENT_BEFORE_TIMER' -or
            $controlRecord -notmatch 'Injected setup failure after job assignment and before watchdog construction' -or
            $controlRecord -notmatch '(?m)^ChildPid=([1-9][0-9]*)\r?$') {
            throw 'Setup-failure control marker does not bind the injected setup error and exact child PID.'
        }
        $controlChildPid = [int]$Matches[1]
        $controlErrors = if (Test-Path -LiteralPath $controlStderr -PathType Leaf) { Get-Content -LiteralPath $controlStderr -Raw } else { '' }
        if ($controlErrors -match 'Job disposition failed|CloseHandle\(job\) failed|Watchdog timer refused disposal') {
            throw 'Setup-failure control reported an owner-disposition failure.'
        }
        $accounting = [Runtime.InteropServices.Marshal]::AllocHGlobal(48)
        try {
            $active = -1
            while ($controlDeadline.ElapsedMilliseconds -lt 30000) {
                if (!$script:queryJobInfo.Invoke($script:jobHandle, 1, $accounting, 48, [IntPtr]::Zero)) {
                    throw "QueryInformationJobObject(after setup-failure control) failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
                }
                $active = [Runtime.InteropServices.Marshal]::ReadInt32($accounting, 40)
                if ($active -eq 1) { break }
                Start-Sleep -Milliseconds ([Math]::Min(100, [Math]::Max(1, 30000 - [int]$controlDeadline.ElapsedMilliseconds)))
            }
            if ($active -ne 1) { throw "Setup-failure control child PID $controlChildPid left $($active - 1) process(es) in the exact outer job at the shared 30-second deadline." }
        }
        finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($accounting) }
        Write-Output "PASS setup-failure-control: child PID $controlChildPid; primary exception retained; nested job teardown removed owned child; outer job returned to owner-only."
    }
    finally { if ($null -ne $controlProcess) { $controlProcess.Dispose() } }
}

    foreach ($relative in ($expected.Keys | Sort-Object)) {
        $inputPath = Join-Path $source $relative
        if (!(Test-Path -LiteralPath $inputPath -PathType Leaf)) { throw "Required immutable input missing: $relative" }
        $actual = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected[$relative]) { throw "Immutable input hash changed: $relative ($actual)" }
        $destination = Join-Path $expectedRoot $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $inputPath -Destination $destination
        if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected[$relative]) {
            throw "Immutable input copy readback mismatch: $relative"
        }
    }

    $compiler = 'C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe'
    if (!(Test-Path -LiteralPath $compiler -PathType Leaf)) { throw "Expected existing compiler is absent; bootstrap is out of scope: $compiler" }
    $production = @(
        'LaunchSpecification.cs','LeaseMonitor.cs','MonitorPayloadJob.cs','MonitorSpecificationIntake.cs',
        'MonitorStagingHandoff.cs','MonitorTransport.cs','ScopedRunner.cs','SpecificationTransfer.cs','WindowsCustodyBackend.cs'
    ) | ForEach-Object { Join-Path $expectedRoot ('tools/windows-scoped-runner/' + $_) }
    $allProduction = @($production)
    $runner = Join-Path $buildRoot 'ScopedRunner.exe'
    Invoke-OwnedProcess $compiler (@('/target:exe','/main:ScopedRunner',('/out:'+$runner)) + $allProduction) 'compile-production-runner' 180

    $fixtureCases = @(
        @{ Name='CustodyBackendFixture'; Timeout=720 },
        @{ Name='LaunchSpecificationFixture'; Timeout=120 },
        @{ Name='LeaseProtocolFixture'; Timeout=180 },
        @{ Name='MonitorPayloadJobFixture'; Timeout=180 },
        @{ Name='MonitorSpecificationIntakeFixture'; Timeout=300 },
        @{ Name='SpecificationTransferFixture'; Timeout=180 }
    )
    foreach ($case in $fixtureCases) {
        $fixtureSource = Join-Path $expectedRoot ('tools/windows-scoped-runner/fixtures/' + $case.Name + '.cs')
        $fixtureSources = @($fixtureSource)
        if ($case.Name -eq 'MonitorSpecificationIntakeFixture') {
            # The intake fixture calls this companion's Run() method; it is a
            # source fixture, not a separately executable fixture.
            $fixtureSources += Join-Path $expectedRoot 'tools/windows-scoped-runner/fixtures/MonitorStagingHandoffFixture.cs'
        }
        $exe = Join-Path $buildRoot ($case.Name + '.exe')
        Invoke-OwnedProcess $compiler (@('/target:exe','/define:SCOPED_RUNNER_TESTING',('/main:'+$case.Name),('/out:'+$exe)) + $allProduction + $fixtureSources) ('compile-' + $case.Name) 180
    }
    $payloadSource = Join-Path $expectedRoot 'tools/windows-scoped-runner/fixtures/PayloadFixture.cs'
    $payloadExe = Join-Path $buildRoot 'PayloadFixture.exe'
    Invoke-OwnedProcess $compiler @('/target:exe','/main:PayloadFixture',('/out:'+$payloadExe),$payloadSource) 'compile-PayloadFixture' 180

    foreach ($case in $fixtureCases) {
        $exe = Join-Path $buildRoot ($case.Name + '.exe')
        Invoke-OwnedProcess $exe @() ('run-' + $case.Name) $case.Timeout
    }
    Write-Output 'UNRUN RunProcessCreationFixtures.ps1: it exercises the disabled legacy --source entrypoint.'
    Write-Output "RETAINED run root: $run"
    $success = $true
}
catch {
    $primaryFailure = $_
    try {
        if ($SetupFailureControl) {
            $markerPath = Join-Path $logRoot 'setup-failure-control.txt'
            $childPid = if ($null -ne $script:setupFailureChild) { $script:setupFailureChild.Id } else { 0 }
            $markerText = "CONTROL_INJECTED_AFTER_JOB_ASSIGNMENT_BEFORE_TIMER`r`nPowerShellPid=$PID`r`nChildPid=$childPid`r`n$($primaryFailure.Exception.ToString())"
            $markerBytes = [Text.UTF8Encoding]::new($false).GetBytes($markerText)
            $markerStream = [IO.File]::Open($markerPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
            try { $markerStream.Write($markerBytes, 0, $markerBytes.Length); $markerStream.Flush($true) }
            finally { $markerStream.Dispose() }
        }
        else {
            [Console]::Error.WriteLine("Primary source-fixture failure: $($primaryFailure.Exception.ToString())")
            [Console]::Error.Flush()
            if (Test-Path -LiteralPath $logRoot -PathType Container) {
                $failurePath = Join-Path $logRoot ("setup-failure-$PID.txt")
                [IO.File]::WriteAllText($failurePath, $primaryFailure.Exception.ToString(), [Text.UTF8Encoding]::new($false))
            }
        }
    }
    catch {
        [Console]::Error.WriteLine("Could not persist primary source-fixture failure diagnostics: $($_.Exception.ToString())")
        [Console]::Error.Flush()
    }
    throw $primaryFailure
}
finally {
    if ($script:jobHandle -ne [IntPtr]::Zero) {
        try {
            if ($success) {
                # All owned children were synchronously waited; require the current
                # PowerShell process to be the only remaining member before close.
                $accounting = [Runtime.InteropServices.Marshal]::AllocHGlobal(48)
                try {
                    if (!$script:queryJobInfo.Invoke($script:jobHandle, 1, $accounting, 48, [IntPtr]::Zero)) {
                        throw "QueryInformationJobObject(accounting) failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
                    }
                    $active = [Runtime.InteropServices.Marshal]::ReadInt32($accounting, 40)
                    if ($active -ne 1) { throw "Owned job has $active active processes at successful exit; refusing clean harness result." }
                }
                finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($accounting) }
                $script:jobInfo = [Runtime.InteropServices.Marshal]::AllocHGlobal(144)
                try {
                    [Runtime.InteropServices.Marshal]::Copy([byte[]]::new(144), 0, $script:jobInfo, 144)
                    if (!$script:setJobInfo.Invoke($script:jobHandle, 9, $script:jobInfo, 144)) {
                        throw "Could not clear KILL_ON_JOB_CLOSE after all children exited: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
                    }
                }
                finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($script:jobInfo); $script:jobInfo = [IntPtr]::Zero }
            }
            if (!$script:closeHandle.Invoke($script:jobHandle)) {
                $closeError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
                # If successful accounting already cleared KILL_ON_JOB_CLOSE,
                # explicitly terminate the exact job before failing the host.
                if ($success -and !$script:terminateJob.Invoke($script:jobHandle, [uint32]3758096387)) { # 0xE0000003
                    [Environment]::FailFast("CloseHandle(job) and recovery TerminateJobObject failed ($closeError / $([Runtime.InteropServices.Marshal]::GetLastWin32Error())); exact handle/watchdog remain owned through process teardown.")
                }
                [Environment]::FailFast("CloseHandle(job) failed ($closeError); exact handle/watchdog remain owned through process teardown.")
            }
            $script:jobHandle = [IntPtr]::Zero
        }
        catch {
            # Never unwind with the exact job handle owned: this shell may have
            # been invoked with &, so script-scope cleanup is not process teardown.
            [Environment]::FailFast("Job disposition failed; preserving watchdog and owner through controller teardown: $($_.Exception.Message)")
        }
    }
    # The timer remains armed through job accounting and handle disposition.
    # Dispose(waitHandle) requests cancellation; only its signaled drain event
    # proves that no callback can still use the retained exact process handle.
    if ($script:wallTimer -ne $null) {
        if (!$script:wallTimer.Dispose($drained)) {
            [Environment]::FailFast('Watchdog timer refused disposal; preserving process/job ownership through controller teardown.')
        }
        if (!$drained.WaitOne(5000)) {
            [Environment]::FailFast('Watchdog callback did not drain within 5 seconds; preserving process/job ownership through controller teardown.')
        }
        $script:wallTimer = $null
    }
    if ($drained -ne $null) { $drained.Dispose() }
    if ($currentProcess -ne $null) { $currentProcess.Dispose() }
}
