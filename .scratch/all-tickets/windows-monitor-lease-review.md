# Windows monitor lease source review

Candidate: task/windows-scoped-runner at
0999a552987d8d836553b4c170cf6e81c8e96d00, following source substep
74138c71e6027c2b584f6a0236c181750ebca398. Owned checkout:
/Users/hoppworks/projects/rhai-windows-scoped-runner. Candidate is not integrated.

OCR delegate preview for 74138c71 selected LeaseMonitor.cs, MonitorTransport.cs
and ScopedRunner.cs, excluding README.md and LeaseProtocolFixture.cs. All five
changed files were manually reviewed under the default correctness/resource
rules: 5 reviewed, 0 skipped. The related 0999a552 transport diff was reviewed.

Source contains detached monitor launch, explicit three-handle inheritance,
restricted real client handle, ambient-job refusal, bounded nonblocking queues,
bounded per-watchdog-pass frame processing, strict UTF-8 and partial-frame
rejection. The state model has phase-bound one-use create/resume authorization,
fresh nonce/sequence, independent setup/lease/absolute expiry and irreversible
stopping. Client failure no longer terminates the monitor. Workload dispatch to
the older unsafe staging path is disabled.

Review corrected no-response authorization, cross-phase/prebuffered response
reuse, zero-time start, API declarations/argument order, platform clock, argv
quoting, pipe buffering, unbounded input processing, monitor dispatch and
exceptional handle transfer/release. Fixture timestamps were corrected to isolate
setup expiry from lease expiry and absolute expiry from setup expiry; the full
queue case now fills its declared bounds while the modeled watchdog is live.
The [Microsoft constructor reference](https://learn.microsoft.com/en-us/dotnet/api/system.io.filestream.-ctor)
confirms the IntPtr FileStream ownership/buffer argument order used in 0999a552.

Actual check: git diff --check passed in the responsible checkout. No C# compiler,
protocol fixture, OS fixture, monitor, guest or package workload was executed.
This is source review, not TDD RED/GREEN, compilation, transport survival,
independent process/job readback or native acceptance. No temporary runtime or
fixture processes were created. Candidate checkout is clean.

The monitor currently stops after its first valid response because no safe
backend exists. The second authorization is implemented only in the protocol
state model/fixture source. There is no immutable workload specification handling,
safe runtime allocation/staging, protected ACL/identity, durable journal, local
evidence receipt/export, monitor-held payload job or actual payload integration.
Termination/finalization budgets and verified runtime removal remain outstanding.
All native gates from the Expert answer remain mandatory. Existing creation
fixtures target the earlier entry and are currently not wired into public dispatch.

Next source step: safe handle-based runtime/staging and ownership journal, then
immutable specification and payload integration with both host authorizations.
Do not merge or enable workload dispatch on this source-only review.
