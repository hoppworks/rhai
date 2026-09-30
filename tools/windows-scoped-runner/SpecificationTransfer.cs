// Pure managed transfer protocol for a bounded immutable launch specification.
// This model is not connected to MonitorTransport or workload creation.
using System;
using System.Globalization;
using System.Text;

internal static class SpecificationTransfer
{
    internal const int MaximumFrameBytes = 512;
    internal const int QueueFrameLimit = 32;
    internal const int QueueByteLimit = 8192;
    internal const int ChunkBytes = 324;
    internal const int MaximumDataFrames = (LaunchSpecification.MaximumWireBytes + ChunkBytes - 1) / ChunkBytes;
    internal const int MaximumTransferFrames = MaximumDataFrames + 2;
    internal const int MaximumAcknowledgementFrames = MaximumTransferFrames;
    // DATA header worst case: version/verb (17), token (32), separators (2),
    // two-digit final index, full base64 chunk (432), and newline (1).
    internal const int MaximumDataFrameBytes = 486;
    // DATA acknowledgement worst case: prefix through ACK (16), token (32),
    // " DATA " (6), two-digit index, and newline = 57 bytes.
    internal const int MaximumAcknowledgementBytes = 57;
    private const string Version = "SPEC-XFER/1";
    private const string Prefix = Version + " ";
    private static readonly UTF8Encoding StrictUtf8 = new UTF8Encoding(false, true);

    internal enum ErrorCode
    {
        None, InvalidState, Expired, FrameTooLarge, TruncatedFrame, InvalidUtf8,
        NonAsciiFrame, MalformedFrame, UnsupportedVersion, WrongToken, InvalidBegin,
        InputTooLarge, ChunkCountMismatch, NonCanonicalNumber, Overflow,
        InvalidBase64, NonCanonicalBase64, InvalidChunkLength, OutOfOrder,
        TruncatedTransfer, InvalidSpecification, InvalidAcknowledgement,
        Cancelled, EndOfStream
    }

    internal sealed class TransferException : FormatException
    {
        internal readonly ErrorCode Code;
        internal TransferException(ErrorCode code, string message) : base(message) { Code = code; }
        internal TransferException(ErrorCode code, string message, Exception inner) : base(message, inner) { Code = code; }
    }

    internal enum ReceiverState { AwaitBegin, ReceivingData, AwaitEnd, Completed, Failed }
    internal enum SenderState { Created, AwaitingAcknowledgement, Completed, Failed }
    internal enum PendingKind { None, Begin, Data, End }

    internal sealed class Receiver
    {
        private readonly string token;
        private readonly long setupDeadline;
        private byte[] assembly;
        private int totalBytes, chunkCount, nextIndex, receivedBytes;
        private LaunchSpecification result;
        internal ReceiverState State { get; private set; }
        internal ErrorCode Failure { get; private set; }
        internal LaunchSpecification Result { get { return result; } }

        internal Receiver(string monitorIssuedToken, long fixedSetupDeadline)
        {
            token = ValidateOwnerToken(monitorIssuedToken);
            if (fixedSetupDeadline < 0) throw new ArgumentOutOfRangeException("fixedSetupDeadline");
            setupDeadline = fixedSetupDeadline;
            State = ReceiverState.AwaitBegin;
        }

        internal byte[] AcceptFrame(byte[] frame, long now)
        {
            EnsureActive(State == ReceiverState.Completed || State == ReceiverState.Failed);
            try
            {
                CheckDeadline(now);
                string[] fields = ParseFrame(frame);
                if (fields[0] != Version) throw FailAndMake(ErrorCode.UnsupportedVersion, "transfer version is unsupported");
                if (fields.Length < 2) throw FailAndMake(ErrorCode.MalformedFrame, "transfer command is missing");
                string verb = fields[1];
                if (verb == "BEGIN") return AcceptBegin(fields);
                if (verb == "DATA") return AcceptData(fields);
                if (verb == "END") return AcceptEnd(fields);
                throw FailAndMake(ErrorCode.MalformedFrame, "transfer command is unknown");
            }
            catch (TransferException e)
            {
                Fail(e.Code);
                throw;
            }
        }

        internal void Cancel(long now) { FailActive(now, ErrorCode.Cancelled); }
        internal void SignalEof(long now) { FailActive(now, ErrorCode.EndOfStream); }

        private byte[] AcceptBegin(string[] fields)
        {
            if (State != ReceiverState.AwaitBegin) throw FailAndMake(ErrorCode.InvalidState, "BEGIN is only valid once");
            if (fields.Length != 5) throw FailAndMake(ErrorCode.MalformedFrame, "BEGIN field count is invalid");
            RequireToken(fields[2]);
            int declaredBytes = ParseDecimal(fields[3]);
            int declaredChunks = ParseDecimal(fields[4]);
            if (declaredBytes <= 0) throw FailAndMake(ErrorCode.InvalidBegin, "specification size must be positive");
            if (declaredBytes > LaunchSpecification.MaximumWireBytes)
                throw FailAndMake(ErrorCode.InputTooLarge, "declared specification exceeds the fixed input bound");
            int expectedChunks = CountChunks(declaredBytes);
            if (declaredChunks != expectedChunks)
                throw FailAndMake(ErrorCode.ChunkCountMismatch, "declared chunk count does not match the fixed chunk size");

            // Allocate only after the monitor token, total bound and exact chunk
            // count have all been validated.
            assembly = new byte[declaredBytes];
            totalBytes = declaredBytes;
            chunkCount = declaredChunks;
            State = ReceiverState.ReceivingData;
            return Acknowledgement("BEGIN", -1);
        }

        private byte[] AcceptData(string[] fields)
        {
            if (State != ReceiverState.ReceivingData)
                throw FailAndMake(ErrorCode.OutOfOrder, "DATA is not expected in the current transfer state");
            if (fields.Length != 5) throw FailAndMake(ErrorCode.MalformedFrame, "DATA field count is invalid");
            RequireToken(fields[2]);
            int index = ParseDecimal(fields[3]);
            if (index != nextIndex) throw FailAndMake(ErrorCode.OutOfOrder, "DATA index is not the next contiguous index");
            byte[] decoded = DecodeCanonicalBase64(fields[4]);
            int expectedLength = index < chunkCount - 1 ? ChunkBytes : totalBytes - index * ChunkBytes;
            if (decoded.Length != expectedLength)
                throw FailAndMake(ErrorCode.InvalidChunkLength, "DATA chunk length does not match its position");
            int offset = checked(index * ChunkBytes);
            if (offset < 0 || offset > totalBytes - decoded.Length)
                throw FailAndMake(ErrorCode.InvalidChunkLength, "DATA chunk exceeds the declared specification size");
            Buffer.BlockCopy(decoded, 0, assembly, offset, decoded.Length);
            receivedBytes = checked(receivedBytes + decoded.Length);
            nextIndex++;
            if (nextIndex == chunkCount)
            {
                if (receivedBytes != totalBytes) throw FailAndMake(ErrorCode.InvalidChunkLength, "accumulated DATA length is not exact");
                State = ReceiverState.AwaitEnd;
            }
            return Acknowledgement("DATA", index);
        }

        private byte[] AcceptEnd(string[] fields)
        {
            if (fields.Length != 3) throw FailAndMake(ErrorCode.MalformedFrame, "END field count is invalid");
            RequireToken(fields[2]);
            if (State == ReceiverState.ReceivingData)
                throw FailAndMake(ErrorCode.TruncatedTransfer, "END arrived before every DATA chunk");
            if (State != ReceiverState.AwaitEnd)
                throw FailAndMake(ErrorCode.InvalidState, "END is not valid in the current transfer state");
            if (receivedBytes != totalBytes || assembly == null)
                throw FailAndMake(ErrorCode.TruncatedTransfer, "assembled specification length is incomplete");
            try { result = LaunchSpecification.Parse(assembly); }
            catch (LaunchSpecification.SpecificationException e)
            {
                throw FailAndMake(ErrorCode.InvalidSpecification, "transferred bytes are not a valid immutable launch specification", e);
            }
            Array.Clear(assembly, 0, assembly.Length);
            assembly = null;
            State = ReceiverState.Completed;
            return Acknowledgement("END", -1);
        }

        private void RequireToken(string value)
        {
            if (!String.Equals(value, token, StringComparison.Ordinal))
                throw FailAndMake(ErrorCode.WrongToken, "transfer correlation token does not match the monitor-issued token");
        }
        private byte[] Acknowledgement(string kind, int index)
        {
            string text = Prefix + "ACK " + token + " " + kind;
            if (kind == "DATA") text += " " + Decimal(index);
            byte[] result = AsciiFrame(text);
            if (result.Length > MaximumAcknowledgementBytes)
                throw FailAndMake(ErrorCode.MalformedFrame, "internal acknowledgement exceeded its fixed bound");
            return result;
        }
        private void CheckDeadline(long now)
        {
            if (now < 0 || now >= setupDeadline) throw FailAndMake(ErrorCode.Expired, "transfer setup deadline has expired");
        }
        private void FailActive(long now, ErrorCode reason)
        {
            if (State == ReceiverState.Completed || State == ReceiverState.Failed) return;
            Fail(now < 0 || now >= setupDeadline ? ErrorCode.Expired : reason);
        }
        private void Fail(ErrorCode reason)
        {
            if (State == ReceiverState.Completed || State == ReceiverState.Failed) return;
            if (assembly != null) { Array.Clear(assembly, 0, assembly.Length); assembly = null; }
            result = null; receivedBytes = 0; Failure = reason; State = ReceiverState.Failed;
        }
        private TransferException FailAndMake(ErrorCode code, string message) { return new TransferException(code, message); }
        private TransferException FailAndMake(ErrorCode code, string message, Exception inner) { return new TransferException(code, message, inner); }
        private void EnsureActive(bool terminal)
        {
            if (terminal) throw new TransferException(ErrorCode.InvalidState, "transfer is terminal");
        }
    }

    internal sealed class Sender
    {
        private readonly string token;
        private readonly long setupDeadline;
        private readonly byte[] wire;
        private readonly int chunkCount;
        private byte[] pendingFrame;
        private PendingKind pendingKind;
        private int pendingIndex, nextIndex;
        internal SenderState State { get; private set; }
        internal ErrorCode Failure { get; private set; }
        internal bool HasOutstandingFrame { get { return State == SenderState.AwaitingAcknowledgement && pendingFrame != null; } }

        internal Sender(LaunchSpecification specification, string monitorIssuedToken, long fixedSetupDeadline)
        {
            if (specification == null) throw new ArgumentNullException("specification");
            token = ValidateOwnerToken(monitorIssuedToken);
            if (fixedSetupDeadline < 0) throw new ArgumentOutOfRangeException("fixedSetupDeadline");
            setupDeadline = fixedSetupDeadline;
            wire = specification.ToWire();
            if (wire.Length <= 0 || wire.Length > LaunchSpecification.MaximumWireBytes)
                throw new TransferException(ErrorCode.InputTooLarge, "specification is outside the fixed transfer bound");
            chunkCount = CountChunks(wire.Length);
            State = SenderState.Created;
        }

        internal byte[] Start(long now)
        {
            if (State != SenderState.Created)
            {
                if (State == SenderState.AwaitingAcknowledgement) Fail(ErrorCode.InvalidState);
                throw new TransferException(ErrorCode.InvalidState, "sender can start only once");
            }
            try
            {
                CheckDeadline(now);
                pendingKind = PendingKind.Begin;
                pendingIndex = -1;
                pendingFrame = AsciiFrame(Prefix + "BEGIN " + token + " " + Decimal(wire.Length) + " " + Decimal(chunkCount));
                State = SenderState.AwaitingAcknowledgement;
                return CopyPending();
            }
            catch (TransferException e) { Fail(e.Code); throw; }
        }

        internal byte[] GetPendingFrame(long now)
        {
            if (State != SenderState.AwaitingAcknowledgement || pendingFrame == null)
                throw new TransferException(ErrorCode.InvalidState, "sender has no pending frame");
            try { CheckDeadline(now); }
            catch (TransferException e) { Fail(e.Code); throw; }
            return CopyPending();
        }

        internal void AcceptAcknowledgement(byte[] acknowledgement, long now)
        {
            if (State == SenderState.Completed || State == SenderState.Failed)
                throw new TransferException(ErrorCode.InvalidState, "sender is terminal");
            if (State != SenderState.AwaitingAcknowledgement || pendingFrame == null)
            {
                Fail(ErrorCode.InvalidState);
                throw FailAndMake(ErrorCode.InvalidState, "sender has no outstanding frame");
            }
            try
            {
                CheckDeadline(now);
                AckFields ack = ParseAcknowledgement(acknowledgement);
                if (!String.Equals(ack.Token, token, StringComparison.Ordinal))
                    throw FailAndMake(ErrorCode.WrongToken, "acknowledgement token does not match this transfer");
                if (pendingKind == PendingKind.Begin)
                {
                    if (ack.Kind != PendingKind.Begin) throw FailAndMake(ErrorCode.InvalidAcknowledgement, "BEGIN acknowledgement was expected");
                    PrepareData(0);
                    return;
                }
                if (pendingKind == PendingKind.Data)
                {
                    if (ack.Kind != PendingKind.Data || ack.Index != pendingIndex)
                        throw FailAndMake(ErrorCode.InvalidAcknowledgement, "acknowledgement does not match the outstanding DATA index");
                    nextIndex = pendingIndex + 1;
                    if (nextIndex < chunkCount) PrepareData(nextIndex);
                    else PrepareEnd();
                    return;
                }
                if (pendingKind == PendingKind.End)
                {
                    if (ack.Kind != PendingKind.End) throw FailAndMake(ErrorCode.InvalidAcknowledgement, "END acknowledgement was expected");
                    pendingFrame = null; pendingKind = PendingKind.None; State = SenderState.Completed;
                    return;
                }
                throw FailAndMake(ErrorCode.InvalidState, "sender pending-frame state is invalid");
            }
            catch (TransferException e)
            {
                Fail(e.Code);
                throw;
            }
        }

        internal void Cancel(long now) { FailActive(now, ErrorCode.Cancelled); }
        internal void SignalEof(long now) { FailActive(now, ErrorCode.EndOfStream); }

        private void PrepareData(int index)
        {
            int offset = checked(index * ChunkBytes);
            int length = Math.Min(ChunkBytes, wire.Length - offset);
            if (index < 0 || offset < 0 || length <= 0) throw FailAndMake(ErrorCode.OutOfOrder, "sender DATA range is invalid");
            var chunk = new byte[length]; Buffer.BlockCopy(wire, offset, chunk, 0, length);
            pendingIndex = index; pendingKind = PendingKind.Data;
            pendingFrame = AsciiFrame(Prefix + "DATA " + token + " " + Decimal(index) + " " + Convert.ToBase64String(chunk));
            if (pendingFrame.Length > MaximumDataFrameBytes || pendingFrame.Length > MaximumFrameBytes)
                throw FailAndMake(ErrorCode.FrameTooLarge, "generated DATA frame exceeds the fixed frame bound");
        }
        private void PrepareEnd()
        {
            pendingKind = PendingKind.End; pendingIndex = -1;
            pendingFrame = AsciiFrame(Prefix + "END " + token);
        }
        private byte[] CopyPending() { return (byte[])pendingFrame.Clone(); }
        private void CheckDeadline(long now)
        {
            if (now < 0 || now >= setupDeadline) throw FailAndMake(ErrorCode.Expired, "transfer setup deadline has expired");
        }
        private void FailActive(long now, ErrorCode reason)
        {
            if (State == SenderState.Completed || State == SenderState.Failed) return;
            Fail(now < 0 || now >= setupDeadline ? ErrorCode.Expired : reason);
        }
        private void Fail(ErrorCode reason)
        {
            if (State == SenderState.Completed || State == SenderState.Failed) return;
            if (pendingFrame != null) { Array.Clear(pendingFrame, 0, pendingFrame.Length); pendingFrame = null; }
            Array.Clear(wire, 0, wire.Length); pendingKind = PendingKind.None; Failure = reason; State = SenderState.Failed;
        }
        private TransferException FailAndMake(ErrorCode code, string message) { return new TransferException(code, message); }
    }

    internal sealed class AckFields
    {
        internal readonly string Token; internal readonly PendingKind Kind; internal readonly int Index;
        internal AckFields(string token, PendingKind kind, int index) { Token = token; Kind = kind; Index = index; }
    }

    private static AckFields ParseAcknowledgement(byte[] frame)
    {
        string[] fields = ParseFrame(frame);
        if (fields[0] != Version) throw new TransferException(ErrorCode.UnsupportedVersion, "acknowledgement version is unsupported");
        if (fields.Length < 3 || fields[1] != "ACK") throw new TransferException(ErrorCode.InvalidAcknowledgement, "acknowledgement command is malformed");
        string token = fields[2];
        if (!IsCanonicalToken(token)) throw new TransferException(ErrorCode.MalformedFrame, "acknowledgement token is not canonical");
        if (fields.Length == 4 && fields[3] == "BEGIN") return new AckFields(token, PendingKind.Begin, -1);
        if (fields.Length == 4 && fields[3] == "END") return new AckFields(token, PendingKind.End, -1);
        if (fields.Length == 5 && fields[3] == "DATA") return new AckFields(token, PendingKind.Data, ParseDecimal(fields[4]));
        throw new TransferException(ErrorCode.InvalidAcknowledgement, "acknowledgement fields are not canonical");
    }

    private static string[] ParseFrame(byte[] frame)
    {
        if (frame == null || frame.Length == 0) throw new TransferException(ErrorCode.TruncatedFrame, "frame is empty");
        if (frame.Length > MaximumFrameBytes) throw new TransferException(ErrorCode.FrameTooLarge, "frame exceeds 512 bytes including delimiter");
        if (frame[frame.Length - 1] != (byte)'\n') throw new TransferException(ErrorCode.TruncatedFrame, "frame lacks its final newline delimiter");
        string text;
        try { text = StrictUtf8.GetString(frame); }
        catch (DecoderFallbackException e) { throw new TransferException(ErrorCode.InvalidUtf8, "frame is not valid UTF-8", e); }
        if (text.Length == 0 || text[text.Length - 1] != '\n' || text.IndexOf('\n') != text.Length - 1 || text.IndexOf('\r') >= 0)
            throw new TransferException(ErrorCode.MalformedFrame, "frame has noncanonical line delimiters");
        for (int i = 0; i < text.Length - 1; i++)
            if (text[i] < 0x20 || text[i] > 0x7e) throw new TransferException(ErrorCode.NonAsciiFrame, "protocol frame must contain printable ASCII only");
        string line = text.Substring(0, text.Length - 1);
        string[] fields = line.Split(new[] { ' ' });
        for (int i = 0; i < fields.Length; i++)
            if (fields[i].Length == 0) throw new TransferException(ErrorCode.MalformedFrame, "frame contains empty fields");
        return fields;
    }

    private static byte[] DecodeCanonicalBase64(string value)
    {
        byte[] bytes;
        try { bytes = Convert.FromBase64String(value); }
        catch (FormatException e) { throw new TransferException(ErrorCode.InvalidBase64, "DATA chunk is not valid base64", e); }
        if (!String.Equals(Convert.ToBase64String(bytes), value, StringComparison.Ordinal))
            throw new TransferException(ErrorCode.NonCanonicalBase64, "DATA chunk base64 is not canonical");
        return bytes;
    }

    private static string ValidateOwnerToken(string token)
    {
        if (token == null || token.Length != 32) throw new ArgumentException("monitor-issued transfer token must be 32 lowercase hexadecimal characters", "token");
        for (int i = 0; i < token.Length; i++)
            if (!((token[i] >= '0' && token[i] <= '9') || (token[i] >= 'a' && token[i] <= 'f')))
                throw new ArgumentException("monitor-issued transfer token must be 32 lowercase hexadecimal characters", "token");
        return token;
    }
    private static bool IsCanonicalToken(string token)
    {
        if (token == null || token.Length != 32) return false;
        for (int i = 0; i < token.Length; i++)
            if (!((token[i] >= '0' && token[i] <= '9') || (token[i] >= 'a' && token[i] <= 'f'))) return false;
        return true;
    }
    private static int ParseDecimal(string value)
    {
        int parsed;
        if (String.IsNullOrEmpty(value)) throw new TransferException(ErrorCode.NonCanonicalNumber, "decimal field is empty");
        for (int i = 0; i < value.Length; i++) if (value[i] < '0' || value[i] > '9') throw new TransferException(ErrorCode.NonCanonicalNumber, "decimal field is not unsigned ASCII decimal");
        if (!Int32.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out parsed))
            throw new TransferException(ErrorCode.Overflow, "decimal field overflows the supported integer range");
        if (!String.Equals(parsed.ToString(CultureInfo.InvariantCulture), value, StringComparison.Ordinal))
            throw new TransferException(ErrorCode.NonCanonicalNumber, "decimal field is not canonical");
        return parsed;
    }
    private static string Decimal(int value) { return value.ToString(CultureInfo.InvariantCulture); }
    private static byte[] AsciiFrame(string line) { return Encoding.ASCII.GetBytes(line + "\n"); }
    internal static int CountChunks(int totalBytes)
    {
        if (totalBytes <= 0) return 0;
        return (int)(((long)totalBytes + ChunkBytes - 1) / ChunkBytes);
    }
}
