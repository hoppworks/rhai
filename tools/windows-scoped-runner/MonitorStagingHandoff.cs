// Single-worker bridge from completed immutable intake to filesystem custody
// and the monitor-owned payload transition.
// The watchdog only changes state and signals; it never performs backend I/O,
// invokes cancellation callbacks, waits, joins, or disposes an allocation.
using System;
using System.Threading;

internal sealed class MonitorStagingHandoff
{
    private const int Idle = 0, Running = 1, Published = 2, AcceptancePending = 3,
        Accepted = 4, Stopping = 5, ReleaseRequested = 6, Finished = 7, Failed = 8;

    internal sealed class Result
    {
        internal readonly IDisposable Owner;
        internal readonly bool Succeeded;
        internal readonly string Diagnostic;
        internal Result(IDisposable owner, bool succeeded, string diagnostic)
        { Owner = owner; Succeeded = succeeded; Diagnostic = diagnostic; }
    }

    private readonly Func<LaunchSpecification, CancellationToken, Result> run;
    private readonly Action<Result, LaunchSpecification, CancellationToken> acceptedOperation;
    private readonly ManualResetEvent cancelSignal = new ManualResetEvent(false);
    private readonly ManualResetEvent workerFinished = new ManualResetEvent(false);
    private readonly CancellationTokenSource cancellation = new CancellationTokenSource();
    private LaunchSpecification specification;
    private Result slot;
    private int state = Idle, stopRequested;
    private string failure;
#if SCOPED_RUNNER_TESTING
    private readonly ManualResetEvent lifecycleObservedForFixture = new ManualResetEvent(false);
    private readonly ManualResetEvent pendingObservedForFixture = new ManualResetEvent(false);
#endif

    private MonitorStagingHandoff(Func<LaunchSpecification, CancellationToken, Result> operation,
        Action<Result, LaunchSpecification, CancellationToken> accepted)
    { run = operation ?? throw new ArgumentNullException("operation"); acceptedOperation=accepted; }

    // Production construction has no caller-supplied backend or path. The
    // immutable specification is the only input to the monitor-owned worker.
    internal static MonitorStagingHandoff CreateProduction(LeaseMonitor.Protocol protocol, Func<long> monotonicNow)
    {
        if(protocol==null || monotonicNow==null) throw new ArgumentNullException("production transition inputs");
        return new MonitorStagingHandoff(StageWithBackend,
            (result,spec,token)=>RunAcceptedLifecycle(result,spec,token,protocol,monotonicNow));
    }

    private static void RunAcceptedLifecycle(Result result, LaunchSpecification specification, CancellationToken token,
        LeaseMonitor.Protocol protocol, Func<long> monotonicNow)
    {
        var allocation=result.Owner as WindowsCustodyBackend.RuntimeAllocation;
        if(allocation==null) throw new InvalidOperationException("accepted staging owner has an unexpected type");
        MonitorPayloadJob payload=null;
        Exception operationFailure=null, cleanupFailure=null;
        uint? payloadExitCode=null;
        WindowsCustodyBackend.PayloadSupervisionOutcome supervisionOutcome=WindowsCustodyBackend.PayloadSupervisionOutcome.TransitionFailed;
        MonitorPayloadJob.ClosureReceipt closureReceipt=null;
        LeaseMonitor.ExactJobClosureProof closureAuthorization=null;
        WindowsCustodyBackend.RuntimeAllocation.OutcomeMetadataReceipt outcomeMetadata=null;
        Exception finalizationFailure=null;
        try
        {
            RequestAndWaitForAuthority(protocol,token,monotonicNow,LeaseMonitor.State.Ready);
            payload=MonitorPayloadJob.CreateSuspended(allocation,specification,protocol);
            RequestAndWaitForAuthority(protocol,token,monotonicNow,LeaseMonitor.State.Suspended);
            payload.ResumeAfterHostChallenge(protocol);
            supervisionOutcome=HoldPayloadUntilStop(payload,protocol,token,monotonicNow);
            payloadExitCode=payload.RootExitCode;
        }
        catch(Exception error)
        {
            operationFailure=error;
            try { protocol.SignalClientExited(monotonicNow()); }
            catch(Exception signalError) { operationFailure=new AggregateException("payload transition failed and stop publication also failed",operationFailure,signalError); }
        }
        finally
        {
            if(payload!=null)
                try { closureReceipt=payload.CloseAndVerify(); closureAuthorization=payload.ClosureAuthorization; }
                catch(Exception error)
                {
                    cleanupFailure=error;
                    try { protocol.SignalClientExited(monotonicNow()); }
                    catch(Exception signalError) { cleanupFailure=new AggregateException("exact-job cleanup failed and stop publication also failed",cleanupFailure,signalError); }
            }
            if(payload!=null) payloadExitCode=payload.RootExitCode;
            if(cleanupFailure==null && closureAuthorization!=null)
            {
                ulong finalizationDeadline=WindowsCustodyBackend.RuntimeAllocation.StartLocalFinalizationDeadline();
                try
                {
                    outcomeMetadata=allocation.RecordLocalOutcomeMetadata(closureAuthorization,payloadExitCode,supervisionOutcome,finalizationDeadline);
                    if(!outcomeMetadata.PayloadEvidenceSaved)
                        throw new InvalidOperationException("payload logs, results, and manifest were not captured and read back; allocation remains retained");
                    if(!allocation.TryRemoveRuntimeAfterOutcomeMetadata(outcomeMetadata,CancellationToken.None))
                        throw new InvalidOperationException(allocation.Failure ?? "runtime disposition failed after local outcome metadata");
                }
                catch(Exception error) { finalizationFailure=error; }
            }
            // Closure and an outcome metadata record are insufficient for runtime
            // disposition: bounded payload logs/results/manifest still need capture
            // and readback. Host export remains false without a response contract.
            GC.KeepAlive(payloadExitCode); GC.KeepAlive(closureReceipt); GC.KeepAlive(closureAuthorization);
            GC.KeepAlive(supervisionOutcome); GC.KeepAlive(outcomeMetadata);
        }
        if(operationFailure!=null && cleanupFailure!=null && finalizationFailure!=null)
            throw new AggregateException("payload transition, exact-job cleanup, and outcome finalization failed",operationFailure,cleanupFailure,finalizationFailure);
        if(operationFailure!=null && cleanupFailure!=null)
            throw new AggregateException("payload transition and exact-job cleanup both failed",operationFailure,cleanupFailure);
        if(operationFailure!=null && finalizationFailure!=null)
            throw new AggregateException("payload transition and local finalization failed",operationFailure,finalizationFailure);
        if(cleanupFailure!=null && finalizationFailure!=null)
            throw new AggregateException("exact-job cleanup and outcome finalization failed",cleanupFailure,finalizationFailure);
        if(operationFailure!=null) throw operationFailure;
        if(cleanupFailure!=null) throw new InvalidOperationException("exact-job cleanup failed; allocation remains retained or uncertain",cleanupFailure);
        if(finalizationFailure!=null) throw new InvalidOperationException("local outcome finalization or runtime disposition failed; allocation remains retained or uncertain",finalizationFailure);
    }

    private static WindowsCustodyBackend.PayloadSupervisionOutcome HoldPayloadUntilStop(MonitorPayloadJob payload,
        LeaseMonitor.Protocol protocol, CancellationToken token, Func<long> monotonicNow)
    {
        while(!token.IsCancellationRequested)
        {
            if(protocol.Tick(monotonicNow())==LeaseMonitor.State.Stopping) return WindowsCustodyBackend.PayloadSupervisionOutcome.MonitorStopped;
            if(payload.ObserveRootExit()) return WindowsCustodyBackend.PayloadSupervisionOutcome.PayloadExited;
            Thread.Sleep(10);
        }
        return WindowsCustodyBackend.PayloadSupervisionOutcome.MonitorStopped;
    }

    internal static void RequestAndWaitForAuthority(LeaseMonitor.Protocol protocol, CancellationToken token,
        Func<long> monotonicNow, LeaseMonitor.State phase)
    {
        if(!protocol.RequestFreshTransitionChallenge(phase,monotonicNow()))
            throw new InvalidOperationException("protocol rejected fresh phase-bound host challenge request");
        for(;;)
        {
            token.ThrowIfCancellationRequested();
            long now=monotonicNow();
            if(protocol.Tick(now)==LeaseMonitor.State.Stopping)
                throw new InvalidOperationException("monitor stopped while waiting for phase-bound host challenge");
            if(phase==LeaseMonitor.State.Ready ? protocol.CanAuthorizeCreate(now) : protocol.CanAuthorizeResume(now)) return;
            Thread.Sleep(10);
        }
    }

    private static Result StageWithBackend(LaunchSpecification spec, CancellationToken token)
    {
        WindowsCustodyBackend.RuntimeAllocation allocation = null;
        try
        {
            token.ThrowIfCancellationRequested();
            allocation = WindowsCustodyBackend.BeginAuthorizedAllocation();
            token.ThrowIfCancellationRequested();
            if (!allocation.CreateRuntime())
                return new Result(allocation, false, allocation.Failure ?? "runtime allocation failed closed");
            token.ThrowIfCancellationRequested();
            if (!allocation.StageSourceTree(spec.SourceDirectory, spec.RelativeExecutable, token))
                return new Result(allocation, false, allocation.Failure ?? "source staging failed closed");
            return new Result(allocation, allocation.IsStaged, allocation.Failure);
        }
        catch (Exception error)
        {
            return new Result(allocation, false, error.GetType().Name + ": " + error.Message);
        }
    }

    internal bool Start(LaunchSpecification completedSpecification)
    {
        if (completedSpecification == null) return false;
        if (Interlocked.CompareExchange(ref state, Running, Idle) != Idle) return false;
        specification = completedSpecification;
        try
        {
            var signaler = new Thread(CancellationSignalMain) { IsBackground = true, Name = "staging-cancel-signal" };
            signaler.Start();
            var worker = new Thread(WorkerMain) { IsBackground = true, Name = "monitor-staging-worker" };
            worker.Start();
            return true;
        }
        catch (Exception error)
        {
            failure = "unable to start monitor staging worker: " + error.GetType().Name;
            Interlocked.Exchange(ref state, Failed);
            Interlocked.Exchange(ref stopRequested, 1);
            cancelSignal.Set();
            workerFinished.Set();
            return false;
        }
    }

    // Called only by the monitor watchdog. State CAS defines whether stop or
    // acceptance won; signaling is bounded and owns no allocation handle.
    internal void Stop()
    {
        Interlocked.Exchange(ref stopRequested, 1);
        for (;;)
        {
            int observed = Volatile.Read(ref state);
            int next;
            if (observed == Idle) next = Finished;
            else if (observed == Running || observed == Published || observed == AcceptancePending) next = Stopping;
            else if (observed == Accepted) next = ReleaseRequested;
            else break;
            if (Interlocked.CompareExchange(ref state, next, observed) == observed) break;
        }
        cancelSignal.Set();
    }

    // The live callback is a pure fresh-time check by the watchdog. It runs on
    // both sides of the acceptance CAS, so a deadline crossing cannot expose
    // a late staged result.
    internal bool TryAccept(Func<bool> isStillLive)
    {
        if (isStillLive == null) throw new ArgumentNullException("isStillLive");
        if (Volatile.Read(ref stopRequested) != 0 || !isStillLive()) { Stop(); return false; }
        if (Interlocked.CompareExchange(ref state, AcceptancePending, Published) != Published) return false;
        if (Volatile.Read(ref stopRequested) != 0 || !isStillLive()) { Stop(); return false; }
        // Lifecycle becomes visible only after the final deadline check.
        // Stop can still win the pending state before this CAS.
        return Interlocked.CompareExchange(ref state, Accepted, AcceptancePending) == AcceptancePending;
    }

    internal bool IsPublished { get { return Volatile.Read(ref state) == Published; } }
    internal bool CanStart { get { return Volatile.Read(ref state) == Idle; } }
    internal bool IsFailed { get { return Volatile.Read(ref state) == Failed; } }
    internal string Failure { get { return failure; } }

    private void CancellationSignalMain()
    {
        cancelSignal.WaitOne();
        // This source is private to the backend operation; the backend only
        // polls ThrowIfCancellationRequested and registers no user callbacks.
        if (Volatile.Read(ref stopRequested) != 0 && !workerFinished.WaitOne(0))
            try { cancellation.Cancel(); } catch { }
    }

    private void WorkerMain()
    {
        Result result = null;
        if (Volatile.Read(ref stopRequested) != 0 || Volatile.Read(ref state) != Running)
        {
            Interlocked.Exchange(ref state, Finished);
            workerFinished.Set(); cancelSignal.Set(); return;
        }
        try { result = run(specification, cancellation.Token); }
        catch (Exception error) { result = new Result(null, false, error.GetType().Name + ": " + error.Message); }
        try
        {
            if (result == null || !result.Succeeded || result.Owner == null)
            {
                failure = result == null ? "staging worker returned no result" :
                    (result.Diagnostic ?? "staging worker did not produce a staged owner");
                DisposeOnWorker(result == null ? null : result.Owner);
                if (Interlocked.CompareExchange(ref state, Failed, Running) != Running)
                    Interlocked.Exchange(ref state, Finished);
                return;
            }

            slot = result;
            if (Interlocked.CompareExchange(ref state, Published, Running) != Running)
            {
                slot = null;
                DisposeOnWorker(result.Owner);
                Interlocked.Exchange(ref state, Finished);
                return;
            }

            for (;;)
            {
                int observed = Volatile.Read(ref state);
                if (observed == Published || observed == AcceptancePending)
                {
#if SCOPED_RUNNER_TESTING
                    if(observed==AcceptancePending) pendingObservedForFixture.Set();
#endif
                    Thread.Sleep(10); continue;
                }
                if (observed == Accepted)
                {
#if SCOPED_RUNNER_TESTING
                    lifecycleObservedForFixture.Set();
#endif
                    if(acceptedOperation==null) { Thread.Sleep(10); continue; }
                    Result accepted=Interlocked.Exchange(ref slot,null);
                    LaunchSpecification acceptedSpecification=specification;
                    if(acceptedOperation!=null)
                    {
                        try { acceptedOperation(accepted,acceptedSpecification,cancellation.Token); }
                        catch(Exception error)
                        {
                            string detail="accepted payload transition failed: "+error.GetType().Name+": "+error.Message;
                            failure=String.IsNullOrEmpty(failure) ? detail : failure+"; "+detail;
                        }
                    }
                    DisposeOnWorker(accepted==null ? null : accepted.Owner);
                    Interlocked.Exchange(ref state,Finished);
                    return;
                }
                if (observed == Stopping || observed == ReleaseRequested)
                {
                    Result owned = Interlocked.Exchange(ref slot, null);
                    DisposeOnWorker(owned == null ? null : owned.Owner);
                    Interlocked.Exchange(ref state, Finished);
                }
                return;
            }
        }
        finally
        {
            workerFinished.Set();
            cancelSignal.Set();
        }
    }

    private void DisposeOnWorker(IDisposable owner)
    {
        if (owner == null) return;
        try
        {
            owner.Dispose();
        }
        catch (Exception error)
        {
            string detail = "allocation disposal failed; runtime and journal remain retained or uncertain: " + error.GetType().Name;
            failure = String.IsNullOrEmpty(failure) ? detail : failure + "; " + detail;
        }
    }

#if SCOPED_RUNNER_TESTING
    private static readonly System.Collections.Generic.List<MonitorStagingHandoff> FixtureInstances = new System.Collections.Generic.List<MonitorStagingHandoff>();
    internal static MonitorStagingHandoff CreateForFixture(Func<LaunchSpecification, CancellationToken, Result> operation)
    {
        var handoff = new MonitorStagingHandoff(operation,null);
        FixtureInstances.Add(handoff);
        return handoff;
    }
    internal static MonitorStagingHandoff CreateForFixture(Func<LaunchSpecification, CancellationToken, Result> operation,
        Action<Result,LaunchSpecification,CancellationToken> accepted)
    {
        var handoff=new MonitorStagingHandoff(operation,accepted);
        FixtureInstances.Add(handoff);
        return handoff;
    }
    internal static void StopFixtures()
    {
        for (int i = 0; i < FixtureInstances.Count; i++) FixtureInstances[i].Stop();
        FixtureInstances.Clear();
    }
    internal string StateForFixture
    {
        get
        {
            switch (Volatile.Read(ref state))
            {
                case Idle: return "Idle"; case Running: return "Running"; case Published: return "Published";
                case AcceptancePending: return "AcceptancePending";
                case Accepted: return "Accepted"; case Stopping: return "Stopping"; case ReleaseRequested: return "ReleaseRequested";
                case Finished: return "Finished"; case Failed: return "Failed"; default: return "Unknown";
            }
        }
    }
    internal bool TryAcceptForFixture(bool live) { return TryAccept(() => live); }
    internal string WaitForAcceptanceObservationForFixture()
    {
        int signaled=WaitHandle.WaitAny(new WaitHandle[] { lifecycleObservedForFixture,pendingObservedForFixture },5000);
        if(signaled==0) return "Accepted";
        if(signaled==1) return "AcceptancePending";
        throw new TimeoutException("owner worker did not observe acceptance state");
    }
    internal void WaitForFixtureWorker()
    {
        // Fixture-only synchronization; production watchdog never calls this.
        // Worker completion is represented by this event, not by a process handle.
        if (!workerFinished.WaitOne(5000)) throw new TimeoutException("staging worker did not finish");
    }
    internal void WaitForPublishedForFixture()
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(5);
        while (!IsPublished && !IsFailed && DateTime.UtcNow < deadline) Thread.Sleep(1);
        if (!IsPublished) throw new TimeoutException("staging worker did not publish a result");
    }
    internal void Poll() { Thread.VolatileRead(ref state); }
#endif
}
