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
        for(long t=0;t<LeaseMonitor.Protocol.TestPolicy().SetupDeadline;t+=2) { LeaseMonitor.Challenge c=p.IssueChallenge(t); if(c!=null) p.AcceptResponse(c.Sequence,c.Nonce,t+1); }
        Expect("setup deadline enters stopping with a live renewed lease", p.Tick(LeaseMonitor.Protocol.TestPolicy().SetupDeadline) == LeaseMonitor.State.Stopping, true);

        p = New(1); first = p.IssueChallenge(1); p.AcceptResponse(first.Sequence, first.Nonce, 2); p.AuthorizeCreate(2); p.MarkSuspended(3);
        Expect("lease expiry before second handshake blocks resume", p.Tick(7) == LeaseMonitor.State.Stopping && !p.AuthorizeResume(7), true);

        p = New(0); first = p.IssueChallenge(0); p.AcceptResponse(first.Sequence, first.Nonce, 1); p.AuthorizeCreate(1); p.MarkSuspended(2);
        LeaseMonitor.Challenge second = p.IssueChallenge(2); p.AcceptResponse(second.Sequence, second.Nonce, 3); p.AuthorizeResume(3); p.MarkRunning(3);
        long now = 4;
        while (p.Tick(now) != LeaseMonitor.State.Stopping && now < LeaseMonitor.Protocol.TestPolicy().AbsoluteDeadline + 2)
        {
            LeaseMonitor.Challenge c = p.IssueChallenge(now);
            if(c!=null) p.AcceptResponse(c.Sequence, c.Nonce, now + 1);
            now += 2;
        }
        Expect("valid renewals cannot extend absolute deadline", p.State == LeaseMonitor.State.Stopping && now >= LeaseMonitor.Protocol.TestPolicy().AbsoluteDeadline, true);

        p = New(1); p.SignalClientEof(1);
        Expect("client EOF is terminal", p.State == LeaseMonitor.State.Stopping, true);
        p = New(1); p.SignalClientExited(1);
        Expect("client process death is terminal", p.State == LeaseMonitor.State.Stopping, true);

        p=New(0); first=p.IssueChallenge(0); p.AcceptResponse(first.Sequence,first.Nonce,1);
        Expect("live but blackholed client expires without EOF", p.Tick(6)==LeaseMonitor.State.Stopping, true);

        p = New(0); first = p.IssueChallenge(0); p.AcceptResponse(first.Sequence, first.Nonce, 1); p.AuthorizeCreate(1); p.MarkSuspended(2);
        second = p.IssueChallenge(2); p.AcceptResponse(second.Sequence, second.Nonce, 3); p.AuthorizeResume(3); p.MarkRunning(3);
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
}
