// Pure source fixture for the native acceptance driver's parser and controls.
// It creates byte arrays only: no processes, filesystem objects, or Win32 calls.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

internal static class MonitorAcceptanceDriverFixture
{
    private static int assertions;
    private static void Expect(string name,bool ok) { assertions++; if(!ok)throw new InvalidOperationException("FAILED: "+name); }
    private static byte[] Journal(params string[] records)
    {
        var output=new List<byte>(); foreach(string record in records)
        {
            byte[] body=Encoding.ASCII.GetBytes(record); string header=body.Length.ToString("X4",CultureInfo.InvariantCulture)+":"+Crc32(body).ToString("X8",CultureInfo.InvariantCulture)+":";
            output.AddRange(Encoding.ASCII.GetBytes(header)); output.AddRange(body); output.Add((byte)'\n');
        }
        return output.ToArray();
    }
    private static uint Crc32(byte[] bytes) { uint crc=0xffffffff; foreach(byte b in bytes) { crc^=b; for(int i=0;i<8;i++)crc=(crc&1)!=0?0xedb88320^(crc>>1):crc>>1; } return ~crc; }
    private static string[] ValidRecords(string supervision="PayloadExited",string exit="0000002A")
    {
        string id="0123456789abcdef0123456789abcdef", runtime=@"C:\RhaiQuality\runs\scoped-"+id,
            journal=@"C:\RhaiQuality\runs\.scoped-run-"+id+".journal", parent="0000000000000001:11111111111111111111111111111111",
            journalId="0000000000000002:22222222222222222222222222222222", runtimeId="0000000000000003:33333333333333333333333333333333",
            evidenceId="0000000000000004:44444444444444444444444444444444", exeId="0000000000000005:55555555555555555555555555555555",
            hash=new string('A',64), digest=new string('B',64);
        return new [] {
            "INTENT|"+id+"|"+runtime+"|"+journal+"|"+parent+"|"+journalId,
            "IDENTITY|"+id+"|"+runtimeId+"|"+parent+"|"+journalId,
            "STAGED|"+id+"|1|10|"+hash+"|"+hash+"|"+exeId,
            "LIFECYCLE|"+id+"|"+runtimeId+"|deadline=123|operation=NONE|cleanup=NONE|cleanup_confirmed=1",
            "EVIDENCE|"+id+"|"+runtimeId+"|proof=EXACT|exit="+exit+"|supervision="+supervision+"|evidence_identity="+evidenceId+"|manifest="+hash+"|stdout="+digest+"|stderr="+digest+"|runtime_bytes=10|logs_bytes=0|deadline=123",
            "OUTCOME|"+id+"|"+runtimeId+"|payload="+exit+"|supervision="+supervision+"|cleanup=CONFIRMED|diagnostics_saved=1|local_metadata_saved=1|payload_evidence_saved=1|evidence="+hash+"|evidence_identity="+evidenceId+"|evidence_bytes=10|host_exported=0|runtime_removed=0",
            "REMOVE_INTENT|"+id+"|"+runtimeId+"|"+parent,
            "REMOVED|"+id+"|"+runtimeId+"|"+parent
        };
    }
    private static bool Rejects(byte[] bytes,string root)
    { try { MonitorAcceptanceDriver.ParseJournalForFixture(bytes,root); return false; } catch(FormatException) { return true; } catch(InvalidOperationException) { return true; } catch(System.IO.InvalidDataException) { return true; } }
    private static bool RejectsMode(MonitorAcceptanceDriver.JournalReport report,string mode,string expected,int clientExit,bool action)
    { try { MonitorAcceptanceDriver.ValidateModeForFixture(report,mode,expected,clientExit,action); return false; } catch(System.IO.InvalidDataException) { return true; } }
    internal static void Run()
    {
        const string root=@"C:\RhaiQuality\runs"; string[] good=ValidRecords();
        var report=MonitorAcceptanceDriver.ParseJournalForFixture(Journal(good),root);
        MonitorAcceptanceDriver.ValidateModeForFixture(report,"success","0000002A",78,true);
        Expect("canonical complete journal and matching success contract accepted",true);
        byte[] torn=Journal(good); Array.Resize(ref torn,torn.Length-1); Expect("missing final LF rejected before semantic use",Rejects(torn,root));
        Expect("declared oversized record rejected from header before body allocation",Rejects(Encoding.ASCII.GetBytes("1001:00000000:\n"),root));
        byte[] badCrc=Journal(good); badCrc[5]=(byte)'0'; Expect("CRC mismatch rejected",Rejects(badCrc,root));
        string[] duplicate=(string[])good.Clone(); duplicate[4]=duplicate[3]; Expect("duplicate and reordered record rejected",Rejects(Journal(duplicate),root));
        string[] extra=new string[9]; Array.Copy(good,extra,good.Length); extra[8]="REMOVED|0123456789abcdef0123456789abcdef|unexpected|identity"; Expect("extra/duplicate terminal record rejected",Rejects(Journal(extra),root));
        string[] mismatch=(string[])good.Clone(); mismatch[1]=mismatch[1].Replace("0000000000000001","0000000000000009"); Expect("identity relationship mismatch rejected",Rejects(Journal(mismatch),root));
        string[] overEntries=(string[])good.Clone(); overEntries[2]=overEntries[2].Replace("|1|10|","|2049|10|"); Expect("staged inventory above fixed cap rejected",Rejects(Journal(overEntries),root));
        string[] overRuntime=(string[])good.Clone(); overRuntime[4]=overRuntime[4].Replace("runtime_bytes=10","runtime_bytes=536870913"); Expect("evidence runtime bytes above fixed cap rejected",Rejects(Journal(overRuntime),root));
        string[] control=ValidRecords("MonitorStopped","NONE"); control[5]=control[5].Replace("payload=NONE","payload=0000000000000000"); Expect("malformed negative-control outcome rejected",Rejects(Journal(control),root));
        var stopped=MonitorAcceptanceDriver.ParseJournalForFixture(Journal(ValidRecords("MonitorStopped","0000007D")),root);
        bool badActionRejected=RejectsMode(stopped,"client-death","0000007D",1,false);
        Expect("client-death cannot pass without driver kill action",badActionRejected);
        MonitorAcceptanceDriver.ValidateModeForFixture(stopped,"client-death","0000007D",1,true);
        Expect("client-death passes only with MonitorStopped, job-terminated payload exit, and observed driver kill",true);
        bool badControlExitRejected=RejectsMode(stopped,"client-death","0000007D",78,true);
        Expect("client-death requires exact client exit code",badControlExitRejected);
        bool missingTerminationRejected=RejectsMode(stopped,"client-death","0000002A",1,true);
        Expect("negative control requires payload exit from exact job termination",missingTerminationRejected);
        bool badExitRejected=RejectsMode(report,"success","0000002A",1,true);
        Expect("success requires exact client exit",badExitRejected);
        Console.WriteLine("MonitorAcceptanceDriverFixture assertions={0}",assertions);
    }
    public static int Main() { Run(); return 0; }
}
