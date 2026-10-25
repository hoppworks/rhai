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
    // One payload worker owns both overlapped named-pipe reads, their events,
    // OVERLAPPED storage, unmanaged buffers, and bounded log destinations. A
    // pending operation never releases any of these until a terminal result is
    // observed; cancellation submission alone is not completion.
    private sealed class PayloadOutputCapture : IDisposable
    {
        private const uint PIPE_ACCESS_INBOUND=0x00000001, FILE_FLAG_OVERLAPPED=0x40000000;
        private const uint PIPE_TYPE_BYTE=0, PIPE_READMODE_BYTE=0, PIPE_WAIT=0, PIPE_REJECT_REMOTE_CLIENTS=0x00000008;
        private const uint GENERIC_WRITE=0x40000000, OPEN_EXISTING=3, FILE_ATTRIBUTE_NORMAL=0x80;
        private const uint FILE_FLAG_FIRST_PIPE_INSTANCE=0x00080000;
        private const uint ERROR_IO_PENDING=997, ERROR_IO_INCOMPLETE=996, ERROR_PIPE_CONNECTED=535,
            ERROR_BROKEN_PIPE=109, ERROR_OPERATION_ABORTED=995, ERROR_NO_DATA=232;
        private const uint LogLimit=67108864;
        private const uint TRANSFER=65536;
        private const uint STARTF_USESTDHANDLES=0x00000100;

        [StructLayout(LayoutKind.Sequential)] private struct PipeSecurityAttributes
        { internal int Length; internal IntPtr SecurityDescriptor; internal int InheritHandle; }
        [StructLayout(LayoutKind.Sequential)] private struct Overlapped
        { internal UIntPtr Internal,InternalHigh; internal uint Offset,OffsetHigh; internal IntPtr Event; }
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] private static extern IntPtr CreateNamedPipeW(string name,uint openMode,uint pipeMode,uint maxInstances,uint outBuffer,uint inBuffer,uint timeout,ref PipeSecurityAttributes security);
        [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true,EntryPoint="CreateFileW")] private static extern IntPtr CreateFileRawW(string name,uint access,uint share,ref PipeSecurityAttributes security,uint creation,uint flags,IntPtr template);
        [DllImport("kernel32.dll",SetLastError=true)] private static extern bool ConnectNamedPipe(SafeFileHandle pipe,IntPtr overlapped);
        [DllImport("kernel32.dll",SetLastError=true)] private static extern bool ReadFile(SafeFileHandle file,IntPtr buffer,uint count,out uint read,IntPtr overlapped);
        [DllImport("kernel32.dll",SetLastError=true)] private static extern bool WriteFile(SafeFileHandle file,IntPtr buffer,uint count,out uint written,IntPtr overlapped);
        [DllImport("kernel32.dll",SetLastError=true)] private static extern bool GetOverlappedResult(SafeFileHandle file,IntPtr overlapped,out uint transferred,bool wait);
        [DllImport("kernel32.dll",SetLastError=true)] private static extern bool CancelIoEx(SafeFileHandle file,IntPtr overlapped);
        [DllImport("kernel32.dll",SetLastError=true)] private static extern IntPtr CreateEventW(IntPtr security,bool manual,bool initial,string name);
        [DllImport("kernel32.dll",SetLastError=true)] private static extern bool ResetEvent(IntPtr value);
        [DllImport("kernel32.dll",SetLastError=true)] private static extern bool CloseHandle(IntPtr value);
        [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr value);

        private sealed class Channel
        {
            internal SafeFileHandle server;
            internal IntPtr eventHandle,overlapped,buffer;
            internal SafeFileHandle log;
            internal bool connected,connectPending,readPending,eof,cancelRequested,terminal=true;
            internal uint logBytes;
            internal readonly string name;
            internal Channel(string value) { name=value; }
        }
        // Strong process-lifetime custody for unresolved kernel I/O. Entries
        // leave only after terminal completion and exact resource release.
        private sealed class PendingOwnerKeeper<T> where T:class
        {
            private readonly object gate=new object();
            private readonly System.Collections.Generic.List<T> owners=new System.Collections.Generic.List<T>();
            internal void Retain(T owner) { lock(gate) if(!owners.Contains(owner)) owners.Add(owner); }
            internal void Release(T owner) { lock(gate) owners.Remove(owner); }
            internal T[] Snapshot() { lock(gate) return owners.ToArray(); }
            internal int Count { get { lock(gate) return owners.Count; } }
        }
        private readonly WindowsCustodyBackend.RuntimeAllocation allocation;
        private readonly int ownerWorkerThreadId;
        private static readonly PendingOwnerKeeper<PayloadOutputCapture> pendingOwners=new PendingOwnerKeeper<PayloadOutputCapture>();
        private readonly Channel stdout,stderr;
        private readonly WindowsCustodyBackend.RuntimeAllocation.PayloadLogHandles logs;
        private readonly string pipePrefix;
        private bool disposed,limitExceeded,ioFailure,retainedForCompletion,cleanupRequested;
        private readonly ulong initialOwnerDeadline;
        private ulong cleanupDeadline;
        private Exception failure;

        internal IntPtr StdoutWriter { get; private set; }
        internal IntPtr StderrWriter { get; private set; }
        internal bool LimitExceeded { get { return limitExceeded; } }
        internal Exception Failure { get { return failure; } }
        internal bool CleanupRequested { get { return cleanupRequested; } }
        internal ulong CleanupDeadline { get { return cleanupDeadline; } }

        internal PayloadOutputCapture(WindowsCustodyBackend.RuntimeAllocation owner,ulong ownerDeadline)
        {
            allocation=owner ?? throw new ArgumentNullException("owner");
            if(ownerDeadline==0) throw new ArgumentOutOfRangeException("ownerDeadline");
            ownerWorkerThreadId=Thread.CurrentThread.ManagedThreadId;
            initialOwnerDeadline=ownerDeadline;
            logs=owner.CreatePayloadLogHandles();
            pipePrefix="\\\\.\\pipe\\Rhai-"+Guid.NewGuid().ToString("N");
            stdout=new Channel(pipePrefix+"-out"); stderr=new Channel(pipePrefix+"-err");
            IntPtr descriptor=WindowsCustodyBackend.CreateProtectedPipeSecurityDescriptor();
            try
            {
                var serverSa=new PipeSecurityAttributes { Length=Marshal.SizeOf(typeof(PipeSecurityAttributes)),SecurityDescriptor=descriptor,InheritHandle=0 };
                stdout.server=CreateServer(stdout.name,ref serverSa); stderr.server=CreateServer(stderr.name,ref serverSa);
                WindowsCustodyBackend.VerifyProtectedPipeDacl(stdout.server); WindowsCustodyBackend.VerifyProtectedPipeDacl(stderr.server);
                stdout.log=logs.StandardOutput; stderr.log=logs.StandardError;
                stdout.eventHandle=CreateEventW(IntPtr.Zero,true,false,null); stderr.eventHandle=CreateEventW(IntPtr.Zero,true,false,null);
                if(stdout.eventHandle==IntPtr.Zero || stderr.eventHandle==IntPtr.Zero) throw Error("CreateEvent(payload pipe OVERLAPPED)");
                stdout.overlapped=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Overlapped)));
                stderr.overlapped=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Overlapped)));
                stdout.buffer=Marshal.AllocHGlobal((int)TRANSFER); stderr.buffer=Marshal.AllocHGlobal((int)TRANSFER);
                BeginConnect(stdout); BeginConnect(stderr);
                var childSa=new PipeSecurityAttributes { Length=Marshal.SizeOf(typeof(PipeSecurityAttributes)),SecurityDescriptor=IntPtr.Zero,InheritHandle=1 };
                StdoutWriter=CreateFileRawW(stdout.name,GENERIC_WRITE,0,ref childSa,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,IntPtr.Zero);
                if(StdoutWriter==IntPtr.Zero || StdoutWriter==new IntPtr(-1)) throw Error("CreateFileW(inheritable payload stdout writer)");
                StderrWriter=CreateFileRawW(stderr.name,GENERIC_WRITE,0,ref childSa,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,IntPtr.Zero);
                if(StderrWriter==IntPtr.Zero || StderrWriter==new IntPtr(-1)) throw Error("CreateFileW(inheritable payload stderr writer)");
            }
            catch { DisposeUntil(ownerDeadline); throw; }
            finally { LocalFree(descriptor); }
        }

        private static SafeFileHandle CreateServer(string name,ref PipeSecurityAttributes security)
        {
            IntPtr value=CreateNamedPipeW(name,PIPE_ACCESS_INBOUND|FILE_FLAG_OVERLAPPED|FILE_FLAG_FIRST_PIPE_INSTANCE,
                PIPE_TYPE_BYTE|PIPE_READMODE_BYTE|PIPE_WAIT|PIPE_REJECT_REMOTE_CLIENTS,1,0,(uint)TRANSFER,0,ref security);
            if(value==new IntPtr(-1) || value==IntPtr.Zero) throw Error("CreateNamedPipeW(restricted payload output)");
            return new SafeFileHandle(value,true);
        }

        internal static void CreateInheritableNullInput(MonitorOwnedKernelHandle owner)
        {
            if(owner==null) throw new ArgumentNullException("owner");
            IntPtr descriptor=WindowsCustodyBackend.CreateProtectedPipeSecurityDescriptor();
            try
            {
                var security=new PipeSecurityAttributes { Length=Marshal.SizeOf(typeof(PipeSecurityAttributes)),SecurityDescriptor=descriptor,InheritHandle=1 };
                IntPtr input=CreateFileRawW("NUL",0x80000000,3,ref security,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,IntPtr.Zero);
                if(input==IntPtr.Zero || input==new IntPtr(-1)) throw Error("CreateFileW(inheritable NUL stdin)");
                owner.Adopt(input);
            }
            finally { LocalFree(descriptor); }
        }

        internal void CloseParentWriters()
        {
            if(StdoutWriter!=IntPtr.Zero) { if(!CloseHandle(StdoutWriter)) throw Error("CloseHandle(parent stdout writer)"); StdoutWriter=IntPtr.Zero; }
            if(StderrWriter!=IntPtr.Zero) { if(!CloseHandle(StderrWriter)) throw Error("CloseHandle(parent stderr writer)"); StderrWriter=IntPtr.Zero; }
        }

        private static void BeginConnect(Channel channel)
        {
            ResetEvent(channel.eventHandle);
            SetOverlapped(channel);
            if(ConnectNamedPipe(channel.server,channel.overlapped)) { channel.connected=true; channel.terminal=true; return; }
            int error=Marshal.GetLastWin32Error();
            if(error==ERROR_IO_PENDING) { channel.connectPending=true; channel.terminal=false; return; }
            if(error==ERROR_PIPE_CONNECTED) { channel.connected=true; channel.terminal=true; return; }
            throw new Win32Exception(error,"ConnectNamedPipe(payload output)");
        }

        private static void SetOverlapped(Channel channel)
        {
            var value=new Overlapped { Event=channel.eventHandle };
            Marshal.StructureToPtr(value,channel.overlapped,false);
        }

        internal bool Pump()
        {
            PumpChannel(stdout); PumpChannel(stderr); return limitExceeded;
        }
        private static bool CanAppendLogBytes(uint current,uint count)
        { return current<=LogLimit && count<=LogLimit-current; }

        internal static void RetryRetainedOnOwningWorker()
        {
            PayloadOutputCapture[] snapshot;
            snapshot=pendingOwners.Snapshot();
            int current=Thread.CurrentThread.ManagedThreadId;
            for(int i=0;i<snapshot.Length;i++)
            {
                PayloadOutputCapture owner=snapshot[i];
                if(owner.ownerWorkerThreadId!=current) continue;
                owner.DisposeUntil(owner.cleanupDeadline);
            }
        }

        private void PumpChannel(Channel channel)
        {
            if(channel.eof) return;
            if(channel.connectPending)
            {
                uint ignored;
                if(!GetOverlappedResult(channel.server,channel.overlapped,out ignored,false))
                {
                    int error=Marshal.GetLastWin32Error();
                    if(error==ERROR_IO_INCOMPLETE) return;
                    if(error!=ERROR_OPERATION_ABORTED) { Fail(new Win32Exception(error,"GetOverlappedResult(payload pipe connect)")); return; }
                    channel.terminal=true; return;
                }
                channel.connectPending=false; channel.connected=true; channel.terminal=true;
            }
            if(!channel.connected || channel.eof || channel.cancelRequested) return;
            if(channel.readPending)
            {
                uint completed;
                if(!GetOverlappedResult(channel.server,channel.overlapped,out completed,false))
                {
                    int error=Marshal.GetLastWin32Error();
                    if(error==ERROR_IO_INCOMPLETE) return;
                    channel.readPending=false; channel.terminal=true;
                    if(error==ERROR_OPERATION_ABORTED) return;
                    if(error==ERROR_BROKEN_PIPE || error==ERROR_NO_DATA) { channel.eof=true; return; }
                    Fail(new Win32Exception(error,"GetOverlappedResult(payload output read)")); return;
                }
                channel.readPending=false; channel.terminal=true;
                if(completed==0) { channel.eof=true; return; }
                Persist(channel,completed);
            }
            if(channel.eof || channel.cancelRequested) return;
            ResetEvent(channel.eventHandle); SetOverlapped(channel); channel.terminal=false;
            uint immediate;
            if(ReadFile(channel.server,channel.buffer,TRANSFER,out immediate,channel.overlapped))
            { channel.terminal=true; if(immediate==0) channel.eof=true; else Persist(channel,immediate); return; }
            int readError=Marshal.GetLastWin32Error();
            if(readError==ERROR_IO_PENDING) { channel.readPending=true; return; }
            channel.terminal=true;
            if(readError==ERROR_BROKEN_PIPE || readError==ERROR_NO_DATA) { channel.eof=true; return; }
            Fail(new Win32Exception(readError,"ReadFile(overlapped payload output)"));
        }

        private void Persist(Channel channel,uint count)
        {
            if(!CanAppendLogBytes(channel.logBytes,count) || !allocation.TryChargePayloadLogBytes(count)) { limitExceeded=true; return; }
            IntPtr addedBuffer=channel.buffer;
            uint offset=0;
            while(offset<count)
            {
                uint written;
                if(!WriteFile(channel.log,IntPtr.Add(addedBuffer,(int)offset),count-offset,out written,IntPtr.Zero) || written==0 || written>count-offset)
                { Fail(Error("WriteFile(bounded payload log)")); limitExceeded=true; return; }
                offset+=written;
            }
            channel.logBytes+=count;
        }

        internal bool FinishAndFlush(ulong deadline)
        {
            while((!stdout.eof || !stderr.eof) && GetTickCount64()<deadline)
            {
                Pump(); Thread.Sleep(1);
            }
            if(!stdout.eof || !stderr.eof)
            {
                Cancel(stdout); Cancel(stderr);
                while((!stdout.terminal || !stderr.terminal) && GetTickCount64()<deadline)
                { PumpTerminal(stdout); PumpTerminal(stderr); Thread.Sleep(1); }
                if(!stdout.terminal || !stderr.terminal)
                {
                    // Keep every exact handle and unmanaged I/O owner alive;
                    // cancellation was requested but no terminal completion was observed.
                    GC.KeepAlive(stdout); GC.KeepAlive(stderr); return false;
                }
                Fail(new TimeoutException("payload output did not reach EOF before the shared closure deadline"));
            }
            if(failure!=null || limitExceeded) return false;
            if(!FlushFileBuffers(stdout.log) || !FlushFileBuffers(stderr.log)) { Fail(Error("FlushFileBuffers(payload logs)")); return false; }
            return true;
        }

        internal bool CancelAndObserve(ulong deadline)
        {
            try { Cancel(stdout); } catch(Exception error) { Fail(error); }
            try { Cancel(stderr); } catch(Exception error) { Fail(error); }
            while((!stdout.terminal || !stderr.terminal) && GetTickCount64()<deadline)
            { PumpTerminal(stdout); PumpTerminal(stderr); Thread.Sleep(1); }
            // A later same-worker retry may observe terminal completion after
            // the deadline without granting another wait or releasing pending
            // OVERLAPPED storage on an unverified cancellation result.
            PumpTerminal(stdout); PumpTerminal(stderr);
            return stdout.terminal && stderr.terminal;
        }

        private static void Cancel(Channel channel)
        {
            channel.cancelRequested=true;
            if(channel.terminal) return;
            if(!CancelIoEx(channel.server,channel.overlapped))
            {
                int error=Marshal.GetLastWin32Error();
                // ERROR_NOT_FOUND can mean normal completion raced cancellation;
                // only a subsequent GetOverlappedResult decides terminality.
                if(error!=1168) throw new Win32Exception(error,"CancelIoEx(exact payload pipe operation)");
            }
        }

        private static void PumpTerminal(Channel channel)
        {
            if(channel.terminal) return;
            uint ignored;
            if(GetOverlappedResult(channel.server,channel.overlapped,out ignored,false)) { channel.terminal=true; return; }
            int error=Marshal.GetLastWin32Error();
            if(error==ERROR_IO_INCOMPLETE) return;
            channel.terminal=true;
        }

        private void Fail(Exception error) { if(failure==null) failure=error; ioFailure=true; }
        private static bool HasTerminalIo(Channel channel)
        { return channel==null || ((!channel.connectPending && !channel.readPending) || channel.terminal); }
#if SCOPED_RUNNER_TESTING
        internal static bool CanReleaseCaptureStorageForFixture(bool connectPending,bool readPending,bool terminal)
        { return ((!connectPending && !readPending) || terminal); }
        internal static bool PendingOwnerKeeperContractForFixture()
        {
            var keeper=new PendingOwnerKeeper<object>();
            object owner=new object(); var weak=new WeakReference(owner);
            keeper.Retain(owner); owner=null;
            GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect();
            bool retained=weak.IsAlive && keeper.Count==1;
            if(retained) keeper.Release(weak.Target);
            return retained && keeper.Count==0;
        }
        internal static ulong BindCleanupDeadlineForFixture(bool alreadyRequested,ulong current,ulong requested)
        { return ChooseCleanupDeadline(alreadyRequested,current,requested); }
        internal static bool CanAppendLogBytesForFixture(uint current,uint count)
        { return CanAppendLogBytes(current,count); }
        internal static bool CreateFileEntryPointForFixture()
        {
            var method=typeof(PayloadOutputCapture).GetMethod("CreateFileRawW",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Static);
            if(method==null) return false;
            var import=(DllImportAttribute)Attribute.GetCustomAttribute(method,typeof(DllImportAttribute));
            return import!=null && import.Value=="kernel32.dll" && import.EntryPoint=="CreateFileW" && import.CharSet==CharSet.Unicode;
        }
#endif
        private static ulong ChooseCleanupDeadline(bool alreadyRequested,ulong current,ulong requested)
        { return !alreadyRequested || current==0 || requested<current ? requested : current; }
        private static Exception Error(string operation) { return new Win32Exception(Marshal.GetLastWin32Error(),operation); }
        [DllImport("kernel32.dll",SetLastError=true)] private static extern bool FlushFileBuffers(SafeFileHandle handle);

        public void Dispose()
        { DisposeUntil(initialOwnerDeadline); }

        internal void DisposeUntil(ulong absoluteDeadline)
        {
            if(disposed) return;
            cleanupDeadline=ChooseCleanupDeadline(cleanupRequested,cleanupDeadline,absoluteDeadline);
            cleanupRequested=true;
            try { CloseParentWriters(); } catch(Exception error) { Fail(error); }
            bool terminal=HasTerminalIo(stdout) && HasTerminalIo(stderr);
            if(!terminal)
            {
                CancelAndObserve(cleanupDeadline);
                terminal=HasTerminalIo(stdout) && HasTerminalIo(stderr);
            }
            if(!terminal)
            {
                if(!retainedForCompletion) { pendingOwners.Retain(this); retainedForCompletion=true; }
                return;
            }
            if(StdoutWriter!=IntPtr.Zero || StderrWriter!=IntPtr.Zero)
            {
                if(!retainedForCompletion) { pendingOwners.Retain(this); retainedForCompletion=true; }
                return;
            }
            Exception releaseFailure=null;
            try { DisposeChannel(stdout); } catch(Exception error) { Fail(error); releaseFailure=error; }
            try { DisposeChannel(stderr); } catch(Exception error) { Fail(error); if(releaseFailure==null) releaseFailure=error; }
            try { logs.Dispose(); } catch(Exception error) { Fail(error); if(releaseFailure==null) releaseFailure=error; }
            bool resourcesReleased=StdoutWriter==IntPtr.Zero && StderrWriter==IntPtr.Zero &&
                (stdout==null || (stdout.buffer==IntPtr.Zero && stdout.overlapped==IntPtr.Zero && stdout.eventHandle==IntPtr.Zero && stdout.server==null)) &&
                (stderr==null || (stderr.buffer==IntPtr.Zero && stderr.overlapped==IntPtr.Zero && stderr.eventHandle==IntPtr.Zero && stderr.server==null)) &&
                (logs==null || ((logs.StandardOutput==null || logs.StandardOutput.IsClosed) && (logs.StandardError==null || logs.StandardError.IsClosed)));
            if(releaseFailure!=null || !resourcesReleased)
            {
                if(!retainedForCompletion) { pendingOwners.Retain(this); retainedForCompletion=true; }
                return;
            }
            disposed=true;
            if(retainedForCompletion) { pendingOwners.Release(this); retainedForCompletion=false; }
        }
        private static void DisposeChannel(Channel channel)
        {
            if(channel==null) return;
            if(channel.buffer!=IntPtr.Zero) { Marshal.FreeHGlobal(channel.buffer); channel.buffer=IntPtr.Zero; }
            if(channel.overlapped!=IntPtr.Zero) { Marshal.FreeHGlobal(channel.overlapped); channel.overlapped=IntPtr.Zero; }
            if(channel.eventHandle!=IntPtr.Zero)
            {
                if(!CloseHandle(channel.eventHandle)) throw Error("CloseHandle(payload pipe event)");
                channel.eventHandle=IntPtr.Zero;
            }
            if(channel.server!=null) { channel.server.Dispose(); if(channel.server.IsClosed) channel.server=null; }
        }
    }

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
    private const int PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002;
    private const int STARTF_USESTDHANDLES = 0x00000100;
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

    private readonly PayloadOutputCapture output;
    private MonitorPayloadJob(WindowsCustodyBackend.RuntimeAllocation owner, MonitorOwnedKernelHandle ownedJob, MonitorOwnedKernelHandle ownedProcess, MonitorOwnedKernelHandle ownedThread, IClosureOperations operations=null,PayloadOutputCapture outputCapture=null)
    { allocation=owner; job = ownedJob; process = ownedProcess; thread = ownedThread; closureOperations=operations ?? new NativeClosureOperations(); output=outputCapture; }

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
        IntPtr attributes=IntPtr.Zero, jobArray=IntPtr.Zero, inheritedArray=IntPtr.Zero;
        MonitorOwnedKernelHandle stdinOwner=new MonitorOwnedKernelHandle(false);
        PayloadOutputCapture outputCapture=null;
        bool attributesInitialized=false;
        ProcessInformation created=new ProcessInformation();
        bool transferred=false;
        MonitorPayloadJob result=null;
        ulong setupCleanupDeadline=0;
        Exception primaryFailure=null, cleanupFailure=null;
        try
        {
            setupCleanupDeadline=GetTickCount64()+CleanupWaitMs;
            var security = new SecurityAttributes { Length=Marshal.SizeOf(typeof(SecurityAttributes)), InheritHandle=0 };
            IntPtr rawJob=CreateJobObjectW(ref security, null);
            if (rawJob==IntPtr.Zero) throw Error("CreateJobObjectW(private unnamed job)");
            ownedJob.Adopt(rawJob);
            var limits=new JobExtendedLimitInformation { Basic=new BasicLimitInformation { LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE } };
            Check(SetInformationJobObject(ownedJob.ExactValue, JobObjectExtendedLimitInformation, ref limits,
                (uint)Marshal.SizeOf(typeof(JobExtendedLimitInformation))), "SetInformationJobObject(kill on last close)");

            outputCapture=new PayloadOutputCapture(allocation,setupCleanupDeadline);
            PayloadOutputCapture.CreateInheritableNullInput(stdinOwner);
            IntPtr size=IntPtr.Zero;
            InitializeProcThreadAttributeList(IntPtr.Zero,2,0,ref size);
            int sizingError=Marshal.GetLastWin32Error();
            if(size==IntPtr.Zero || sizingError!=ERROR_INSUFFICIENT_BUFFER)
                throw new Win32Exception(sizingError,"InitializeProcThreadAttributeList(size)");
            attributes=Marshal.AllocHGlobal(size);
            jobArray=Marshal.AllocHGlobal(IntPtr.Size);
            inheritedArray=Marshal.AllocHGlobal(IntPtr.Size*3);
            if(attributes==IntPtr.Zero || jobArray==IntPtr.Zero || inheritedArray==IntPtr.Zero) throw new OutOfMemoryException("job/handle-list attribute allocation failed");
            Marshal.WriteIntPtr(jobArray,ownedJob.ExactValue);
            Marshal.WriteIntPtr(inheritedArray,0,stdinOwner.ExactValue);
            Marshal.WriteIntPtr(inheritedArray,IntPtr.Size,outputCapture.StdoutWriter);
            Marshal.WriteIntPtr(inheritedArray,IntPtr.Size*2,outputCapture.StderrWriter);
            Check(InitializeProcThreadAttributeList(attributes,2,0,ref size),"InitializeProcThreadAttributeList");
            attributesInitialized=true;
            Check(UpdateProcThreadAttribute(attributes,0,new IntPtr(PROC_THREAD_ATTRIBUTE_JOB_LIST),jobArray,
                new UIntPtr((uint)IntPtr.Size),IntPtr.Zero,IntPtr.Zero),"UpdateProcThreadAttribute(JOB_LIST)");
            Check(UpdateProcThreadAttribute(attributes,0,new IntPtr(PROC_THREAD_ATTRIBUTE_HANDLE_LIST),inheritedArray,
                new UIntPtr((uint)(IntPtr.Size*3)),IntPtr.Zero,IntPtr.Zero),"UpdateProcThreadAttribute(HANDLE_LIST)");

            // Staging copies the immutable input directly beneath RuntimePath.
            // Launch the recorded, pinned relative name rather than an invented
            // source subdirectory that was never created or verified.
            string executable=Path.Combine(allocation.RuntimePath,allocation.StagedExecutableRelativePath);
            string command=specification.BuildQuotedCommandLine(executable);
            var startup=new StartupInfoEx { StartupInfo=new StartupInfo { cb=Marshal.SizeOf(typeof(StartupInfoEx)),Flags=STARTF_USESTDHANDLES,
                StdInput=stdinOwner.ExactValue,StdOutput=outputCapture.StdoutWriter,StdError=outputCapture.StderrWriter }, AttributeList=attributes };
            bool createdOk=CreateProcessW(executable,new StringBuilder(command),IntPtr.Zero,IntPtr.Zero,true,
                EXTENDED_STARTUPINFO_PRESENT|CREATE_SUSPENDED|CREATE_UNICODE_ENVIRONMENT,IntPtr.Zero,
                allocation.RuntimePath,ref startup,out created);
            int createError=createdOk ? 0 : Marshal.GetLastWin32Error();
            if(created.Process!=IntPtr.Zero) { ownedProcess.Adopt(created.Process); created.Process=IntPtr.Zero; }
            if(created.Thread!=IntPtr.Zero) { ownedThread.Adopt(created.Thread); created.Thread=IntPtr.Zero; }
            Exception parentWriterCloseFailure=null,stdinCloseFailure=null;
            try { outputCapture.CloseParentWriters(); } catch(Exception error) { parentWriterCloseFailure=error; }
            CloseOwned(ref stdinOwner,ref stdinCloseFailure);
            if(!createdOk) throw new Win32Exception(createError,"CreateProcessW(CREATE_SUSPENDED, JOB_LIST), Win32Error="+createError);
            if(parentWriterCloseFailure!=null && stdinCloseFailure!=null)
                throw new AggregateException("payload process creation succeeded but inherited parent handles failed to close",parentWriterCloseFailure,stdinCloseFailure);
            if(parentWriterCloseFailure!=null) throw new IOException("payload parent writer handles failed to close",parentWriterCloseFailure);
            if(stdinCloseFailure!=null) throw new IOException("inheritable NUL stdin handle failed to close after process creation",stdinCloseFailure);
            if(!Owned(ownedProcess) || !Owned(ownedThread)) throw new InvalidOperationException("CreateProcessW returned incomplete exact handles");
            bool inOwnedJob;
            Check(IsProcessInJob(ownedProcess.ExactValue,ownedJob.ExactValue,out inOwnedJob),"IsProcessInJob(payload, monitor-owned job)");
            if(!inOwnedJob) throw new InvalidOperationException("payload is not in the exact monitor-owned job");
            if(!protocol.MarkSuspended((long)GetTickCount64())) throw new InvalidOperationException("monitor protocol rejected suspended payload transition");

            result=new MonitorPayloadJob(allocation,ownedJob,ownedProcess,ownedThread,null,outputCapture);
            outputCapture=null;
            ownedJob=ownedProcess=ownedThread=null;
            transferred=true;
        }
        catch(Exception error) { primaryFailure=error; }
        finally
        {
            // Attribute storage is always released, including failures after
            // process creation. SafeHandle remains the fallback owner if an
            // explicit close fails while this stack is unwinding.
            if(!transferred)
                try { protocol.SignalClientExited((long)GetTickCount64()); }
                catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
            if(outputCapture!=null)
            {
                try { outputCapture.CloseParentWriters(); } catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
                try { outputCapture.DisposeUntil(setupCleanupDeadline); } catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
            }
            CloseOwned(ref stdinOwner,ref cleanupFailure);
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
            if(inheritedArray!=IntPtr.Zero) try { Marshal.FreeHGlobal(inheritedArray); } catch(Exception error) { RecordFailure(ref cleanupFailure,error); }
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
        CloseAndVerify(closureOperations.Now()+CleanupWaitMs);
    }

    // The worker calls this once for either ordinary root completion or
    // stop/deadline. Every phase consumes the same absolute monotonic bound.
    // Cleanup diagnostics accumulate; no individual failure skips later safe
    // close attempts, and no receipt exists unless every fact is confirmed.
    internal ClosureReceipt CloseAndVerify()
    { return CloseAndVerify(closureOperations.Now()+CleanupWaitMs); }

    internal ClosureReceipt CloseAndVerify(ulong deadline)
    {
        lock(this)
        {
            if(disposed)
            {
                if(cleanupFailure!=null) throw new IOException("exact-job cleanup previously failed; no new cleanup budget was allocated",cleanupFailure);
                return closureReceipt;
            }
            if(deadline==0 || closureOperations.Now()>=deadline)
                throw new TimeoutException("exact-job closure requires the existing live absolute finalization deadline");
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

                if(output!=null)
                {
                    try
                    {
                        if(facts.JobEmpty)
                        {
                            if(!output.FinishAndFlush(deadline)) failures.Add(output.Failure ?? new IOException(output.LimitExceeded ?
                                "payload output exceeded its fixed bound; output was drained but evidence is incomplete" :
                                "payload output did not reach a verified EOF or log flush"));
                        }
                        else output.CancelAndObserve(deadline);
                        if(closureOperations.Now()>deadline) { facts.WithinDeadline=false; failures.Add(new TimeoutException("payload output drain or cancellation exceeded the shared cleanup deadline")); }
                    }
                    catch(Exception error) { failures.Add(error); }
                    try { output.DisposeUntil(deadline); } catch(Exception error) { failures.Add(error); }
                    if(output.Failure!=null && !failures.Contains(output.Failure)) failures.Add(output.Failure);
                }

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
                if(output!=null)
                {
                    try { output.CancelAndObserve(deadline); } catch(Exception error) { failures.Add(error); }
                    try { output.DisposeUntil(deadline); } catch(Exception error) { failures.Add(error); }
                    if(output.Failure!=null && !failures.Contains(output.Failure)) failures.Add(output.Failure);
                }
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

    internal bool PumpOutput()
    {
        if(output==null) return false;
        PayloadOutputCapture.RetryRetainedOnOwningWorker();
        bool exceeded=output.Pump();
        if(output.CleanupRequested) output.DisposeUntil(output.CleanupDeadline);
        if(output.Failure!=null) throw new IOException("payload output capture failed; payload stop and cleanup required",output.Failure);
        return exceeded;
    }

#if SCOPED_RUNNER_TESTING
    internal static bool CanReleaseCaptureStorageForFixture(bool connectPending,bool readPending,bool terminal)
    { return PayloadOutputCapture.CanReleaseCaptureStorageForFixture(connectPending,readPending,terminal); }
    internal static bool CreateFileEntryPointForFixture()
    { return PayloadOutputCapture.CreateFileEntryPointForFixture(); }
    internal static bool PendingOwnerKeeperContractForFixture()
    { return PayloadOutputCapture.PendingOwnerKeeperContractForFixture(); }
    internal static ulong BindCleanupDeadlineForFixture(bool alreadyRequested,ulong current,ulong requested)
    { return PayloadOutputCapture.BindCleanupDeadlineForFixture(alreadyRequested,current,requested); }
    internal static bool CanAppendLogBytesForFixture(uint current,uint count)
    { return PayloadOutputCapture.CanAppendLogBytesForFixture(current,count); }
#endif

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
