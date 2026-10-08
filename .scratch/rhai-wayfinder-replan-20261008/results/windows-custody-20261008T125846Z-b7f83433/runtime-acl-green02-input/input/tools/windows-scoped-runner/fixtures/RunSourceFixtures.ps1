param(
    [Parameter(Mandatory = $true)] [string] $SourceRoot,
    [Parameter(Mandatory = $true)] [string] $RunRoot,
    [switch] $SetupFailureControl,
    [switch] $BuildOnly
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
    'tools/windows-scoped-runner/MonitorPayloadJob.cs' = 'ac5c62bdcd4402b1f103131e082ab6e35a6d979b80629ea6ffef82b386f2353b'
    'tools/windows-scoped-runner/MonitorSpecificationIntake.cs' = '0f0a71563e6c3d99f0c643644d4b56951f6c69ceb3b10b03157f68dc37bb8412'
    'tools/windows-scoped-runner/MonitorStagingHandoff.cs' = 'c541f7d885d032c074461a5a0173b9ae6291ef7d8cd1b9fd2ce4a4f56d1e0e6e'
    'tools/windows-scoped-runner/MonitorTransport.cs' = '4a307370af955b49bae50b86fec5be9039db392c730897a3c87111e0191b89a7'
    'tools/windows-scoped-runner/ScopedRunner.cs' = 'd3a77f0daeebd5beed2b277fae9dc6a522acf1454bb5d8d776d84e1dc8e896c8'
    'tools/windows-scoped-runner/SpecificationTransfer.cs' = '7a9edfe98d84868b55146280bd5ed29576ee0c8725cf9f6c785b784bc0ad25c2'
    'tools/windows-scoped-runner/WindowsCustodyBackend.cs' = '14e4231986ac7b95fd4f142b37a68bf295aec124b9ee66a6b5018fa0b07b2a46'
    'tools/windows-scoped-runner/fixtures/CustodyBackendFixture.cs' = '4d0ec278445be0220dffef8db31f25dbb424a88833b2b434328d6969e085c07c'
    'tools/windows-scoped-runner/fixtures/LaunchSpecificationFixture.cs' = '5acc9ddd831fef39bdcd5c540a5404c5dd077abda731a67d16ecd4d92c82313e'
    'tools/windows-scoped-runner/fixtures/LeaseProtocolFixture.cs' = 'c466da5498e6908f273158384c73d58b055f083930bc9fac7c7af2a7dbf12251'
    'tools/windows-scoped-runner/fixtures/MonitorPayloadJobFixture.cs' = 'd9aae76fd68a2cb52721618cd0746af36892a7951c9d0c4d11867a05e11ca7c0'
    'tools/windows-scoped-runner/fixtures/MonitorSpecificationIntakeFixture.cs' = '3e774455bc25a3f0fa40162e4ca3f5d59f35270d27b41c3e2aceb0f144f73d8d'
    'tools/windows-scoped-runner/fixtures/MonitorStagingHandoffFixture.cs' = '463273337d01e64b4285031858188b5ef886bb5cf150f6dabe2ac637bca999d5'
    'tools/windows-scoped-runner/fixtures/PayloadFixture.cs' = 'e806b393f9f7fe24d349879e70ff247479592373831a1eb30f55e5950d341676'
    'tools/windows-scoped-runner/fixtures/SpecificationTransferFixture.cs' = 'a6b901d0a9cf59faba2d5f056d983ef627b92b2e9535277b60a1e2e75541e504'
}

# The narrow native bootstrap compiles only the public runner, real-client driver
# and finite payload. It never runs the driver inside this compiler owner's job.
$expected['tools/windows-scoped-runner/MonitorAcceptanceDriver.cs'] = 'd6c37fafc3ce96650e28d506ac06c97ea5a3554c5a9103ad5dae60c329eeb199'
$expected['tools/windows-scoped-runner/fixtures/NativeScopePolicyFixture.cs'] = '8f43d33928262ae181aa5396feffef9b0260653609b5be8b01da7b0a7e7b00f7'
if ($BuildOnly) {
    foreach ($relative in @($expected.Keys)) {
        if ($relative -like '*/fixtures/*' -and $relative -ne 'tools/windows-scoped-runner/fixtures/PayloadFixture.cs' -and
            $relative -ne 'tools/windows-scoped-runner/fixtures/NativeScopePolicyFixture.cs' -and
            $relative -ne 'tools/windows-scoped-runner/fixtures/CustodyBackendFixture.cs') {
            $expected.Remove($relative)
        }
    }
}

$source = (Resolve-Path -LiteralPath $SourceRoot).Path
function Resolve-PrivateRunLayout([string] $RunRoot, [string] $UserProfile) {
    if ($RunRoot -match '(^|[\\/])\.\.([\\/]|$)') { throw 'RunRoot cannot contain parent-directory traversal.' }
    $profileRoot = [IO.Path]::GetFullPath($UserProfile).TrimEnd('\')
    $privateBuildRoot = [IO.Path]::GetFullPath((Join-Path $profileRoot '.local\share\agent-builds\rhai')).TrimEnd('\')
    $privatePrefix = $privateBuildRoot + '\'
    $run = [IO.Path]::GetFullPath($RunRoot)
    if (!$privateBuildRoot.StartsWith(($profileRoot + '\'), [StringComparison]::OrdinalIgnoreCase) -or
        !$run.StartsWith($privatePrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'RunRoot must be inside the current user private agent-builds/rhai tree.'
    }
    $relativeRun = $run.Substring($privatePrefix.Length)
    $runParts = $relativeRun.Split([char[]]@('\'))
    if ($runParts.Length -ne 3 -or
        $runParts[0] -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$' -or
        $runParts[1] -cne 'run' -or
        $runParts[2] -notmatch '^monitor-source-[0-9a-f]{32}$') {
        throw 'RunRoot must be a unique monitor-source-GUID child of <private-session-root>\run.'
    }
    $sessionRoot = Join-Path $privateBuildRoot $runParts[0]
    $allowedParent = Join-Path $sessionRoot 'run'
    $expectedRun = Join-Path $allowedParent $runParts[2]
    if (!$run.Equals($expectedRun, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'RunRoot must be the canonical direct child of the current private session run directory.'
    }
    $volumeRoot = [IO.Path]::GetPathRoot($run)
    if (![IO.Path]::GetPathRoot($profileRoot).Equals($volumeRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'RunRoot and USERPROFILE must use the same volume.'
    }
    $trustedDirectories = @()
    $cursor = $allowedParent
    while ($true) {
        $trustedDirectories += $cursor
        if ($cursor.Equals($volumeRoot, [StringComparison]::OrdinalIgnoreCase)) { break }
        $parent = [IO.Directory]::GetParent($cursor)
        if ($null -eq $parent) { throw 'Could not enumerate every RunRoot ancestor through the volume root.' }
        $cursor = $parent.FullName
    }
    return [PSCustomObject]@{
        RunRoot = $run
        AllowedParent = $allowedParent
        DriveRoot = $volumeRoot
        TrustedDirectories = $trustedDirectories
    }
}
function Assert-NoReparseDirectories([string[]] $TrustedDirectories, [string[]] $ReparseDirectories) {
    foreach ($trustedDirectory in $TrustedDirectories) {
        foreach ($reparseDirectory in $ReparseDirectories) {
            if ($trustedDirectory.Equals($reparseDirectory, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Approved run ancestor is a reparse point: $trustedDirectory"
            }
        }
    }
}
function Assert-RunRootRejected([string] $Name, [string] $RunRoot, [string] $UserProfile) {
    $rejected = $false
    try { $null = Resolve-PrivateRunLayout $RunRoot $UserProfile } catch { $rejected = $true }
    if (!$rejected) { throw "Private run-root policy accepted invalid case: $Name" }
}

# Exercise the path policy without creating files or native resources.
$policyProfile = [IO.Path]::GetFullPath($env:USERPROFILE)
$policyPrivate = Join-Path $policyProfile '.local\share\agent-builds\rhai'
$policySession = Join-Path $policyPrivate 'policy-test-session'
$policyRunName = 'monitor-source-0123456789abcdef0123456789abcdef'
$policyValidRun = Join-Path (Join-Path $policySession 'run') $policyRunName
$policyLayout = Resolve-PrivateRunLayout $policyValidRun $policyProfile
if (!$policyLayout.RunRoot.Equals([IO.Path]::GetFullPath($policyValidRun), [StringComparison]::OrdinalIgnoreCase) -or
    !$policyLayout.DriveRoot.Equals([IO.Path]::GetPathRoot($policyProfile), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Private run-root valid-case or volume binding failed.'
}
Assert-RunRootRejected 'old-root' (Join-Path (Join-Path $policyLayout.DriveRoot 'RhaiQuality\runs') $policyRunName) $policyProfile
Assert-RunRootRejected 'wrong-session-depth' (Join-Path (Join-Path (Join-Path $policySession 'nested') 'run') $policyRunName) $policyProfile
Assert-RunRootRejected 'parent-traversal' ((Join-Path (Join-Path $policySession 'run') '..\run') + '\' + $policyRunName) $policyProfile
$alternateProfile = Join-Path ([IO.Path]::GetPathRoot($policyProfile)) 'Profiles\PolicyFixture'
$alternatePrivate = Join-Path $alternateProfile '.local\share\agent-builds\rhai'
$alternateSession = Join-Path $alternatePrivate 'alternate-session'
$alternateParent = Join-Path $alternateSession 'run'
$alternateRun = Join-Path $alternateParent $policyRunName
$alternateLayout = Resolve-PrivateRunLayout $alternateRun $alternateProfile
$expectedAlternateAncestors = @(
    $alternateParent,
    $alternateSession,
    $alternatePrivate,
    (Join-Path $alternateProfile '.local\share\agent-builds'),
    (Join-Path $alternateProfile '.local\share'),
    (Join-Path $alternateProfile '.local'),
    $alternateProfile,
    (Join-Path ([IO.Path]::GetPathRoot($alternateProfile)) 'Profiles'),
    [IO.Path]::GetPathRoot($alternateProfile)
)
if (!$alternateLayout.DriveRoot.Equals([IO.Path]::GetPathRoot($alternateRun), [StringComparison]::OrdinalIgnoreCase) -or
    $alternateLayout.TrustedDirectories.Length -ne $expectedAlternateAncestors.Length) {
    throw 'Private run-root drive binding or nonstandard-profile ancestor count failed.'
}
for ($ancestorIndex = 0; $ancestorIndex -lt $expectedAlternateAncestors.Length; $ancestorIndex++) {
    if (!$alternateLayout.TrustedDirectories[$ancestorIndex].Equals($expectedAlternateAncestors[$ancestorIndex], [StringComparison]::OrdinalIgnoreCase)) {
        throw "Private run-root ancestor enumeration failed at index $ancestorIndex."
    }
}
$reparseRejected = $false
try { Assert-NoReparseDirectories $policyLayout.TrustedDirectories @($policyLayout.TrustedDirectories[1]) } catch { $reparseRejected = $true }
if (!$reparseRejected) { throw 'Private run-root policy accepted a reparse-point ancestor case.' }
Write-Output 'PASS private-run-root policy cases: valid, old-root, depth, traversal, reparse, nonstandard ancestors, drive binding'

$policyLayout = Resolve-PrivateRunLayout $RunRoot $env:USERPROFILE
$run = $policyLayout.RunRoot
$allowedParent = $policyLayout.AllowedParent
$driveRoot = $policyLayout.DriveRoot
$trustedDirectories = $policyLayout.TrustedDirectories
$reparseDirectories = @()
foreach ($trustedDirectory in $trustedDirectories) {
    if (!(Test-Path -LiteralPath $trustedDirectory -PathType Container)) { throw "Approved run ancestor is absent: $trustedDirectory" }
    $directoryInfo = Get-Item -LiteralPath $trustedDirectory -Force
    if (($directoryInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { $reparseDirectories += $trustedDirectory }
}
Assert-NoReparseDirectories $trustedDirectories $reparseDirectories
if ($SetupFailureControl) {
    if (!(Test-Path -LiteralPath $run -PathType Container)) { throw "SetupFailureControl requires the existing owner run root: $run" }
}
elseif (Test-Path -LiteralPath $run) { throw "RunRoot already exists; preserve and inspect it: $run" }
$drive = [IO.DriveInfo]::new($driveRoot)
if ($drive.AvailableFreeSpace -lt 2GB) { throw "At least 2 GiB free on $driveRoot is required by the fixed fixture storage plan" }

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
$overallLimitMilliseconds = if ($BuildOnly) { 900000 } else { 3600000 }
$script:wallTimer = [Threading.Timer]::new($watchdogDelegate, $timerState, $overallLimitMilliseconds, [System.Threading.Timeout]::Infinite)

$runwatch = [Diagnostics.Stopwatch]::StartNew()
$totalRunLimitSeconds = $overallLimitMilliseconds / 1000
$maximumLogBytes = 4MB

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

function Get-RequiredExitCode([object] $ExitCode, [string] $Name) {
    if ($null -eq $ExitCode) { throw "$Name exited with unavailable exit status." }
    if ($ExitCode -isnot [int]) { throw "$Name returned invalid exit status '$ExitCode' (expected Int32)." }
    return [int]$ExitCode
}

function Invoke-OwnedProcess([string] $Path, [string[]] $Arguments, [string] $Name, [int] $TimeoutSeconds, [int] $ExpectedExitCode = 0) {
    $stdout = Join-Path $logRoot ($Name + '.stdout.txt')
    $stderr = Join-Path $logRoot ($Name + '.stderr.txt')
    $argumentLine = (($Arguments | ForEach-Object { Quote-ProcessArgument ([string]$_) }) -join ' ')
    $remaining = [Math]::Min($TimeoutSeconds, $totalRunLimitSeconds - [int]$runwatch.Elapsed.TotalSeconds)
    if ($remaining -le 0) { throw 'Overall source-fixture limit elapsed.' }
    $launch = @{ FilePath = $Path; WorkingDirectory = $buildRoot;
        RedirectStandardOutput = $stdout; RedirectStandardError = $stderr;
        PassThru = $true; NoNewWindow = $true }
    # Windows PowerShell rejects an explicitly empty ArgumentList. Preserve a
    # true zero-argument child by omitting that optional parameter entirely.
    if ($Arguments.Count -gt 0) { $launch.ArgumentList = $argumentLine }
    $process = Start-Process @launch
    try {
        # Retain the exact handle before waiting: redirected Start-Process on
        # Windows PowerShell 5.1 otherwise exposes a missing ExitCode.
        $processHandle = $process.Handle
        if ($processHandle -eq [IntPtr]::Zero) { throw "$Name did not expose a valid process handle before waiting." }
        $deadline = [Diagnostics.Stopwatch]::StartNew()
        while (!$process.HasExited -and $deadline.ElapsedMilliseconds -lt $remaining * 1000) {
            foreach ($log in @($stdout, $stderr)) {
                if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt $maximumLogBytes) {
                    [void]$script:terminateJob.Invoke($script:jobHandle, [uint32]3758096385)
                    [Environment]::FailFast("$Name exceeded its per-log output cap; exact compiler job teardown required.")
                }
            }
            [void]$process.WaitForExit(100)
        }
        if (!$process.HasExited) {
            [void]$script:terminateJob.Invoke($script:jobHandle, [uint32]3758096385)
            [Environment]::FailFast("$Name exceeded its bounded timeout; exact compiler job teardown required.")
        }
        $process.Refresh()
        $exitCode = $process.ExitCode
        $exitCode = Get-RequiredExitCode $exitCode $Name
        foreach ($log in @($stdout, $stderr)) {
            if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt $maximumLogBytes) {
                throw "$Name exceeded its per-log output cap at exit."
            }
        }
        [GC]::KeepAlive($processHandle)
        if ($exitCode -ne $ExpectedExitCode) { throw "$Name exited $exitCode (expected $ExpectedExitCode); inspect $stdout and $stderr" }
        Write-Output "PASS $Name exit=$exitCode"
    }
    finally { $process.Dispose() }
}

function Test-OwnedProcessExitCodes([string] $PowerShellPath) {
    $wrongExpectedOutput = Join-Path $logRoot 'exit-code-regression-17-wrong-expected.stdout.txt'
    $zeroOutput = Join-Path $logRoot 'exit-code-regression-zero.stdout.txt'
    $seventeenOutput = Join-Path $logRoot 'exit-code-regression-17.stdout.txt'
    $wrongExpectedRejected = $false
    try {
        Invoke-OwnedProcess $PowerShellPath @('-NoLogo','-NoProfile','-Command',"Write-Output 'EXIT_CODE_REGRESSION_17_WRONG_EXPECTED'; exit 17") `
            'exit-code-regression-17-wrong-expected' 30 0
    }
    catch {
        $wrongExpectedRejected = $_.Exception.Message -match 'exit-code-regression-17-wrong-expected exited 17 \(expected 0\)'
    }
    if (!$wrongExpectedRejected) { throw 'Real exit-17 child was not rejected with its actual 17 and expected 0 status.' }
    if ((Get-Content -LiteralPath $wrongExpectedOutput -Raw).Trim() -ne 'EXIT_CODE_REGRESSION_17_WRONG_EXPECTED') {
        throw 'Exit-code regression child with the wrong expected status did not produce its expected redirected output.'
    }
    Write-Output 'PASS exit-code-regression-17-wrong-expected rejected with actual 17 expected 0'
    Invoke-OwnedProcess $PowerShellPath @('-NoLogo','-NoProfile','-Command',"Write-Output 'EXIT_CODE_REGRESSION_ZERO'; exit 0") `
        'exit-code-regression-zero' 30 0
    Invoke-OwnedProcess $PowerShellPath @('-NoLogo','-NoProfile','-Command',"Write-Output 'EXIT_CODE_REGRESSION_17'; exit 17") `
        'exit-code-regression-17' 30 17
    if ((Get-Content -LiteralPath $zeroOutput -Raw).Trim() -ne 'EXIT_CODE_REGRESSION_ZERO') {
        throw 'Exit-code regression child with exit 0 did not produce its expected redirected output.'
    }
    if ((Get-Content -LiteralPath $seventeenOutput -Raw).Trim() -ne 'EXIT_CODE_REGRESSION_17') {
        throw 'Exit-code regression child with exit 17 did not produce its expected redirected output.'
    }
    $unavailableRejected = $false
    try { $null = Get-RequiredExitCode $null 'exit-code-regression-unavailable' }
    catch { $unavailableRejected = $_.Exception.Message -match 'unavailable exit status' }
    if (!$unavailableRejected) { throw 'Unavailable child exit status was not rejected explicitly.' }
    Write-Output 'PASS exit-code-regression-unavailable rejected'
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
        $controlProcessHandle = $controlProcess.Handle
        if ($controlProcessHandle -eq [IntPtr]::Zero) { throw 'Setup-failure control did not expose a valid process handle before waiting.' }
        $remainingMilliseconds = [Math]::Max(0, 30000 - [int]$controlDeadline.ElapsedMilliseconds)
        if (!$controlProcess.WaitForExit($remainingMilliseconds)) {
            [void]$script:terminateJob.Invoke($script:jobHandle, [uint32]3758096385)
            throw 'Setup-failure control exceeded its shared 30-second deadline; the exact outer job was terminated.'
        }
        $controlProcess.Refresh()
        $controlExitCode = $controlProcess.ExitCode
        $controlExitCode = Get-RequiredExitCode $controlExitCode 'Setup-failure control'
        [GC]::KeepAlive($controlProcessHandle)
        if ($controlExitCode -eq 0) { throw 'Setup-failure control unexpectedly succeeded.' }
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

if (!$SetupFailureControl) { Test-OwnedProcessExitCodes $childPowerShell }

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
    if ($BuildOnly) {
        $policySource = Join-Path $expectedRoot 'tools/windows-scoped-runner/fixtures/NativeScopePolicyFixture.cs'
        $policyExe = Join-Path $buildRoot 'NativeScopePolicyFixture.exe'
        Invoke-OwnedProcess $compiler (@('/target:exe','/main:NativeScopePolicyFixture',('/out:'+$policyExe)) + $allProduction + @($policySource)) 'compile-native-scope-policy' 180
        Invoke-OwnedProcess $policyExe @() 'run-native-scope-policy' 30
        $custodySource = Join-Path $expectedRoot 'tools/windows-scoped-runner/fixtures/CustodyBackendFixture.cs'
        $custodyExe = Join-Path $buildRoot 'CustodyBackendFixture.exe'
        Invoke-OwnedProcess $compiler (@('/target:exe','/define:SCOPED_RUNNER_TESTING','/main:CustodyBackendFixture',('/out:'+$custodyExe)) + $allProduction + @($custodySource)) 'compile-native-runtime-acl' 180
        # A single existing fixture selection exercises ordinary payload ACLs.
        # It does not run the historical synthetic suite or the public driver.
        Invoke-OwnedProcess $custodyExe @('--ordinary-runtime') 'run-native-runtime-acl' 30
    }
    $runner = Join-Path $buildRoot 'ScopedRunner.exe'
    Invoke-OwnedProcess $compiler (@('/target:exe','/main:ScopedRunner',('/out:'+$runner)) + $allProduction) 'compile-production-runner' 180

    $fixtureCases = if ($BuildOnly) { @() } else { @(
        @{ Name='CustodyBackendFixture'; Timeout=720 },
        @{ Name='LaunchSpecificationFixture'; Timeout=120 },
        @{ Name='LeaseProtocolFixture'; Timeout=180 },
        @{ Name='MonitorPayloadJobFixture'; Timeout=180 },
        @{ Name='MonitorSpecificationIntakeFixture'; Timeout=300 },
        @{ Name='SpecificationTransferFixture'; Timeout=180 }
    ) }
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
    if ($BuildOnly) {
        $driverSource = Join-Path $expectedRoot 'tools/windows-scoped-runner/MonitorAcceptanceDriver.cs'
        $driverExe = Join-Path $buildRoot 'MonitorAcceptanceDriver.exe'
        Invoke-OwnedProcess $compiler (@('/target:exe','/main:MonitorAcceptanceDriver',('/out:'+$driverExe)) + $allProduction + @($driverSource)) 'compile-native-driver' 180
        $missingSource = Join-Path $expectedRoot 'deliberately-missing-compiler-control.cs'
        Invoke-OwnedProcess $compiler @('/target:library',$missingSource) 'expected-compiler-failure' 180 1
        $compilerControl = [IO.File]::ReadAllText((Join-Path $logRoot 'expected-compiler-failure.stdout.txt')) + [IO.File]::ReadAllText((Join-Path $logRoot 'expected-compiler-failure.stderr.txt'))
        if (!$compilerControl.Contains('error CS2001')) { throw 'The missing-source control did not reach the intended compiler diagnostic.' }
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
            if (!$success) {
                # Closing a self-inclusive kill-on-close job supplies no failure
                # status: the native setup control observed exit zero. Preserve
                # the primary diagnostics, then terminate only this exact job
                # with an explicit nonzero status before owner teardown.
                [Console]::Error.WriteLine('Failed source fixture: terminating the exact compiler job with status E0000003.')
                [Console]::Error.Flush()
                if (!$script:terminateJob.Invoke($script:jobHandle, [uint32]3758096387)) {
                    [Environment]::FailFast('Failure TerminateJobObject failed; preserving exact job/watchdog through controller teardown.')
                }
                [Environment]::FailFast('Failure TerminateJobObject returned without terminating this exact controller; preserving job custody.')
            }
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

if ($success -and $BuildOnly) {
    $manifest = @('compiler_sha256=' + (Get-FileHash -LiteralPath $compiler -Algorithm SHA256).Hash.ToLowerInvariant())
    $manifest += @($expected.Keys | Sort-Object | ForEach-Object { "$($expected[$_])  $_" })
    $manifest += @(Get-ChildItem -LiteralPath $buildRoot -File | Sort-Object Name | ForEach-Object { "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant())  build/$($_.Name)" })
    [IO.File]::WriteAllLines((Join-Path $run 'build-manifest.txt'), [string[]]$manifest, [Text.Encoding]::ASCII)
    [IO.File]::WriteAllText((Join-Path $run 'run-result.txt'), "BUILD_ONLY_PASS: exact job owner-only accounting, successful disposition and drained watchdog; native driver not launched.`r`n", [Text.Encoding]::ASCII)
    Write-Output "BUILD_ONLY_PASS: retained native binaries and original logs at $run; driver must be launched from an independent uncontained process."
}
