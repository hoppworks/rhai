// Source contract fixture for monitor-owned transition and handle failure
// semantics. Compile only in the authorized Windows custody harness; this
// task leaves it intentionally uncompiled and unexecuted.
using System;
using System.IO;
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

        uint capturedExit;
        Expect("signaled root may legitimately report exit code 259",MonitorPayloadJob.TryCaptureSignaledExitCode(true,259,out capturedExit) && capturedExit==259);
        Expect("unsignaled root never captures a value that resembles STILL_ACTIVE",!MonitorPayloadJob.TryCaptureSignaledExitCode(false,259,out capturedExit));

        var normalOps=new MonitorPayloadJob.ScriptedClosureOperations { RootWaitElapsed=250, ActiveCounts=new uint[] { 1,0 } };
        var normalJob=MonitorPayloadJob.ForClosureFixture(null,normalOps);
        bool normalCleanupFailed=false;
        try { normalJob.CloseAndVerify(); } catch(IOException) { normalCleanupFailed=true; }
        Expect("normal root exit with residual members terminates, waits, closes exact handles, and polls the same job",
            normalCleanupFailed && normalOps.Events.IndexOf("terminate-job")<normalOps.Events.IndexOf("wait-root") &&
            normalOps.Events.IndexOf("wait-root")<normalOps.Events.IndexOf("read-exit-code") &&
            normalOps.Events.IndexOf("read-exit-code")<normalOps.Events.IndexOf("close-thread") &&
            normalOps.Events.IndexOf("close-thread")<normalOps.Events.IndexOf("close-process") &&
            normalOps.Events.IndexOf("close-process")<normalOps.Events.IndexOf("query-job") &&
            normalOps.Events.IndexOf("query-job")<normalOps.Events.IndexOf("close-job") &&
            normalOps.Events.Contains("sleep-100") && normalOps.RootWaitBudgets.Count==1 && normalOps.RootWaitBudgets[0]==30000 &&
            normalOps.QueryTimes.Count==2 && normalJob.RootExitCode==259);

        var deadlineOps=new MonitorPayloadJob.ScriptedClosureOperations { RootWaitResult=258, RootWaitElapsed=30000, ActiveCounts=new uint[] { 1 } };
        var deadlineJob=MonitorPayloadJob.ForClosureFixture(null,deadlineOps);
        bool deadlineFailed=false; try { deadlineJob.CloseAndVerify(); } catch(IOException) { deadlineFailed=true; }
        Expect("root wait consumes the one cleanup deadline and still attempts job close without polling on a fresh budget",
            deadlineFailed && deadlineOps.Events.Contains("terminate-job") && !deadlineOps.Events.Contains("query-job") && deadlineOps.Events.Contains("close-job"));

        var sharedOps=new MonitorPayloadJob.ScriptedClosureOperations { RootWaitElapsed=29500, ActiveCounts=new uint[] { 1 } };
        var sharedJob=MonitorPayloadJob.ForClosureFixture(null,sharedOps);
        bool sharedDeadlineFailed=false; try { sharedJob.CloseAndVerify(); } catch(IOException) { sharedDeadlineFailed=true; }
        Expect("job emptiness polling receives only the time left after the exact-root wait",
            sharedDeadlineFailed && sharedOps.RootWaitBudgets.Count==1 && sharedOps.RootWaitBudgets[0]==30000 &&
            sharedOps.QueryTimes.Count==5 && sharedOps.QueryTimes[0]==30500 && sharedOps.QueryTimes[4]==30900 &&
            sharedOps.Events.FindAll(delegate(string item) { return item=="sleep-100"; }).Count==5 &&
            sharedOps.Clock==31000 && sharedOps.Events.IndexOf("query-job")<sharedOps.Events.IndexOf("close-job"));

        var queryOps=new MonitorPayloadJob.ScriptedClosureOperations { QuerySucceeds=false };
        var queryJob=MonitorPayloadJob.ForClosureFixture(null,queryOps);
        IOException queryError=null; try { queryJob.CloseAndVerify(); } catch(IOException error) { queryError=error; }
        Expect("query failure is retained while exact job close still runs and proof stays withheld",
            queryError!=null && queryError.ToString().Contains("scripted operation failure: QueryInformationJobObject(payload closure)") &&
            queryOps.Events.Contains("query-job") && queryOps.Events.Contains("close-job") && queryJob.ClosureAuthorization==null);

        var terminationOps=new MonitorPayloadJob.ScriptedClosureOperations { TerminationSucceeds=false };
        var terminationJob=MonitorPayloadJob.ForClosureFixture(null,terminationOps);
        IOException terminationError=null; try { terminationJob.CloseAndVerify(); } catch(IOException error) { terminationError=error; }
        Expect("termination failure does not skip waits, closes, or accounting and withholds proof",
            terminationError!=null && terminationError.ToString().Contains("scripted operation failure: TerminateJobObject(exact payload closure)") &&
            terminationOps.Events.Contains("wait-root") && terminationOps.Events.Contains("query-job") &&
            terminationOps.Events.Contains("close-job") && terminationJob.ClosureAuthorization==null);

        var closeOps=new MonitorPayloadJob.ScriptedClosureOperations { CloseFailureRole="process" };
        var closeJob=MonitorPayloadJob.ForClosureFixture(null,closeOps);
        IOException processCloseError=null; try { closeJob.CloseAndVerify(); } catch(IOException error) { processCloseError=error; }
        Expect("failed process close retains its owner while emptiness query and job close are still attempted",
            processCloseError!=null && processCloseError.ToString().Contains("scripted close failure: process") &&
            closeOps.Events.Contains("query-job") && closeOps.Events.Contains("close-job") && closeJob.ClosureAuthorization==null);

        var threadCloseOps=new MonitorPayloadJob.ScriptedClosureOperations { CloseFailureRole="thread" };
        var threadClose=MonitorPayloadJob.ForClosureFixture(null,threadCloseOps);
        IOException threadCloseError=null; try { threadClose.CloseAndVerify(); } catch(IOException error) { threadCloseError=error; }
        Expect("failed thread close retains its owner while process and job cleanup continue",
            threadCloseError!=null && threadCloseError.ToString().Contains("scripted close failure: thread") &&
            threadCloseOps.Events.Contains("close-process") && threadCloseOps.Events.Contains("query-job") &&
            threadCloseOps.Events.Contains("close-job") && threadClose.ClosureAuthorization==null);

        var exitReadOps=new MonitorPayloadJob.ScriptedClosureOperations { ExitReadSucceeds=false };
        var exitReadJob=MonitorPayloadJob.ForClosureFixture(null,exitReadOps);
        IOException exitReadError=null; try { exitReadJob.CloseAndVerify(); } catch(IOException error) { exitReadError=error; }
        Expect("exit-code read failure is retained while later closure steps continue",
            exitReadError!=null && exitReadError.ToString().Contains("scripted operation failure: GetExitCodeProcess(signaled exact payload root during closure)") &&
            exitReadOps.Events.Contains("close-thread") && exitReadOps.Events.Contains("query-job") && exitReadOps.Events.Contains("close-job"));

        var jobCloseOps=new MonitorPayloadJob.ScriptedClosureOperations { CloseFailureRole="job" };
        var jobClose=MonitorPayloadJob.ForClosureFixture(null,jobCloseOps);
        IOException jobCloseError=null; try { jobClose.CloseAndVerify(); } catch(IOException error) { jobCloseError=error; }
        Expect("failed final job close retains the exact owner and withholds proof",
            jobCloseError!=null && jobCloseError.ToString().Contains("scripted close failure: job") &&
            jobCloseOps.Events.Contains("query-job") && jobCloseOps.Events.Contains("close-job") && jobClose.ClosureAuthorization==null);

        var lateCloseOps=new MonitorPayloadJob.ScriptedClosureOperations { FinalJobCloseElapsed=30001 };
        var lateCloseJob=MonitorPayloadJob.ForClosureFixture(null,lateCloseOps);
        IOException lateCloseError=null; try { lateCloseJob.CloseAndVerify(); } catch(IOException error) { lateCloseError=error; }
        Expect("job handle close finishing beyond the shared deadline withholds proof",
            lateCloseError!=null && lateCloseError.ToString().Contains("exact job handle closure completed after the shared cleanup deadline") &&
            lateCloseJob.ClosureAuthorization==null);

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
