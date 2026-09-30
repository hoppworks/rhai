// Production monitor dispatcher for canonical control frames and bounded
// immutable launch-specification transfer. It performs no workload creation.
using System;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;

internal static class MonitorSpecificationIntake
{
    private static readonly UTF8Encoding StrictUtf8 = new UTF8Encoding(false, true);

    internal static string CreateMonitorToken()
    {
        byte[] random = new byte[16];
        using (RandomNumberGenerator rng = RandomNumberGenerator.Create()) rng.GetBytes(random);
        var text = new StringBuilder(32);
        for (int i = 0; i < random.Length; i++) text.Append(random[i].ToString("x2", CultureInfo.InvariantCulture));
        Array.Clear(random, 0, random.Length);
        return text.ToString();
    }

    internal sealed class Dispatcher
    {
        private readonly Func<long> monotonicNow;
        private readonly string token;
        private readonly long started, setupDeadline, challengeInterval;
        private readonly SpecificationTransfer.Receiver receiver;
        private long lastChallenge;
        private bool startedOnce;
        internal LeaseMonitor.Protocol Protocol { get; private set; }
        internal LeaseMonitor.BoundedFrameQueue Outgoing { get; private set; }
        internal bool Stopped { get; private set; }
        internal LaunchSpecification CompletedSpecification { get; private set; }

        internal Dispatcher(LeaseMonitor.Protocol protocol,
            LeaseMonitor.BoundedFrameQueue outgoing, Func<long> monotonicNow,
            string monitorIssuedToken, long monitorStarted, long fixedSetupDeadline,
            long challengeIntervalMilliseconds)
        {
            if (protocol == null) throw new ArgumentNullException("protocol");
            if (outgoing == null) throw new ArgumentNullException("outgoing");
            if (monotonicNow == null) throw new ArgumentNullException("monotonicNow");
            if (monitorStarted < 0 || fixedSetupDeadline <= monitorStarted)
                throw new ArgumentOutOfRangeException("fixedSetupDeadline");
            if (challengeIntervalMilliseconds <= 0)
                throw new ArgumentOutOfRangeException("challengeIntervalMilliseconds");
            Protocol = protocol;
            Outgoing = outgoing;
            this.monotonicNow = monotonicNow;
            token = monitorIssuedToken;
            started = monitorStarted;
            setupDeadline = fixedSetupDeadline;
            challengeInterval = challengeIntervalMilliseconds;
            receiver = new SpecificationTransfer.Receiver(token, fixedSetupDeadline);
            lastChallenge = monitorStarted - challengeIntervalMilliseconds;
        }

        internal bool Start()
        {
            if (startedOnce) return FailAt(monotonicNow());
            startedOnce = true;
            Protocol.Start(started);
            long admissionNow = monotonicNow();
            if (!CheckLive(admissionNow)) return false;
            byte[] ready = Ascii("MONITOR_READY protocol-only token=" + token + "\n");
            return Outgoing.TryWrite(ready) || FailAt(admissionNow);
        }

        internal bool Poll()
        {
            if (Stopped) return false;
            return CheckLive(monotonicNow());
        }

        internal bool TryIssueChallenge()
        {
            if (Stopped) return false;
            long now = monotonicNow();
            if (!CheckLive(now)) return false;
            if (now - lastChallenge < challengeInterval) return true;
            lastChallenge = now;
            LeaseMonitor.Challenge challenge = Protocol.IssueChallenge(now);
            if (challenge == null)
                return Protocol.State != LeaseMonitor.State.Stopping || FailAt(now);
            long admissionNow = monotonicNow();
            if (!CheckLive(admissionNow)) return false;
            byte[] frame = Ascii("CHALLENGE " + challenge.Sequence.ToString(CultureInfo.InvariantCulture) + " " + challenge.Nonce + "\n");
            return Outgoing.TryWrite(frame) || FailAt(admissionNow);
        }

        // Dispatches one original LF-inclusive transport frame. Each frame
        // gets a fresh monotonic read; transfer ACK admission gets another.
        internal bool Dispatch(byte[] originalFrame)
        {
            if (Stopped) return false;
            long now = monotonicNow();
            if (!CheckLive(now)) return false;
            if (originalFrame == null || originalFrame.Length == 0 || originalFrame.Length > SpecificationTransfer.MaximumFrameBytes)
                return FailAt(now);

            try
            {
                if (IsTransferFrame(originalFrame))
                {
                    byte[] acknowledgement = receiver.AcceptFrame(originalFrame, now);
                    if (receiver.State == SpecificationTransfer.ReceiverState.Completed)
                        CompletedSpecification = receiver.Result;
                    long admissionNow = monotonicNow();
                    if (!CheckLive(admissionNow)) return false;
                    return Outgoing.TryWrite(acknowledgement) || FailAt(admissionNow);
                }

                string line = DecodeCanonicalFrame(originalFrame);
                string[] fields = line.Split(new[] { ' ' });
                if (fields.Length != 3 || fields[0] != "RESPONSE" || fields[1].Length == 0 || fields[2].Length != 32 || !IsCanonicalToken(fields[2]))
                    return FailAt(now);
                long sequence;
                if (!Int64.TryParse(fields[1], NumberStyles.None, CultureInfo.InvariantCulture, out sequence) ||
                    sequence.ToString(CultureInfo.InvariantCulture) != fields[1])
                    return FailAt(now);

                // Stale/replayed/prebuffered responses are ignored by the
                // protocol; accepted setup responses renew only the short
                // lease and cannot pre-authorize later process creation.
                Protocol.AcceptMaintenanceResponse(sequence, fields[2], now);
                return CheckLive(monotonicNow());
            }
            catch (SpecificationTransfer.TransferException)
            {
                return FailAt(monotonicNow());
            }
            catch (FormatException)
            {
                return FailAt(monotonicNow());
            }
            catch (DecoderFallbackException)
            {
                return FailAt(monotonicNow());
            }
        }

        internal void Stop()
        {
            if (Stopped) return;
            FailAt(monotonicNow());
        }

        private bool CheckLive(long now)
        {
            if (Stopped) return false;
            if (Protocol.Tick(now) == LeaseMonitor.State.Stopping || now >= setupDeadline)
                return FailAt(now);
            return true;
        }

        private bool FailAt(long now)
        {
            if (!Stopped)
            {
                Stopped = true;
                CompletedSpecification = null;
                receiver.Cancel(now);
                Protocol.SignalClientEof(now);
            }
            return false;
        }

        private static string DecodeCanonicalFrame(byte[] frame)
        {
            if (frame[frame.Length - 1] != (byte)'\n') throw new FormatException("control frame lacks LF");
            string text = StrictUtf8.GetString(frame);
            if (text.Length == 0 || text[text.Length - 1] != '\n' || text.IndexOf('\n') != text.Length - 1 || text.IndexOf('\r') >= 0)
                throw new FormatException("control frame delimiter is not canonical LF");
            for (int i = 0; i < text.Length - 1; i++)
                if (text[i] < 0x20 || text[i] > 0x7e) throw new FormatException("control frame must be printable ASCII");
            return text.Substring(0, text.Length - 1);
        }

        private static bool IsTransferFrame(byte[] frame)
        {
            byte[] prefix = Encoding.ASCII.GetBytes("SPEC-XFER/");
            if (frame.Length < prefix.Length) return false;
            for (int i = 0; i < prefix.Length; i++) if (frame[i] != prefix[i]) return false;
            return true;
        }

        private static bool IsCanonicalToken(string value)
        {
            for (int i = 0; i < value.Length; i++)
                if (!((value[i] >= '0' && value[i] <= '9') || (value[i] >= 'a' && value[i] <= 'f'))) return false;
            return true;
        }
        private static byte[] Ascii(string value) { return Encoding.ASCII.GetBytes(value); }
    }
}
