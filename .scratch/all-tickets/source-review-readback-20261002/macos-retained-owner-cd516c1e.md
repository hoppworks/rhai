**Disposition: rejected for native launch.** Commit `cd516c1ecb58d77340dbdc247f17b82b9e128b3d`, reviewed against `cfd6a9ea29bb5ee2410593d3be6d5bf112281dda`, retains real handles during an uninterrupted wait, but still permits unresolved ownership to be discarded.

Confirmed instruction revision `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. Read current instructions, OCR Delegate, roles/templates, prior custody review, correction result and escalation09’s existing answer. This remains the same cause09 review; no new escalation or native allocation.

**High — controller signals can unwind the retained owner.**

In [run-macos-process-overhead-control-package.py](/Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai/.scratch/all-tickets/run-macos-process-overhead-control-package.py:266), cancellation timeout calls `retain_failed_adapter()`, which parks in `Event.wait()` at lines 47–56. However, the installed INT/TERM handlers still raise `ControlCancelled` at lines 307–310.

A concrete sequence is:

1. Controller cancellation cleanup times out and registers the adapter owner.
2. A later INT/TERM arrives while that owner waits.
3. The raised exception escapes the wait and is caught as `cleanup_error` at lines 364–366.
4. The original exception is rethrown, handlers are restored, and `main()` returns failure at lines 385–387.

The controller exits with the adapter unresolved. The global list keeps the handle reachable only until that process exits; it is not a custody transfer. The outer runner’s TERM at its soft deadline can supply this later signal after an earlier controller timeout.

**High — logging failure can bypass ownership retention.**

The adapter’s anchored-command cleanup logs before registering its owner at [lines 1016–1018](/Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai/.scratch/all-tickets/run-macos-process-overhead-scoped.py:1016). RPC-client finalization does the same at lines 1560–1562. An output error therefore unwinds these paths before retention.

Both retention helpers also print after appending the owner but before entering its wait: adapter lines 640–645 and controller lines 51–56. If that print raises, the registered object does not prevent process exit. A failed evidence-file write, including ENOSPC or another I/O error, is sufficient; registration alone does not establish the claimed lifetime.

Retention must survive diagnostic failures. Logs cannot be a prerequisite for preserving the owner.

**Medium — retained handles have no operational accounting or reaping path.**

Both `RetainedOwner.wait()` implementations only wait on an event. Production code never sets that event, observes subsequent child exit, reaps through the retained handle, or accepts an acknowledged ownership handoff. Only the tests release it.

Thus, if a retained child subsequently exits, it can remain unreaped while its owner waits indefinitely. This is distinct from the original bounded cleanup attempt: parking preserves potential authority, but does not implement later safe accounting. Numeric PID readback cannot supply the missing reaping relationship.

This gap does not justify a fresh successful-cleanup budget, indefinite cleanup retries, or accepting the failed case.

The affected paths have these dispositions:

| Path | Source assessment |
|---|---|
| Incomplete anchored setup | Handles, descriptors and state remain reachable while parked. In actual `main()`, restored adapter handlers are non-raising; no separate setup-handler defect found. |
| Anchored-command cleanup | Exact handles and signal state retained during uninterrupted parking; diagnostic exceptions can defeat it. |
| RPC-client cleanup | Client handle and sockets retained during uninterrupted parking; diagnostic exceptions can defeat it. |
| Controller adapter timeout | Exact adapter handle retained until a raising signal or diagnostic exception unwinds the wait. |
| Outer timeout/exit | No forced KILL, but returning still relinquishes the outer direct-child reaping relationship. |
| External outer death | A surviving adapter retains its own direct children; no acknowledged recovery or complete custody-chain proof is supplied. Custodian death remains outside escalation09’s guarantee. |

The 585/600-second work envelopes are unchanged. The event wait extends failed-owner lifetime, not successful cleanup time. Setup fallback can also retain already-reaped handles after post-release uncertainty; those handles do not restore group-signaling authority.

**Evidence and coverage**

The saved `retained-owner-python312-readback.log` ends with **96 tests, OK**. The coordinator records the pinned Python 3.12 invocation and terminal status 0; the log itself contains no interpreter-version banner. The correction’s separate reported suite used Python 3.14.7.

The new tests meaningfully exercise `owned_command()` cleanup failure and `_stop_exact_adapter()` timeout. They verify handle identity and blocked execution. They do not cover:

- `run_control_case()` with its installed raising signal handlers;
- incomplete setup or RPC-client finalizer retention;
- diagnostic failure;
- later exact-child reaping or handoff;
- external outer death.

The recorded RED disables the adapter handoff and fails because no owner exists (`IndexError`); it establishes sensitivity to missing registration, not signal-safe lifetime or native custody.

| Changed file | Reviewed |
|---|---|
| `retained-owner-fix-result.md` | Yes |
| `run-macos-process-overhead-control-package.py` | Yes |
| `run-macos-process-overhead-scoped.py` | Yes |
| `test-macos-process-overhead-source.py` | Yes |

**Total 4; reviewed 4; skipped 0; coverage 100%.** Relevant working files matched the target revision, and the immutable range’s whitespace check passed. OCR rule mapping remains unavailable because of the known cache diagnostic failure; no retry was attempted.

Unchanged reader, observer and measurement conclusions remain reusable for their unaffected paths. They do not establish retained-owner lifecycle correctness.

The concrete missing mechanism is a failure state that cannot unwind on ordinary cancellation or logging errors, preserves permitted shutdown state, and provides exact-handle accounting/reaping or acknowledged handoff without reopening successful cleanup. **Under the brief’s stop condition, this rejection ends the dependent repair path: no blind fourth correction or second Expert chain.** The coordinator should record these blockers against the existing09 route.

Native prerequisites remain unchanged: Darwin signal/registration and wait/list behavior, setup/build interruption, real Managed dual-stream capture, exact reaping, complete escaped-leaf/group absence, runtime removal and independent readback. Source mocks do not satisfy them.

No edits, tests, builds, native controls, VM operations, installs, pushes or report-file writes were performed. Launch guard remains **false**; Unix **84 consumed**, measurement **85 unlaunched**, four controls **unallocated**.