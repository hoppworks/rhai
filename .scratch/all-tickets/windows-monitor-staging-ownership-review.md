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
