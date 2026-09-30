# Question

Does the final listener clone-close fixture prove actual waiting accept and own its
worker on every outcome within finite bounds? Identify any concrete correction
needed before accepting candidate8b825577; no production rewrite or execution.

# Why escalated

At least two executed readiness checks failed for the same quota-probe race
(final-green/final-net-sync/diagnostic logs). They are failed fixture corrections,
not expected TDD REDs or approved calibration. The responsible agent later fixed
the race and obtained green, but classified it as informative without escalation.
Coordinator catches this history before acceptance. One fresh Expert is required
for this cause; no previous Expert for TCP listener readiness.

# Context by reference

Owned candidate /Users/hoppworks/projects/rhai-tcp-listener, task/tcp-listener,
8b8255774a2685c2116383520853f9e667f3a79b. Read tests/net_listen.rs,
src/packages/net/listener.rs, reservation code in mod.rs, proof/state and final
accept logs at .scratch/tcp-listener/. Owner proposals and AGENTS in coordinator
/Users/hoppworks/projects/rhai-all-tickets. Full six-file coordinator source
review found only quota-release/readiness/ownership fixture concerns.

# Constraints and decisions

No builds, fixture executions, installation, remote operations or source edits.
Strict real-OS proof, explicit readiness, finite waits and close/join ownership.
Original listener package12:34–13:34UTC including review, not reset. Maximum
16 fixture resources,900s runner,2GiB. Existing green cannot alone waive a source
bound. Only one Expert and bounded responsible-context followup per cause.

# Tried so far

Initial bind-probe transiently took the second quota slot, making worker fail
ResourceLimit and exit. Accept1ms probe had same race. Final worker retries only
ResourceLimit; observed pressure then controller closes clone and joins before
assertions. Worker script retry itself has no explicit deadline. Controller probe
is bounded2s, individual accept5s, channel1s then join. Final net4+6 and sync4+7
pass; wrong independent peer assertion fails. Quota2 timeout-release now proven.

# Deliverable

Write 03-tcp-accept-readiness.answer.md next to this brief: concrete source/proof
conclusion and minimal finite correction if needed, by path/line. Return at most
15 lines plus answer path. No speculative findings or duplicate proof round.

# Budget

Maximum10 active minutes source review within original remaining listener allowance.
Zero executions/builds/resources. Stop with exact open requirement if exhausted.
