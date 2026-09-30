// Source-only contract cases for monitor staging ownership. Not executed here.
using System;
using System.Threading;

internal static class MonitorStagingHandoffFixture
{
    internal static void Run()
    {
        try
        {
            StartOnce(); StopBeforeStart(); WorkerFailure(); StopDuringWork();
            LateCompletion(); SingleHandoff(); RejectedHandoff(); DeadlineCrossing(); WatchdogDoesNotWaitForWorker();
        }
        finally
        {
            MonitorStagingHandoff.StopFixtures();
            FakeBackend.ReleaseAll();
        }
    }

    private static void StartOnce()
    {
        var backend = new FakeBackend();
        var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        var spec = LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0]);
        Expect("first start accepted", handoff.Start(spec));
        Expect("second start refused", !handoff.Start(spec));
        backend.WaitEntered(); handoff.Stop(); backend.Release(); handoff.WaitForFixtureWorker();
        Expect("one backend invocation", backend.Calls == 1);
    }

    private static void WorkerFailure()
    {
        var backend = new FakeBackend { Fail = true };
        var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        handoff.Start(LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0]));
        backend.WaitEntered(); handoff.Poll(); backend.Release(); handoff.WaitForFixtureWorker();
        Expect("failed owner disposed by worker", backend.Owner.DisposeCount == 1 && handoff.StateForFixture == "Failed");
    }

    private static void StopBeforeStart()
    {
        var backend = new FakeBackend(); var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        handoff.Stop();
        Expect("stopped handoff cannot start", !handoff.Start(LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0])) && backend.Calls == 0);
    }

    private static void StopDuringWork()
    {
        var backend = new FakeBackend(); var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        handoff.Start(LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0])); backend.WaitEntered();
        handoff.Stop();
        Expect("worker receives the signal without opening its work gate", backend.CancellationSignalSeen.WaitOne(5000));
        backend.Release(); handoff.WaitForFixtureWorker();
        Expect("worker observes cancellation and disposes its owner", backend.CancellationObserved && backend.Owner.DisposeCount == 1);
    }

    private static void LateCompletion()
    {
        var backend = new FakeBackend { IgnoreCancellation = true }; var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        handoff.Start(LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0])); backend.WaitEntered();
        handoff.Stop(); backend.Release(); handoff.WaitForFixtureWorker();
        Expect("late staged completion never publishes", !handoff.TryAcceptForFixture(true) && backend.Owner.DisposeCount == 1);
    }

    private static void SingleHandoff()
    {
        var backend = new FakeBackend(); var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        handoff.Start(LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0])); backend.Release();
        handoff.WaitForPublishedForFixture();
        Expect("one live acceptance", handoff.TryAcceptForFixture(true));
        Expect("replay rejected", !handoff.TryAcceptForFixture(true) && backend.Owner.DisposeCount == 0);
        handoff.Stop(); handoff.WaitForFixtureWorker();
        Expect("accepted owner returned and disposed by worker on stop", backend.Owner.DisposeCount == 1);
    }

    private static void RejectedHandoff()
    {
        var backend = new FakeBackend(); var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        handoff.Start(LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0])); backend.Release(); handoff.WaitForPublishedForFixture();
        Expect("deadline rejection", !handoff.TryAcceptForFixture(false)); handoff.WaitForFixtureWorker();
        Expect("rejected owner disposed on worker", backend.Owner.DisposeCount == 1);
    }

    private static void DeadlineCrossing()
    {
        var backend = new FakeBackend(); var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        handoff.Start(LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0])); backend.Release(); handoff.WaitForPublishedForFixture();
        int checks = 0;
        Expect("deadline crossing rejects post-CAS result", !handoff.TryAccept(() => ++checks == 1));
        handoff.WaitForFixtureWorker();
        Expect("deadline crossing releases owner to worker", checks == 2 && backend.Owner.DisposeCount == 1);
    }

    private static void WatchdogDoesNotWaitForWorker()
    {
        var backend = new FakeBackend { IgnoreCancellation = true }; var handoff = MonitorStagingHandoff.CreateForFixture(backend.Run);
        handoff.Start(LaunchSpecification.Create(@"C:\src", @"bin\app.exe", new string[0])); backend.WaitEntered();
        var finished = new ManualResetEvent(false);
        var watchdog = new Thread(() => { handoff.Stop(); handoff.Poll(); finished.Set(); }); watchdog.IsBackground = true; watchdog.Start();
        Expect("watchdog stop and poll return while backend remains gated", finished.WaitOne(5000) && backend.Owner.DisposeCount == 0);
        backend.Release(); handoff.WaitForFixtureWorker();
    }

    private static void Expect(string message, bool condition) { if (!condition) throw new InvalidOperationException(message); }

    private sealed class FakeOwner : IDisposable
    {
        internal int DisposeCount;
        public void Dispose() { Interlocked.Increment(ref DisposeCount); }
    }
    private sealed class FakeBackend
    {
        private static readonly System.Collections.Generic.List<FakeBackend> Instances = new System.Collections.Generic.List<FakeBackend>();
        internal FakeBackend() { Instances.Add(this); }
        internal static void ReleaseAll() { for (int i = 0; i < Instances.Count; i++) Instances[i].Release(); Instances.Clear(); }
        internal readonly FakeOwner Owner = new FakeOwner();
        internal readonly ManualResetEvent Entered = new ManualResetEvent(false), Gate = new ManualResetEvent(false), CancellationSignalSeen = new ManualResetEvent(false);
        internal int Calls; internal bool Fail; internal bool IgnoreCancellation; internal bool CancellationObserved;
        internal MonitorStagingHandoff.Result Run(LaunchSpecification spec, CancellationToken token)
        {
            Interlocked.Increment(ref Calls); Entered.Set();
            bool released = false;
            var deadline = DateTime.UtcNow.AddSeconds(5);
            while (!released && DateTime.UtcNow < deadline)
            {
                released = Gate.WaitOne(10);
                if (!IgnoreCancellation && token.IsCancellationRequested)
                {
                    CancellationObserved = true; CancellationSignalSeen.Set();
                    return new MonitorStagingHandoff.Result(Owner, false, "fixture observed cancellation");
                }
            }
            if (!released) return new MonitorStagingHandoff.Result(Owner, false, "fixture backend gate timed out");
            return new MonitorStagingHandoff.Result(Owner, !Fail, Fail ? "fixture failure" : null);
        }
        internal void WaitEntered() { if (!Entered.WaitOne(5000)) throw new TimeoutException("fake backend did not start"); }
        internal void Release() { Gate.Set(); }
    }
}
