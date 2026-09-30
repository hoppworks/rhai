# Process prototype continuation state

## Goal

Complete the owner-approved same-cause POSIX process prototype continuation using the reviewed custody adapter, then hand exact native receipts to the coordinator for acceptance review. Do not merge or push.

## State and cause history

The sole Expert answer is `/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/01-process-prototype-proof.answer.md`. Preserve earlier source candidates `3fb742a3` and `65483bf9`; coordinator found source defects in both before execution. Candidate `9bf32e45d770ce3b021ac7e8f333d0d2bbe11501` fixed assertion-reader ordering and was explicitly source-gate approved before any build or fixture. Its source is unchanged by subsequent evidence commits. No additional Expert or cause chain was opened.

Continuation start was recorded as 2026-09-30 13:18:05 UTC; the fixed hard stop is 14:18:05 UTC. Final work stop/handoff: 2026-09-30 14:09:42 UTC, leaving 8m23s of the original extension. This does not reset or extend the budget.

## Completed steps and accepted evidence

- Scoped private Cargo build passed on Darwin 27.0 arm64 with Rust/Cargo 1.93.0, jobs=2, in 0.78s. Build source was copied into the shared scoped runner's private runtime, and the exact executable was exported before that runtime cleaned. Temporary executable (`evidence/process-prototype-native`, 819,392 bytes, SHA-256 `903a3b4f8fc31379898e8262b307c0554642448f0b0e4a19584b9c3bf2f6a54a`) was removed after all cases. Peak memory was not measured.
- Normal vertical proof passed: `evidence/custodian-88024-normal.json`; runner/workload exited 0, 3 I/O workers joined, exact 2 MiB input/stdout/stderr checksums passed, sentinel survived until cleanup, exact children were reaped and absent, matching quiescence/receipt readback passed, and runtime was removed.
- Live assertion passed: `evidence/custodian-91927-assert.json`; all four precondition processes were live; exact snapshot had all three workers alive, active, held and acknowledged; runner exited 86 after all workers joined; exact cleanup/readback/removal passed.
- Runner timeout passed: `evidence/custodian-92369-timeout.json`; runner exited 124 after its actual timeout, 3 workers joined, and all four scope resources were live before cleanup; exact cleanup/readback/removal passed. Receipt does not serialize the prior stream checkpoints or readiness identity, though the unchanged approved protocol only sends `io_live` after validating both checkpoints and a complete exact PID/PGID line. This distinction is recorded in `evidence/correction-attempt.md`.
- Runner TERM passed: `evidence/custodian-92635-term.json`; runner wait status 15 with all scope resources live at injection; custodian performed owned-group SIGKILL while identity was pinned, then exact cleanup/readback/removal. Worker joins after abrupt runner termination are not claimed.
- Runner KILL passed: `evidence/custodian-92930-kill.json`; runner wait status 9 with all scope resources live at injection; owned-group cleanup, exact reaping, readback and removal passed. Worker joins after abrupt runner termination are not claimed.
- Held-pipe cooperative cancellation passed: `evidence/custodian-93052-cancel.json`; leader exited 0 while holder retained output pipes; runner joined all 3 workers, returned 1, and exact 2 MiB stream hashes, cleanup/readback/removal passed.
- Separate shared-runner timeout status control passed: `evidence/shared-runner-timeout.txt`; shared `run_scoped.py --timeout 1` returned 124. This only proves status propagation, not private fixture cleanup.
- Each native receipt was independently read, hashes were recomputed by the coordinator, exact recorded PIDs and runtimes were verified absent, and the binary was removed. Evidence commits use author and committer `hoppworks` with the configured email. Current HEAD at state write is `dda53b3b0bec1b9af1bd43498a485d32851e28aa`.

## Current step and remaining limits

Execution is complete; the coordinator's final assessment is pending. Worktree is clean, exact temporary binary is absent, and the project `runs` directory has no retained case runtime. Do not rerun unchanged cases or rebuild without new evidence. Do not merge or push.

Claims apply only to this native Darwin 27.0 arm64 host and Rust 1.93.0. Rust 1.77.2/MSRV, Linux/other Unix, Windows, production Rhai Engine process behavior and wider release matrix remain open. No worker-join claim is made after runner TERM/KILL; no custody-failure recovery is claimed. Source-validated anchor PID/PGID equality was not separately serialized in the normal receipt. The prior source-gate and live-proof boundaries remain in `evidence/correction-attempt.md` and `adapter/README.md`.
