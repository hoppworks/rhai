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
        if(args.Length!=2||(args[0]!="--parent"&&args[0]!="--leaf"&&args[0]!="--parent-exit"))return 64;
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
                if(args[0]=="--parent-exit") {
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
