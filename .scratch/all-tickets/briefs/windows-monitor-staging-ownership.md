# Monitor-owned allocation and staging

## Remaining repair allowance

Continue the single incomplete Windows custody correction justified by
`escalations/02-windows-runtime-custody.answer.md`; this is not a new correction
package or Expert chain. Preserve all earlier source work and cause history.
This remaining source slice starts on 2026-09-30 at 11:17 UTC and stops by
11:47 UTC, with at most 30 minutes of active work including independent review.
No compilation, fixture execution, native operation, measurement or build launch
is allowed (zero launches). No runtime, process, guest, service, installation or
remote resource may be created. Only the existing owned worktree's source,
fixtures and documentation may change. Do not reset past effort accounting;
prior cumulative active time was not measured and remains unknown.

Stop on the deadline, an uncovered design decision, contradictory ownership
evidence, or two consecutive source revisions without closing a concrete
requirement. Return the exact unfinished requirement; do not start a replacement
package. Expected unexecuted test specifications are not RED/GREEN evidence.

## Requirement

Connect completed immutable intake in the actual monitor path to the existing
allocation/staging backend through one worker. File I/O, journal flushes,
allocation, source copies and resource disposal must never run on or block the
watchdog. Keep payload invocation, job creation/resume, runtime deletion and
ExactJobClosureProof issuance closed. Existing native bootstrap/custody gates
remain prerequisites for execution and acceptance.

## Ownership and stopping contract

- Start at most once after immutable transfer completion. The worker owns every
  allocation and handle until an explicit single-owner completion handoff.
- Use a bounded nonblocking completion channel; completion publication and stop
  must have a defined ordering. No double disposal, concurrent handle close or
  late staged result becoming usable after stopping.
- Watchdog cancellation only publishes a signal. Do not invoke arbitrary
  cancellation callbacks, wait, join, flush or dispose worker-owned handles on
  that thread. The worker checks cancellation at the backend's existing seams.
- Failed, cancelled or rejected completion is disposed by its current owner on
  the worker. Dispose retains exact runtime/journal; it does not prove removal.
  Stalled filesystem operations remain an honest retained-custody limitation.
- A successful staged result stays monitor-owned and pinned. It confers no
  launch authority. Maintenance responses collected during transfer/staging
  must not become create/resume authorization; later launch integration needs
  a fresh phase-bound post-staging round trip.
- Start/progress/result handling must recheck fresh time and irreversible
  stopping. A full queue, malformed input, EOF, failed client/writer or deadline
  cannot start or accept more work.

## Source fixtures and deliverable

Write finite contract fixtures before implementation for start-once, worker
failure, stop before start, stop during work, late completion, successful single
handoff, rejected handoff and watchdog independence from a stalled worker.
Use the actual production seam, with fixture-only fake backend operations where
needed; do not present them as native proof. Preserve existing frame/lease tests.

Commit atomically as the configured author, leave the worktree clean and report
whitespace checks, source paths, ownership transitions and unverified paths.
Do not enable legacy RunBody or alternative unsafe cleanup. No new public API or
release choice is part of this slice.
