// Source-only contract fixture for the production monitor intake dispatcher.
// Uses memory streams and deterministic time; it does not launch processes or
// allocate custody/runtime resources. This fixture has not been executed.
using System;
using System.IO;
using System.Text;

internal static class MonitorSpecificationIntakeFixture
{
    private const string Token = "00112233445566778899aabbccddeeff";
    private const string Source = @"Z:\never-created\source";
    private const string Executable = @"bin\runner.exe";
    private static int failures;

    public static int Main()
    {
        OriginalFrameReaderFixtures();
        DispatcherInterleaveFixtures();
        QueueAndTerminalFixtures();
        MaintenanceHandshakeFixtures();
        AdmissionDeadlineFixtures();
        return failures == 0 ? 0 : 1;
    }

    private static void OriginalFrameReaderFixtures()
    {
        byte[] accepted = new byte[512];
        for (int i = 0; i < accepted.Length - 1; i++) accepted[i] = (byte)'A';
        accepted[accepted.Length - 1] = (byte)'\n';
        byte[] actual = ReadOne(accepted);
        Expect("511 content bytes plus LF are accepted as 512 original bytes", Equal(accepted, actual));

        byte[] overlong = new byte[513];
        for (int i = 0; i < overlong.Length - 1; i++) overlong[i] = (byte)'A';
        overlong[overlong.Length - 1] = (byte)'\n';
        ExpectReadFailure("512 content bytes plus LF exceed frame bound", overlong);
        ExpectReadFailure("partial EOF is rejected", Encoding.ASCII.GetBytes("RESPONSE 1 nonce"));

        byte[] crlf = Encoding.ASCII.GetBytes("SPEC-XFER/1 BEGIN " + Token + " 8 1\r\n");
        var crlfDispatcher = NewDispatcher(new FakeClock(1), 0, 12);
        crlfDispatcher.Start();
        Expect("CRLF is rejected rather than normalized", !crlfDispatcher.Dispatch(ReadOne(crlf)) && crlfDispatcher.Stopped);

        var responseCrLf = NewDispatcher(new FakeClock(1), 0, 12);
        responseCrLf.Start();
        Expect("RESPONSE CRLF framing is rejected", !responseCrLf.Dispatch(ReadOne(Encoding.ASCII.GetBytes("RESPONSE 1 " + Token + "\r\n"))) && responseCrLf.Stopped);
        var responseNumber = NewDispatcher(new FakeClock(1), 0, 12);
        responseNumber.Start();
        Expect("noncanonical RESPONSE sequence is rejected", !responseNumber.Dispatch(ReadOne(Encoding.ASCII.GetBytes("RESPONSE 01 " + Token + "\n"))) && responseNumber.Stopped);

        byte[] invalidUtf8 = new byte[] { 0xff, (byte)'\n' };
        var utf8Dispatcher = NewDispatcher(new FakeClock(1), 0, 12);
        utf8Dispatcher.Start();
        Expect("invalid UTF-8 stops monitor intake", !utf8Dispatcher.Dispatch(ReadOne(invalidUtf8)) && utf8Dispatcher.Stopped);
    }

    private static void DispatcherInterleaveFixtures()
    {
        var clock = new FakeClock(0);
        var dispatcher = NewDispatcher(clock, 0, 120, new LeaseMonitor.Policy(2, 5, 120, 300, 5, 5));
        Expect("ready frame advertises monitor-issued token", dispatcher.Start() && IsReady(Drain(dispatcher.Outgoing), Token));
        Expect("monitor issues a fresh phase-bound setup challenge", dispatcher.TryIssueChallenge());
        byte[] challengeFrame = Drain(dispatcher.Outgoing);
        long sequence; string nonce;
        Expect("challenge frame carries canonical sequence and nonce", TryChallenge(challengeFrame, out sequence, out nonce));
        clock.Now = 1;
        Expect("valid setup response renews lease without authorizing work", dispatcher.Dispatch(Response(sequence, nonce)) && dispatcher.Protocol.State == LeaseMonitor.State.Ready);
        Expect("setup response does not create/resume authority", !dispatcher.Protocol.AuthorizeCreate(1) && !dispatcher.Protocol.AuthorizeResume(1));

        LaunchSpecification specification = CreateMaximumWireSpecification();
        var sender = new SpecificationTransfer.Sender(specification, Token, 120);
        int ackCount = 0;
        byte[] frame = sender.Start(2);
        for (int i = 0; i < SpecificationTransfer.MaximumTransferFrames && frame != null; i++)
        {
            clock.Now = 2 + i;
            Expect("production dispatcher accepts transfer frame " + i, dispatcher.Dispatch(frame));
            byte[] ack = Drain(dispatcher.Outgoing);
            Expect("production dispatcher queues matching bounded ACK " + i, ack != null && ack.Length <= SpecificationTransfer.MaximumAcknowledgementBytes);
            if (ack == null) break;
            ackCount++;
            sender.AcceptAcknowledgement(ack, clock.Now);
            frame = sender.HasOutstandingFrame ? sender.GetPendingFrame(clock.Now) : null;
            if (clock.Now >= 2 && clock.Now % 2 == 0 && i < SpecificationTransfer.MaximumTransferFrames - 1)
            {
                Expect("challenge renewal can interleave between transfer frames", dispatcher.TryIssueChallenge());
                byte[] renewal = Drain(dispatcher.Outgoing);
                long renewalSequence; string renewalNonce;
                Expect("interleaved renewal challenge is canonical", TryChallenge(renewal, out renewalSequence, out renewalNonce));
                Expect("interleaved valid RESPONSE renews lease without authorization", dispatcher.Dispatch(Response(renewalSequence, renewalNonce)) && dispatcher.Protocol.State == LeaseMonitor.State.Ready);
            }
        }
        LaunchSpecification completed = dispatcher.CompletedSpecification;
        Expect("dispatcher completes exact immutable specification intake", completed != null && completed.SourceDirectory == Source && sender.State == SpecificationTransfer.SenderState.Completed);
        if (completed == null) return;
        string[] completedArgs = completed.Arguments;
        completedArgs[0] = "mutated";
        Expect("dispatcher retains immutable completed specification", completed.Arguments[0] != "mutated");
        Expect("transfer ACKs do not authorize create or resume", !dispatcher.Protocol.AuthorizeCreate(clock.Now) && !dispatcher.Protocol.AuthorizeResume(clock.Now));
        Expect("maximum-input transfer dispatch uses exact BEGIN/DATA/END receipt count", specification.ToWire().Length == LaunchSpecification.MaximumWireBytes && ackCount == SpecificationTransfer.CountChunks(specification.ToWire().Length) + 2);
        Expect("completed intake rejects replay terminally", !dispatcher.Dispatch(frame ?? Begin(Token, specification)) && dispatcher.Stopped);
    }

    private static void QueueAndTerminalFixtures()
    {
        var pressureClock = new FakeClock(1);
        var pressure = NewDispatcher(pressureClock, 0, 12);
        Expect("pressure dispatcher starts", pressure.Start());
        Drain(pressure.Outgoing);
        for (int i = 0; i < 32; i++) Expect("queue pressure fixture fills frame slot " + i, pressure.Outgoing.TryWrite(new byte[256]));
        Expect("queue pressure stops dispatcher without blocking", !pressure.Dispatch(Begin(Token, LaunchSpecification.Create(Source, Executable, new string[0]))) && pressure.Stopped);

        var wrongToken = NewDispatcher(new FakeClock(1), 0, 12);
        wrongToken.Start(); Drain(wrongToken.Outgoing);
        Expect("wrong transfer token stops dispatcher", !wrongToken.Dispatch(Begin("ffeeddccbbaa99887766554433221100", LaunchSpecification.Create(Source, Executable, new string[0]))) && wrongToken.Stopped);

        var replay = NewDispatcher(new FakeClock(1), 0, 12);
        replay.Start(); Drain(replay.Outgoing);
        LaunchSpecification spec = LaunchSpecification.Create(Source, Executable, new string[0]);
        var sender = new SpecificationTransfer.Sender(spec, Token, 12);
        byte[] begin = sender.Start(1);
        Expect("first BEGIN is dispatched", replay.Dispatch(begin)); Drain(replay.Outgoing);
        Expect("active BEGIN replay stops dispatcher", !replay.Dispatch(begin) && replay.Stopped);

        var expiryClock = new FakeClock(1);
        var expiry = NewDispatcher(expiryClock, 0, 12);
        expiry.Start(); Drain(expiry.Outgoing);
        var expirySender = new SpecificationTransfer.Sender(spec, Token, 12);
        byte[] start = expirySender.Start(1);
        Expect("expiry case accepts BEGIN before deadline", expiry.Dispatch(start)); Drain(expiry.Outgoing);
        expiryClock.Now = 12;
        Expect("frame at fixed setup deadline stops intake", !expiry.Dispatch(expirySender.GetPendingFrame(11)) && expiry.Stopped);

        var endAdmissionClock = new ArmedClock(1);
        var endAdmissionPolicy = new LeaseMonitor.Policy(2, 30, 12, 60, 5, 5);
        var endAdmission = NewDispatcher(endAdmissionClock.Read, 0, 12, endAdmissionPolicy);
        endAdmission.Start(); Drain(endAdmission.Outgoing);
        byte[] wire = spec.ToWire();
        bool beginAccepted = endAdmission.Dispatch(Begin(Token, spec));
        byte[] beginAck = Drain(endAdmission.Outgoing);
        Expect("END equality setup fixture accepts BEGIN with its ACK", beginAccepted && beginAck != null);
        if (!beginAccepted || beginAck == null) return;
        bool dataAccepted = endAdmission.Dispatch(Data(Token, 0, wire));
        byte[] dataAck = Drain(endAdmission.Outgoing);
        Expect("END equality setup fixture accepts DATA with its ACK", dataAccepted && dataAck != null);
        if (!dataAccepted || dataAck == null) return;
        endAdmissionClock.Arm(9, 12);
        Expect("END accepted before deadline but ACK admission at equality stops monitor", !endAdmission.Dispatch(End(Token)) && endAdmission.Stopped);
        Expect("END deadline equality never queues a receipt", Drain(endAdmission.Outgoing) == null);
        Expect("END equality reaches both processing and ACK-admission clock reads", endAdmissionClock.ArmedReads == 2 && endAdmission.CompletedSpecification == null);

        var leaseClock = new FakeClock(1);
        var lease = NewDispatcher(leaseClock, 0, 12);
        lease.Start(); Drain(lease.Outgoing);
        Expect("BEGIN is accepted and acknowledgement queued before lease expiry", lease.Dispatch(Begin(Token, spec)) && Drain(lease.Outgoing) != null);
        leaseClock.Now = 5;
        Expect("transfer receipt cannot extend short lease", !lease.Poll() && lease.Stopped);

        var renewClock = new FakeClock(0);
        var renew = NewDispatcher(renewClock, 0, 12);
        renew.Start(); Drain(renew.Outgoing);
        renew.TryIssueChallenge();
        long seq; string nonce;
        Expect("renewal challenge is available", TryChallenge(Drain(renew.Outgoing), out seq, out nonce));
        renewClock.Now = 4;
        Expect("valid RESPONSE before lease expiry renews setup", renew.Dispatch(Response(seq, nonce)) && renew.Poll() && renew.Protocol.State == LeaseMonitor.State.Ready);
        renewClock.Now = 6;
        Expect("renewed RESPONSE keeps setup alive beyond original lease expiry", renew.Poll() && renew.Protocol.State == LeaseMonitor.State.Ready);
        Expect("renewed setup response still cannot authorize create/resume", !renew.Protocol.AuthorizeCreate(6) && !renew.Protocol.AuthorizeResume(6));
    }

    private static void MaintenanceHandshakeFixtures()
    {
        var createProtocol = new LeaseMonitor.Protocol(new LeaseMonitor.Policy(2, 5, 12, 30, 5, 5));
        createProtocol.Start(0);
        LeaseMonitor.Challenge create = createProtocol.IssueChallenge(0);
        Expect("legacy ready response can create a pending transition handshake", create != null && createProtocol.AcceptResponse(create.Sequence, create.Nonce, 1));
        LeaseMonitor.Challenge maintenance = createProtocol.IssueChallenge(2);
        Expect("maintenance response clears a previously accepted create handshake", maintenance != null && createProtocol.AcceptMaintenanceResponse(maintenance.Sequence, maintenance.Nonce, 2) && !createProtocol.AuthorizeCreate(2));

        var resumeProtocol = new LeaseMonitor.Protocol(new LeaseMonitor.Policy(2, 5, 12, 30, 5, 5));
        resumeProtocol.Start(0);
        LeaseMonitor.Challenge createForResume = resumeProtocol.IssueChallenge(0);
        bool created = createForResume != null && resumeProtocol.AcceptResponse(createForResume.Sequence, createForResume.Nonce, 1) && resumeProtocol.AuthorizeCreate(1) && resumeProtocol.MarkSuspended(1);
        LeaseMonitor.Challenge resume = created ? resumeProtocol.IssueChallenge(2) : null;
        bool resumePending = resume != null && resumeProtocol.AcceptResponse(resume.Sequence, resume.Nonce, 2);
        LeaseMonitor.Challenge maintenanceResume = resumePending ? resumeProtocol.IssueChallenge(4) : null;
        Expect("maintenance response clears a previously accepted resume handshake", maintenanceResume != null && resumeProtocol.AcceptMaintenanceResponse(maintenanceResume.Sequence, maintenanceResume.Nonce, 4) && !resumeProtocol.AuthorizeResume(4));
    }

    private static void AdmissionDeadlineFixtures()
    {
        var readyClock = new ArmedClock(12);
        var ready = NewDispatcher(readyClock.Read, 0, 12, new LeaseMonitor.Policy(2, 30, 12, 60, 5, 5));
        Expect("ready frame is not queued at the fixed setup deadline", !ready.Start() && Drain(ready.Outgoing) == null && ready.Stopped);

        var challengeClock = new ArmedClock(0);
        var challenge = NewDispatcher(challengeClock.Read, 0, 12, new LeaseMonitor.Policy(2, 5, 12, 60, 5, 5));
        Expect("challenge fixture queues ready before its lease deadline", challenge.Start() && Drain(challenge.Outgoing) != null);
        challengeClock.Arm(0, 5);
        Expect("challenge is not queued when fresh admission time reaches lease expiry", !challenge.TryIssueChallenge() && Drain(challenge.Outgoing) == null && challenge.Stopped);
    }

    private static MonitorSpecificationIntake.Dispatcher NewDispatcher(FakeClock clock, long start, long setupDuration)
    {
        return NewDispatcher(clock.Read, start, setupDuration, LeaseMonitor.Protocol.TestPolicy());
    }
    private static MonitorSpecificationIntake.Dispatcher NewDispatcher(FakeClock clock, long start, long setupDuration, LeaseMonitor.Policy policy)
    {
        return NewDispatcher(clock.Read, start, setupDuration, policy);
    }
    private static MonitorSpecificationIntake.Dispatcher NewDispatcher(Func<long> readClock, long start, long setupDuration, LeaseMonitor.Policy policy)
    {
        return new MonitorSpecificationIntake.Dispatcher(new LeaseMonitor.Protocol(policy),
            new LeaseMonitor.BoundedFrameQueue(32, 8192), readClock, Token, start, start + setupDuration, policy.ChallengePeriod);
    }
    private static byte[] ReadOne(byte[] input)
    {
        using (var memory = new MemoryStream(input)) return MonitorTransport.ReadBoundedFrame(memory, 512);
    }
    private static void ExpectReadFailure(string name, byte[] input)
    {
        try { ReadOne(input); failures++; Console.Error.WriteLine("FAIL " + name + ": accepted"); }
        catch (InvalidDataException) { Console.WriteLine("PASS " + name); }
    }
    private static byte[] Begin(string token, LaunchSpecification specification)
    {
        return Encoding.ASCII.GetBytes("SPEC-XFER/1 BEGIN " + token + " " + specification.ToWire().Length + " " + SpecificationTransfer.CountChunks(specification.ToWire().Length) + "\n");
    }
    private static byte[] End(string token) { return Encoding.ASCII.GetBytes("SPEC-XFER/1 END " + token + "\n"); }
    private static byte[] Data(string token, int index, byte[] bytes) { return Encoding.ASCII.GetBytes("SPEC-XFER/1 DATA " + token + " " + index + " " + Convert.ToBase64String(bytes) + "\n"); }
    private static byte[] Response(long sequence, string nonce) { return Encoding.ASCII.GetBytes("RESPONSE " + sequence + " " + nonce + "\n"); }
    private static LaunchSpecification CreateMaximumWireSpecification()
    {
        var empty = new string[10];
        for (int i = 0; i < empty.Length; i++) empty[i] = String.Empty;
        int additional = LaunchSpecification.MaximumWireBytes - LaunchSpecification.Create(Source, Executable, empty).ToWire().Length;
        if (additional < 0 || additional % 4 != 0) throw new InvalidOperationException("fixture cannot construct exact maximum specification");
        int remaining = additional / 4;
        var args = new string[10];
        for (int i = 0; i < args.Length; i++) { int take = Math.Min(341, remaining); args[i] = new string('漢', take); remaining -= take; }
        if (remaining != 0) throw new InvalidOperationException("fixture maximum exceeds argument field bound");
        return LaunchSpecification.Create(Source, Executable, args);
    }
    private static byte[] Drain(LeaseMonitor.BoundedFrameQueue queue)
    {
        byte[] frame; return queue.TryRead(out frame) ? frame : null;
    }
    private static bool IsReady(byte[] frame, string token)
    {
        return frame != null && String.Equals(Encoding.ASCII.GetString(frame), "MONITOR_READY protocol-only token=" + token + "\n", StringComparison.Ordinal);
    }
    private static bool TryChallenge(byte[] frame, out long sequence, out string nonce)
    {
        sequence = 0; nonce = null;
        if (frame == null) return false;
        string value = Encoding.ASCII.GetString(frame);
        if (!value.StartsWith("CHALLENGE ", StringComparison.Ordinal) || !value.EndsWith("\n", StringComparison.Ordinal)) return false;
        string[] fields = value.Substring(0, value.Length - 1).Split(' ');
        return fields.Length == 3 && Int64.TryParse(fields[1], out sequence) && fields[2].Length == 32 && (nonce = fields[2]) != null;
    }
    private static bool Equal(byte[] left, byte[] right)
    {
        if (left == null || right == null || left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
        return true;
    }
    private static void Expect(string name, bool actual) { if (!actual) { failures++; Console.Error.WriteLine("FAIL " + name); } else Console.WriteLine("PASS " + name); }
    private sealed class FakeClock { internal long Now; internal FakeClock(long value) { Now = value; } internal long Read() { return Now; } }
    private sealed class ArmedClock
    {
        private readonly long steady; private long[] values = new long[0]; private int position;
        internal int ArmedReads { get { return position; } }
        internal ArmedClock(long steadyValue) { steady = steadyValue; }
        internal void Arm(params long[] readings) { values = readings; position = 0; }
        internal long Read() { return position < values.Length ? values[position++] : steady; }
    }
}
