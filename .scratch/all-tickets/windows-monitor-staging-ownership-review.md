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


## Exact-job lifecycle candidate review — not yet accepted

Current source-only package uses exact root polling, a shared cleanup deadline
and allocation-bound receipt. Early review corrected rejection of legitimate
signaled exit259 and missing deadline readback after final job closure.
Primary API reference: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getexitcodeprocess.
No executed compiler or native evidence supports this candidate.

A subsequent frozen candidate was not accepted: boolean ClosureFacts fixture
checks mirror the mint conjunction but do not exercise actual termination,
root observation, handle closure, job polling, ordering or budget consumption.
The responsible context is adding deterministic fake native operations around
the same production cleanup algorithm, with explicit model/native boundaries.
Private nested ClosureReceipt construction from its containing owner also
requires a compiler-safe guarded factory; changing to an unchecked internal
constructor would invalidate the proof authority. Microsoft constructor rule:
https://learn.microsoft.com/en-us/dotnet/csharp/programming-guide/classes-and-structs/private-constructors.
These are unexecuted source review findings, not failed native corrections.
Existing sole Expert02/history, private ownership, source-only scope and all
actual resource limits remain unchanged. Runtime removal stays uninvoked.

## Exact-job closure source checkpoint — 2026-10-01

Independently verified fork task/windows-scoped-runner at c08bdd089bfa09d8b2ec61d7fe1f13939eb10951, with author and committer hoppworks <daniel@hoppworks.de>. OCR selected three production files and excluded two fixtures and state. All six paths reviewed; no skipped path. Diff check passed. Immutable input SHA-256 values:

- .scratch/windows-monitor-job-owner/coordinator-state.md: 5273922bf7f0938bbb76e8918821781dd4e5be579d999f427c48bb7608d6bc5a
- tools/windows-scoped-runner/LeaseMonitor.cs: 72c79f18c96e28f27cd1b7b39b1025da9a250e0608885de7dc48934512a46bfc
- tools/windows-scoped-runner/MonitorPayloadJob.cs: 8a470c33a82b218dd6fc9f1942f5a6822e861db8107b66649fcc98300108713a
- tools/windows-scoped-runner/MonitorStagingHandoff.cs: 33351d7af0579fdc1a3913674f0fd4f4b731a2b897e05944bba732bee65dd044
- tools/windows-scoped-runner/fixtures/CustodyBackendFixture.cs: a09228f19b3b66f6c5e6726dd88bb79540e5c5237bc98e9892a54ad56781f329
- tools/windows-scoped-runner/fixtures/MonitorPayloadJobFixture.cs: d9aae76fd68a2cb52721618cd0746af36892a7951c9d0c4d11867a05e11ca7c0

The same owner worker observes exact root exit and preserves a signaled exit code259 as data. Ordinary completion and stop both terminate residual exact-job members, wait/capture root status, close thread/process handles, query exact-job accounting until empty, then close the job. One absolute30s monotonic deadline applies throughout, including the final job close. All failures accumulate; only all confirmed facts mint a private receipt bound to the same allocation reference/recorded immutable identity. Nested factory checks the owner's private verified flag, rather than exposing an unchecked constructor. Handoff stop-publication exceptions preserve operation/cleanup diagnostics.

Source fixtures now drive the shared production cleanup algorithm through scripted operations. Root corrected a real schedule mismatch:500ms left means five100ms sleeps/queries, with no query at deadline. Failure assertions match their specific nested diagnostics, so null allocation cannot make them pass for an unrelated reason. Custody fixture supplies actual allocation identities and checks owner/identity mismatch without using a valid proof to remove runtime data.

Static checkpoint only: no compilation, executed fixture, Windows kernel operation or native strict proof. Simulated operations do not establish native membership, handle release or cleanup. Outcome finalization, saved/exported evidence and runtime removal remain incomplete and uninvoked. Next source route retains exact worker/allocation ownership and implements bounded local evidence finalization before any exact-proof removal. No native/bootstrap scope or resource limit changed.

## Outcome metadata source gate — 2026-10-01

All five changed paths independently read, hashes matched, diff check passed. This is a source-only checkpoint, not executed or native acceptance. Metadata explicitly distinguishes saved metadata from unsaved payload artifacts; neither exact closure alone nor the metadata receipt can authorize production removal. Receipt creation checks privately recorded outcome, proof, identity and deadline; repeat-call mismatches reject. Fixture-only NoPayload capability remains separate. Fixtures cover truthful flags, changed exit/supervision/deadline, foreign receipt, specific pending-artifact refusal and retained files, pre-append expiry and injected append failure. None ran.

- .scratch/windows-monitor-job-owner/coordinator-state.md: 70d40afac6e1334fd6cfef2ed4e644daffffd849488f03320bf3f2e631e70010
- tools/windows-scoped-runner/MonitorStagingHandoff.cs: 4123b6321e0b0146acf76bbef237cc61cfa19a57cc390636f66b717cc88847ce
- tools/windows-scoped-runner/README.md: 753e58b8df6f9fb5240c47c10851af737c16eb60765222f184a39a6faad9fdcd
- tools/windows-scoped-runner/WindowsCustodyBackend.cs: 7ccee601fdf73da4f91b6057f3de037887adc61516661eafbd63acee44beaba3
- tools/windows-scoped-runner/fixtures/CustodyBackendFixture.cs: 9e3e3ed3f1c2655cb74bc0c109d61a2c0ac77b700d7cb5e2b072f8922a33e5fc

Immutable6152e24677b8202cd6ba354cc0a91c3fe377cc8b independently read back on https://github.com/hoppworks/rhai.git task/windows-scoped-runner, author/committer both hoppworks <daniel@hoppworks.de>; all five immutable hashes match. Next required behavior is actual bounded payload logs/results/manifest capture outside runtime, independent readback and allocation-bound finalization authority. Preserve failure diagnostics too: current cleanup-failure path bypasses outcome append. No removal execution, compiler/native/bootstrap launch, new Expert chain or resource-cap change authorized by this gate.


## Mutable capture continuation: independent source findings

The current package is not frozen, compiled, executed, or accepted as evidence capture. Independent review found lifecycle diagnostics falsely used absence of cleanup exceptions as cleanup confirmation and silently ignored changed repeat inputs. The responsible owner now requires an allocation-bound exact closure proof for confirmation and compares diagnostic/proof/deadline repeat binding; these source corrections remain unexecuted and part of the cohesive capture package.

Preliminary review of the new PayloadOutputCapture found pending-I/O disposal was not retained custody: GC.KeepAlive lasts only through the call, while setting disposed prevents retry and no completion observer is retained. Partial constructor failure after pending ConnectNamedPipe and finalization deadline with incomplete cancellation require retained exact channel ownership until terminal completion. Assigned to the same owner under existing Expert02; no extra native/build launch or advisory chain. Successful evidence/removal must independently reject TransitionFailed rather than infer operation success solely from absent exception fields.

Primary API cross-check: [CancelIoEx](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelioex) requests cancellation without waiting; a raced no-request-found result does not certify completion. [GetOverlappedResult](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-getoverlappedresult) with nonblocking retrieval distinguishes pending from terminal state. Exact buffer/OVERLAPPED/event custody must survive either race. This is source/API review, not native proof.
