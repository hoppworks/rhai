// Independent monitor/client lease protocol source. This protocol-only source
// deliberately stops before workload allocation until safe backend custody is
// implemented. Do not treat protocol fixtures as native process proof.
using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;

internal static class LeaseMonitor
{
    internal enum State { Ready, CreateAuthorized, Suspended, ResumeAuthorized, Running, Stopping }

    // Unconstructible in this source slice: a future private monitor path may
    // issue this only after its owned job reports zero active processes and it
    // has independently released its retained payload process/thread handles.
    // No PID, caller boolean, or protocol fixture can manufacture that proof.
    internal sealed class ExactJobClosureProof
    {
        private readonly WindowsCustodyBackend.RuntimeAllocation allocation;
        private readonly WindowsCustodyBackend.FileIdentity runtimeIdentity;
        private ExactJobClosureProof(WindowsCustodyBackend.RuntimeAllocation owner,
            WindowsCustodyBackend.FileIdentity identity)
        {
            allocation = owner;
            runtimeIdentity = identity;
        }
        internal bool Authorizes(WindowsCustodyBackend.RuntimeAllocation owner,
            WindowsCustodyBackend.FileIdentity identity)
        {
            return Object.ReferenceEquals(allocation, owner) && runtimeIdentity != null && runtimeIdentity.SameAs(identity);
        }
    }

    internal sealed class Policy
    {
        internal readonly long ChallengePeriod, LeaseDuration, SetupDeadline, AbsoluteDeadline, TerminationDeadline, FinalizationDeadline;
        internal Policy(long challengePeriod, long leaseDuration, long setupDeadline, long absoluteDeadline, long terminationDeadline, long finalizationDeadline)
        {
            ChallengePeriod = challengePeriod; LeaseDuration = leaseDuration; SetupDeadline = setupDeadline;
            AbsoluteDeadline = absoluteDeadline; TerminationDeadline = terminationDeadline; FinalizationDeadline = finalizationDeadline;
        }
    }

    internal sealed class Challenge { internal readonly long Sequence, Expires; internal readonly string Nonce; internal readonly State Phase; internal Challenge(long s, string n, long e, State phase) { Sequence = s; Nonce = n; Expires = e; Phase=phase; } }

    internal sealed class Protocol
    {
        private readonly Policy policy;
        private long started, leaseDeadline, nextChallenge, sequence;
        private Challenge outstanding;
        private bool hasStarted, createHandshake, resumeHandshake;
        internal State State { get; private set; }
        internal Protocol(Policy fixedPolicy)
        {
            policy = fixedPolicy ?? throw new ArgumentNullException("fixedPolicy");
            State = State.Ready;
        }
        internal static Policy ProductionPolicy() { return new Policy(2000, 15000, 120000, 1800000, 30000, 30000); }
#if SCOPED_RUNNER_TESTING
        internal static Policy TestPolicy() { return new Policy(2, 5, 12, 30, 5, 5); }
#endif
        private bool Expired(long now)
        {
            if (!hasStarted) return false;
            if (now >= started + policy.AbsoluteDeadline || now >= leaseDeadline) return true;
            return State != State.Running && now >= started + policy.SetupDeadline;
        }
        private void Stop() { State = State.Stopping; outstanding = null; }
        internal void Start(long now) { if(hasStarted) return; hasStarted=true; started = now; leaseDeadline = now + policy.LeaseDuration; nextChallenge = now; }
        internal State Tick(long now)
        {
            if (State == State.Stopping) return State;
            if (Expired(now)) { Stop(); return State; }
            return State;
        }
        internal Challenge IssueChallenge(long now)
        {
            if (!hasStarted) Start(now);
            if (Tick(now) == State.Stopping ||
                (State != State.Ready && State != State.Suspended && State != State.Running) ||
                outstanding != null || now < nextChallenge) return null;
            sequence++;
            byte[] nonce = new byte[16]; using (var rng = RandomNumberGenerator.Create()) rng.GetBytes(nonce);
            outstanding = new Challenge(sequence, BitConverter.ToString(nonce).Replace("-", "").ToLowerInvariant(), now + policy.LeaseDuration, State);
            nextChallenge = now + policy.ChallengePeriod;
            return outstanding;
        }
        internal bool AcceptResponse(long seq, string nonce, long now)
        {
            if (Tick(now) == State.Stopping || outstanding == null || outstanding.Phase!=State || now >= outstanding.Expires ||
                seq != outstanding.Sequence || !String.Equals(nonce, outstanding.Nonce, StringComparison.Ordinal)) return false;
            outstanding = null;
            leaseDeadline = Math.Min(now + policy.LeaseDuration, started + policy.AbsoluteDeadline);
            if(State==State.Ready) createHandshake=true;
            else if(State==State.Suspended) resumeHandshake=true;
            // Running responses only renew the short lease. They cannot
            // authorize another create or resume transition.
            return true;
        }
        internal bool AuthorizeCreate(long now)
        {
            if (Tick(now) == State.Stopping || outstanding != null || State != State.Ready || !createHandshake) return false;
            createHandshake=false;
            State = State.CreateAuthorized; return true;
        }
        internal bool MarkSuspended(long now)
        {
            if (Tick(now) == State.Stopping || State != State.CreateAuthorized) return false;
            outstanding=null;
            State = State.Suspended; return true;
        }
        internal bool AuthorizeResume(long now)
        {
            if (Tick(now) == State.Stopping || outstanding != null || State != State.Suspended || !resumeHandshake) return false;
            resumeHandshake=false;
            State = State.ResumeAuthorized; return true;
        }
        internal void MarkRunning(long now) { if (Tick(now) != State.Stopping && State == State.ResumeAuthorized) State = State.Running; }
        internal void SignalClientEof(long now) { if (Tick(now) != State.Stopping) Stop(); }
        internal void SignalClientExited(long now) { if (Tick(now) != State.Stopping) Stop(); }
    }

    // Nonblocking producer/consumer seam. Production transport uses separate
    // blocking pipe workers; the watchdog never waits for this queue or joins them.
    internal sealed class BoundedFrameQueue
    {
        private readonly int maxFrames, maxBytes; private int bytes;
        private readonly Queue<byte[]> frames = new Queue<byte[]>();
        private readonly object sync = new object();
        internal BoundedFrameQueue(int framesLimit, int bytesLimit) { maxFrames = framesLimit; maxBytes = bytesLimit; }
        internal bool TryWrite(byte[] frame)
        {
            if (frame == null || frame.Length > 512) return false;
            var copy = (byte[])frame.Clone();
            if(!System.Threading.Monitor.TryEnter(sync,0)) return false;
            try { if (frames.Count >= maxFrames || bytes + copy.Length > maxBytes) return false; frames.Enqueue(copy); bytes += copy.Length; return true; }
            finally { System.Threading.Monitor.Exit(sync); }
        }
        internal bool TryRead(out byte[] frame)
        {
            if(!System.Threading.Monitor.TryEnter(sync,0)) { frame=null; return false; }
            try { if(frames.Count==0) { frame=null; return false; } frame=frames.Dequeue(); bytes-=frame.Length; return true; }
            finally { System.Threading.Monitor.Exit(sync); }
        }
    }

    internal static int MonitorMain(string[] args)
    {
        return MonitorTransport.MonitorMain(args);
    }
}
