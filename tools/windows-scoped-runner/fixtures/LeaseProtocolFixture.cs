// Protocol-only behavioral fixture source. Compile all runner sources under
// SCOPED_RUNNER_TESTING with LeaseProtocolFixture as the startup object, and run
// only in an authorized Windows custody harness.
// This fixture does not create payload processes or access a staging backend.
using System;
using System.Collections.Generic;

internal static class LeaseProtocolFixture
{
    private static int failures;

    private static void Expect(string name, bool actual, bool expected)
    {
        if (actual != expected)
        {
            failures++;
            Console.Error.WriteLine("FAIL " + name + ": expected " + expected + ", got " + actual);
        }
        else Console.WriteLine("PASS " + name);
    }

    private static bool AuthorizationSurvives(LeaseMonitor.Protocol protocol, long now, string kind)
    {
        LeaseMonitor.Challenge c = protocol.IssueChallenge(now);
        if (kind == "stale-sequence") return protocol.AcceptResponse(c.Sequence - 1, c.Nonce, now);
        if (kind == "stale-nonce") return protocol.AcceptResponse(c.Sequence, "old-nonce", now);
        if (kind == "prebuffered-future") return protocol.AcceptResponse(c.Sequence + 1, c.Nonce, now);
        return protocol.AcceptResponse(c.Sequence, c.Nonce, now);
    }

    public static int Main()
    {
        var p = New(10); Expect("stale sequence is rejected", AuthorizationSurvives(p, 10, "stale-sequence"), false);
        p = New(10); Expect("stale nonce is rejected", AuthorizationSurvives(p, 10, "stale-nonce"), false);
        p = New(10); Expect("prebuffered future sequence is rejected", AuthorizationSurvives(p, 10, "prebuffered-future"), false);

        p = New(10);
        Expect("create cannot be authorized without a host response", p.AuthorizeCreate(10), false);
        LeaseMonitor.Challenge first = p.IssueChallenge(10);
        Expect("valid response authorizes create", p.AcceptResponse(first.Sequence, first.Nonce, 11) && p.AuthorizeCreate(11), true);
        Expect("same consumed response cannot authorize resume", p.MarkSuspended(12) && !p.AcceptResponse(first.Sequence, first.Nonce, 12) && !p.AuthorizeResume(12), true);

        p=New(0); first=p.IssueChallenge(0); p.AcceptResponse(first.Sequence,first.Nonce,1); p.AuthorizeCreate(1);
        Expect("consumed create-phase challenge cannot authorize resume after suspended transition", p.MarkSuspended(3) && !p.AcceptResponse(first.Sequence,first.Nonce,3) && !p.AuthorizeResume(3), true);

        p = New(0);
        for(long t=0;t<LeaseMonitor.Protocol.TestPolicy().SetupDeadline;t+=2)
        {
            LeaseMonitor.Challenge c=p.IssueChallenge(t);
            Expect("setup challenge is issued before setup deadline at " + t, c != null, true);
            if(c!=null) Expect("setup response renews lease at " + t, p.AcceptResponse(c.Sequence,c.Nonce,t+1), true);
            Expect("setup remains active before setup deadline at " + (t+1), p.Tick(t+1) == LeaseMonitor.State.Ready, true);
        }
        Expect("setup deadline enters stopping with a live renewed lease", p.Tick(LeaseMonitor.Protocol.TestPolicy().SetupDeadline) == LeaseMonitor.State.Stopping, true);

        p = New(1); first = p.IssueChallenge(1); p.AcceptResponse(first.Sequence, first.Nonce, 2); p.AuthorizeCreate(2); p.MarkSuspended(3);
        Expect("lease expiry before second handshake blocks resume", p.Tick(7) == LeaseMonitor.State.Stopping && !p.AuthorizeResume(7), true);

        p = EnterRunning();
        long absolute = LeaseMonitor.Protocol.TestPolicy().AbsoluteDeadline;
        long renewalAt = 5;
        while (renewalAt < absolute - 1)
        {
            Expect("running remains live before renewal at " + renewalAt, p.Tick(renewalAt) == LeaseMonitor.State.Running, true);
            LeaseMonitor.Challenge renewal = p.IssueChallenge(renewalAt);
            Expect("fresh Running challenge issued at " + renewalAt, renewal != null, true);
            if (renewal != null)
            {
                Expect("fresh Running response accepted at " + (renewalAt+1), p.AcceptResponse(renewal.Sequence,renewal.Nonce,renewalAt+1), true);
                Expect("Running response stays Running without create/resume authorization", p.State == LeaseMonitor.State.Running && !p.AuthorizeCreate(renewalAt+1) && !p.AuthorizeResume(renewalAt+1), true);
                Expect("renewed Running lease remains live at " + (renewalAt+1), p.Tick(renewalAt+1) == LeaseMonitor.State.Running, true);
            }
            renewalAt += 3;
        }
        Expect("timely Running renewals keep payload alive beyond initial lease and setup deadline", p.Tick(absolute-1) == LeaseMonitor.State.Running, true);
        Expect("renewal cannot pass fixed absolute deadline", p.Tick(absolute) == LeaseMonitor.State.Stopping, true);

        p = EnterRunning();
        LeaseMonitor.Challenge firstRenewal = p.IssueChallenge(5);
        Expect("Running challenge exists before original lease expires", firstRenewal != null, true);
        if (firstRenewal != null)
        {
            Expect("response before original lease expiry is accepted", p.AcceptResponse(firstRenewal.Sequence,firstRenewal.Nonce,7), true);
            LeaseMonitor.Challenge boundary = p.IssueChallenge(7);
            Expect("next Running challenge is issued at aligned lease boundary", boundary != null, true);
            if (boundary != null)
            {
                Expect("protocol remains Running before exact expiry", p.Tick(boundary.Expires-1) == LeaseMonitor.State.Running, true);
                Expect("response at exact lease and challenge expiry is rejected", !p.AcceptResponse(boundary.Sequence,boundary.Nonce,boundary.Expires), true);
                Expect("exact lease expiry enters stopping", p.State == LeaseMonitor.State.Stopping, true);
                Expect("response after terminal stopping is rejected", !p.AcceptResponse(boundary.Sequence,boundary.Nonce,boundary.Expires+1), true);
            }
        }

        p = New(0);
        LeaseMonitor.Challenge oldCreate = p.IssueChallenge(0);
        Expect("old create response accepted", oldCreate != null && p.AcceptResponse(oldCreate.Sequence,oldCreate.Nonce,1), true);
        Expect("create authorization succeeds for phase test", p.AuthorizeCreate(1), true);
        Expect("phase test suspends", p.MarkSuspended(2), true);
        LeaseMonitor.Challenge oldResume = p.IssueChallenge(2);
        Expect("old resume response accepted", oldResume != null && p.AcceptResponse(oldResume.Sequence,oldResume.Nonce,3), true);
        Expect("resume authorization succeeds for phase test", p.AuthorizeResume(3), true);
        p.MarkRunning(3);
        LeaseMonitor.Challenge replay = p.IssueChallenge(5);
        Expect("wrong sequence in Running is rejected", replay != null && !p.AcceptResponse(replay.Sequence+1,replay.Nonce,6), true);
        Expect("wrong nonce in Running is rejected", replay != null && !p.AcceptResponse(replay.Sequence,"old-nonce",6), true);
        Expect("consumed create-phase token cannot renew Running", oldCreate != null && !p.AcceptResponse(oldCreate.Sequence,oldCreate.Nonce,6), true);
        Expect("consumed resume-phase token cannot renew Running", oldResume != null && !p.AcceptResponse(oldResume.Sequence,oldResume.Nonce,6), true);
        Expect("valid Running response still accepted after invalid attempts", replay != null && p.AcceptResponse(replay.Sequence,replay.Nonce,6), true);
        Expect("consumed Running response replay is rejected", replay != null && !p.AcceptResponse(replay.Sequence,replay.Nonce,6), true);

        p = EnterRunning();
        LeaseMonitor.Challenge blackholed = p.IssueChallenge(5);
        Expect("blackholed live Running client expires at original lease boundary", p.Tick(8) == LeaseMonitor.State.Stopping, true);
        Expect("blackholed response after expiry is rejected", blackholed != null && !p.AcceptResponse(blackholed.Sequence,blackholed.Nonce,8), true);

        p = New(1); p.SignalClientEof(1);
        Expect("client EOF is terminal", p.State == LeaseMonitor.State.Stopping, true);
        p = New(1); p.SignalClientExited(1);
        Expect("client process death is terminal", p.State == LeaseMonitor.State.Stopping, true);

        p=New(0); first=p.IssueChallenge(0); p.AcceptResponse(first.Sequence,first.Nonce,1);
        Expect("live but blackholed client expires without EOF", p.Tick(6)==LeaseMonitor.State.Stopping, true);

        p = EnterRunning();
        var queue = new LeaseMonitor.BoundedFrameQueue(2, 32);
        Expect("output backpressure queue accepts first bounded frame", queue.TryWrite(new byte[16]), true);
        Expect("output backpressure queue accepts second bounded frame", queue.TryWrite(new byte[16]), true);
        Expect("output backpressure rejects full queue without blocking", queue.TryWrite(new byte[] { 1 }), false);
        Expect("watchdog expires live lease despite full output queue", p.Tick(9) == LeaseMonitor.State.Stopping, true);

        return failures == 0 ? 0 : 1;
    }

    private static LeaseMonitor.Protocol New(long start)
    {
        var p = new LeaseMonitor.Protocol(LeaseMonitor.Protocol.TestPolicy()); p.Start(start); return p;
    }

    private static LeaseMonitor.Protocol EnterRunning()
    {
        LeaseMonitor.Protocol p=New(0);
        LeaseMonitor.Challenge create=p.IssueChallenge(0);
        Expect("Running setup create challenge issued",create!=null,true);
        Expect("Running setup create response accepted",create!=null && p.AcceptResponse(create.Sequence,create.Nonce,1),true);
        Expect("Running setup create authorization succeeds",p.AuthorizeCreate(1),true);
        Expect("Running setup marks suspended",p.MarkSuspended(2),true);
        LeaseMonitor.Challenge resume=p.IssueChallenge(2);
        Expect("Running setup resume challenge issued",resume!=null,true);
        Expect("Running setup resume response accepted",resume!=null && p.AcceptResponse(resume.Sequence,resume.Nonce,3),true);
        Expect("Running setup resume authorization succeeds",p.AuthorizeResume(3),true);
        p.MarkRunning(3);
        Expect("protocol reaches Running state",p.State==LeaseMonitor.State.Running,true);
        return p;
    }
}
