param(
    [Parameter(Mandatory = $true)] [string] $SourceRoot,
    [Parameter(Mandatory = $true)] [string] $RunRoot
)

$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'Use the already-installed PowerShell 7 host; Windows PowerShell 5.1 is outside this harness contract.'
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
if (Test-Path -LiteralPath $run) { throw "RunRoot already exists; preserve and inspect it: $run" }
$drive = [IO.DriveInfo]::new('C:')
if ($drive.AvailableFreeSpace -lt 2GB) { throw 'At least 2 GiB free on C: is required by the fixed fixture storage plan' }

$expectedRoot = Join-Path $run 'input'
$buildRoot = Join-Path $run 'build'
$logRoot = Join-Path $run 'logs'
$tempRoot = Join-Path $run 'temp'
New-Item -ItemType Directory -Path $run | Out-Null
foreach ($directory in @($expectedRoot, $buildRoot, $logRoot, $tempRoot)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}
$env:TEMP = $tempRoot
$env:TMP = $tempRoot

# Bind kernel32 exports through runtime-generated delegates. This emits managed
# metadata only; no C# compiler or other child is started before ownership.
$script:delegateAssembly = [Reflection.Emit.AssemblyBuilder]::DefineDynamicAssembly(
    [Reflection.AssemblyName]::new('RhaiFixtureNativeBindings'), [Reflection.Emit.AssemblyBuilderAccess]::Run)
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
$script:kernel32 = [Diagnostics.Process]::GetCurrentProcess().Modules |
    Where-Object { $_.ModuleName -ieq 'kernel32.dll' } | Select-Object -First 1 -ExpandProperty BaseAddress
if ($script:kernel32 -eq [IntPtr]::Zero) { throw 'kernel32 module handle was not available in the current process.' }
function Get-KernelDelegate([string] $Export, [Type] $DelegateType) {
    $address = [Runtime.InteropServices.NativeLibrary]::GetExport($script:kernel32, $Export)
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
finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($script:jobInfo) }
$currentProcess = [Diagnostics.Process]::GetCurrentProcess()
if (!$script:assignJob.Invoke($script:jobHandle, $currentProcess.Handle)) {
    $failure = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    [void]$script:closeHandle.Invoke($script:jobHandle)
    $script:jobHandle = [IntPtr]::Zero
    throw "AssignProcessToJobObject(current PowerShell process) failed before any child was launched: $failure"
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
$timerState[2] = [uint32]0xE0000002
$watchdogDelegate = $script:wallWatchdogType.GetMethod('Fire').CreateDelegate([Threading.TimerCallback])
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
        [void]$script:terminateJob.Invoke($script:jobHandle, 0xE0000001)
        [void]$process.WaitForExit(5000)
        throw "$Name exceeded its bounded timeout; inherited job was terminated"
    }
    $process.Refresh()
    if ($process.ExitCode -ne 0) { throw "$Name exited $($process.ExitCode); inspect $stdout and $stderr" }
    Write-Output "PASS $Name"
}

$success = $false
try {
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
finally {
    try {
      if ($script:jobHandle -ne [IntPtr]::Zero) {
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
        else {
            # Failure closes the only job handle while KILL_ON_JOB_CLOSE remains
            # set. If explicit close fails, retain the exact value until this
            # one-shot -File host exits and the OS closes its handles.
            if ($script:closeHandle.Invoke($script:jobHandle)) { $script:jobHandle = [IntPtr]::Zero }
            else { Write-Error "CloseHandle(failing fixture job) failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error()); OS process-exit closure remains outstanding." }
        }
        if ($success) {
            if ($script:closeHandle.Invoke($script:jobHandle)) { $script:jobHandle = [IntPtr]::Zero }
            else { throw "CloseHandle(successful fixture job) failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error()); exact handle remains owned until this host exits." }
        }
      }
    }
    finally {
        if ($script:wallTimer -ne $null) {
            $timerDrain = [Threading.ManualResetEvent]::new($false)
            try {
                [void]$script:wallTimer.Dispose($timerDrain)
                [void]$timerDrain.WaitOne()
            }
            finally { $timerDrain.Dispose(); $script:wallTimer = $null }
        }
        $currentProcess.Dispose()
    }
}
