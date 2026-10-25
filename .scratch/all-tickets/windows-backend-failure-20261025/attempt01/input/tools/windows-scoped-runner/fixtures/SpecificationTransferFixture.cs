// Pure managed launch-specification transfer contract fixture source.
// It does not connect pipes, allocate runtime directories, launch workloads,
// or renew monitor leases.
using System;
using System.Text;

internal static class SpecificationTransferFixture
{
    private const string Token = "00112233445566778899aabbccddeeff";
    private const string OtherToken = "ffeeddccbbaa99887766554433221100";
    private const string Source = @"Z:\never-created\source";
    private const string Executable = @"bin\runner.exe";
    private static int failures;

    public static int Main()
    {
        LaunchSpecification maximum = CreateMaximumWireSpecification();
        byte[] wire = maximum.ToWire();
        Expect("fixture source reaches exact specification byte maximum", wire.Length == LaunchSpecification.MaximumWireBytes);

        var sender = new SpecificationTransfer.Sender(maximum, Token, 1000);
        var receiver = new SpecificationTransfer.Receiver(Token, 1000);
        byte[] first = sender.Start(1);
        Expect("sender begins with one bounded pending frame", first.Length <= SpecificationTransfer.MaximumFrameBytes && sender.HasOutstandingFrame);
        byte[] pendingAgain = sender.GetPendingFrame(1);
        Expect("re-reading pending frame does not advance sender", Equal(first, pendingAgain));
        pendingAgain[0] ^= 0xff;
        Expect("pending frame is returned as a defensive copy", Equal(first, sender.GetPendingFrame(1)));

        int sentFrames = 0, acknowledgementFrames = 0, dataFrames = 0, maximumObservedFrame = 0, maximumObservedAck = 0;
        byte[] frame = first;
        bool pumpCompleted = false;
        for (int pumpIteration = 0; pumpIteration <= SpecificationTransfer.MaximumTransferFrames; pumpIteration++)
        {
            if (frame == null) { pumpCompleted = true; break; }
            if (pumpIteration == SpecificationTransfer.MaximumTransferFrames)
            {
                Expect("transfer pump is bounded by the maximum frame count", false);
                break;
            }
            sentFrames++;
            maximumObservedFrame = Math.Max(maximumObservedFrame, frame.Length);
            if (IsFrameKind(frame, "DATA")) dataFrames++;
            byte[] acknowledgement = receiver.AcceptFrame(frame, 2);
            acknowledgementFrames++;
            maximumObservedAck = Math.Max(maximumObservedAck, acknowledgement.Length);
            Expect("receiver acknowledgement is bounded", acknowledgement.Length <= SpecificationTransfer.MaximumAcknowledgementBytes);
            sender.AcceptAcknowledgement(acknowledgement, 2);
            frame = sender.HasOutstandingFrame ? sender.GetPendingFrame(2) : null;
        }
        Expect("bounded transfer pump completes within the maximum frame count", pumpCompleted);
        Expect("maximum specification uses the exact fixed data-frame count", dataFrames == SpecificationTransfer.MaximumDataFrames);
        Expect("maximum transfer has exact BEGIN/DATA/END frame count", sentFrames == SpecificationTransfer.MaximumTransferFrames && acknowledgementFrames == SpecificationTransfer.MaximumTransferFrames);
        Expect("largest generated frame matches the documented bound", maximumObservedFrame == SpecificationTransfer.MaximumDataFrameBytes && maximumObservedFrame <= 512);
        Expect("all generated acknowledgements fit the documented bound", maximumObservedAck <= SpecificationTransfer.MaximumAcknowledgementBytes);
        Expect("sender and receiver complete only after END acknowledgement", sender.State == SpecificationTransfer.SenderState.Completed && receiver.State == SpecificationTransfer.ReceiverState.Completed);
        LaunchSpecification result = receiver.Result;
        Expect("END produces the original immutable launch specification", result != null && result.SourceDirectory == Source && result.RelativeExecutable == Executable && result.Arguments.Length == 10);
        string[] returnedArguments = result.Arguments;
        returnedArguments[0] = "mutated";
        Expect("completed result collections are defensive copies", result.Arguments[0] != "mutated");
        ExpectTransferError("completed receiver cannot be restarted", delegate { receiver.AcceptFrame(Begin(Token, wire.Length, SpecificationTransfer.MaximumDataFrames), 3); }, SpecificationTransfer.ErrorCode.InvalidState);
        ExpectTransferError("completed sender rejects replayed END acknowledgement", delegate { sender.AcceptAcknowledgement(AckEnd(Token), 3); }, SpecificationTransfer.ErrorCode.InvalidState);
        Expect("completed transfer result remains stable after replay attempts", receiver.State == SpecificationTransfer.ReceiverState.Completed && Object.ReferenceEquals(result, receiver.Result));

        QueuePressureFixture(maximum);
        SenderAcknowledgementFixtures();
        MalformedFrameFixtures(wire);
        ChunkAndTerminalFixtures();
        ExpiryFixtures();
        AcknowledgementsDoNotAuthorize();

        return failures == 0 ? 0 : 1;
    }

    private static void QueuePressureFixture(LaunchSpecification specification)
    {
        var queue = new LeaseMonitor.BoundedFrameQueue(32, 8192);
        for (int i = 0; i < 16; i++) Expect("existing queue accepts bounded 512-byte frame " + i, queue.TryWrite(new byte[512]));
        Expect("existing 8192-byte queue rejects one more byte without blocking", !queue.TryWrite(new byte[] { 1 }));
        var sender = new SpecificationTransfer.Sender(specification, Token, 1000);
        sender.Start(1);
        byte[] pending = sender.GetPendingFrame(1);
        Expect("full output queue rejects pending transfer frame", !queue.TryWrite(pending));
        Expect("queue pressure leaves exactly the same single frame pending", sender.HasOutstandingFrame && Equal(pending, sender.GetPendingFrame(1)));
    }

    private static void SenderAcknowledgementFixtures()
    {
        LaunchSpecification small = LaunchSpecification.Create(Source, Executable, new string[0]);
        var wrongToken = new SpecificationTransfer.Sender(small, Token, 100);
        wrongToken.Start(1);
        ExpectSenderError("sender rejects acknowledgement with another token", wrongToken, AckBegin(OtherToken), 2, SpecificationTransfer.ErrorCode.WrongToken);

        var outOfOrder = new SpecificationTransfer.Sender(small, Token, 100);
        outOfOrder.Start(1);
        ExpectSenderError("sender rejects DATA acknowledgement before BEGIN receipt", outOfOrder, AckData(Token, 0), 2, SpecificationTransfer.ErrorCode.InvalidAcknowledgement);

        var replayed = new SpecificationTransfer.Sender(small, Token, 100);
        replayed.Start(1);
        replayed.AcceptAcknowledgement(AckBegin(Token), 2);
        byte[] dataZero = replayed.GetPendingFrame(2);
        ExpectSenderError("sender rejects replayed BEGIN acknowledgement while DATA is outstanding", replayed, AckBegin(Token), 3, SpecificationTransfer.ErrorCode.InvalidAcknowledgement);
        Expect("invalid acknowledgement makes sender terminal and clears outstanding data", replayed.State == SpecificationTransfer.SenderState.Failed && replayed.Failure == SpecificationTransfer.ErrorCode.InvalidAcknowledgement && !replayed.HasOutstandingFrame && dataZero.Length > 0);

        var malformedToken = new SpecificationTransfer.Sender(small, Token, 100);
        malformedToken.Start(1);
        ExpectSenderError("sender rejects malformed acknowledgement token terminally", malformedToken, Ascii("SPEC-XFER/1 ACK bad BEGIN\n"), 2, SpecificationTransfer.ErrorCode.MalformedFrame);

        var created = new SpecificationTransfer.Sender(small, Token, 100);
        ExpectSenderError("acknowledgement before sender start is terminal", created, AckBegin(Token), 1, SpecificationTransfer.ErrorCode.InvalidState);

        var repeatedStart = new SpecificationTransfer.Sender(small, Token, 100);
        repeatedStart.Start(1);
        ExpectTransferError("second start fails active transfer terminally", delegate { repeatedStart.Start(2); }, SpecificationTransfer.ErrorCode.InvalidState);
        Expect("second start failure leaves sender terminal", repeatedStart.State == SpecificationTransfer.SenderState.Failed && !repeatedStart.HasOutstandingFrame);
    }

    private static void MalformedFrameFixtures(byte[] validWire)
    {
        ExpectReceiverError("unknown transfer version", NewReceiver(), Ascii("SPEC-XFER/2 BEGIN " + Token + " 8 1\n"), 1, SpecificationTransfer.ErrorCode.UnsupportedVersion);
        ExpectReceiverError("malformed UTF-8 frame", NewReceiver(), new byte[] { 0xff, 0x0a }, 1, SpecificationTransfer.ErrorCode.InvalidUtf8);
        ExpectReceiverError("truncated frame delimiter", NewReceiver(), Ascii("SPEC-XFER/1 BEGIN " + Token + " 8 1"), 1, SpecificationTransfer.ErrorCode.TruncatedFrame);
        ExpectReceiverError("trailing frame data", NewReceiver(), Ascii("SPEC-XFER/1 BEGIN " + Token + " 8 1\nextra\n"), 1, SpecificationTransfer.ErrorCode.MalformedFrame);
        ExpectReceiverError("wrong monitor-issued correlation token", NewReceiver(), Ascii(BeginText(OtherToken, 8, 1)), 1, SpecificationTransfer.ErrorCode.WrongToken);
        ExpectReceiverError("oversized declared specification rejected before assembly", NewReceiver(), Ascii(BeginText(Token, LaunchSpecification.MaximumWireBytes + 1, 26)), 1, SpecificationTransfer.ErrorCode.InputTooLarge);
        ExpectReceiverError("declared chunk-count mismatch", NewReceiver(), Ascii(BeginText(Token, 8192, 25)), 1, SpecificationTransfer.ErrorCode.ChunkCountMismatch);
        ExpectReceiverError("noncanonical decimal rejected", NewReceiver(), Ascii("SPEC-XFER/1 BEGIN " + Token + " 08192 26\n"), 1, SpecificationTransfer.ErrorCode.NonCanonicalNumber);
        ExpectReceiverError("oversized transfer frame rejected", NewReceiver(), new byte[SpecificationTransfer.MaximumFrameBytes + 1], 1, SpecificationTransfer.ErrorCode.FrameTooLarge);
        ExpectReceiverError("decimal overflow rejected", NewReceiver(), Ascii("SPEC-XFER/1 BEGIN " + Token + " 2147483648 1\n"), 1, SpecificationTransfer.ErrorCode.Overflow);

        var duplicateBegin = NewReceiver();
        duplicateBegin.AcceptFrame(Ascii(BeginText(Token, validWire.Length, SpecificationTransfer.CountChunks(validWire.Length))), 1);
        ExpectReceiverError("duplicate BEGIN cannot replace an active transfer", duplicateBegin, Ascii(BeginText(Token, validWire.Length, SpecificationTransfer.CountChunks(validWire.Length))), 1, SpecificationTransfer.ErrorCode.InvalidState);

        var wrongOrder = NewReceiver();
        wrongOrder.AcceptFrame(Ascii(BeginText(Token, 8192, SpecificationTransfer.MaximumDataFrames)), 1);
        ExpectReceiverError("out-of-order data index rejected", wrongOrder, Data(Token, 1, new byte[] { 0 }), 1, SpecificationTransfer.ErrorCode.OutOfOrder);

        var noncanonicalBase64 = NewReceiver();
        noncanonicalBase64.AcceptFrame(Ascii(BeginText(Token, 1, 1)), 1);
        ExpectReceiverError("noncanonical base64 pad bits rejected", noncanonicalBase64, Ascii("SPEC-XFER/1 DATA " + Token + " 0 AB==\n"), 1, SpecificationTransfer.ErrorCode.NonCanonicalBase64);

        var malformedBase64 = NewReceiver();
        malformedBase64.AcceptFrame(Ascii(BeginText(Token, 1, 1)), 1);
        ExpectReceiverError("malformed base64 rejected", malformedBase64, Ascii("SPEC-XFER/1 DATA " + Token + " 0 !!!\n"), 1, SpecificationTransfer.ErrorCode.InvalidBase64);
    }

    private static void ChunkAndTerminalFixtures()
    {
        var duplicateChunk = NewReceiver();
        duplicateChunk.AcceptFrame(Ascii(BeginText(Token, 8192, SpecificationTransfer.MaximumDataFrames)), 1);
        byte[] fullChunk = new byte[SpecificationTransfer.ChunkBytes];
        duplicateChunk.AcceptFrame(Data(Token, 0, fullChunk), 1);
        ExpectReceiverError("duplicate chunk index rejected", duplicateChunk, Data(Token, 0, fullChunk), 1, SpecificationTransfer.ErrorCode.OutOfOrder);

        var badFinalLength = NewReceiver();
        badFinalLength.AcceptFrame(Ascii(BeginText(Token, 325, 2)), 1);
        badFinalLength.AcceptFrame(Data(Token, 0, new byte[SpecificationTransfer.ChunkBytes]), 1);
        ExpectReceiverError("final chunk must have exact remaining byte length", badFinalLength, Data(Token, 1, new byte[2]), 1, SpecificationTransfer.ErrorCode.InvalidChunkLength);

        var shortNonfinal = NewReceiver();
        shortNonfinal.AcceptFrame(Ascii(BeginText(Token, 325, 2)), 1);
        ExpectReceiverError("nonfinal chunk must have exact fixed length", shortNonfinal, Data(Token, 0, new byte[SpecificationTransfer.ChunkBytes - 1]), 1, SpecificationTransfer.ErrorCode.InvalidChunkLength);

        byte[] invalidSpecification = Ascii("not-a-launch-specification\n");
        var invalidEnd = NewReceiver();
        invalidEnd.AcceptFrame(Ascii(BeginText(Token, invalidSpecification.Length, 1)), 1);
        invalidEnd.AcceptFrame(Data(Token, 0, invalidSpecification), 1);
        ExpectReceiverError("END rejects assembled bytes that fail immutable specification parse", invalidEnd, Ascii(EndText(Token)), 1, SpecificationTransfer.ErrorCode.InvalidSpecification);

        var truncated = NewReceiver();
        truncated.AcceptFrame(Ascii(BeginText(Token, 8192, SpecificationTransfer.MaximumDataFrames)), 1);
        ExpectReceiverError("END before all data is a truncated transfer", truncated, Ascii(EndText(Token)), 1, SpecificationTransfer.ErrorCode.TruncatedTransfer);
        Expect("truncated receiver discards partial assembly and becomes terminal", truncated.State == SpecificationTransfer.ReceiverState.Failed && truncated.Result == null);
        ExpectTransferError("failed receiver cannot restart or replace transfer", delegate { truncated.AcceptFrame(Ascii(BeginText(Token, 1, 1)), 2); }, SpecificationTransfer.ErrorCode.InvalidState);

        var cancelled = NewReceiver();
        cancelled.AcceptFrame(Ascii(BeginText(Token, 8192, SpecificationTransfer.MaximumDataFrames)), 1);
        cancelled.Cancel(2);
        Expect("cancellation invalidates partial transfer", cancelled.State == SpecificationTransfer.ReceiverState.Failed && cancelled.Failure == SpecificationTransfer.ErrorCode.Cancelled && cancelled.Result == null);
        ExpectTransferError("cancelled receiver is terminal", delegate { cancelled.AcceptFrame(Ascii(BeginText(Token, 1, 1)), 2); }, SpecificationTransfer.ErrorCode.InvalidState);

        var eof = NewReceiver();
        eof.AcceptFrame(Ascii(BeginText(Token, 8192, SpecificationTransfer.MaximumDataFrames)), 1);
        eof.SignalEof(2);
        Expect("EOF invalidates partial transfer", eof.State == SpecificationTransfer.ReceiverState.Failed && eof.Failure == SpecificationTransfer.ErrorCode.EndOfStream);
    }

    private static void ExpiryFixtures()
    {
        var receiver = new SpecificationTransfer.Receiver(Token, 10);
        receiver.AcceptFrame(Ascii(BeginText(Token, 8192, SpecificationTransfer.MaximumDataFrames)), 9);
        ExpectReceiverError("data acceptance at exact setup deadline expires", receiver, Data(Token, 0, new byte[SpecificationTransfer.ChunkBytes]), 10, SpecificationTransfer.ErrorCode.Expired);

        LaunchSpecification small = LaunchSpecification.Create(Source, Executable, new string[0]);
        byte[] smallWire = small.ToWire();
        var endReceiver = new SpecificationTransfer.Receiver(Token, 10);
        endReceiver.AcceptFrame(Ascii(BeginText(Token, smallWire.Length, 1)), 9);
        endReceiver.AcceptFrame(Data(Token, 0, smallWire), 9);
        ExpectReceiverError("END acceptance at exact setup deadline expires", endReceiver, Ascii(EndText(Token)), 10, SpecificationTransfer.ErrorCode.Expired);

        var sender = new SpecificationTransfer.Sender(small, Token, 10);
        sender.Start(9);
        ExpectTransferError("acknowledgement at exact setup deadline expires", delegate { sender.AcceptAcknowledgement(AckBegin(Token), 10); }, SpecificationTransfer.ErrorCode.Expired);

        var beforeExpiry = new SpecificationTransfer.Receiver(Token, 10);
        Expect("frame before fixed setup deadline is accepted", beforeExpiry.AcceptFrame(Ascii(BeginText(Token, smallWire.Length, 1)), 9) != null);
    }

    private static void AcknowledgementsDoNotAuthorize()
    {
        var protocol = new LeaseMonitor.Protocol(LeaseMonitor.Protocol.TestPolicy());
        protocol.Start(0);
        var sender = new SpecificationTransfer.Sender(LaunchSpecification.Create(Source, Executable, new string[0]), Token, 100);
        var receiver = NewReceiver();
        byte[] frame = sender.Start(1);
        byte[] acknowledgement = receiver.AcceptFrame(frame, 1);
        Expect("transfer acknowledgement is a bounded receipt", acknowledgement.Length <= SpecificationTransfer.MaximumAcknowledgementBytes);
        Expect("transfer receipt alone cannot authorize create", !protocol.AuthorizeCreate(1) && protocol.State == LeaseMonitor.State.Ready);
        Expect("transfer receipt does not renew lease", protocol.Tick(5) == LeaseMonitor.State.Stopping);
    }

    private static LaunchSpecification CreateMaximumWireSpecification()
    {
        var empty = new string[10];
        for (int i = 0; i < empty.Length; i++) empty[i] = String.Empty;
        int additional = LaunchSpecification.MaximumWireBytes - LaunchSpecification.Create(Source, Executable, empty).ToWire().Length;
        if (additional < 0 || additional % 4 != 0) throw new InvalidOperationException("fixture cannot construct the exact launch-specification bound");
        int chars = additional / 4;
        var args = new string[empty.Length];
        for (int i = 0; i < args.Length; i++)
        {
            int take = Math.Min(341, chars);
            args[i] = new string('漢', take);
            chars -= take;
        }
        if (chars != 0) throw new InvalidOperationException("fixture maximum value exceeds the fixed field bound");
        return LaunchSpecification.Create(Source, Executable, args);
    }

    private static SpecificationTransfer.Receiver NewReceiver() { return new SpecificationTransfer.Receiver(Token, 100); }
    private static string BeginText(string token, int total, int chunks) { return "SPEC-XFER/1 BEGIN " + token + " " + total + " " + chunks + "\n"; }
    private static byte[] Begin(string token, int total, int chunks) { return Ascii(BeginText(token, total, chunks)); }
    private static string EndText(string token) { return "SPEC-XFER/1 END " + token + "\n"; }
    private static byte[] AckBegin(string token) { return Ascii("SPEC-XFER/1 ACK " + token + " BEGIN\n"); }
    private static byte[] AckEnd(string token) { return Ascii("SPEC-XFER/1 ACK " + token + " END\n"); }
    private static byte[] AckData(string token, int index) { return Ascii("SPEC-XFER/1 ACK " + token + " DATA " + index + "\n"); }
    private static byte[] Data(string token, int index, byte[] bytes) { return Ascii("SPEC-XFER/1 DATA " + token + " " + index + " " + Convert.ToBase64String(bytes) + "\n"); }
    private static byte[] Ascii(string text) { return Encoding.ASCII.GetBytes(text); }
    private static bool IsFrameKind(byte[] frame, string kind) { return Encoding.ASCII.GetString(frame).StartsWith("SPEC-XFER/1 " + kind + " ", StringComparison.Ordinal); }
    private static bool Equal(byte[] left, byte[] right)
    {
        if (left == null || right == null || left.Length != right.Length) return false;
        for (int i = 0; i < left.Length; i++) if (left[i] != right[i]) return false;
        return true;
    }
    private static void Expect(string name, bool actual) { if (!actual) { failures++; Console.Error.WriteLine("FAIL " + name); } else Console.WriteLine("PASS " + name); }
    private static void ExpectReceiverError(string name, SpecificationTransfer.Receiver receiver, byte[] frame, long now, SpecificationTransfer.ErrorCode expected)
    {
        ExpectTransferError(name, delegate { receiver.AcceptFrame(frame, now); }, expected);
        Expect(name + " leaves terminal failure diagnostic", receiver.State == SpecificationTransfer.ReceiverState.Failed && receiver.Failure == expected);
    }
    private static void ExpectTransferError(string name, Action action, SpecificationTransfer.ErrorCode expected)
    {
        try { action(); failures++; Console.Error.WriteLine("FAIL " + name + ": accepted"); }
        catch (SpecificationTransfer.TransferException e)
        {
            if (e.Code != expected) { failures++; Console.Error.WriteLine("FAIL " + name + ": expected " + expected + ", got " + e.Code); }
            else Console.WriteLine("PASS " + name + ": " + e.Code);
        }
    }
    private static void ExpectSenderError(string name, SpecificationTransfer.Sender sender, byte[] acknowledgement, long now, SpecificationTransfer.ErrorCode expected)
    {
        ExpectTransferError(name, delegate { sender.AcceptAcknowledgement(acknowledgement, now); }, expected);
        Expect(name + " leaves sender terminal with intended diagnostic", sender.State == SpecificationTransfer.SenderState.Failed && sender.Failure == expected && !sender.HasOutstandingFrame);
    }
}
