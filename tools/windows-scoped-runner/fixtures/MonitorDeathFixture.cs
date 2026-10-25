using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

// Finite real-process input for the public monitor-death contract. This fixture
// creates records and an ordinary child; it never kills a monitor or foreign PID.
internal static class MonitorDeathFixture
{
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    private struct ProcessEntry
    {
        internal uint Size, Usage, Pid;
        internal UIntPtr DefaultHeap;
        internal uint Module, Threads, ParentPid;
        internal int BasePriority;
        internal uint Flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=260)] internal string Executable;
    }
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern IntPtr CreateToolhelp32Snapshot(uint flags,uint pid);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern bool Process32FirstW(IntPtr snapshot,ref ProcessEntry entry);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern bool Process32NextW(IntPtr snapshot,ref ProcessEntry entry);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool CloseHandle(IntPtr handle);

    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool IsProcessInJob(IntPtr process,IntPtr job,out bool member);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool QueryInformationJobObject(IntPtr job,int kind,IntPtr buffer,uint length,IntPtr returned);

    // Both actors query their own immediate Job and its complete PID list before
    // writing useful work. A mere process count or successful spawn is not proof.
    private static string Membership(Process self,Process peer)
    {
        bool selfMember,peerMember;
        if(!IsProcessInJob(self.Handle,IntPtr.Zero,out selfMember)||!selfMember||
           !IsProcessInJob(peer.Handle,IntPtr.Zero,out peerMember)||!peerMember)
            throw new InvalidOperationException("both exact actors must be Job members");
        const int capacity=16;
        int size=8+capacity*IntPtr.Size;
        IntPtr list=Marshal.AllocHGlobal(size);
        try {
            if(!QueryInformationJobObject(IntPtr.Zero,3,list,(uint)size,IntPtr.Zero))
                throw new Win32Exception(Marshal.GetLastWin32Error(),"query immediate Job PID list");
            int assigned=Marshal.ReadInt32(list,0),returned=Marshal.ReadInt32(list,4);
            if(assigned<2||assigned>capacity||returned!=assigned)
                throw new InvalidDataException("incomplete/bounded Job list: assigned="+assigned+";returned="+returned);
            var members=new int[returned];
            for(int index=0;index<returned;index++)members[index]=checked((int)Marshal.ReadIntPtr(list,8+index*IntPtr.Size).ToInt64());
            Array.Sort(members);
            for(int index=0;index<members.Length;index++)
                if(members[index]<=0||(index>0&&members[index]==members[index-1]))
                    throw new InvalidDataException("Job list has an invalid/duplicate PID");
            if(Array.IndexOf(members,self.Id)<0||Array.IndexOf(members,peer.Id)<0)
                throw new InvalidDataException("complete Job list does not contain both exact actors: "+String.Join(",",members));
            return "self="+Identity(self)+";peer="+Identity(peer)+";members="+
                String.Join(",",Array.ConvertAll(members,x=>x.ToString(CultureInfo.InvariantCulture)))+
                ";assigned="+assigned.ToString(CultureInfo.InvariantCulture)+";returned="+returned.ToString(CultureInfo.InvariantCulture);
        } finally {Marshal.FreeHGlobal(list);}
    }
    private static void WaitForRecord(string path,string expected,Process peer)
    {
        var bound=Stopwatch.StartNew();
        while(!File.Exists(path)) {
            if(peer.HasExited)throw new InvalidOperationException("exact peer exited before handshake");
            if(bound.ElapsedMilliseconds>=5000)throw new TimeoutException("membership handshake exceeded5seconds");
            Thread.Sleep(10);
        }
        if(File.ReadAllText(path)!=expected+"\r\n")throw new InvalidDataException("membership handshake mismatch");
    }
    private static int MembershipControl(string prefix,bool leaf,bool deadline)
    {
        Process child=null;bool childStarted=false,transferred=false;
        try {
            using(var self=Process.GetCurrentProcess()) {
                Record(prefix+".identity",Identity(self));
                if(leaf) {
                    using(var parent=ParentProcess(self)) {
                        Record(prefix+".membership",Membership(self,parent));
                        Record(prefix+".ready","membership-leaf-ready");
                        WaitForRecord(prefix+".release","both-members-confirmed",parent);
                        Record(prefix+".work","child-work-after-both-membership");
                    }
                    using(var hold=new ManualResetEvent(false))hold.WaitOne(240000);
                    return 126;
                }
                child=new Process {StartInfo=new ProcessStartInfo {
                    FileName=self.MainModule.FileName,Arguments="--membership-leaf \""+prefix+".child\"",
                    WorkingDirectory=Environment.CurrentDirectory,UseShellExecute=false,CreateNoWindow=true}};
                if(!child.Start())throw new InvalidOperationException("membership child did not start");
                childStarted=true;
                WaitForRecord(prefix+".child.ready","membership-leaf-ready",child);
                string member=Membership(self,child);
                string leafRecord=File.ReadAllText(prefix+".child.membership");
                if(!leafRecord.StartsWith("self="+Identity(child)+";peer="+Identity(self)+";members=",StringComparison.Ordinal)||
                   !leafRecord.EndsWith("\r\n",StringComparison.Ordinal))
                    throw new InvalidDataException("independent leaf membership identity differs");
                Record(prefix+".membership",member);
                Record(prefix+".child.release","both-members-confirmed");
                WaitForRecord(prefix+".child.work","child-work-after-both-membership",child);
                Record(prefix+".work","parent-work-after-both-membership");
                Record(prefix+".ready","both-membership-and-work-confirmed");
                // Ordinary child remains in the public monitor's exact Job. The
                // deadline variant cannot naturally finish before Driver180s.
                transferred=true;
                if(deadline) {using(var hold=new ManualResetEvent(false))hold.WaitOne(240000);return 126;}
                return 0;
            }
        } finally {
            if(childStarted&&!transferred) {
                if(!child.HasExited)child.Kill();
                if(!child.WaitForExit(10000))throw new TimeoutException("membership child cleanup did not finish");
            }
            if(child!=null)child.Dispose();
        }
    }

    private static string Identity(Process process)
    {
        return "pid="+process.Id.ToString(CultureInfo.InvariantCulture)+
            " creation="+process.StartTime.ToUniversalTime().ToFileTimeUtc().ToString(CultureInfo.InvariantCulture);
    }
    private static void Record(string path,string text)
    {
        string pending=path+".pending";
        using(var stream=new FileStream(pending,FileMode.CreateNew,FileAccess.Write,FileShare.Read))
        using(var writer=new StreamWriter(stream)) { writer.Write(text+"\r\n"); writer.Flush(); stream.Flush(true); }
        File.Move(pending,path); // Publish only after both writers have closed.
    }
    private static Process ParentProcess(Process self)
    {
        IntPtr snapshot=CreateToolhelp32Snapshot(2,0);
        if(snapshot==new IntPtr(-1))throw new Win32Exception(Marshal.GetLastWin32Error(),"process snapshot");
        uint parent=0;
        try
        {
            var entry=new ProcessEntry {Size=(uint)Marshal.SizeOf(typeof(ProcessEntry))};
            if(!Process32FirstW(snapshot,ref entry))throw new Win32Exception(Marshal.GetLastWin32Error(),"first process");
            do { if(entry.Pid==(uint)self.Id) {parent=entry.ParentPid;break;} }
            while(Process32NextW(snapshot,ref entry));
            if(parent==0)throw new InvalidOperationException("exact current process missing from snapshot");
        }
        finally { if(!CloseHandle(snapshot))throw new Win32Exception(Marshal.GetLastWin32Error(),"close snapshot"); }
        var process=Process.GetProcessById(checked((int)parent));
        try {
            if(process.HasExited||process.StartTime.ToUniversalTime()>self.StartTime.ToUniversalTime())
                throw new InvalidOperationException("parent identity is unavailable or reused");
            return process;
        } catch {process.Dispose();throw;}
    }
    private static void Hold()
    {
        using(var wait=new ManualResetEvent(false))wait.WaitOne(120000);
    }
    private static int Main(string[] args)
    {
        if(args.Length==2&&(args[0]=="--membership"||args[0]=="--membership-deadline"||args[0]=="--membership-leaf")) {
            try {return MembershipControl(Path.GetFullPath(args[1]),args[0]=="--membership-leaf",args[0]=="--membership-deadline");}
            catch(Exception error) {
                // A spawned console-less child may not inherit the monitor's
                // diagnostic pipe. Preserve its original error beside its identity.
                try {Record(Path.GetFullPath(args[1])+".failure",error.ToString());}
                catch(Exception recordError) {Console.Error.WriteLine("membership diagnostic: "+recordError);}
                Console.Error.WriteLine(error.ToString());return 2;
            }
        }
        if(args.Length!=2||(args[0]!="--parent"&&args[0]!="--leaf"&&args[0]!="--parent-exit"&&args[0]!="--output-limit"))return 64;
        string prefix=Path.GetFullPath(args[1]);
        Process child=null;bool childStarted=false,childExited=false,childTransferred=false;int result=126;
        try
        {
            using(var self=Process.GetCurrentProcess())
            {
                Record(prefix+".identity",Identity(self));
                if(args[0]=="--leaf") {Record(prefix+".ready","leaf-ready");Hold();return 126;}
                using(var monitor=ParentProcess(self))
                using(var client=ParentProcess(monitor))
                using(var driver=ParentProcess(client)) {
                    Record(prefix+".monitor",Identity(monitor));
                    Record(prefix+".client",Identity(client));
                    Record(prefix+".driver",Identity(driver));
                }
                child=new Process {StartInfo=new ProcessStartInfo {
                    FileName=self.MainModule.FileName,
                    Arguments="--leaf \""+prefix+".child\"",
                    WorkingDirectory=Environment.CurrentDirectory,
                    UseShellExecute=false,CreateNoWindow=true }};
                if(!child.Start())throw new InvalidOperationException("ordinary child did not start");
                childStarted=true;
                string expected=Identity(child)+"\r\n";
                var ready=Stopwatch.StartNew();
                while(!File.Exists(prefix+".child.ready"))
                {
                    if(child.HasExited)throw new InvalidOperationException("child exited before readiness");
                    if(ready.ElapsedMilliseconds>=5000)throw new TimeoutException("child readiness exceeded 5 seconds");
                    Thread.Sleep(10);
                }
                if(File.ReadAllText(prefix+".child.ready")!="leaf-ready\r\n"||
                   File.ReadAllText(prefix+".child.identity")!=expected)
                    throw new InvalidDataException("child readiness/identity mismatch");
                Record(prefix+".ready","parent-and-child-ready");
                if(args[0]=="--output-limit") {
                    var release=Stopwatch.StartNew();
                    while(!File.Exists(prefix+".release")) {
                        if(child.HasExited)throw new InvalidOperationException("output child stopped before release");
                        if(release.ElapsedMilliseconds>=30000)throw new TimeoutException("output release exceeded30seconds");
                        Thread.Sleep(10);
                    }
                    string command;
                    using(var input=new FileStream(prefix+".release",FileMode.Open,FileAccess.Read,
                        FileShare.ReadWrite|FileShare.Delete))
                    using(var reader=new StreamReader(input)) command=reader.ReadToEnd();
                    if(command!="output-limit\r\n")throw new InvalidDataException("output release input mismatch");
                    Record(prefix+".output-start","stdout-limit=67108864;attempt=134217728;byte=90");
                    // The child remains under the real monitor's Job, including failure paths.
                    childTransferred=true;
                    var finished=new ManualResetEvent(false);
                    var expiry=new Thread(()=> {
                        if(!finished.WaitOne(120000))Environment.Exit(126);
                    }) {IsBackground=true};
                    expiry.Start();
                    try {
                        var block=new byte[65536];
                        for(int i=0;i<block.Length;i++)block[i]=90;
                        using(var output=Console.OpenStandardOutput()) {
                            for(int i=0;i<2048;i++)output.Write(block,0,block.Length);
                            output.Flush();
                        }
                        Record(prefix+".output-complete","unexpected-unbounded-output-completion");
                        result=0;
                    } finally {
                        finished.Set();
                        if(!expiry.Join(1000))throw new TimeoutException("output expiry worker did not join");
                        finished.Dispose();
                    }
                } else if(args[0]=="--parent-exit") {
                    var release=Stopwatch.StartNew();
                    while(!File.Exists(prefix+".release")) {
                        if(child.HasExited)throw new InvalidOperationException("residual child stopped before parent release");
                        if(release.ElapsedMilliseconds>=30000)throw new TimeoutException("parent release exceeded30seconds");
                        Thread.Sleep(10);
                    }
                    if(File.ReadAllText(prefix+".release")!="exit-parent\r\n")
                        throw new InvalidDataException("parent release input mismatch");
                    Record(prefix+".parent-exit","normal-parent-exit");
                    // Leave the ordinary child alive for the real monitor Job closure.
                    childTransferred=true;result=0;
                } else Hold();
            }
        }
        catch(Exception error) {Console.Error.WriteLine(error.ToString());result=2;}
        finally
        {
            if(childStarted&&!childTransferred)
            {
                try {
                    if(!child.HasExited)child.Kill();
                    if(!child.WaitForExit(10000))throw new TimeoutException("exact direct child did not exit");
                    childExited=true;
                }
                catch(Exception error) {Console.Error.WriteLine("exact-child cleanup: "+error);result=2;}
            }
            if(child!=null&&(!childStarted||childExited||childTransferred))child.Dispose();
        }
        return result;
    }
}
