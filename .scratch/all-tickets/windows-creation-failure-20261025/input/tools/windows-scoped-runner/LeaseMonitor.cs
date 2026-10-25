// Monitor/client lease protocol and phase-bound transition authority. Its
// source integration does not constitute native process or custody proof.
using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;

internal static class LeaseMonitor
{
    internal enum State { Ready, CreateAuthorized, Suspended, ResumeAuthorized, Running, Stopping }

    // The only minting path consumes a receipt that the exact-job owner can
    // create only after termination, signaled root wait, process/thread handle
    // closure, job emptiness, and job-handle closure all succeed.
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
        internal static ExactJobClosureProof FromVerifiedClosure(MonitorPayloadJob.ClosureReceipt receipt)
        {
            if (receipt == null || receipt.Allocation == null || receipt.RuntimeIdentity == null)
                throw new InvalidOperationException("exact-job closure receipt is incomplete");
            return new ExactJobClosureProof(receipt.Allocation, receipt.RuntimeIdentity);
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

    internal sealed class Challenge { internal readonly long Sequence, Expires; internal readonly string Nonce; internal readonly State Phase; internal readonly bool TransitionRequested; internal Challenge(long s, string n, long e, State phase, bool transition) { Sequence = s; Nonce = n; Expires = e; Phase=phase; TransitionRequested=transition; } }

    internal sealed class Protocol
    {
        private readonly object sync = new object();
        private readonly Policy policy;
        private long started, leaseDeadline, nextChallenge, sequence;
        private Challenge outstanding;
        private bool hasStarted, createHandshake, resumeHandshake;
        private State requestedTransition;
        private State state;
        internal State State { get { lock(sync) return state; } private set { lock(sync) state=value; } }
        internal Protocol(Policy fixedPolicy)
        {
            policy = fixedPolicy ?? throw new ArgumentNullException("fixedPolicy");
            requestedTransition=State.Stopping;
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
        private void Stop() { lock(sync) { State = State.Stopping; outstanding = null; createHandshake=false; resumeHandshake=false; requestedTransition=State.Stopping; } }
        internal void Start(long now) { lock(sync) { if(hasStarted) return; hasStarted=true; started = now; leaseDeadline = now + policy.LeaseDuration; nextChallenge = now; } }
        internal State Tick(long now)
        {
            lock(sync)
            {
            if (State == State.Stopping) return State;
            if (Expired(now)) { Stop(); return State; }
            return State;
            }
        }
        internal Challenge IssueChallenge(long now)
        {
            lock(sync)
            {
            if (!hasStarted) Start(now);
            if (Tick(now) == State.Stopping ||
                (State != State.Ready && State != State.Suspended && State != State.Running) ||
                outstanding != null || createHandshake || resumeHandshake || now < nextChallenge) return null;
            sequence++;
            byte[] nonce = new byte[16]; using (var rng = RandomNumberGenerator.Create()) rng.GetBytes(nonce);
            bool transition=requestedTransition==State;
            outstanding = new Challenge(sequence, BitConverter.ToString(nonce).Replace("-", "").ToLowerInvariant(), now + policy.LeaseDuration, State, transition);
            if(transition) requestedTransition=State.Stopping;
            nextChallenge = now + policy.ChallengePeriod;
            return outstanding;
            }
        }
        // Called by the owner worker only after the prerequisite phase is
        // reached. It invalidates any maintenance challenge that predates the
        // transition and causes the dispatcher to issue a fresh phase-bound
        // challenge on its next poll.
        internal bool RequestFreshTransitionChallenge(State phase, long now)
        {
            lock(sync)
            {
                if(Tick(now)==State.Stopping || phase!=State.Ready && phase!=State.Suspended || State!=phase) return false;
                outstanding=null; createHandshake=false; resumeHandshake=false;
                requestedTransition=phase; nextChallenge=now;
                return true;
            }
        }
        internal bool HasRequestedTransitionChallenge { get { lock(sync) return requestedTransition==State.Ready || requestedTransition==State.Suspended; } }
        internal bool CanAuthorizeCreate(long now) { lock(sync) return Tick(now)!=State.Stopping && State==State.Ready && outstanding==null && createHandshake; }
        internal bool CanAuthorizeResume(long now) { lock(sync) return Tick(now)!=State.Stopping && State==State.Suspended && outstanding==null && resumeHandshake; }
        internal bool AcceptResponse(long seq, string nonce, long now)
        {
            return AcceptResponseCore(seq, nonce, now, true);
        }
        // Setup-only transport responses renew the short lease but never mint
        // a create/resume handshake. Creation must use a later phase-bound
        // response after staging has completed.
        internal bool AcceptMaintenanceResponse(long seq, string nonce, long now)
        {
            return AcceptResponseCore(seq, nonce, now, false);
        }
        private bool AcceptResponseCore(long seq, string nonce, long now, bool allowTransitionHandshake)
        {
            lock(sync)
            {
            if (Tick(now) == State.Stopping || outstanding == null || outstanding.Phase!=State || now >= outstanding.Expires ||
                seq != outstanding.Sequence || !String.Equals(nonce, outstanding.Nonce, StringComparison.Ordinal)) return false;
            Challenge accepted=outstanding;
            outstanding = null;
            leaseDeadline = Math.Min(now + policy.LeaseDuration, started + policy.AbsoluteDeadline);
            if(!allowTransitionHandshake) { createHandshake=false; resumeHandshake=false; }
            else if(accepted.TransitionRequested && State==State.Ready) createHandshake=true;
            else if(accepted.TransitionRequested && State==State.Suspended) resumeHandshake=true;
            // Running responses only renew the short lease. They cannot
            // authorize another create or resume transition.
            return true;
            }
        }
        internal bool AuthorizeCreate(long now)
        {
            lock(sync)
            {
            if (Tick(now) == State.Stopping || outstanding != null || State != State.Ready || !createHandshake) return false;
            createHandshake=false;
            State = State.CreateAuthorized; return true;
            }
        }
        internal bool MarkSuspended(long now)
        {
            lock(sync)
            {
            if (Tick(now) == State.Stopping || State != State.CreateAuthorized) return false;
            outstanding=null;
            State = State.Suspended; return true;
            }
        }
        internal bool AuthorizeResume(long now)
        {
            lock(sync)
            {
            if (Tick(now) == State.Stopping || outstanding != null || State != State.Suspended || !resumeHandshake) return false;
            resumeHandshake=false;
            State = State.ResumeAuthorized; return true;
            }
        }
        internal void MarkRunning(long now) { lock(sync) { if (Tick(now) != State.Stopping && State == State.ResumeAuthorized) State = State.Running; } }
        // The resume operation runs under the same lock as stop, expiry, and
        // challenge transitions. Thus a concurrent stop cannot land between
        // authorizing resume and calling ResumeThread. The caller supplies a
        // monotonic clock and a synchronous operation over its exact thread.
        internal bool TryResumeAtomically(Func<long> clock, Func<bool> resume)
        {
            if(clock==null || resume==null) throw new ArgumentNullException("resume gate inputs");
            lock(sync)
            {
                try
                {
                    long before=clock();
                    if(Tick(before)==State.Stopping || outstanding!=null || State!=State.Suspended || !resumeHandshake) return false;
                    resumeHandshake=false;
                    State=State.ResumeAuthorized;
                    if(!resume()) { Stop(); return false; }
                    if(Tick(clock())==State.Stopping) return false;
                    State=State.Running;
                    return true;
                }
                catch { Stop(); throw; }
            }
        }
        internal void SignalClientEof(long now) { lock(sync) { if (Tick(now) != State.Stopping) Stop(); } }
        internal void SignalClientExited(long now) { lock(sync) { if (Tick(now) != State.Stopping) Stop(); } }
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
