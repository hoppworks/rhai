// Monitor-owned payload process creation and exact-handle lifetime owner.
// Native creation, resume, cleanup, and host transport behavior remain
// unverified until the authorized Windows acceptance gates run.
using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using Microsoft.Win32.SafeHandles;

// SafeHandle keeps ownership alive after owner-object loss. A job-handle
// finalization attempt terminates the exact job before closing the sole
// noninheritable handle, so abandoned owners still get kernel fallback.
internal sealed class MonitorOwnedKernelHandle : SafeHandleZeroOrMinusOneIsInvalid
{
    private readonly bool isJob;
    internal MonitorOwnedKernelHandle(bool job) : base(true) { isJob=job; }
    // The wrapper is allocated before the native API can return an owned
    // handle. Adoption only writes the handle field and allocates nothing.
    internal void Adopt(IntPtr value) { SetHandle(value); }
#if SCOPED_RUNNER_TESTING
    private readonly Func<IntPtr, bool> fixtureClose;
    private readonly Action<IntPtr> fixtureTerminate;
    internal MonitorOwnedKernelHandle(IntPtr value, bool job, Func<IntPtr, bool> close, Action<IntPtr> terminate) : base(true)
    { isJob=job; fixtureClose=close; fixtureTerminate=terminate; SetHandle(value); }
#endif
    internal MonitorOwnedKernelHandle(IntPtr value, bool job) : base(true) { isJob=job; SetHandle(value); }
    internal IntPtr ExactValue { get { return DangerousGetHandle(); } }

    internal bool TryClose(out Exception failure)
    {
        failure=null;
        bool added=false;
        try
        {
            DangerousAddRef(ref added);
            IntPtr exact=DangerousGetHandle();
            bool closed;
#if SCOPED_RUNNER_TESTING
            closed=fixtureClose==null ? CloseHandle(exact) : fixtureClose(exact);
#else
            closed=CloseHandle(exact);
#endif
            if(!closed) { failure=Error("CloseHandle(exact owned handle)"); return false; }
            SetHandleAsInvalid();
            return true;
        }
        catch(Exception error) { failure=error; return false; }
        finally { if(added) DangerousRelease(); }
    }

    protected override bool ReleaseHandle()
    {
        if(isJob)
        {
#if SCOPED_RUNNER_TESTING
            if(fixtureTerminate!=null) try { fixtureTerminate(handle); } catch { }
            else TerminateJobObject(handle,126);
#else
            TerminateJobObject(handle,126);
#endif
        }
#if SCOPED_RUNNER_TESTING
        if(fixtureClose!=null)
        {
            try { if(fixtureClose(handle)) return true; return fixtureClose(handle); }
            catch { return false; }
        }
#endif
        if(CloseHandle(handle)) return true;
        // A transient close failure gets one bounded retry; job termination
        // was already requested above and Windows closes handles on exit.
        return CloseHandle(handle);
    }

    private static bool CloseHandle(IntPtr value) { return NativeCloseHandle(value); }
    [DllImport("kernel32.dll", SetLastError=true, EntryPoint="CloseHandle")] private static extern bool NativeCloseHandle(IntPtr value);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool TerminateJobObject(IntPtr job, uint exitCode);
    private static Exception Error(string operation) { return new Win32Exception(Marshal.GetLastWin32Error(),operation); }
}

internal sealed class MonitorPayloadJob : IDisposable
{
    internal interface IClosureOperations
    {
        ulong Now();
        bool TerminateJob(IntPtr job);
        uint WaitForRoot(IntPtr process,uint milliseconds);
        bool ReadExitCode(IntPtr process,out uint exitCode);
        bool Close(string role,MonitorOwnedKernelHandle handle,out Exception failure);
        bool QueryActiveProcesses(IntPtr job,out uint activeProcesses);
        void Sleep(uint milliseconds);
        Exception Failure(string operation);
    }

    private sealed class NativeClosureOperations : IClosureOperations
    {
        public ulong Now() { return GetTickCount64(); }
        public bool TerminateJob(IntPtr job) { return MonitorPayloadJob.TerminateJobObject(job,125); }
        public uint WaitForRoot(IntPtr process,uint milliseconds) { return WaitForSingleObject(process,milliseconds); }
        public bool ReadExitCode(IntPtr process,out uint exitCode) { return GetExitCodeProcess(process,out exitCode); }
        public bool Close(string role,MonitorOwnedKernelHandle handle,out Exception failure) { return handle.TryClose(out failure); }
        public bool QueryActiveProcesses(IntPtr job,out uint activeProcesses)
        {
            BasicAccounting accounting;
            bool result=QueryInformationJobObject(job,JobObjectBasicAccountingInformation,out accounting,
                (uint)Marshal.SizeOf(typeof(BasicAccounting)),IntPtr.Zero);
            activeProcesses=result ? accounting.ActiveProcesses : 0;
            return result;
        }
        public void Sleep(uint milliseconds) { Thread.Sleep((int)milliseconds); }
        public Exception Failure(string operation) { return Error(operation); }
    }

#if SCOPED_RUNNER_TESTING
    internal sealed class ScriptedClosureOperations : IClosureOperations
    {
        internal readonly System.Collections.Generic.List<string> Events=new System.Collections.Generic.List<string>();
        internal readonly System.Collections.Generic.List<uint> RootWaitBudgets=new System.Collections.Generic.List<uint>();
        internal readonly System.Collections.Generic.List<ulong> QueryTimes=new System.Collections.Generic.List<ulong>();
        internal ulong Clock=1000;
        internal uint RootWaitResult=WAIT_OBJECT_0, RootExitCode=259, RootWaitElapsed;
        internal bool TerminationSucceeds=true, ExitReadSucceeds=true, QuerySucceeds=true;
        internal string CloseFailureRole;
        internal uint FinalJobCloseElapsed;
        internal uint[] ActiveCounts=new uint[] { 1,0 };
        private int queryIndex;

        public ulong Now() { return Clock; }
        public bool TerminateJob(IntPtr exactJob) { Events.Add("terminate-job"); return TerminationSucceeds; }
        public uint WaitForRoot(IntPtr exactProcess,uint milliseconds)
        { Events.Add("wait-root"); RootWaitBudgets.Add(milliseconds); Clock+=RootWaitElapsed; return RootWaitResult; }
        public bool ReadExitCode(IntPtr exactProcess,out uint exitCode)
        { Events.Add("read-exit-code"); exitCode=RootExitCode; return ExitReadSucceeds; }
        public bool Close(string role,MonitorOwnedKernelHandle handle,out Exception failure)
        {
            Events.Add("close-"+role);
            if(role=="job") Clock+=FinalJobCloseElapsed;
            if(String.Equals(role,CloseFailureRole,StringComparison.Ordinal))
            { failure=new IOException("scripted close failure: "+role); return false; }
            return handle.TryClose(out failure);
        }
        public bool QueryActiveProcesses(IntPtr exactJob,out uint activeProcesses)
        {
            Events.Add("query-job"); QueryTimes.Add(Clock);
            if(!QuerySucceeds) { activeProcesses=0; return false; }
            int index=queryIndex++;
            activeProcesses=ActiveCounts.Length==0 ? 1 : ActiveCounts[Math.Min(index,ActiveCounts.Length-1)];
            return true;
        }
        public void Sleep(uint milliseconds) { Events.Add("sleep-"+milliseconds); Clock+=milliseconds; }
        public Exception Failure(string operation) { return new IOException("scripted operation failure: "+operation); }
    }
#endif
    private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    private const uint CREATE_SUSPENDED = 0x00000004;
    private const uint CREATE_UNICODE_ENVIRONMENT = 0x00000400;
    private const uint EXTENDED_STARTUPINFO_PRESENT = 0x00080000;
    private const int PROC_THREAD_ATTRIBUTE_JOB_LIST = 0x0002000D;
    private const int JobObjectExtendedLimitInformation = 9;
    private const int JobObjectBasicAccountingInformation = 1;
    private const int ERROR_INSUFFICIENT_BUFFER = 122;
    private const uint WAIT_OBJECT_0 = 0;
    private const uint WAIT_TIMEOUT = 258;
    private const uint CleanupWaitMs = 30000;

    [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes
    { internal int Length; internal IntPtr SecurityDescriptor; internal int InheritHandle; }
    [StructLayout(LayoutKind.Sequential)] private struct StartupInfo
    {
        internal int cb; internal string Reserved, Desktop, Title; internal int X, Y, XSize, YSize, XCountChars, YCountChars, FillAttribute;
        internal int Flags; internal short ShowWindow, Reserved2; internal IntPtr Reserved2Pointer, StdInput, StdOutput, StdError;
    }
    [StructLayout(LayoutKind.Sequential)] private struct StartupInfoEx { internal StartupInfo StartupInfo; internal IntPtr AttributeList; }
    [StructLayout(LayoutKind.Sequential)] private struct ProcessInformation { internal IntPtr Process, Thread; internal uint ProcessId, ThreadId; }
    [StructLayout(LayoutKind.Sequential)] private struct BasicAccounting
    {
        internal long TotalUserTime, TotalKernelTime, ThisPeriodTotalUserTime, ThisPeriodTotalKernelTime;
        internal uint TotalPageFaultCount, TotalProcesses, ActiveProcesses, TotalTerminatedProcesses;
    }
    [StructLayout(LayoutKind.Sequential)] private struct BasicLimitInformation
    {
        internal long PerProcessUserTimeLimit, PerJobUserTimeLimit; internal uint LimitFlags;
        internal UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize; internal uint ActiveProcessLimit;
        internal UIntPtr Affinity; internal uint PriorityClass, SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)] private struct IoCounters
    { internal ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
    [StructLayout(LayoutKind.Sequential)] private struct JobExtendedLimitInformation
    { internal BasicLimitInformation Basic; internal IoCounters Io; internal UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed; }

    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] private static extern IntPtr CreateJobObjectW(ref SecurityAttributes attributes, string name);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool SetInformationJobObject(IntPtr job, int infoClass, ref JobExtendedLimitInformation info, uint size);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool InitializeProcThreadAttributeList(IntPtr list, int count, uint flags, ref IntPtr size);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool UpdateProcThreadAttribute(IntPtr list, uint flags, IntPtr attribute, IntPtr value, UIntPtr size, IntPtr previous, IntPtr returned);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern void DeleteProcThreadAttributeList(IntPtr list);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true, EntryPoint="CreateProcessW")]
    private static extern bool CreateProcessW(string app, StringBuilder command, IntPtr processAttributes, IntPtr threadAttributes,
        bool inheritHandles, uint flags, IntPtr environment, string directory, ref StartupInfoEx startup, out ProcessInformation process);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool IsProcessInJob(IntPtr process, IntPtr job, out bool result);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool TerminateJobObject(IntPtr job, uint exitCode);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool TerminateProcess(IntPtr process, uint exitCode);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool QueryInformationJobObject(IntPtr job, int infoClass, out BasicAccounting info, uint size, IntPtr returned);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool GetExitCodeProcess(IntPtr process, out uint exitCode);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] private static extern ulong GetTickCount64();

    internal sealed class ClosureReceipt
    {
        internal readonly WindowsCustodyBackend.RuntimeAllocation Allocation;
        internal readonly WindowsCustodyBackend.FileIdentity RuntimeIdentity;
        private ClosureReceipt(WindowsCustodyBackend.RuntimeAllocation allocation, WindowsCustodyBackend.FileIdentity identity)
        { Allocation=allocation; RuntimeIdentity=identity; }
        internal static ClosureReceipt FromVerifiedOwner(MonitorPayloadJob owner)
        {
            if(owner==null || !owner.closureVerified || owner.allocation==null || owner.allocation.RuntimeIdentity==null)
                throw new InvalidOperationException("only an owner with verified exact-job closure can mint a receipt");
            return new ClosureReceipt(owner.allocation,owner.allocation.RuntimeIdentity);
        }
    }

    // Production fills this exclusively from native return values. Keeping the
    // conjunction in one helper makes failure ownership rules fixture-checkable
    // without a native process or caller-supplied proof constructor.
    internal sealed class ClosureFacts
    {
        internal bool TerminationSucceeded, RootSignaled, ThreadClosed, ProcessClosed,
            RootExitCodeCaptured, JobEmpty, JobHandleClosed, WithinDeadline;
        internal bool CanMint
        { get { return TerminationSucceeded && RootSignaled && RootExitCodeCaptured && ThreadClosed && ProcessClosed && JobEmpty && JobHandleClosed && WithinDeadline; } }
    }

    internal static bool TryCaptureSignaledExitCode(bool signaled,uint value,out uint exitCode)
    {
        if(!signaled) { exitCode=0; return false; }
        exitCode=value; return true;
    }

    private readonly WindowsCustodyBackend.RuntimeAllocation allocation;
    private readonly IClosureOperations closureOperations;
    private MonitorOwnedKernelHandle job, process, thread;
    private bool resumed, disposed;
    private Exception cleanupFailure;
    private bool rootExitObserved;
    private uint rootExitCode;
    private ClosureReceipt closureReceipt;
    private bool closureVerified;
    internal bool IsResumed { get { return resumed; } }

    private MonitorPayloadJob(WindowsCustodyBackend.RuntimeAllocation owner, MonitorOwnedKernelHandle ownedJob, MonitorOwnedKernelHandle ownedProcess, MonitorOwnedKernelHandle ownedThread, IClosureOperations operations=null)
    { allocation=owner; job = ownedJob; process = ownedProcess; thread = ownedThread; closureOperations=operations ?? new NativeClosureOperations(); }

#if SCOPED_RUNNER_TESTING
    internal static MonitorPayloadJob ForClosureFixture(WindowsCustodyBackend.RuntimeAllocation owner,ScriptedClosureOperations operations)
    {
        if(operations==null) throw new ArgumentNullException("operations");
        Func<IntPtr,bool> close=delegate { return true; };
        Action<IntPtr> terminate=delegate { };
        return new MonitorPayloadJob(owner,
            new MonitorOwnedKernelHandle(new IntPtr(0x501),true,close,terminate),
            new MonitorOwnedKernelHandle(new IntPtr(0x502),false,close,terminate),
            new MonitorOwnedKernelHandle(new IntPtr(0x503),false,close,terminate),operations);
    }
#endif

    internal uint? RootExitCode { get { return rootExitObserved ? (uint?)rootExitCode : null; } }
    internal ClosureReceipt VerifiedClosure { get { return closureReceipt; } }
    internal LeaseMonitor.ExactJobClosureProof ClosureAuthorization
    { get { return closureReceipt==null ? null : LeaseMonitor.ExactJobClosureProof.FromVerifiedClosure(closureReceipt); } }

    // Polling is owner-worker-only. Exit status is captured only after the
    // exact process handle reports signaled; the DWORD value is retained as
    // data and is never used to infer whether the process has exited.
    internal bool ObserveRootExit()
    {
        lock(this)
        {
            if(rootExitObserved) return true;
            if(!Owned(process)) throw new InvalidOperationException("exact payload process handle is unavailable");
            uint wait=closureOperations.WaitForRoot(process.ExactValue,0);
            if(wait==WAIT_TIMEOUT) return false;
            if(wait!=WAIT_OBJECT_0) throw closureOperations.Failure("WaitForSingleObject(poll exact payload root)");
            uint code;
            if(!closureOperations.ReadExitCode(process.ExactValue,out code)) throw closureOperations.Failure("GetExitCodeProcess(signaled exact payload root)");
            if(!TryCaptureSignaledExitCode(true,code,out rootExitCode)) throw new InvalidOperationException("root exit status requires a signaled exact process handle");
            rootExitObserved=true; return true;
        }
    }

    // The protocol object is the only source of transition authority. Staging
    // identity/pins must already be complete before this method is called.
    internal static MonitorPayloadJob CreateSuspended(WindowsCustodyBackend.RuntimeAllocation allocation,
        LaunchSpecification specification, LeaseMonitor.Protocol protocol)
    {
        if (allocation == null || specification == null || protocol == null || !allocation.IsStaged ||
            allocation.StagedExecutableHandle == null || allocation.StagedExecutableHandle.IsInvalid ||
            allocation.StagedExecutableHandle.IsClosed ||
            !String.Equals(allocation.StagedExecutableRelativePath, specification.RelativeExecutable, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("staged executable identity and pins are unavailable");
        // Allocate every final owner before native creation can produce a raw
        // handle. The wrappers remain invalid until allocation-free adoption.
        MonitorOwnedKernelHandle ownedJob=new MonitorOwnedKernelHandle(true);
        MonitorOwnedKernelHandle ownedProcess=new MonitorOwnedKernelHandle(false);
        MonitorOwnedKernelHandle ownedThread=new MonitorOwnedKernelHandle(false);
        long createAt=(long)GetTickCount64();
        if (!protocol.AuthorizeCreate(createAt)) throw new InvalidOperationException("fresh monitor create challenge is unavailable");
        IntPtr attributes=IntPtr.Zero, jobArray=IntPtr.Zero;
        bool attributesInitialized=false;
        ProcessInformation created=new ProcessInformation();
        bool transferred=false;
        MonitorPayloadJob result=null;
        ulong setupCleanupDeadline=0;
        Exception primaryFailure=null, cleanupFailure=null;
        try
        {
            var security = new SecurityAttributes { Length=Marshal.SizeOf(typeof(SecurityAttributes)), InheritHandle=0 };
            IntPtr rawJob=CreateJobObjectW(ref security, null);
            if (rawJob==IntPtr.Zero) throw Error("CreateJobObjectW(private unnamed job)");
            ownedJob.Adopt(rawJob);
            var limits=new JobExtendedLimitInformation { Basic=new BasicLimitInformation { LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE } };
            Check(SetInformationJobObject(ownedJob.ExactValue, JobObjectExtendedLimitInformation, ref limits,
                (uint)Marshal.SizeOf(typeof(JobExtendedLimitInformation))), "SetInformationJobObject(kill on last close)");

            IntPtr size=IntPtr.Zero;
            InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref size);
            int sizingError=Marshal.GetLastWin32Error();
            if(size==IntPtr.Zero || sizingError!=ERROR_INSUFFICIENT_BUFFER)
                throw new Win32Exception(sizingError,"InitializeProcThreadAttributeList(size)");
            attributes=Marshal.AllocHGlobal(size);
            jobArray=Marshal.AllocHGlobal(IntPtr.Size);
            if(attributes==IntPtr.Zero || jobArray==IntPtr.Zero) throw new OutOfMemoryException("job-list attribute allocation failed");
            Marshal.WriteIntPtr(jobArray,ownedJob.ExactValue);
            Check(InitializeProcThreadAttributeList(attributes,1,0,ref size),"InitializeProcThreadAttributeList");
            attributesInitialized=true;
            Check(UpdateProcThreadAttribute(attributes,0,new IntPtr(PROC_THREAD_ATTRIBUTE_JOB_LIST),jobArray,
                new UIntPtr((uint)IntPtr.Size),IntPtr.Zero,IntPtr.Zero),"UpdateProcThreadAttribute(JOB_LIST)");

            string executable=Path.Combine(allocation.RuntimePath,"source",specification.RelativeExecutable);
            string command=specification.BuildQuotedCommandLine(executable);
            var startup=new StartupInfoEx { StartupInfo=new StartupInfo { cb=Marshal.SizeOf(typeof(StartupInfoEx)) }, AttributeList=attributes };
            bool createdOk=CreateProcessW(executable,new StringBuilder(command),IntPtr.Zero,IntPtr.Zero,false,
                EXTENDED_STARTUPINFO_PRESENT|CREATE_SUSPENDED|CREATE_UNICODE_ENVIRONMENT,IntPtr.Zero,
                allocation.RuntimePath,ref startup,out created);
            int createError=createdOk ? 0 : Marshal.GetLastWin32Error();
            if(created.Process!=IntPtr.Zero) { ownedProcess.Adopt(created.Process); created.Process=IntPtr.Zero; }
            if(created.Thread!=IntPtr.Zero) { ownedThread.Adopt(created.Thread); created.Thread=IntPtr.Zero; }
            if(!createdOk) throw new Win32Exception(createError,"CreateProcessW(CREATE_SUSPENDED, JOB_LIST)");
            if(!Owned(ownedProcess) || !Owned(ownedThread)) throw new InvalidOperationException("CreateProcessW returned incomplete exact handles");
            bool inOwnedJob;
            Check(IsProcessInJob(ownedProcess.ExactValue,ownedJob.ExactValue,out inOwnedJob),"IsProcessInJob(payload, monitor-owned job)");
            if(!inOwnedJob) throw new InvalidOperationException("payload is not in the exact monitor-owned job");
            if(!protocol.MarkSuspended((long)GetTickCount64())) throw new InvalidOperationException("monitor protocol rejected suspended payload transition");

            result=new MonitorPayloadJob(allocation,ownedJob,ownedProcess,ownedThread);
            ownedJob=ownedProcess=ownedThread=null;
            transferred=true;
        }
        catch(Exception error) { primaryFailure=error; }
        finally
        {
            setupCleanupDeadline=GetTickCount64()+CleanupWaitMs;
            // Attribute storage is always released, including failures after
            // process creation. SafeHandle remains the fallback owner if an
            // explicit close fails while this stack is unwinding.
            if(!transferred)
                try { protocol.SignalClientExited((long)GetTickCount64()); }
                catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
            IntPtr exactRoot=Owned(ownedProcess) ? ownedProcess.ExactValue : created.Process;
            if(!transferred && exactRoot!=IntPtr.Zero && Owned(ownedJob))
            {
                try { if(!TerminateJobObject(ownedJob.ExactValue,126)) RecordFailure(ref cleanupFailure,Error("TerminateJobObject(setup unwind)")); }
                catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
                // Exact process-handle termination covers an unexpected
                // membership verification failure without guessing a PID.
                try { if(!TerminateProcess(exactRoot,126)) RecordFailure(ref cleanupFailure,Error("TerminateProcess(exact setup handle)")); }
                catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
                try
                {
                    uint wait=WaitForSingleObject(exactRoot,Remaining(setupCleanupDeadline));
                    if(wait!=WAIT_OBJECT_0)
                        RecordFailure(ref cleanupFailure,wait==WAIT_TIMEOUT ? new TimeoutException("payload process did not signal during setup unwind") : Error("WaitForSingleObject(setup unwind)"));
                    if(wait==WAIT_OBJECT_0 && GetTickCount64()>setupCleanupDeadline)
                        RecordFailure(ref cleanupFailure,new TimeoutException("payload signaled after setup unwind deadline"));
                    if(wait==WAIT_OBJECT_0) { /* root observation is recorded; preserve earlier cleanup diagnostics */ }
                }
                catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
            }
            if(!transferred && created.Process!=IntPtr.Zero)
            {
                ownedProcess.Adopt(created.Process);
                created.Process=IntPtr.Zero;
            }
            if(!transferred && created.Thread!=IntPtr.Zero)
            {
                ownedThread.Adopt(created.Thread);
                created.Thread=IntPtr.Zero;
            }
            CloseOwned(ref ownedThread,ref cleanupFailure);
            CloseOwned(ref ownedProcess,ref cleanupFailure);
            if(!transferred && Owned(ownedJob) && !Owned(ownedProcess))
            {
                try { WaitForJobEmpty(new NativeClosureOperations(),ownedJob.ExactValue,"setup unwind",setupCleanupDeadline); }
                catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
            }
            if(attributes!=IntPtr.Zero)
            {
                if(attributesInitialized) try { DeleteProcThreadAttributeList(attributes); } catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
                try { Marshal.FreeHGlobal(attributes); } catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
            }
            if(jobArray!=IntPtr.Zero) try { Marshal.FreeHGlobal(jobArray); } catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
            CloseOwned(ref ownedJob,ref cleanupFailure);
        }
        if(primaryFailure!=null && cleanupFailure!=null) throw new AggregateException("payload creation failed and cleanup is incomplete; SafeHandle retains unresolved exact ownership for finalizer fallback",primaryFailure,cleanupFailure);
        if(primaryFailure!=null) throw primaryFailure;
        if(cleanupFailure!=null) throw new IOException("payload setup cleanup is incomplete; SafeHandle retains unresolved exact ownership for finalizer fallback",cleanupFailure);
        return result;
    }

    // Resume remains gated on a distinct fresh challenge in Suspended state.
    // The current transport cannot issue this authority, so the public monitor
    // has no path to execute this method yet.
    internal void ResumeAfterHostChallenge(LeaseMonitor.Protocol protocol)
    {
        lock(this)
        {
            if(disposed || resumed || protocol==null || !Owned(job) || !Owned(process) || !Owned(thread))
                throw new InvalidOperationException("payload handles are unavailable or already resumed");
            Exception operationFailure=null;
            Exception gateFailure=null;
            bool invoked=false;
            bool running=false;
            try { running=protocol.TryResumeAtomically(delegate { return (long)GetTickCount64(); },delegate
            {
                invoked=true;
                try
                {
                    uint previous=ResumeThread(thread.ExactValue);
                    if(previous==0xffffffff) { operationFailure=Error("ResumeThread(payload)"); return false; }
                    if(previous!=1) { operationFailure=new InvalidOperationException("unexpected prior primary-thread suspension count: "+previous); return false; }
                    return true;
                }
                catch(Exception error) { operationFailure=error; return false; }
            }); }
            catch(Exception error) { gateFailure=error; }
            if(running) { resumed=true; return; }
            if(gateFailure!=null)
            {
                throw gateFailure;
            }
            if(!invoked) throw new InvalidOperationException("fresh monitor resume challenge is unavailable");
            if(operationFailure!=null) throw operationFailure;
            throw new InvalidOperationException("resume transition was stopped; exact job termination was requested");
        }
    }

    // Exceptional owner loss closes the sole kill-on-close job handle. This
    // is kernel termination fallback only; it is not an emptiness proof or a
    // runtime-removal authorization.
    public void Dispose()
    {
        CloseAndVerify();
    }

    // The worker calls this once for either ordinary root completion or
    // stop/deadline. Every phase consumes the same absolute monotonic bound.
    // Cleanup diagnostics accumulate; no individual failure skips later safe
    // close attempts, and no receipt exists unless every fact is confirmed.
    internal ClosureReceipt CloseAndVerify()
    {
        lock(this)
        {
            if(disposed)
            {
                if(cleanupFailure!=null) throw new IOException("exact-job cleanup previously failed; no new cleanup budget was allocated",cleanupFailure);
                return closureReceipt;
            }
            ulong deadline=closureOperations.Now()+CleanupWaitMs;
            var failures=new System.Collections.Generic.List<Exception>();
            var facts=new ClosureFacts { WithinDeadline=true };
            if(Owned(job))
            {
                try
                {
                    facts.TerminationSucceeded=closureOperations.TerminateJob(job.ExactValue);
                    if(!facts.TerminationSucceeded) failures.Add(closureOperations.Failure("TerminateJobObject(exact payload closure)"));
                }
                catch(Exception error) { failures.Add(error); }
                if(Owned(process))
                {
                    try
                    {
                        uint remaining=Remaining(closureOperations.Now(),deadline);
                        uint wait=closureOperations.WaitForRoot(process.ExactValue,remaining);
                        if(wait==WAIT_OBJECT_0)
                        {
                            if(closureOperations.Now()>deadline) throw new TimeoutException("exact root signaled after the shared cleanup deadline");
                            facts.RootSignaled=true;
                            uint code;
                            if(!closureOperations.ReadExitCode(process.ExactValue,out code)) throw closureOperations.Failure("GetExitCodeProcess(signaled exact payload root during closure)");
                            if(!TryCaptureSignaledExitCode(true,code,out rootExitCode)) throw new InvalidOperationException("root exit status requires a signaled exact process handle");
                            rootExitObserved=true; facts.RootExitCodeCaptured=true;
                        }
                        else if(wait==WAIT_TIMEOUT) failures.Add(new TimeoutException("exact root did not signal before the shared cleanup deadline"));
                        else failures.Add(closureOperations.Failure("WaitForSingleObject(exact payload root closure)"));
                    }
                    catch(Exception error) { failures.Add(error); }
                }
                else { facts.RootSignaled=rootExitObserved; facts.RootExitCodeCaptured=rootExitObserved; }

                Exception threadClose=null, processClose=null;
                CloseOwned(closureOperations,"thread",ref thread,ref threadClose);
                CloseOwned(closureOperations,"process",ref process,ref processClose);
                if(threadClose!=null) failures.Add(threadClose);
                if(processClose!=null) failures.Add(processClose);
                facts.ThreadClosed=thread==null || thread.IsClosed;
                facts.ProcessClosed=process==null || process.IsClosed;
                if(closureOperations.Now()>deadline) { facts.WithinDeadline=false; failures.Add(new TimeoutException("exact process/thread handle closure completed after the shared cleanup deadline")); }

                try { WaitForJobEmpty(closureOperations,job.ExactValue,"payload closure",deadline); facts.JobEmpty=true; }
                catch(Exception error) { failures.Add(error); if(closureOperations.Now()>deadline) facts.WithinDeadline=false; }

                Exception jobClose=null;
                CloseOwned(closureOperations,"job",ref job,ref jobClose);
                if(jobClose!=null) failures.Add(jobClose);
                facts.JobHandleClosed=job==null || job.IsClosed;
                if(closureOperations.Now()>deadline) { facts.WithinDeadline=false; failures.Add(new TimeoutException("exact job handle closure completed after the shared cleanup deadline")); }
                if(facts.CanMint && failures.Count==0)
                {
                    if(allocation==null || allocation.RuntimeIdentity==null)
                        failures.Add(new InvalidOperationException("allocation identity unavailable for exact-job closure receipt"));
                    else { closureVerified=true; closureReceipt=ClosureReceipt.FromVerifiedOwner(this); }
                }
            }
            else
            {
                failures.Add(new InvalidOperationException("exact job handle unavailable; closure cannot be proven"));
                Exception threadClose=null,processClose=null;
                CloseOwned(closureOperations,"thread",ref thread,ref threadClose); CloseOwned(closureOperations,"process",ref process,ref processClose);
                if(threadClose!=null) failures.Add(threadClose);
                if(processClose!=null) failures.Add(processClose);
            }
            disposed=true;
            if(failures.Count!=0)
            {
                cleanupFailure=new AggregateException(failures);
                throw new IOException("exact-job cleanup incomplete; runtime removal remains unauthorized and exact ownership may remain unresolved",cleanupFailure);
            }
            return closureReceipt;
        }
    }

    private static uint Remaining(ulong deadline) { return Remaining(GetTickCount64(),deadline); }
    private static uint Remaining(ulong now,ulong deadline)
    {
        if(now>=deadline) return 0;
        ulong remaining=deadline-now;
        return remaining>UInt32.MaxValue ? UInt32.MaxValue : (uint)remaining;
    }

    private static void WaitForJobEmpty(IClosureOperations operations,IntPtr exactJob,string context,ulong deadline)
    {
        for(;;)
        {
            if(Remaining(operations.Now(),deadline)==0) throw new TimeoutException(context+": no cleanup budget remained for exact-job accounting");
            uint active;
            if(!operations.QueryActiveProcesses(exactJob,out active)) throw operations.Failure("QueryInformationJobObject("+context+")");
            if(operations.Now()>deadline) throw new TimeoutException(context+": exact-job accounting returned after the shared cleanup deadline");
            if(active==0) return;
            uint remaining=Remaining(operations.Now(),deadline);
            if(remaining==0) throw new TimeoutException(context+": exact job remained nonempty at the shared cleanup deadline");
            operations.Sleep(remaining<100 ? remaining : 100);
        }
    }

    private static Exception Error(string operation) { return new Win32Exception(Marshal.GetLastWin32Error(),operation); }
    private static void RecordFailure(ref Exception current,Exception next)
    {
        if(next==null) return;
        current=current==null ? next : new AggregateException(current,next);
    }
    private static void Check(bool success,string operation) { if(!success) throw Error(operation); }
    private static bool Owned(MonitorOwnedKernelHandle handle) { return handle!=null && !handle.IsInvalid && !handle.IsClosed; }
    private static void CloseOwned(ref MonitorOwnedKernelHandle handle,ref Exception failure)
    {
        if(!Owned(handle)) { handle=null; return; }
        MonitorOwnedKernelHandle exactOwner=handle;
        try { Exception closeFailure; if(exactOwner.TryClose(out closeFailure)) handle=null; else RecordFailure(ref failure,closeFailure); }
        catch(Exception error) { RecordFailure(ref failure,error); }
    }
    private static void CloseOwned(IClosureOperations operations,string role,ref MonitorOwnedKernelHandle handle,ref Exception failure)
    {
        if(!Owned(handle)) { handle=null; return; }
        MonitorOwnedKernelHandle exactOwner=handle;
        try { Exception closeFailure; if(operations.Close(role,exactOwner,out closeFailure)) handle=null; else RecordFailure(ref failure,closeFailure); }
        catch(Exception error) { RecordFailure(ref failure,error); }
    }
}
