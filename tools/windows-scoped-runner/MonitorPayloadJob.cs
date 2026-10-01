// Monitor-owned payload process creation prerequisite. This class is not
// called by the current transport: its intake dispatcher only grants
// maintenance renewals, so it cannot establish the post-staging create and
// resume handshakes required below.
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
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] private static extern ulong GetTickCount64();

    private MonitorOwnedKernelHandle job, process, thread;
    private bool resumed, disposed;
    internal bool IsResumed { get { return resumed; } }

    private MonitorPayloadJob(MonitorOwnedKernelHandle ownedJob, MonitorOwnedKernelHandle ownedProcess, MonitorOwnedKernelHandle ownedThread)
    { job = ownedJob; process = ownedProcess; thread = ownedThread; }

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

            result=new MonitorPayloadJob(ownedJob,ownedProcess,ownedThread);
            ownedJob=ownedProcess=ownedThread=null;
            transferred=true;
        }
        catch(Exception error) { primaryFailure=error; }
        finally
        {
            // Attribute storage is always released, including failures after
            // process creation. SafeHandle remains the fallback owner if an
            // explicit close fails while this stack is unwinding.
            if(!transferred) protocol.SignalClientExited((long)GetTickCount64());
            IntPtr exactRoot=Owned(ownedProcess) ? ownedProcess.ExactValue : created.Process;
            if(!transferred && exactRoot!=IntPtr.Zero && Owned(ownedJob))
            {
                try { if(!TerminateJobObject(ownedJob.ExactValue,126)) cleanupFailure=Error("TerminateJobObject(setup unwind)"); }
                catch(Exception error) { cleanupFailure=error; }
                // Exact process-handle termination covers an unexpected
                // membership verification failure without guessing a PID.
                try { if(!TerminateProcess(exactRoot,126) && cleanupFailure==null) cleanupFailure=Error("TerminateProcess(exact setup handle)"); }
                catch(Exception error) { if(cleanupFailure==null) cleanupFailure=error; }
                try
                {
                    uint wait=WaitForSingleObject(exactRoot,CleanupWaitMs);
                    if(wait!=WAIT_OBJECT_0 && cleanupFailure==null)
                        cleanupFailure=wait==WAIT_TIMEOUT ? new TimeoutException("payload process did not signal during setup unwind") : Error("WaitForSingleObject(setup unwind)");
                    if(wait==WAIT_OBJECT_0) { /* root observation is recorded; preserve earlier cleanup diagnostics */ }
                }
                catch(Exception error) { if(cleanupFailure==null) cleanupFailure=error; }
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
                try { WaitForJobEmpty(ownedJob.ExactValue,"setup unwind"); }
                catch(Exception error) { if(cleanupFailure==null) cleanupFailure=error; }
            }
            if(attributes!=IntPtr.Zero)
            {
                if(attributesInitialized) try { DeleteProcThreadAttributeList(attributes); } catch(Exception error) { if(cleanupFailure==null) cleanupFailure=error; }
                try { Marshal.FreeHGlobal(attributes); } catch(Exception error) { if(cleanupFailure==null) cleanupFailure=error; }
            }
            if(jobArray!=IntPtr.Zero) try { Marshal.FreeHGlobal(jobArray); } catch(Exception error) { if(cleanupFailure==null) cleanupFailure=error; }
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
                Exception gateCleanupFailure=null;
                try { Dispose(); } catch(Exception error) { gateCleanupFailure=error; }
                if(gateCleanupFailure!=null) throw new AggregateException("resume gate failed and exact job cleanup is incomplete",gateFailure,gateCleanupFailure);
                throw gateFailure;
            }
            if(!invoked) throw new InvalidOperationException("fresh monitor resume challenge is unavailable");
            Exception cleanupFailure=null;
            try { Dispose(); } catch(Exception error) { cleanupFailure=error; }
            if(operationFailure!=null && cleanupFailure!=null) throw new AggregateException("resume failed and exact job cleanup is incomplete",operationFailure,cleanupFailure);
            if(operationFailure!=null) throw operationFailure;
            if(cleanupFailure!=null) throw cleanupFailure;
            throw new InvalidOperationException("resume transition was stopped; exact job termination was requested");
        }
    }

    // Exceptional owner loss closes the sole kill-on-close job handle. This
    // is kernel termination fallback only; it is not an emptiness proof or a
    // runtime-removal authorization.
    public void Dispose()
    {
        lock(this)
        {
            if(disposed) return;
            Exception failure=null;
            if(Owned(job))
            {
                if(!TerminateJobObject(job.ExactValue,125)) throw new IOException("exact payload job termination failed; job handle retained",Error("TerminateJobObject(payload stop)"));
                if(Owned(process))
                {
                    uint wait=WaitForSingleObject(process.ExactValue,CleanupWaitMs);
                    if(wait!=WAIT_OBJECT_0)
                        throw wait==WAIT_TIMEOUT ? new TimeoutException("exact payload process did not signal; job and process handles retained") :
                            new IOException("exact payload process wait failed; handles retained",Error("WaitForSingleObject(payload stop)"));
                }
                CloseOwned(ref thread,ref failure);
                CloseOwned(ref process,ref failure);
                if(failure!=null) throw new IOException("payload signaled but an exact process/thread handle did not close; job retained",failure);
                try { WaitForJobEmpty(job.ExactValue,"payload stop"); }
                catch(Exception error) { throw new IOException("exact job did not prove empty; job handle retained",error); }
                CloseOwned(ref job,ref failure);
                if(failure!=null) throw new IOException("empty payload job handle did not close; SafeHandle retains exact ownership",failure);
            }
            else { CloseOwned(ref thread,ref failure); CloseOwned(ref process,ref failure); if(failure!=null) throw new IOException("exact payload handles failed to close",failure); }
            disposed=true;
        }
    }

    private static void WaitForJobEmpty(IntPtr exactJob,string context)
    {
        ulong started=GetTickCount64();
        while(GetTickCount64()-started<CleanupWaitMs)
        {
            BasicAccounting accounting;
            Check(QueryInformationJobObject(exactJob,JobObjectBasicAccountingInformation,out accounting,
                (uint)Marshal.SizeOf(typeof(BasicAccounting)),IntPtr.Zero),"QueryInformationJobObject("+context+")");
            if(accounting.ActiveProcesses==0) return;
            Thread.Sleep(100);
        }
        throw new TimeoutException(context+": exact job remained nonempty after the fixed cleanup bound");
    }

    private static Exception Error(string operation) { return new Win32Exception(Marshal.GetLastWin32Error(),operation); }
    private static void Check(bool success,string operation) { if(!success) throw Error(operation); }
    private static bool Owned(MonitorOwnedKernelHandle handle) { return handle!=null && !handle.IsInvalid && !handle.IsClosed; }
    private static void CloseOwned(ref MonitorOwnedKernelHandle handle,ref Exception failure)
    {
        if(!Owned(handle)) { handle=null; return; }
        MonitorOwnedKernelHandle exactOwner=handle;
        try { Exception closeFailure; if(exactOwner.TryClose(out closeFailure)) handle=null; else if(failure==null) failure=closeFailure; }
        catch(Exception error) { if(failure==null) failure=error; }
    }
}
