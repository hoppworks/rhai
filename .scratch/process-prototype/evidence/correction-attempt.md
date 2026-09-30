# Corrected proof attempt: stopped before execution

Date: 2026-09-30 (native macOS ARM64, Darwin 27 host)

## Outcome

The single correction attempt did not establish safe supervision, so no prototype executable was run. The original source and its two logs remain unchanged and are historical observations only. In particular, they do not prove simultaneous I/O, cleanup on live-resource failure, or safe timeout behavior.

## Ownership assessment

The scoped runner starts its command in a private supervisor process group. Its timeout cleanup signals that group with `SIGTERM`, waits 200 ms, then sends `SIGKILL` to that same group. The existing prototype moves fixtures into separate process groups. Therefore the runner cannot terminate those fixtures, and adding `--timeout` alone would leave them running.

A live in-group lease could provide independent cleanup: the first fixture code would arm a finite alarm before blocking, and the alarm handler would signal only its still-live own group. A parent-side owner would separately retain the direct `Child`, pipe-holder, worker stop tokens and join handles, and explicitly clean them on assertion/setup failures. The parent would signal a group only while its unreaped direct child anchors that identity. This design has not been implemented or validated here. The current source lacks the lease, immediate ownership guard, bounded worker lifecycle and held-pipe owner. Running it again would repeat known unowned-resource hazards.

The lease would also need to be validated against the actual spawn and failure ordering, including the first-instruction window, alarm delivery, normal exit, and harness termination. No assertion about managed-scope closure after normal leader exit follows from an in-group lease alone; that remains a separate identity/guardian gate.

## Evidence not produced

No corrected scoped run was performed. Consequently there are no corrected logs for overlap gating, live-resource assertion failure and cleanup readback, watchdog stall, wrapper exit propagation, exact holder cleanup, or sentinel preservation. Creating synthetic output for these checks would misrepresent execution. Existing `native-macos.log` and `wrong-assertion.log` are preserved verbatim as historical evidence.

## Remaining gate

Implement and review the lease and immediate owner as one coherent harness change, then validate ownership before execution. Only after that should the scoped run execute the overlap, live-failure and watchdog controls with reliable status capture and exact cleanup/readback. Rust 1.77.2 compilation and non-macOS platform behavior remain unverified.

## Owner-authorized retry: source preparation only (2026-09-30)

Requirement: close the native POSIX process-scope setup and cancellable stdin/stdout/stderr lifecycle gate, including actual project-local runner timeout and `SIGKILL` while live owned workload, anchor, holder, sentinel, and I/O workers exist. Preserve sole Expert answer and both prior stopped/rejected attempts above; this is the same single further correction attempt, not a new cause or budget reset. The earlier review's adapter-boundary question is resolved by owner approval of a project-local scoped-runner copy. The source gate still precedes every build and fixture launch.

This resumption began at 12:06:47 UTC. At the source update (12:33:38 UTC), 26m51s of the 30 active-minute source/review budget had elapsed and 3m09s remained, including coordinator review. No build, fixture, workload, signal, interruption, or runtime launch occurred. The shared runner and agent homes were not modified.

Source changes under review: `evidence/retry-design.md`, `adapter/controller.py`, `adapter/custodian.py`, and `adapter/run_scoped.py` now describe an active copied-runner RPC client, external custodian, direct child slots, anchor readiness, bounded stream workers, held-pipe cancellation, and receipt readback. The client closes passed descriptors on parse errors and gates runner interruption on the workload PID/PGID readiness record. These remain unexecuted source, not proof. In response to parent review, the outer controller's exact-custodian `SIGKILL` fallback is now gated on readback of an atomic quiescence record, written only after every recorded child is reaped and owned descriptors are closed; absent a valid record, the controller does not signal or remove runtime. This is a proposal requiring independent review, not validated behavior. Parent review found nested cleanup errors were not promoted to the completion gate, anchor liveness errors could abort cleanup, and an exited leader incorrectly suppressed the final group signal. The latest source attempts to propagate nested errors, continue cleanup after anchor observation failures, and retain group identity through the independently live anchor for TERM and KILL. These fixes remain unexecuted and unapproved. The source gate remains closed; no fixture execution is authorized.

Historical cause and Expert/review chain remains above and in the referenced answer/review files; this entry does not reset any attempt. Do not consume additional implementation or infrastructure correction attempts for the same cause.

Proposed resource/control limits for any later run, subject to stricter original bounds and independent source approval: one native macOS scoped build invocation with a 10-minute hard timeout and at most 2 GiB of private build storage; one custody session with at most 10 directly owned child slots, at most 6 I/O worker threads, and at most 15 minutes total including cleanup; each case has a 30-second deadline, 5-second cooperative grace, 5-second exact-child termination/reap window, and 10-second outer-custodian cleanup/readback window. Controls: passing overlap; active live-resource assertion failure; runner timeout; runner `SIGKILL`; normal leader exit with retained-pipe cancellation and valid group closure; and separate shared-runner timeout/status propagation without private scopes. Every launch consumes the same 30-minute original active-work budget; no default launch-count cap is imposed. No launch occurs until the coordinator source gate approves the complete adapter and these numeric caps.


## Remaining acceptance gaps for this attempt

- Independent source review has not approved the complete controller, custodian, RPC client, and fixture ordering.
- No native macOS build, fixture run, interruption control, byte-integrity readback, worker-join assertion, cleanup receipt, or runtime-removal readback was executed; source is not evidence of those behaviors.
- Rust 1.77.2/MSRV and non-macOS behavior remain unverified.
- The outer timeout fallback and all custodian error paths require independent source approval; the quiescence record is a source-only proposal.
- Original Expert/review history and this single retry remain unchanged; no further correction or escalation is authorized by this attempt.

Parent's final source review (2026-09-30 12:35 UTC) found additional acceptance gaps: the ordinary Rust anchor has default SIGTERM behavior, so group TERM can terminate it before the final KILL identity gate and prevent a successful normal cleanup; the control matrix still lacks real runner-timeout and live assertion-failure cases; and if the outer timeout finds no valid quiescence record, it retains but does not itself reap/read back the still-live custodian. These remain unresolved. The source gate is closed. No executable, fixture, workload, or process signal was launched during this attempt; no owned live process resources exist.

## Owner-authorized continuation (2026-09-30)

Accepted additional source/review allowance: 60 active minutes for this same cause, inclusive of independent coordinator review. Continuation start: 2026-09-30 13:18:05 UTC; 60 minutes remained at start. Cold-start reads completed before this entry: project `AGENTS.md`, prior correction history, retry design, all adapter sources, and sole Expert answer. No build, fixture, signal, or control has run in this continuation. Prior attempts and cause history remain unchanged. Source gate remains closed pending coordinator review.

Continuation source correction in progress (same authorized extension): `cleanup_owned` now uses one managed-group `SIGKILL` while an unreaped same-group anchor is live, avoiding a TERM that could remove the identity before escalation. The actual timeout and intentional live-assertion controls use a two-way cleanup request: runner workers remain live while the custodian verifies leader/anchor/holder/sentinel liveness and kills the scope, then the runner joins workers and reports actual counts and expected status (86 for assertion, 124 for its own timeout). Cleanup records that earlier group signal and does not issue a redundant group signal after the anchor has exited. The outer timeout retains runtime and live custodian and writes/reads back an incomplete record if a complete quiescence receipt is absent. Source-only AST and whitespace checks have passed so far; no build or process/fixture launch has run. A sequencing defect found during self-review (readers could wait for fixture pipe EOF before the custodian was asked to kill the fixture) was corrected before gate submission. Full adapter source review and source diff remain pending; no behavior is accepted yet.

Source candidate handed to coordinator for full gate review at 2026-09-30 13:36:33 UTC, commit `3fb742a3`. Elapsed active allowance: 18m28s; remaining: 41m32s, including coordinator review and any permitted same-cause source correction. Stop at handoff: 13:36:33 UTC. No build, fixture, process signal, or control was launched. Source gate remains closed pending coordinator decision.

Coordinator review of `3fb742a3` found that timeout readiness did not prove the full stderr PID/PGID line, assertion injection did not snapshot every live I/O worker, the TERM control was missing, successful controller completion did not independently read the quiescence receipt, and the Python 3.9.6 host lacks `os.waitid`. This same authorized continuation corrected the readiness gate to require both stream checkpoints and a complete newline-terminated stderr prefix capped at 256 bytes; the assertion control now holds and snapshots all three active workers before the custodian releases the injected failure, and assertion/timeout workers remain live until scope-closure acknowledgement. Added distinct TERM/SIGKILL controls and expected statuses, normal-path quiescence/receipt equality readback, and a Darwin ctypes WNOWAIT adapter gated by `siginfo_t` size, SDK flags, native symbol and POSIX/socket capability checks. Exact source applicability is Xcode `MacOSX.sdk` version 27.0 (`macosx27.0`) headers checked on Darwin 27 arm64; the adapter rejects layouts other than 104-byte `siginfo_t`. Bare Rust main remains forbidden; source invokes only explicit fixture modes. Static AST and whitespace checks pass. The no-child native capability probe resolved `waitid`, flags and ABI without invoking wait or launching a child. No build, fixture, process, signal or control ran; the native behavior and cleanup are still unproven.

Frozen source handoff: 2026-09-30 13:53:58 UTC, with 24m07s of the original 60-minute continuation remaining through the 14:18:05 UTC hard stop, including coordinator review. This stop/handoff does not reset the same-cause correction history or authorize execution; the source gate remains closed until independent coordinator approval of the exact immutable candidate.
