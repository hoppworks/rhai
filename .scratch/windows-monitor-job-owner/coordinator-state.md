# Monitor-owned payload job prerequisite

## Goal and limits
Complete the source-only owner prerequisite in the exact owned `task/windows-scoped-runner` worktree. No native build/run, guest input, bootstrap, home/config change, push, or merge. Existing Expert02 answer governs; no new escalation.

## Done
- Read project `AGENTS.md`, monitor implementation brief, Expert02 answer, and relevant monitor/staging/backend sources.
- Added `MonitorPayloadJob.cs`: private unnamed noninheritable kill-on-last-close job, `JOB_LIST` association at suspended process creation, exact SafeHandle-owned process/thread/job, job membership check, and protocol-gated atomic resume.
- Preallocated job/process/thread SafeHandle owners before native creation and adopted handles without allocating. Captured `CreateProcessW` last-error immediately before adoption. Failed-close paths keep handles under SafeHandle ownership.
- Setup failure adopts returned process/thread handles even when `CreateProcessW` reports failure, requests termination through the exact job/root, waits on the exact root handle, releases initialized attribute storage, attempts exact-owner closes, and preserves primary plus cleanup failures.
- Job SafeHandle release requests termination before bounded close retry. This is a fallback attempt, not proof that Windows accepted termination/close; unresolved state remains unknown.
- Lease transitions serialize stop/deadline and resume callback under one protocol lock; callback false and callback/clock exceptions enter `Stopping`. The owner requests exact-job cleanup if resume gate throws. Owner `Dispose` shares its lock with resume.
- Added `fixtures/MonitorPayloadJobFixture.cs` for missing/stale transition authority, exact lease deadline, callback false/throw, post-callback absolute deadline, clock throw, stop/resume serialization, and injected handle-close ownership cases. The fixture directly invokes SafeHandle release via `Dispose`; GC finalization is not exercised. Its stop race samples noncompletion for 100 ms after a signaled attempt; this is not a deterministic scheduler proof.
- Updated README with implementation and boundaries. `MonitorTransport` remains fail-closed; no workload launch, runtime removal, closure proof, or native claim was enabled.

## Checks and boundaries
- `git diff --check`: passed.
- No C# source or fixture compilation/execution, native Windows calls, guest command, or build was performed. Fixtures and platform behavior remain unverified.
- Static review confirms no create-then-assign or unmanaged process fallback, and no code path from MonitorTransport into this owner. SafeHandle native release/finalizer ordering is unverified. A repeated kernel close/termination failure remains unknown until process exit.
- Candidate uncommitted/unpushed pending root source review.

## Frozen candidate SHA-256
- `tools/windows-scoped-runner/MonitorPayloadJob.cs`: `c195a67361ec6822dfb5a9b3a3ab2d9214659d587aa2ba31f6317c8dd9142f7f`
- `tools/windows-scoped-runner/LeaseMonitor.cs`: `864f1b25f1a3bd3edcf593ada17a2c2fff94863f8ed8ad06bb936dc64645587b`
- `tools/windows-scoped-runner/fixtures/MonitorPayloadJobFixture.cs`: `c0d5155aa7dbf119ec012558bce06471fc92911248ee07760297c640449874a9`
- `tools/windows-scoped-runner/README.md`: `2f62b3cd423ffecdc4f9f2d34007ae7f3890bfde50ca3e1ea8eaeb562bccc5c5`
