# Monitor staging ownership source review

Reviewed candidate `8f75da530c91c34fc3062e29d45bb865e2d411e4` in
`/Users/hoppworks/projects/rhai-windows-scoped-runner` on 2026-09-30.
This closes the source slice in briefs/windows-monitor-staging-ownership.md,
not the full custody correction or any strict/native acceptance requirement.

OCR commit preview selected three production C# files. All three were reviewed
under the default correctness, ownership, failure and coverage rules. The README
and both fixture files excluded by OCR were reviewed manually in full/diff.
Total files: six; reviewed: six; skipped: zero; coverage: 100 percent.
Configured author is Daniel Hopp. Candidate worktree is clean; immutable commit
whitespace inspection passed. No source was integrated into the coordinator.

## Closed source requirements

Actual RunMonitor starts at most one worker after immutable input completion and
fresh protocol, client, EOF and writer checks. It polls completion without
waiting. The backend factory is fixed, not caller-supplied in production.
BeginAuthorizedAllocation, CreateRuntime and StageSourceTree run on the worker.
The watchdog never invokes these operations or allocation disposal.

One atomic slot orders publication, acceptance and stop. Stop rejects pending
and late results; accepted ownership returns to the worker for disposal.
Acceptance checks fresh liveness on both sides of its CAS. No allocation handle
is exposed to a concurrent watchdog close. Independent cancellation signalling
updates the backend's private token away from the watchdog. Existing backend
token checks register no callbacks. Already admitted I/O can finish after stop;
process exit can preempt disposal. Neither result is a removal receipt.

Contract fixture source predates implementation and exercises the real handoff
seam with a testing-only fake backend: single start, failure, stop before/during
work, token observation, late successful completion, acceptance/replay, rejected
acceptance, deadline crossing and a gated worker independent of watchdog stop.
Finite fake waits and a finally block stop controllers and release their gates
on assertion failure. The intake fixture entrypoint calls these cases.

Draft findings were corrected: nonexistent backend factory, missing pre-run
stop check, overwritten disposal diagnostic, start/stop and cancellation-test
races, scheduling-sensitive stopwatch assertion, unbounded fake gate and
missing assertion-failure stop/release. Final source has no remaining finding
that blocks this closed-launch slice. This is static assessment only.

## Unverified and incomplete

No compiler, fixture, guest, native operation, runtime allocation or build was
launched. No executed RED/GREEN or failing assertion control exists for this
slice. Compiler/runtime ABI, real worker scheduling, OS handles, cancellation,
source copying, ACLs, journal durability and process-teardown behavior remain
unverified. Fake fixtures prove no native property.

Payload invocation, job creation/resume, runtime deletion and exact-job closure
proof remain disabled. Post-staging launch challenges, payload/job integration,
termination/finalization budgets, evidence export and full native proof remain
incomplete. Prior intake/lease/backend source reviews remain applicable where
unchanged. Strict production acceptance and local integration are not granted.

The fixed remaining source allowance ran from 11:17 UTC to completion of this
review before 11:47 UTC. Zero execution launches and zero runtime resources.
This is the same Expert-02 correction, with no new package, escalation or reset
of prior history. Do not silently extend its scope or start native work.


## Monitor-owned launch transitions checkpoint — 2026-10-01

Accepted source-only checkpoint `09b0fd4d4a09625fa8589193390e6c8689296070`
on the fork's `task/windows-scoped-runner`. Independent remote readback matches;
both immutable author and committer are `hoppworks <daniel@hoppworks.de>`.
Earlier published attribution remains preserved; this does not integrate that
history or production source into fork main.

The prior review covered all eleven changed paths: OCR selected five production
C# sources; the README, state and four fixture exclusions were manually reviewed.
No path was skipped. Independent immutable blob hashes below match the frozen
inputs reviewed before commit. Whitespace validation passed.

One staging worker now retains allocation custody through creation, suspended
state, resume and stop/disposal. Fresh explicitly requested phase-bound challenges
authorize creation and resume separately; ordinary maintenance responses and
replays cannot authorize either. Setup deadline stops applying after Running;
lease and absolute deadlines continue. Watchdog dispatch/poll/stop stays separate
from native operations and worker disposal. Public workload invocation remains
disabled while the remaining custody requirements are unfinished.

Review corrected a real acceptance-publication race: Accepted was visible before
the final liveness check. AcceptancePending now prevents worker continuation until
that check succeeds; stop can win in the pending state. The fixture source pauses
the final callback and acknowledges the worker's observation of Pending before
asserting no continuation. An intake lifecycle fixture exercises production
challenge request/wait helpers with model allocation/native callbacks and atomic
clock access. These fixtures remain uncompiled and unexecuted; they establish no
native scheduling, OS job membership or cleanup property.

Next source requirement reuses sole Expert02: exact-handle root-exit/status
observation, termination of residual job members on normal root completion,
one bounded cleanup deadline, confirmed process/thread handle closure, exact-job
emptiness and final job handle closure. Only all verified facts may mint private
closure proof bound to the exact allocation reference and immutable identity.
Outcome and cleanup diagnostics remain separate. Evidence export/finalization and
runtime removal remain fail-closed until implemented and proved. No compiler,
native guest, bootstrap, install, agent-home mutation or resource-cap extension
is authorized by this source checkpoint. Full strict Windows acceptance is open.

Immutable reviewed input hashes (SHA-256):

```text
a7f8ac07402ebe3fe0d02787ecbca50647e5c4cabb26c291a030bcf7c3cc3299  .scratch/windows-monitor-job-owner/coordinator-state.md
dcc73bab92fe0b83a27256ccade1c1136f92a5b2415add2376b6401f896ffab5  tools/windows-scoped-runner/LeaseMonitor.cs
7cd0fc2295d20f2c4eb3633f78919a8a2b0571faef6dbc133fae6b1253508378  tools/windows-scoped-runner/MonitorPayloadJob.cs
0f0a71563e6c3d99f0c643644d4b56951f6c69ceb3b10b03157f68dc37bb8412  tools/windows-scoped-runner/MonitorSpecificationIntake.cs
2347f91682945caf9a8c883cde6467c9a1c6ed1248b7048a9959fa691d15e6d7  tools/windows-scoped-runner/MonitorStagingHandoff.cs
3deef5657e57394fb96c78f8a7f177d696a2c8a2c1bc60bc7320b1e57e526ec9  tools/windows-scoped-runner/MonitorTransport.cs
d8d578f5e94d8e2700d45d072aa13f5ebfb12d3770191ef9fbb1ba8005dfdcac  tools/windows-scoped-runner/README.md
c466da5498e6908f273158384c73d58b055f083930bc9fac7c7af2a7dbf12251  tools/windows-scoped-runner/fixtures/LeaseProtocolFixture.cs
139e4ccc854c3cd5dcc0bb51e043c00fa74ced1ff05584fb4362449fb4d05ecb  tools/windows-scoped-runner/fixtures/MonitorPayloadJobFixture.cs
3e774455bc25a3f0fa40162e4ca3f5d59f35270d27b41c3e2aceb0f144f73d8d  tools/windows-scoped-runner/fixtures/MonitorSpecificationIntakeFixture.cs
e4dce4e35d3779d76f20be03bddfb4acbc138eda6a54d6c9011b5932d2a409cb  tools/windows-scoped-runner/fixtures/MonitorStagingHandoffFixture.cs
```
