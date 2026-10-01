// Source contract fixture for monitor-owned transition and handle failure
// semantics. Compile only in the authorized Windows custody harness; this
// task leaves it intentionally uncompiled and unexecuted.
using System;
using System.Threading;

internal static class MonitorPayloadJobFixture
{
    private static int failures;
    private static void Expect(string name, bool value)
    {
        if (!value) { failures++; Console.Error.WriteLine("FAIL " + name); }
        else Console.WriteLine("PASS " + name);
    }

    public static int Main()
    {
        var protocol = New();
        int resumed = 0;
        Expect("resume callback is gated without a suspended-phase response",
            !protocol.TryResumeAtomically(delegate { return 3; }, delegate { resumed++; return true; }) && resumed == 0);

        LeaseMonitor.Challenge maintenanceCreate = protocol.IssueChallenge(0);
        Expect("ordinary ready response cannot authorize create", maintenanceCreate != null && protocol.AcceptResponse(maintenanceCreate.Sequence, maintenanceCreate.Nonce, 1) && !protocol.AuthorizeCreate(1));
        Expect("create transition can be authorized once", protocol.RequestFreshTransitionChallenge(LeaseMonitor.State.Ready,1));
        LeaseMonitor.Challenge create = protocol.IssueChallenge(1);
        Expect("fresh create response advances to suspended", create != null && protocol.AcceptResponse(create.Sequence, create.Nonce, 1) && protocol.AuthorizeCreate(1) && protocol.MarkSuspended(2));
        Expect("create-phase response cannot authorize resume", !protocol.TryResumeAtomically(delegate { return 3; }, delegate { resumed++; return true; }) && resumed == 0);

        Expect("resume requires a newly requested suspended phase challenge", protocol.RequestFreshTransitionChallenge(LeaseMonitor.State.Suspended,2));
        LeaseMonitor.Challenge resume = protocol.IssueChallenge(2);
        Expect("fresh suspended-phase response gates atomic resume", resume != null && protocol.AcceptResponse(resume.Sequence, resume.Nonce, 3) &&
            protocol.TryResumeAtomically(delegate { return 3; }, delegate { resumed++; return true; }) && resumed == 1 && protocol.State == LeaseMonitor.State.Running);

        protocol = New();
        protocol.RequestFreshTransitionChallenge(LeaseMonitor.State.Ready,0);
        create = protocol.IssueChallenge(0);
        protocol.AcceptResponse(create.Sequence, create.Nonce, 1); protocol.AuthorizeCreate(1); protocol.MarkSuspended(2);
        protocol.RequestFreshTransitionChallenge(LeaseMonitor.State.Suspended,2);
        resume = protocol.IssueChallenge(2); protocol.AcceptResponse(resume.Sequence, resume.Nonce, 3);
        resumed = 0;
        Expect("exact lease deadline blocks callback and stops protocol", !protocol.TryResumeAtomically(delegate { return 8; }, delegate { resumed++; return true; }) && resumed == 0 && protocol.State == LeaseMonitor.State.Stopping);

        protocol = PrepareResume(out resume);
        Expect("false resume callback enters terminal stopping state", !protocol.TryResumeAtomically(delegate { return 3; }, delegate { return false; }) && protocol.State == LeaseMonitor.State.Stopping);

        protocol = PrepareResume(out resume);
        int clockReads = 0; resumed = 0;
        Expect("deadline after successful resume callback stops and rejects transition", !protocol.TryResumeAtomically(
            delegate { return ++clockReads == 1 ? 3 : 30; }, delegate { resumed++; return true; }) && resumed == 1 && protocol.State == LeaseMonitor.State.Stopping);

        protocol = PrepareResume(out resume);
        bool callbackThrew = false;
        try { protocol.TryResumeAtomically(delegate { return 3; }, delegate { throw new InvalidOperationException("fixture callback failure"); }); }
        catch (InvalidOperationException) { callbackThrew = true; }
        Expect("thrown resume callback propagates only after terminal stop", callbackThrew && protocol.State == LeaseMonitor.State.Stopping);

        protocol = PrepareResume(out resume);
        bool clockThrew = false;
        try { protocol.TryResumeAtomically(delegate { throw new InvalidOperationException("fixture clock failure"); }, delegate { resumed++; return true; }); }
        catch (InvalidOperationException) { clockThrew = true; }
        Expect("thrown resume clock propagates only after terminal stop", clockThrew && protocol.State == LeaseMonitor.State.Stopping);

        // Hold the resume callback while a competing stop arrives. The protocol
        // lock must serialize stop after the callback/state transition.
        protocol = PrepareResume(out resume);
        var entered = new ManualResetEvent(false); var release = new ManualResetEvent(false); var stopAttempted = new ManualResetEvent(false); var stopped = new ManualResetEvent(false);
        Exception threadError = null;
        var resumeThread = new Thread(delegate
        {
            try { protocol.TryResumeAtomically(delegate { return 3; }, delegate { entered.Set(); return release.WaitOne(2000); }); }
            catch (Exception error) { threadError = error; }
        });
        var stopThread = new Thread(delegate { stopAttempted.Set(); protocol.SignalClientExited(3); stopped.Set(); });
        resumeThread.Start();
        bool reached = entered.WaitOne(2000);
        stopThread.Start();
        bool stopStarted = stopAttempted.WaitOne(2000);
        // This bounded noncompletion observation is a narrow race fixture,
        // not a deterministic scheduler proof: it can only show the stop did
        // not complete during this sample after its attempt was signaled.
        bool stopWaited = stopStarted && !stopped.WaitOne(100);
        release.Set();
        bool joined = resumeThread.Join(2000) && stopThread.Join(2000);
        Expect("stop waits behind in-flight atomic resume and then becomes terminal", reached && stopWaited && joined && threadError == null && protocol.State == LeaseMonitor.State.Stopping);
        entered.Dispose(); release.Dispose(); stopAttempted.Dispose(); stopped.Dispose();

        int closeCalls = 0; int terminateCalls = 0; IntPtr exact = new IntPtr(0x1234);
        var owned = new MonitorOwnedKernelHandle(exact, true, delegate(IntPtr value)
        {
            Expect("close receives exact retained handle", value == exact);
            closeCalls++;
            return closeCalls > 1;
        }, delegate(IntPtr value) { Expect("job fallback terminates exact retained handle", value == exact); terminateCalls++; });
        Exception closeFailure;
        bool firstClose = owned.TryClose(out closeFailure);
        Expect("failed explicit close keeps SafeHandle owner open", !firstClose && closeFailure != null && !owned.IsClosed && owned.ExactValue == exact);
        bool secondClose = owned.TryClose(out closeFailure);
        Expect("retry closes retained exact owner", secondClose && owned.IsClosed && closeCalls == 2 && terminateCalls == 0);
        owned.Dispose();

        // Failed explicit close followed by Dispose invokes the SafeHandle
        // release path: terminate exact job before bounded close retry.
        closeCalls = 0; terminateCalls = 0;
        var fallback = new MonitorOwnedKernelHandle(exact, true, delegate(IntPtr value) { closeCalls++; return false; },
            delegate(IntPtr value) { if(value == exact) terminateCalls++; });
        Expect("explicit close failure is reported without surrendering ownership", !fallback.TryClose(out closeFailure) && !fallback.IsClosed);
        fallback.Dispose();
        Expect("SafeHandle release requests exact-job termination before close attempts", terminateCalls == 1 && closeCalls >= 2);
        return failures == 0 ? 0 : 1;
    }

    private static LeaseMonitor.Protocol New()
    {
        var result = new LeaseMonitor.Protocol(LeaseMonitor.Protocol.TestPolicy()); result.Start(0); return result;
    }

    private static LeaseMonitor.Protocol PrepareResume(out LeaseMonitor.Challenge resume)
    {
        LeaseMonitor.Protocol result = New();
        result.RequestFreshTransitionChallenge(LeaseMonitor.State.Ready,0);
        LeaseMonitor.Challenge create = result.IssueChallenge(0);
        result.AcceptResponse(create.Sequence, create.Nonce, 1); result.AuthorizeCreate(1); result.MarkSuspended(2);
        result.RequestFreshTransitionChallenge(LeaseMonitor.State.Suspended,2);
        resume = result.IssueChallenge(2); result.AcceptResponse(resume.Sequence, resume.Nonce, 3);
        return result;
    }
}
