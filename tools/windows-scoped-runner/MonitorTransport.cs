using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Collections.Generic;

// Windows pipe/process boundary. Only three explicit handles cross the launch:
// monitor input, monitor output, and a real restricted handle to this client.
internal static class MonitorTransport
{
    private const uint DETACHED_PROCESS = 0x00000008, EXTENDED_STARTUPINFO_PRESENT = 0x00080000, CREATE_BREAKAWAY_FROM_JOB = 0x01000000;
    private const uint HANDLE_FLAG_INHERIT = 1, PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002;
    private const uint SYNCHRONIZE = 0x00100000, PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
    private const uint WAIT_OBJECT_0 = 0, WAIT_TIMEOUT = 258;
    private const int ERROR_INSUFFICIENT_BUFFER = 122;

    [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes { public int nLength; public IntPtr lpSecurityDescriptor; public int bInheritHandle; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] private struct StartupInfo
    {
        public int cb; public string lpReserved, lpDesktop, lpTitle; public int dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
        public short wShowWindow, cbReserved2; public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
    }
    [StructLayout(LayoutKind.Sequential)] private struct StartupInfoEx { public StartupInfo StartupInfo; public IntPtr AttributeList; }
    [StructLayout(LayoutKind.Sequential)] private struct ProcessInfo { public IntPtr Process, Thread; public uint ProcessId, ThreadId; }

    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool CreatePipe(out IntPtr read, out IntPtr write, ref SecurityAttributes attrs, uint size);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool SetHandleInformation(IntPtr handle, uint mask, uint flags);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool IsProcessInJob(IntPtr process, IntPtr job, out bool result);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool InitializeProcThreadAttributeList(IntPtr list, int count, uint flags, ref IntPtr size);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool UpdateProcThreadAttribute(IntPtr list, uint flags, IntPtr attribute, IntPtr value, UIntPtr size, IntPtr previous, IntPtr returned);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern void DeleteProcThreadAttributeList(IntPtr list);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true, EntryPoint="CreateProcessW")]
    private static extern bool CreateProcess(string app, StringBuilder command, IntPtr pa, IntPtr ta, bool inherit, uint flags, IntPtr env, string cwd, ref StartupInfoEx si, out ProcessInfo pi);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern uint WaitForSingleObject(IntPtr handle, uint ms);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool GetExitCodeProcess(IntPtr process, out uint code);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true, EntryPoint="GetModuleFileNameW")] private static extern uint GetModuleFileName(IntPtr module, StringBuilder path, int size);
    [DllImport("kernel32.dll")] private static extern ulong GetTickCount64();

    private static Exception Error(string what) { return new Win32Exception(Marshal.GetLastWin32Error(), what); }
    private static void Check(bool ok, string what) { if (!ok) throw Error(what); }
    private static string Quote(string value)
    {
        var b=new StringBuilder("\""); int slashes=0;
        foreach(char c in value) { if(c=='\\') { slashes++; continue; } if(c=='"') { b.Append('\\',slashes*2+1).Append('"'); slashes=0; continue; } b.Append('\\',slashes).Append(c); slashes=0; }
        return b.Append('\\',slashes*2).Append('"').ToString();
    }
    private static string SelfPath()
    {
        var b = new StringBuilder(32768); uint length=GetModuleFileName(IntPtr.Zero, b, b.Capacity);
        if(length==0 || length>=b.Capacity) throw Error("GetModuleFileNameW (empty path or truncation)"); return b.ToString();
    }

    internal static int ClientMain(string[] args)
    {
        IntPtr monitorInputRead=IntPtr.Zero, clientInputWrite=IntPtr.Zero, clientOutputRead=IntPtr.Zero, monitorOutputWrite=IntPtr.Zero, clientProcess=IntPtr.Zero;
        if(args.Length!=1 || args[0]!="--lease-client") return 64;
        IntPtr attrs=IntPtr.Zero, handles=IntPtr.Zero; ProcessInfo child=new ProcessInfo(); bool attrsInitialized=false;
        try
        {
            var sa = new SecurityAttributes { nLength=Marshal.SizeOf(typeof(SecurityAttributes)), bInheritHandle=1 };
            Check(CreatePipe(out monitorInputRead, out clientInputWrite, ref sa, 0), "CreatePipe(client-to-monitor)");
            Check(CreatePipe(out clientOutputRead, out monitorOutputWrite, ref sa, 0), "CreatePipe(monitor-to-client)");
            Check(SetHandleInformation(clientInputWrite, HANDLE_FLAG_INHERIT, 0), "SetHandleInformation(client input writer)");
            Check(SetHandleInformation(clientOutputRead, HANDLE_FLAG_INHERIT, 0), "SetHandleInformation(client output reader)");
            clientProcess = OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, true, (uint)System.Diagnostics.Process.GetCurrentProcess().Id);
            if (clientProcess == IntPtr.Zero) throw Error("OpenProcess(real restricted client handle)");
            IntPtr size=IntPtr.Zero; InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref size);
            int err=Marshal.GetLastWin32Error(); if (size==IntPtr.Zero || err!=ERROR_INSUFFICIENT_BUFFER) throw new Win32Exception(err,"InitializeProcThreadAttributeList(size)");
            attrs=Marshal.AllocHGlobal(size); handles=Marshal.AllocHGlobal(IntPtr.Size*3);
            Check(InitializeProcThreadAttributeList(attrs,1,0,ref size),"InitializeProcThreadAttributeList"); attrsInitialized=true;
            Marshal.WriteIntPtr(handles,0,monitorInputRead); Marshal.WriteIntPtr(handles,IntPtr.Size,monitorOutputWrite); Marshal.WriteIntPtr(handles,IntPtr.Size*2,clientProcess);
            Check(UpdateProcThreadAttribute(attrs,0,new IntPtr(PROC_THREAD_ATTRIBUTE_HANDLE_LIST),handles,new UIntPtr((uint)(IntPtr.Size*3)),IntPtr.Zero,IntPtr.Zero),"UpdateProcThreadAttribute(HANDLE_LIST)");
            bool ambientJob; Check(IsProcessInJob(new IntPtr(-1),IntPtr.Zero,out ambientJob),"IsProcessInJob(client)");
            string exe=SelfPath();
            string cmd=Quote(exe)+" --monitor "+monitorInputRead.ToInt64()+" "+monitorOutputWrite.ToInt64()+" "+clientProcess.ToInt64();
            var si=new StartupInfoEx { StartupInfo=new StartupInfo { cb=Marshal.SizeOf(typeof(StartupInfoEx)) }, AttributeList=attrs };
            uint flags=EXTENDED_STARTUPINFO_PRESENT|DETACHED_PROCESS|(ambientJob?CREATE_BREAKAWAY_FROM_JOB:0);
            Check(CreateProcess(exe,new StringBuilder(cmd),IntPtr.Zero,IntPtr.Zero,true,flags,IntPtr.Zero,PathDirectory(exe),ref si,out child),"CreateProcess(detached monitor)");
            // Parent closes all copies of child ends immediately; only the child
            // retains those pipe handles. I/O workers may block, but this thread
            // polls the exact monitor process handle and never joins them.
            CloseAndZero(ref monitorInputRead); CloseAndZero(ref monitorOutputWrite);
            StartPipeForwarder(Console.OpenStandardInput(),new FileStream(clientInputWrite,FileAccess.Write,false,1),ref clientInputWrite);
            StartPipeForwarder(new FileStream(clientOutputRead,FileAccess.Read,false),Console.OpenStandardOutput(),ref clientOutputRead);
            ulong clientStart=GetTickCount64();
            for(;;)
            {
                uint wait=WaitForSingleObject(child.Process,100);
                if(wait==WAIT_OBJECT_0) break;
                if(wait!=WAIT_TIMEOUT) throw Error("WaitForSingleObject(monitor)");
                if(GetTickCount64()-clientStart>=1800000UL) { Console.Error.WriteLine("client monitor wait reached fixed absolute deadline; closing client-side handles without terminating monitor"); return 124; }
            }
            uint code; Check(GetExitCodeProcess(child.Process,out code),"GetExitCodeProcess(monitor)"); return unchecked((int)code);
        }
        catch(Exception e) { Console.Error.WriteLine("monitor client launch failed: "+e.Message); return 70; }
        finally
        {
            CloseAndZero(ref monitorInputRead); CloseAndZero(ref clientInputWrite); CloseAndZero(ref clientOutputRead); CloseAndZero(ref monitorOutputWrite); CloseAndZero(ref clientProcess);
            if(attrs!=IntPtr.Zero) { if(attrsInitialized) { try { DeleteProcThreadAttributeList(attrs); } catch { } } Marshal.FreeHGlobal(attrs); }
            if(handles!=IntPtr.Zero) Marshal.FreeHGlobal(handles);
            if(child.Process!=IntPtr.Zero) CloseHandle(child.Process); if(child.Thread!=IntPtr.Zero) CloseHandle(child.Thread);
        }
    }
    private static string PathDirectory(string path) { return System.IO.Path.GetDirectoryName(path); }
    private static void StartPipeForwarder(Stream input, Stream output, ref IntPtr owner)
    {
        IntPtr handle=owner; owner=IntPtr.Zero;
        try { var t=new Thread(()=>CopyBounded(input,output,handle)); t.IsBackground=true; t.Start(); }
        catch { CloseHandle(handle); try { input.Dispose(); } catch { } try { output.Dispose(); } catch { } throw; }
    }
    private static void CopyBounded(Stream input, Stream output, IntPtr ownedPipeHandle)
    {
        try { byte[] b=new byte[512]; int n; while((n=input.Read(b,0,b.Length))>0) output.Write(b,0,n); }
        catch { }
        finally { try { output.Dispose(); } catch { } if(ownedPipeHandle!=IntPtr.Zero) CloseHandle(ownedPipeHandle); }
    }
    private static void CloseAndZero(ref IntPtr handle) { if(handle!=IntPtr.Zero) { CloseHandle(handle); handle=IntPtr.Zero; } }

    internal static int MonitorMain(string[] args)
    {
        if(args.Length!=4 || args[0]!="--monitor") return 64;
        long inputValue, outputValue, clientValue;
        if(!Int64.TryParse(args[1],out inputValue)||!Int64.TryParse(args[2],out outputValue)||!Int64.TryParse(args[3],out clientValue)) return 64;
        IntPtr input=new IntPtr(inputValue), output=new IntPtr(outputValue), client=new IntPtr(clientValue);
        try
        {
            // Refuse inherited transport jobs before allocating runtime, job, or journal.
            Check(SetHandleInformation(input,HANDLE_FLAG_INHERIT,0),"clear monitor input inheritance");
            Check(SetHandleInformation(output,HANDLE_FLAG_INHERIT,0),"clear monitor output inheritance");
            Check(SetHandleInformation(client,HANDLE_FLAG_INHERIT,0),"clear client-handle inheritance");
            bool ambient; Check(IsProcessInJob(new IntPtr(-1),IntPtr.Zero,out ambient),"IsProcessInJob(monitor)");
            if(ambient) { Console.Error.WriteLine("monitor refused: ambient job membership"); return 78; }
            IntPtr ownedInput=input, ownedOutput=output, ownedClient=client; input=IntPtr.Zero; output=IntPtr.Zero; client=IntPtr.Zero;
            return RunMonitor(ownedInput,ownedOutput,ownedClient);
        }
        catch(Exception e) { Console.Error.WriteLine("monitor failed closed: "+e.Message); return 79; }
        finally { if(input!=IntPtr.Zero) CloseHandle(input); if(output!=IntPtr.Zero) CloseHandle(output); if(client!=IntPtr.Zero) CloseHandle(client); }
    }

    private static int RunMonitor(IntPtr input,IntPtr output,IntPtr client)
    {
        int stopWriter=0;
        MonitorStagingHandoff staging=null;
        try
        {
        LeaseMonitor.Policy policy=LeaseMonitor.Protocol.ProductionPolicy();
        long started=(long)GetTickCount64();
        string token=MonitorSpecificationIntake.CreateMonitorToken();
        var incoming=new LeaseMonitor.BoundedFrameQueue(32,8192); var outgoing=new LeaseMonitor.BoundedFrameQueue(32,8192);
        var protocol=new LeaseMonitor.Protocol(policy);
        var dispatcher=new MonitorSpecificationIntake.Dispatcher(
            protocol, outgoing, ()=> (long)GetTickCount64(), token,
            started, started+policy.SetupDeadline, policy.ChallengePeriod);
        staging=MonitorStagingHandoff.CreateProduction(protocol,()=> (long)GetTickCount64());
        if(!dispatcher.Start()) return 78;
        int eof=0, writeFailed=0;
        IntPtr inputOwner=input;
        var reader=new Thread(()=>{
            try { using(var s=new FileStream(inputOwner,FileAccess.Read,false)) {
                for(;;) { byte[] frame=ReadBoundedFrame(s,512); if(frame==null) break; if(!incoming.TryWrite(frame)) throw new InvalidDataException("bounded input queue is full"); }
            }} catch { } finally { Interlocked.Exchange(ref eof,1); CloseHandle(inputOwner); }
        }); reader.IsBackground=true;
        try { reader.Start(); input=IntPtr.Zero; } catch { if(input!=IntPtr.Zero) { CloseHandle(input); input=IntPtr.Zero; } throw; }
        IntPtr outputOwner=output;
        var writer=new Thread(()=>{
            try { using(var s=new FileStream(outputOwner,FileAccess.Write,false,1)) { for(;;) { byte[] frame; if(outgoing.TryRead(out frame)) s.Write(frame,0,frame.Length); else if(Volatile.Read(ref stopWriter)!=0) break; else Thread.Sleep(10); } }
            } catch { Interlocked.Exchange(ref writeFailed,1); } finally { CloseHandle(outputOwner); }
        }); writer.IsBackground=true;
        try { writer.Start(); output=IntPtr.Zero; } catch { if(output!=IntPtr.Zero) { CloseHandle(output); output=IntPtr.Zero; } throw; }
        while(dispatcher.Poll() && Volatile.Read(ref eof)==0 && Volatile.Read(ref writeFailed)==0 && WaitForSingleObject(client,0)==WAIT_TIMEOUT)
        {
            if(!dispatcher.TryIssueChallenge()) break;
            for(int handled=0;handled<16 && !dispatcher.Stopped;handled++)
            {
                byte[] originalFrame; if(!incoming.TryRead(out originalFrame)) break;
                if(!dispatcher.Dispatch(originalFrame)) break;
            }
            if(!dispatcher.Stopped && staging.CanStart && dispatcher.CompletedSpecification!=null &&
                dispatcher.Poll() && Volatile.Read(ref eof)==0 && Volatile.Read(ref writeFailed)==0 &&
                WaitForSingleObject(client,0)==WAIT_TIMEOUT)
            {
                if(!staging.Start(dispatcher.CompletedSpecification)) { dispatcher.Stop(); break; }
            }
            if(staging.IsPublished)
            {
                Func<bool> live = () => dispatcher.Poll() && !dispatcher.Stopped &&
                    Volatile.Read(ref eof)==0 && Volatile.Read(ref writeFailed)==0 &&
                    WaitForSingleObject(client,0)==WAIT_TIMEOUT;
                staging.TryAccept(live);
            }
            if(staging.IsFailed) { dispatcher.Stop(); break; }
            Thread.Sleep(25); // finite watchdog poll; never waits for a pipe or worker join
        }
        dispatcher.Stop();
        staging.Stop(); // signal only; a worker blocked in I/O keeps ownership
        // The accepted owner worker owns create/resume and exact-job cleanup.
        // Runtime removal remains closed until exact-job closure is proven.
        return Volatile.Read(ref writeFailed)!=0 ? 79 : 78;
        }
        finally
        {
            if(staging!=null)
            {
                staging.Stop();
                // Keep this independent monitor process alive through the
                // owner's already established cleanup deadline. The watchdog
                // only polls; it never joins, performs I/O, or starts a fresh
                // cleanup budget after an earlier lifecycle deadline exists.
                staging.WaitForOwnerUntilCleanupDeadline();
            }
            Volatile.Write(ref stopWriter,1);
            if(input!=IntPtr.Zero) CloseHandle(input);
            if(output!=IntPtr.Zero) CloseHandle(output);
            if(client!=IntPtr.Zero) CloseHandle(client);
        }
    }

    internal static byte[] ReadBoundedFrame(Stream stream,int max)
    {
        var b=new List<byte>(64);
        if(stream==null) throw new ArgumentNullException("stream");
        if(max<1) throw new ArgumentOutOfRangeException("max");
        for(;;)
        {
            int n=stream.ReadByte();
            if(n<0) { if(b.Count==0) return null; throw new InvalidDataException("partial protocol frame at EOF"); }
            if(b.Count>=max) throw new InvalidDataException("protocol frame exceeds fixed "+max.ToString()+"-byte limit");
            b.Add((byte)n);
            if(n=='\n') return b.ToArray();
        }
    }
}
