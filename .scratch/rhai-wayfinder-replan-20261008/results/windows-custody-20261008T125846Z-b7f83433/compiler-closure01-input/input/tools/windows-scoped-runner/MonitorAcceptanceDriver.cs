// Separate native acceptance route. Source only until reviewed and compiled on
// the authorized Windows guest; this driver is not part of the source fixtures.
using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

internal static class MonitorAcceptanceDriver
{
    private static string RunsRoot { get { return WindowsCustodyBackend.AuthorizedRoot; } }
    private const int MaximumRecords = 64, MaximumRecordBytes = 4096, MaximumJournalBytes = MaximumRecords * (MaximumRecordBytes + 15);
    private const int MaximumJournalInventory = 512, MaximumEvidenceLogBytes = 536870912;
    private const uint JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008, JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100,
        JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200, JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    private const int JobObjectExtendedLimitInformation = 9, JobObjectBasicAccountingInformation = 1;

    [StructLayout(LayoutKind.Sequential)] private struct BasicLimitInformation
    { public long PerProcessUserTimeLimit, PerJobUserTimeLimit; public uint LimitFlags; public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize; public uint ActiveProcessLimit; public UIntPtr Affinity; public uint PriorityClass, SchedulingClass; }
    [StructLayout(LayoutKind.Sequential)] private struct IoCounters
    { public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
    [StructLayout(LayoutKind.Sequential)] private struct JobExtendedLimitInformation
    { public BasicLimitInformation BasicLimitInformation; public IoCounters IoInfo; public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed; }
    [StructLayout(LayoutKind.Sequential)] private struct JobBasicAccountingInformation
    { public long TotalUserTime, TotalKernelTime, ThisPeriodTotalUserTime, ThisPeriodTotalKernelTime; public uint TotalPageFaultCount, TotalProcesses, ActiveProcesses, TotalTerminatedProcesses; }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] private static extern IntPtr CreateJobObjectW(IntPtr attributes, string name);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool SetInformationJobObject(IntPtr job, int infoClass, ref JobExtendedLimitInformation info, uint length);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool QueryInformationJobObject(IntPtr job, int infoClass, out JobBasicAccountingInformation info, uint length, IntPtr returned);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool IsProcessInJob(IntPtr process, IntPtr job, out bool result);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool TerminateProcess(IntPtr process,uint exitCode);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool TerminateJobObject(IntPtr job,uint exitCode);
    [DllImport("kernel32.dll")] private static extern ulong GetTickCount64();

    private sealed class Deadline
    {
        private readonly ulong end;
        internal Deadline(uint milliseconds) { end=GetTickCount64()+milliseconds; }
        internal int Remaining { get { ulong now=GetTickCount64(); if(now>=end)return 0; ulong left=end-now; return left>Int32.MaxValue?Int32.MaxValue:(int)left; } }
        internal void Check(string operation) { if(Remaining==0) throw new TimeoutException("whole-driver deadline expired during "+operation); }
    }
    internal sealed class JournalReport
    {
        internal string Path, RuntimePath, Invocation, RuntimeIdentity, PayloadExit, Supervision, EvidenceIdentity;
        internal bool Removed, CleanupConfirmed, HostExported;
        internal readonly Dictionary<string,string> Evidence=new Dictionary<string,string>(StringComparer.Ordinal);
    }
    private sealed class ControlState
    {
        internal bool TransferComplete, ClientKilledByDriver, HostDisconnected, ReplayPrimed, ReplaySent;
        internal int PostTransferChallenges;
    }

    public static int Main(string[] args)
    {
        if(args.Length<9 || args[0]!="--mode" || args[2]!="--source" || args[4]!="--exe" || args[6]!="--expected-payload-exit" || args[8]!="--")
        { Console.Error.WriteLine("usage: MonitorAcceptanceDriver --mode success|disconnect-alive|client-death|replay --source DIR --exe RELATIVE --expected-payload-exit HEX -- [payload-args...]"); return 64; }
        string mode=args[1], source=args[3], executable=args[5], expectedPayloadExit;
        if(mode!="success" && mode!="disconnect-alive" && mode!="client-death" && mode!="replay" || !Hex8(args[7],out expectedPayloadExit)) return 64;
        string[] payloadArgs=args.Skip(9).ToArray(); Deadline deadline=new Deadline(180000);
        IntPtr job=IntPtr.Zero; Process selfProcess=Process.GetCurrentProcess(); IntPtr self=selfProcess.Handle; Process client=null; bool clientStarted=false, clientWaited=false, safeToRelease=false;
        int clientExit=Int32.MinValue, result=2; Exception cleanupFailure=null;
        var watchdogStop=new ManualResetEvent(false);
        Thread watchdog=new Thread(()=>WatchDeadline(deadline,watchdogStop,self)) { IsBackground=true, Name="monitor-driver-deadline" };
        watchdog.Start(); BoundedPipes pipes=null;
        try
        {
            bool ambient;
            if(!IsProcessInJob(self,IntPtr.Zero,out ambient)||ambient) throw new InvalidOperationException("driver requires an uncontained parent; refusing ambient job membership");
            job=CreateJobObjectW(IntPtr.Zero,null); Check(job!=IntPtr.Zero,"CreateJobObjectW");
            var limits=CreateLimits(true);
            Check(SetInformationJobObject(job,JobObjectExtendedLimitInformation,ref limits,(uint)Marshal.SizeOf(typeof(JobExtendedLimitInformation))),"SetInformationJobObject");
            Check(AssignProcessToJobObject(job,self),"AssignProcessToJobObject(driver)");
            string[] before=SnapshotJournals(deadline);
            string runner=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"ScopedRunner.exe");
            var spec=LaunchSpecification.Create(source,executable,payloadArgs);
            byte[] specWire=spec.ToWire();
            if(specWire.Length<14||Encoding.ASCII.GetString(specWire,0,14)!="RHAI-LAUNCH/1\n")throw new InvalidDataException("launch specification version mismatch");
            client=new Process { StartInfo=new ProcessStartInfo { FileName=runner, Arguments="--lease-client", UseShellExecute=false, RedirectStandardInput=true, RedirectStandardOutput=true, RedirectStandardError=true, CreateNoWindow=true } };
            client.StartInfo.StandardOutputEncoding=Encoding.ASCII; client.StartInfo.StandardErrorEncoding=Encoding.ASCII;
            Check(client.Start(),"start --lease-client"); clientStarted=true;
            Check(IsProcessInJob(client.Handle,job,out ambient)&&ambient,"lease client is not a member of controller job");
            pipes=new BoundedPipes(client,deadline);
            ControlState control=new ControlState();
            DriveProtocol(client,pipes,spec,mode,deadline,control);
            deadline.Check("client completion wait");
            if(!client.WaitForExit(deadline.Remaining)) throw new TimeoutException("exact client did not exit before whole-driver deadline");
            clientWaited=true; clientExit=client.ExitCode;
            if(!control.TransferComplete || mode=="client-death" && !control.ClientKilledByDriver || mode=="disconnect-alive" && !control.HostDisconnected || mode=="replay" && !control.ReplaySent)
                throw new InvalidDataException("mode action was not actually performed after immutable transfer");
            JournalReport report=ReadSingleNewJournal(before,SnapshotJournals(deadline),deadline);
            ValidateMode(report,mode,expectedPayloadExit,clientExit,control);
            VerifyEvidence(report,deadline);
            if(Directory.Exists(report.RuntimePath)) throw new InvalidDataException("REMOVED receipt contradicts runtime directory presence");
            PrintReport(report,clientExit,mode,control); result=0;
        }
        catch(Exception e) { Console.Error.WriteLine("driver failure: {0}: {1}",e.GetType().Name,e.Message); result=2; }
        finally
        {
            if(clientStarted && !clientWaited)
            {
                try
                {
                    if(!client.HasExited) client.Kill();
                    if(!client.WaitForExit(deadline.Remaining)) throw new TimeoutException("could not confirm exact client exit during cleanup");
                    clientWaited=true; clientExit=client.ExitCode;
                }
                catch(Exception e) { cleanupFailure=e; Console.Error.WriteLine("cleanup failure: {0}: {1}",e.GetType().Name,e.Message); result=2; }
            }
            if(pipes!=null)
            {
                try { pipes.StopAndJoin(deadline); }
                catch(Exception e) { if(cleanupFailure==null)cleanupFailure=e; Console.Error.WriteLine("pipe cleanup failure: {0}: {1}",e.GetType().Name,e.Message); result=2; }
            }
            if(job!=IntPtr.Zero)
            {
                try
                {
                    JobBasicAccountingInformation accounting;
                    Check(QueryInformationJobObject(job,JobObjectBasicAccountingInformation,out accounting,(uint)Marshal.SizeOf(typeof(JobBasicAccountingInformation)),IntPtr.Zero),"QueryInformationJobObject(cleanup)");
                    if(!clientWaited || accounting.ActiveProcesses!=1) throw new InvalidOperationException("cannot release controller job: exact client is not confirmed exited or active process count is not exactly the driver");
                    var release=CreateLimits(false);
                    Check(SetInformationJobObject(job,JobObjectExtendedLimitInformation,ref release,(uint)Marshal.SizeOf(typeof(JobExtendedLimitInformation))),"clear KILL_ON_JOB_CLOSE after exact accounting");
                    Check(CloseHandle(job),"CloseHandle(controller job)"); job=IntPtr.Zero;
                    safeToRelease=true;
                }
                catch(Exception e)
                {
                    cleanupFailure=e; Console.Error.WriteLine("cleanup failure (restoring fail-closed job custody): {0}: {1}",e.GetType().Name,e.Message); result=2;
                    if(job!=IntPtr.Zero)
                    {
                        var failClosed=CreateLimits(true);
                        if(!SetInformationJobObject(job,JobObjectExtendedLimitInformation,ref failClosed,(uint)Marshal.SizeOf(typeof(JobExtendedLimitInformation))))
                        {
                            int restoreError=Marshal.GetLastWin32Error(); Console.Error.WriteLine("could not restore kill-on-close (error {0}); terminating controller job",restoreError);
                            if(!TerminateJobObject(job,124)) Console.Error.WriteLine("failed to terminate controller job after disposition failure: {0}",Marshal.GetLastWin32Error());
                        }
                    }
                }
            }
            if(client!=null && clientWaited && (pipes==null||pipes.AllJoined)) client.Dispose();
            else if(client!=null) Console.Error.WriteLine("process/pipe handles retained until driver process teardown because exact exit or worker joins were not confirmed");
            if(job!=IntPtr.Zero && !safeToRelease) Console.Error.WriteLine("controller job retains kill-on-close custody until driver process teardown");
            watchdogStop.Set();
            if(!watchdog.Join(Math.Max(1,deadline.Remaining)))
            {
                Console.Error.WriteLine("cleanup failure: exact-process deadline watchdog did not join; terminating exact driver process");
                if(!TerminateProcess(self,124)) Environment.FailFast("could not terminate driver after watchdog join failure");
                Environment.FailFast("driver watchdog remained live at terminal cleanup");
            }
            watchdogStop.Dispose(); selfProcess.Dispose();
            if(cleanupFailure!=null) result=2;
        }
        return result;
    }

    private static JobExtendedLimitInformation CreateLimits(bool killOnClose)
    {
        var value=new JobExtendedLimitInformation();
        value.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_BREAKAWAY_OK|JOB_OBJECT_LIMIT_ACTIVE_PROCESS|JOB_OBJECT_LIMIT_PROCESS_MEMORY|JOB_OBJECT_LIMIT_JOB_MEMORY|(killOnClose?JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:0);
        value.BasicLimitInformation.ActiveProcessLimit=16; value.ProcessMemoryLimit=new UIntPtr(1024UL*1024*1024); value.JobMemoryLimit=new UIntPtr(2UL*1024*1024*1024); return value;
    }
    private static void WatchDeadline(Deadline deadline,ManualResetEvent stop,IntPtr self)
    {
        while(!stop.WaitOne(25))
        {
            if(deadline.Remaining==0) { if(!TerminateProcess(self,124)) Environment.FailFast("whole-driver deadline could not terminate exact driver process"); return; }
        }
    }
    private sealed class BoundedPipes
    {
        private readonly BlockingCollection<string> frames=new BlockingCollection<string>(32);
        private readonly Stream input; private readonly Stream error; private readonly Deadline deadline;
        private readonly Thread reader,drainer; private Exception readerError,drainerError; private long drained; private bool stderrOverflow, allJoined;
        internal bool AllJoined { get { return allJoined; } }
        internal BoundedPipes(Process client,Deadline d)
        {
            input=client.StandardOutput.BaseStream; error=client.StandardError.BaseStream; deadline=d;
            reader=new Thread(ReadFrames) { IsBackground=true, Name="bounded-monitor-frame-reader" };
            drainer=new Thread(DrainErrors) { IsBackground=true, Name="bounded-client-stderr-drainer" }; reader.Start(); drainer.Start();
        }
        private void ReadFrames()
        {
            byte[] line=new byte[512]; int count=0;
            try
            {
                for(;;)
                {
                    int value=input.ReadByte(); if(value<0) { if(count!=0) throw new EndOfStreamException("truncated monitor frame without LF"); AddFrame(null); return; }
                    if(value=='\n') { if(count==0||line[count-1]=='\r') throw new InvalidDataException("empty or CRLF monitor frame"); AddFrame(Encoding.ASCII.GetString(line,0,count)); count=0; continue; }
                    if(value<0x20||value>0x7e||count==line.Length) throw new InvalidDataException("monitor frame is noncanonical or exceeds 512 bytes"); line[count++]=(byte)value;
                }
            }
            catch(Exception e) { readerError=e; try { frames.TryAdd(null,100); } catch { } }
        }
        private void AddFrame(string frame) { while(deadline.Remaining>0) if(frames.TryAdd(frame,100)) return; throw new TimeoutException("bounded monitor frame queue remained full"); }
        private void DrainErrors()
        {
            byte[] chunk=new byte[1024];
            try { int n; while((n=error.Read(chunk,0,chunk.Length))>0) { Interlocked.Add(ref drained,n); if(Interlocked.Read(ref drained)>65536)stderrOverflow=true; } }
            catch(Exception e) { drainerError=e; }
        }
        internal string ReadFrame()
        {
            for(;;) { deadline.Check("monitor frame wait"); string frame; if(frames.TryTake(out frame,Math.Min(100,deadline.Remaining))) { if(frame==null) { if(readerError!=null) throw new IOException("bounded monitor stdout reader failed",readerError); return null; } return frame; } if(readerError!=null) throw new IOException("bounded monitor stdout reader failed",readerError); }
        }
        internal void StopAndJoin(Deadline d)
        {
            Exception closeFailure=null; try { clientClose(); } catch(Exception e) { closeFailure=e; }
            bool readerJoined=reader.Join(Math.Max(1,d.Remaining));
            bool drainerJoined=drainer.Join(Math.Max(1,d.Remaining));
            allJoined=readerJoined&&drainerJoined;
            if(!readerJoined||!drainerJoined) throw new TimeoutException("bounded stdout reader or stderr drainer did not stop");
            if(closeFailure!=null) throw closeFailure;
            if(drainerError!=null) throw new IOException("bounded stderr drain failed",drainerError);
            if(stderrOverflow)throw new InvalidDataException("client stderr exceeded 64 KiB diagnostic cap; stream was drained to avoid pipe deadlock");
        }
        private void clientClose()
        {
            Exception closeFailure=null;
            try { input.Close(); } catch(Exception e) { closeFailure=e; }
            try { error.Close(); } catch(Exception e) { if(closeFailure==null)closeFailure=e; }
            if(closeFailure!=null) throw new IOException("closing bounded client pipe streams failed",closeFailure);
        }
    }

    private static void DriveProtocol(Process client,BoundedPipes pipes,LaunchSpecification specification,string mode,Deadline deadline,ControlState control)
    {
        StreamWriter input=client.StandardInput; byte[] wire=specification.ToWire(); input.NewLine="\n";
        var seenNonces=new HashSet<string>(StringComparer.Ordinal); long sequence=0; int acks=0; string token=null; string replayFrame=null; bool replaySent=false;
        int expectedAcks=(wire.Length+SpecificationTransfer.ChunkBytes-1)/SpecificationTransfer.ChunkBytes+2;
        for(;;)
        {
            deadline.Check("protocol loop"); if(client.HasExited) break;
            string line=pipes.ReadFrame(); if(line==null) break;
            if(line.StartsWith("MONITOR_READY token=",StringComparison.Ordinal))
            {
                token=line.Substring(20); if(token.Length!=32||token.Any(c=>!((c>='0'&&c<='9')||(c>='a'&&c<='f')))) throw new InvalidDataException("invalid transfer token");
                acks=SendTransfer(input,pipes,token,wire,deadline,ref sequence,seenNonces); if(acks!=expectedAcks) throw new InvalidDataException("immutable transfer ACK count mismatch"); control.TransferComplete=true; continue;
            }
            if(line.StartsWith("SPEC-XFER/1 ACK ",StringComparison.Ordinal)) throw new InvalidDataException("unexpected or duplicate transfer acknowledgement");
            if(line.StartsWith("CHALLENGE ",StringComparison.Ordinal))
            {
                string[] f=ParseFreshChallenge(line,ref sequence,seenNonces); string response="RESPONSE "+f[1]+" "+f[2];
                if(control.TransferComplete) control.PostTransferChallenges++;
                if(mode=="replay" && !control.ReplayPrimed && control.PostTransferChallenges>=4) { replayFrame=response; input.WriteLine(response); input.Flush(); control.ReplayPrimed=true; continue; }
                if(mode=="replay" && control.ReplayPrimed) { if(!replaySent) { Thread.Sleep(Math.Min(10000,deadline.Remaining)); deadline.Check("delayed replay control"); input.WriteLine(replayFrame); input.Flush(); replaySent=true; control.ReplaySent=true; } continue; }
                input.WriteLine(response); input.Flush();
                if(mode=="disconnect-alive" && control.PostTransferChallenges>=4 && !control.HostDisconnected) { input.Close(); control.HostDisconnected=true; }
                if(mode=="client-death" && control.PostTransferChallenges>=4) { client.Kill(); control.ClientKilledByDriver=true; return; }
                continue;
            }
            throw new InvalidDataException("unexpected monitor frame: "+line);
        }
        if(mode=="success" && (!control.TransferComplete||acks!=expectedAcks)) throw new InvalidDataException("successful transfer and all exact acknowledgements required");
        if(mode=="disconnect-alive"&&!control.HostDisconnected) throw new InvalidDataException("disconnect control did not occur after transfer");
        if(mode=="replay"&&!control.ReplaySent) throw new InvalidDataException("replay control did not occur after transfer");
    }
    private static int SendTransfer(StreamWriter input,BoundedPipes pipes,string token,byte[] wire,Deadline d,ref long sequence,HashSet<string> nonces)
    {
        int responses=0,chunks=(wire.Length+SpecificationTransfer.ChunkBytes-1)/SpecificationTransfer.ChunkBytes;
        SendAndAck(input,pipes,d,"SPEC-XFER/1 BEGIN "+token+" "+wire.Length.ToString(CultureInfo.InvariantCulture)+" "+chunks.ToString(CultureInfo.InvariantCulture),"SPEC-XFER/1 ACK "+token+" BEGIN",ref responses,ref sequence,nonces);
        for(int i=0;i<chunks;i++) { int n=Math.Min(SpecificationTransfer.ChunkBytes,wire.Length-i*SpecificationTransfer.ChunkBytes); byte[] part=new byte[n]; Buffer.BlockCopy(wire,i*SpecificationTransfer.ChunkBytes,part,0,n); SendAndAck(input,pipes,d,"SPEC-XFER/1 DATA "+token+" "+i.ToString(CultureInfo.InvariantCulture)+" "+Convert.ToBase64String(part),"SPEC-XFER/1 ACK "+token+" DATA "+i.ToString(CultureInfo.InvariantCulture),ref responses,ref sequence,nonces); }
        SendAndAck(input,pipes,d,"SPEC-XFER/1 END "+token,"SPEC-XFER/1 ACK "+token+" END",ref responses,ref sequence,nonces); return chunks+2;
    }
    private static void SendAndAck(StreamWriter input,BoundedPipes pipes,Deadline d,string frame,string expected,ref int responses,ref long sequence,HashSet<string> nonces)
    {
        d.Check("transfer write"); input.WriteLine(frame); input.Flush();
        for(;;) { d.Check("transfer ACK"); string line=pipes.ReadFrame(); if(line==null) throw new EndOfStreamException("EOF before exact transfer ACK"); if(line==expected)return; if(line.StartsWith("CHALLENGE ",StringComparison.Ordinal)) { string[] f=ParseFreshChallenge(line,ref sequence,nonces); input.WriteLine("RESPONSE "+f[1]+" "+f[2]); input.Flush(); responses++; continue; } throw new InvalidDataException("unexpected transfer frame"); }
    }
    private static string[] ParseFreshChallenge(string line,ref long sequence,HashSet<string> nonces)
    {
        string[] f=line.Split(' '); long next;
        if(f.Length!=3||f[0]!="CHALLENGE"||!Int64.TryParse(f[1],NumberStyles.None,CultureInfo.InvariantCulture,out next)||next<=sequence||next.ToString(CultureInfo.InvariantCulture)!=f[1]||f[2].Length!=32||f[2].Any(c=>!((c>='0'&&c<='9')||(c>='a'&&c<='f')))||!nonces.Add(f[2])) throw new InvalidDataException("challenge is malformed, stale, or nonce-reused");
        sequence=next; return f;
    }
    private static bool Hex8(string value,out string canonical)
    { canonical=null; uint parsed; if(value==null||value.Length!=8||!UInt32.TryParse(value,NumberStyles.AllowHexSpecifier,CultureInfo.InvariantCulture,out parsed))return false; canonical=parsed.ToString("X8",CultureInfo.InvariantCulture); return true; }

    // This pure bounded decoder and semantic validator are also called directly
    // by source-only C# fixtures; no filesystem or process APIs are involved.
    internal static string[] DecodeJournalFrames(byte[] bytes)
    {
        if(bytes==null||bytes.Length==0||bytes.Length>MaximumJournalBytes) throw new InvalidDataException("journal byte bound");
        var records=new List<string>(MaximumRecords); int at=0;
        while(at<bytes.Length)
        {
            if(records.Count==MaximumRecords||bytes.Length-at<15) throw new InvalidDataException("journal record/count bound or truncated header");
            int length=Hex(bytes,at,4); if(bytes[at+4]!=':'||bytes[at+13]!=':'||length<1||length>MaximumRecordBytes) throw new InvalidDataException("journal header malformed or record too large");
            uint crc=(uint)Hex(bytes,at+5,8); at+=14; if(bytes.Length-at<length+1)throw new InvalidDataException("truncated journal body");
            for(int i=0;i<length;i++) if(bytes[at+i]<0x20||bytes[at+i]>0x7e)throw new InvalidDataException("journal body is not printable ASCII");
            if(bytes[at+length]!='\n')throw new InvalidDataException("journal frame lacks mandatory LF");
            byte[] body=new byte[length]; Buffer.BlockCopy(bytes,at,body,0,length); if(Crc32(body)!=crc)throw new InvalidDataException("journal CRC mismatch");
            records.Add(Encoding.ASCII.GetString(body)); at+=length+1;
        }
        return records.ToArray();
    }
    internal static JournalReport ParseJournalForFixture(byte[] bytes,string root)
    { return ParseRecords(DecodeJournalFrames(bytes),root); }
    private static int Hex(byte[] b,int start,int count)
    { int value=0; for(int i=0;i<count;i++) { int c=b[start+i],n=c>='0'&&c<='9'?c-'0':c>='A'&&c<='F'?c-'A'+10:-1; if(n<0)throw new InvalidDataException("journal hex is not canonical uppercase"); value=(value<<4)|n; } return value; }
    private static JournalReport ParseRecords(string[] records,string root)
    {
        if(records.Length!=8)throw new InvalidDataException("journal must contain the exact eight-record completion grammar");
        string[] types={"INTENT","IDENTITY","STAGED","LIFECYCLE","EVIDENCE","OUTCOME","REMOVE_INTENT","REMOVED"};
        string[] fields={"","","","","proof,exit,supervision,evidence_identity,manifest,stdout,stderr,runtime_bytes,logs_bytes,deadline","payload,supervision,cleanup,diagnostics_saved,local_metadata_saved,payload_evidence_saved,evidence,evidence_identity,evidence_bytes,host_exported,runtime_removed","",""};
        string invocation=null, parent=null, journalId=null, runtimeId=null, evidenceId=null; var report=new JournalReport();
        for(int i=0;i<records.Length;i++)
        {
            string[] p=records[i].Split('|'); if(p.Length<2||p[0]!=types[i]||!GuidN(p[1]))throw new InvalidDataException("journal record grammar/order invalid");
            if(invocation==null)invocation=p[1]; else if(invocation!=p[1])throw new InvalidDataException("invocation identity mismatch");
            if(i==0)
            {
                if(p.Length!=6||!SameDirectChild(root,p[2],"scoped-")||!SameDirectChild(root,p[3],".scoped-run-")||!CanonicalJournalName(Path.GetFileName(p[3]))||!FileIdentityText(p[4])||!FileIdentityText(p[5]))throw new InvalidDataException("INTENT fields/path invalid");
                report.RuntimePath=p[2]; report.Path=p[3]; parent=p[4]; journalId=p[5];
                if(Path.GetFileName(p[2])!="scoped-"+invocation)throw new InvalidDataException("INTENT runtime name does not match invocation");
            }
            if(i==1) { if(p.Length!=5||p[4]!=journalId||!FileIdentityText(p[2])||!FileIdentityText(p[3]))throw new InvalidDataException("IDENTITY fields invalid"); runtimeId=p[2]; if(p[3]!=parent)throw new InvalidDataException("allocation parent identity mismatch"); }
            if(i==2) { ulong entries,bytes; if(p.Length!=7||!CanonicalUInt64(p[2],out entries)||entries==0||entries>2048||!CanonicalUInt64(p[3],out bytes)||bytes>512UL*1024*1024||!Hash64(p[4])||!Hash64(p[5])||!FileIdentityText(p[6]))throw new InvalidDataException("STAGED fields invalid or over the staging inventory/byte caps"); }
            if(i==3) { ulong lifecycleDeadline; if(p.Length!=7||p[2]!=runtimeId||!p[3].StartsWith("deadline=",StringComparison.Ordinal)||!CanonicalUInt64(p[3].Substring(9),out lifecycleDeadline)||p[4]!="operation=NONE"||p[5]!="cleanup=NONE"||p[6]!="cleanup_confirmed=1")throw new InvalidDataException("LIFECYCLE is not clean"); }
            if(i==4) { Dictionary<string,string> evidence=ParseKeyValueRecord(p,types[i],fields[i],2,runtimeId); evidenceId=evidence["evidence_identity"]; ulong runtimeBytes,logBytes,evidenceDeadline; if(evidence["proof"]!="EXACT"||!IsExit(evidence["exit"])||!IsSupervision(evidence["supervision"])||!FileIdentityText(evidenceId)||!Hash64(evidence["manifest"])||!Hash64(evidence["stdout"])||!Hash64(evidence["stderr"])||!CanonicalUInt64(evidence["runtime_bytes"],out runtimeBytes)||runtimeBytes>512UL*1024*1024||!CanonicalUInt64(evidence["logs_bytes"],out logBytes)||!CanonicalUInt64(evidence["deadline"],out evidenceDeadline)||logBytes>(ulong)(MaximumEvidenceLogBytes*2L))throw new InvalidDataException("evidence fields are invalid or over bounds"); foreach(var pair in evidence) report.Evidence.Add(pair.Key,pair.Value); }
            if(i==5)
            {
                var outFields=ParseKeyValueRecord(p,types[i],fields[i],2,runtimeId); report.PayloadExit=outFields["payload"]; report.Supervision=outFields["supervision"]; ulong evidenceBytes;
                if(!IsExit(report.PayloadExit)||!IsSupervision(report.Supervision)||outFields["cleanup"]!="CONFIRMED"||outFields["diagnostics_saved"]!="1"||outFields["local_metadata_saved"]!="1"||outFields["payload_evidence_saved"]!="1"||outFields["evidence_identity"]!=evidenceId||!FileIdentityText(outFields["evidence_identity"])||outFields["evidence"]!=report.Evidence["manifest"]||!CanonicalUInt64(outFields["evidence_bytes"],out evidenceBytes)||evidenceBytes>(ulong)(MaximumEvidenceLogBytes*2L+8L*1024*1024)||outFields["host_exported"]!="0"||outFields["runtime_removed"]!="0")throw new InvalidDataException("OUTCOME does not exactly bind evidence and cleanup");
                report.CleanupConfirmed=true; report.HostExported=false; report.EvidenceIdentity=evidenceId;
            }
            if(i==6) { if(p.Length!=4||p[2]!=runtimeId||p[3]!=parent)throw new InvalidDataException("REMOVE_INTENT identity mismatch"); }
            if(i==7) { if(p.Length!=4||p[2]!=runtimeId||p[3]!=parent)throw new InvalidDataException("REMOVED identity mismatch"); report.Removed=true; }
        }
        report.Invocation=invocation; report.RuntimeIdentity=runtimeId;
        if(!report.RuntimePath.StartsWith(root+"\\scoped-",StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("runtime path escaped fixed root");
        return report;
    }
    private static Dictionary<string,string> ParseKeyValueRecord(string[] p,string type,string expected,int prefix,string runtime)
    {
        if(p.Length<3||p[2]!=runtime)throw new InvalidDataException(type+" fixed fields invalid");
        var keys=expected.Split(','); if(p.Length!=3+keys.Length)throw new InvalidDataException(type+" key count invalid"); var values=new Dictionary<string,string>(StringComparer.Ordinal);
        for(int i=0;i<keys.Length;i++) { string tag=keys[i]+"="; string pair=p[3+i]; if(!pair.StartsWith(tag,StringComparison.Ordinal)||pair.Length==tag.Length)throw new InvalidDataException(type+" key order/value invalid"); values.Add(keys[i],pair.Substring(tag.Length)); }
        return values;
    }
    private static bool GuidN(string s) { Guid g; return s.Length==32&&Guid.TryParseExact(s,"N",out g)&&g.ToString("N")==s; }
    private static bool Hash64(string s) { return s!=null&&s.Length==64&&s.All(c=>(c>='0'&&c<='9')||(c>='A'&&c<='F')); }
    private static bool FileIdentityText(string s) { return s!=null&&s.Length==49&&s[16]==':'&&s.Count(c=>c==':')==1&&s.All(c=>c==':'||(c>='0'&&c<='9')||(c>='A'&&c<='F')); }
    private static bool CanonicalUInt64(string s,out ulong value) { return UInt64.TryParse(s,NumberStyles.None,CultureInfo.InvariantCulture,out value)&&value.ToString(CultureInfo.InvariantCulture)==s; }
    private static bool IsExit(string s) { string canonical; return s=="NONE"||Hex8(s,out canonical)&&canonical==s; }
    private static bool IsSupervision(string s) { return s=="PayloadExited"||s=="MonitorStopped"||s=="TransitionFailed"; }
    private static bool SameDirectChild(string root,string path,string prefix)
    { string fullRoot=Path.GetFullPath(root).TrimEnd('\\'); string full=Path.GetFullPath(path); string parent=Path.GetDirectoryName(full); return String.Equals(parent,fullRoot,StringComparison.OrdinalIgnoreCase)&&Path.GetFileName(full).StartsWith(prefix,StringComparison.OrdinalIgnoreCase); }
    private static bool CanonicalJournalName(string name)
    {
        const string prefix=".scoped-run-", suffix=".journal";
        return name.Length==prefix.Length+32+suffix.Length&&name.StartsWith(prefix,StringComparison.Ordinal)&&name.EndsWith(suffix,StringComparison.Ordinal)&&GuidN(name.Substring(prefix.Length,32));
    }
    private static void BindOpenedJournal(JournalReport report,string openedPath,string root)
    {
        if(!SameDirectChild(root,openedPath,".scoped-run-")||!CanonicalJournalName(Path.GetFileName(openedPath))||!String.Equals(Path.GetFullPath(report.Path),Path.GetFullPath(openedPath),StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("INTENT journal path does not match the independently opened journal");
        report.Path=openedPath;
    }
    internal static void BindOpenedJournalForFixture(JournalReport report,string openedPath,string root)
    { BindOpenedJournal(report,openedPath,root); }
    internal static void ValidateModeForFixture(JournalReport report,string mode,string expectedPayloadExit,int clientExit,bool actionPerformed)
    { ValidateMode(report,mode,expectedPayloadExit,clientExit,new ControlState { TransferComplete=true, ClientKilledByDriver=mode=="client-death"&&actionPerformed, HostDisconnected=mode=="disconnect-alive"&&actionPerformed, ReplaySent=mode=="replay"&&actionPerformed }); }
    private static void ValidateMode(JournalReport r,string mode,string expected,string clientExit,ControlState c) { uint x; if(!UInt32.TryParse(clientExit,NumberStyles.AllowHexSpecifier,CultureInfo.InvariantCulture,out x))throw new InvalidDataException("client exit malformed"); ValidateMode(r,mode,expected,(int)x,c); }
    private static void ValidateMode(JournalReport r,string mode,string expected,int clientExit,ControlState c)
    {
        if(!r.CleanupConfirmed||!r.Removed||r.HostExported||r.Evidence["exit"]!=r.PayloadExit||r.Evidence["supervision"]!=r.Supervision)throw new InvalidDataException("completion receipt or evidence binding absent");
        if(mode=="success") { if(!c.TransferComplete||r.Supervision!="PayloadExited"||r.PayloadExit!=expected||clientExit!=78)throw new InvalidDataException("success does not match exact payload/client exit contract"); }
        else { bool action=mode=="disconnect-alive"?c.HostDisconnected:mode=="client-death"?c.ClientKilledByDriver:c.ReplaySent; int expectedClient=mode=="client-death"?1:78; if(!c.TransferComplete||!action||r.Supervision!="MonitorStopped"||expected!="0000007D"||r.PayloadExit!=expected||clientExit!=expectedClient)throw new InvalidDataException("negative control lacks its exact action, expected job-termination payload exit 0000007D, MonitorStopped outcome, or client exit"); }
    }

    private static string[] SnapshotJournals(Deadline d)
    {
        d.Check("journal inventory"); if(!Directory.Exists(RunsRoot))return new string[0]; RejectReparse(RunsRoot);
        var paths=new List<string>(MaximumJournalInventory+1); foreach(string p in Directory.EnumerateFiles(RunsRoot,".scoped-run-*.journal",SearchOption.TopDirectoryOnly)) { d.Check("bounded journal inventory"); RejectReparse(p); paths.Add(p); if(paths.Count>MaximumJournalInventory)throw new InvalidDataException("journal inventory exceeds 512 entries"); }
        return paths.ToArray();
    }
    private static JournalReport ReadSingleNewJournal(string[] before,string[] after,Deadline d)
    {
        var old=new HashSet<string>(before,StringComparer.OrdinalIgnoreCase); string[] added=after.Where(p=>!old.Contains(p)).ToArray(); if(added.Length!=1)throw new InvalidDataException("expected exactly one new journal");
        d.Check("journal open/readback"); RejectReparse(added[0]); byte[] bytes;
        using(var fs=new FileStream(added[0],FileMode.Open,FileAccess.Read,FileShare.Read)) { if(fs.Length<=0||fs.Length>MaximumJournalBytes)throw new InvalidDataException("journal size bound"); bytes=new byte[(int)fs.Length]; int at=0,n; while(at<bytes.Length) { d.Check("bounded journal read"); n=fs.Read(bytes,at,Math.Min(4096,bytes.Length-at)); if(n<=0)throw new EndOfStreamException("journal changed during readback"); at+=n; } if(fs.ReadByte()!=-1)throw new InvalidDataException("journal grew past prechecked bound"); }
        JournalReport r=ParseRecords(DecodeJournalFrames(bytes),RunsRoot); BindOpenedJournal(r,added[0],RunsRoot); if(Directory.Exists(r.RuntimePath))RejectReparse(r.RuntimePath); return r;
    }
    private static void VerifyEvidence(JournalReport r,Deadline d)
    {
        string directory=Path.Combine(RunsRoot,".scoped-evidence-"+r.Invocation); RejectReparse(directory);
        VerifyHash(Path.Combine(directory,"manifest.txt"),r.Evidence["manifest"],8L*1024*1024,d);
        VerifyHash(Path.Combine(directory,"stdout.log"),r.Evidence["stdout"],MaximumEvidenceLogBytes,d);
        VerifyHash(Path.Combine(directory,"stderr.log"),r.Evidence["stderr"],MaximumEvidenceLogBytes,d);
    }
    private static void VerifyHash(string path,string expected,long max,Deadline d)
    {
        RejectReparse(path); using(var input=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)) using(var sha=SHA256.Create())
        { if(input.Length<0||input.Length>max)throw new InvalidDataException("evidence length bound"); byte[] b=new byte[65536]; int n; while((n=input.Read(b,0,b.Length))>0) { d.Check("evidence hash"); sha.TransformBlock(b,0,n,b,0); } sha.TransformFinalBlock(new byte[0],0,0); string actual=BitConverter.ToString(sha.Hash).Replace("-",""); if(!String.Equals(actual,expected,StringComparison.Ordinal))throw new InvalidDataException("evidence hash mismatch"); }
    }
    private static void RejectReparse(string path) { FileAttributes a=File.GetAttributes(path); if((a&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException("reparse point refused: "+Path.GetFileName(path)); }
    private static uint Crc32(byte[] bytes) { uint crc=0xffffffff; foreach(byte b in bytes) { crc^=b; for(int i=0;i<8;i++)crc=(crc&1)!=0?0xedb88320^(crc>>1):crc>>1; } return ~crc; }
    private static void PrintReport(JournalReport r,int exit,string mode,ControlState c)
    { bool action=mode=="success"?c.TransferComplete:mode=="disconnect-alive"?c.HostDisconnected:mode=="client-death"?c.ClientKilledByDriver:c.ReplaySent; Console.WriteLine("CLIENT_EXIT=0x{0:X8}",exit); Console.WriteLine("MODE={0};ACTION_CONFIRMED={1};POST_TRANSFER_CHALLENGES={2}",mode,action,c.PostTransferChallenges); Console.WriteLine("JOURNAL={0}",r.Path); Console.WriteLine("RUNTIME={0}",r.RuntimePath); Console.WriteLine("RUNTIME_IDENTITY={0}",r.RuntimeIdentity); Console.WriteLine("PAYLOAD_EXIT={0}",r.PayloadExit); Console.WriteLine("SUPERVISION={0}",r.Supervision); Console.WriteLine("CLEANUP_CONFIRMED={0}",r.CleanupConfirmed); Console.WriteLine("RUNTIME_REMOVED={0}",r.Removed); Console.WriteLine("HOST_EXPORTED={0}",r.HostExported); }
    private static void Check(bool ok,string operation) { if(!ok)throw new InvalidOperationException(operation+" failed: "+Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture)); }
}
