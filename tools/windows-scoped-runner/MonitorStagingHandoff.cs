// Single-worker bridge from completed immutable intake to filesystem custody.
// The watchdog only changes state and signals; it never performs backend I/O,
// invokes cancellation callbacks, waits, joins, or disposes an allocation.
using System;
using System.Threading;

internal sealed class MonitorStagingHandoff
{
    private const int Idle = 0, Running = 1, Published = 2, Accepted = 3,
        Stopping = 4, ReleaseRequested = 5, Finished = 6, Failed = 7;

    internal sealed class Result
    {
        internal readonly IDisposable Owner;
        internal readonly bool Succeeded;
        internal readonly string Diagnostic;
        internal Result(IDisposable owner, bool succeeded, string diagnostic)
        { Owner = owner; Succeeded = succeeded; Diagnostic = diagnostic; }
    }

    private readonly Func<LaunchSpecification, CancellationToken, Result> run;
    private readonly ManualResetEvent cancelSignal = new ManualResetEvent(false);
    private readonly ManualResetEvent workerFinished = new ManualResetEvent(false);
    private readonly CancellationTokenSource cancellation = new CancellationTokenSource();
    private LaunchSpecification specification;
    private Result slot;
    private int state = Idle, stopRequested;
    private string failure;

    private MonitorStagingHandoff(Func<LaunchSpecification, CancellationToken, Result> operation)
    { run = operation ?? throw new ArgumentNullException("operation"); }

    // Production construction has no caller-supplied backend or path. The
    // immutable specification is the only input to the monitor-owned worker.
    internal static MonitorStagingHandoff CreateProduction()
    { return new MonitorStagingHandoff(StageWithBackend); }

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
            else if (observed == Running || observed == Published) next = Stopping;
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
        if (Interlocked.CompareExchange(ref state, Accepted, Published) != Published) return false;
        if (Volatile.Read(ref stopRequested) != 0 || !isStillLive()) { Stop(); return false; }
        return true;
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
                if (observed == Published || observed == Accepted) { Thread.Sleep(10); continue; }
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
        try { owner.Dispose(); }
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
        var handoff = new MonitorStagingHandoff(operation);
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
                case Accepted: return "Accepted"; case Stopping: return "Stopping"; case ReleaseRequested: return "ReleaseRequested";
                case Finished: return "Finished"; case Failed: return "Failed"; default: return "Unknown";
            }
        }
    }
    internal bool TryAcceptForFixture(bool live) { return TryAccept(() => live); }
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
