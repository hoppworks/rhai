**Source disposition: not accepted for native launch.** Commit `cfd6a9ea29bb5ee2410593d3be6d5bf112281dda` removes the outer runner’s forced SIGKILL, but does not establish the required retained-owner failure contract. The existing high-severity custody finding remains unresolved.

Reviewed against rejected commit `7e8183a6b416c481fe7d165d4dbe834f1ff3e93c`. Separately confirmed instruction repository revision `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. Read current global/project instructions, `ocr-delegate`, roles and Expert templates, escalation09’s answer, the prior affected review and the correction result.

**High — returning with a live child does not preserve the complete custody chain**

| Field | Assessment |
|---|---|
| Category | Bug |
| Changed path | `.scratch/all-tickets/run-macos-overhead-scoped-runner.py` |
| Changed lines | 30–46, 104–110, 115–128 |
| Impact | Unresolved workload custody can outlive the processes holding its exact child handles. |

The runner sends a stop signal, boundedly waits, then reports `outer_custodian_custody_retained=1` and exits. This avoids destroying its direct child by forced escalation. However, that child’s shutdown implementation does not guarantee continued ownership until closure.

The relevant paths are:

- **Control mode:** [`run-macos-process-overhead-control-package.py`](/Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai/.scratch/all-tickets/run-macos-process-overhead-control-package.py:234) sends TERM to the adapter and waits for at most 15 seconds, capped by its own deadline. On timeout, lines 338–344 print an incomplete-cancellation diagnostic and rethrow. Lines 345–347 only restore handlers; `main()` then returns failure and exits at lines 362–368. The controller holding the adapter’s direct-child handle therefore exits without a custody transfer. Leaving it alive at the outer runner’s deadline does not make it a durable owner.
- **Normal and control modes:** [`run-macos-process-overhead-scoped.py`](/Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai/.scratch/all-tickets/run-macos-process-overhead-scoped.py:981) catches incomplete command cleanup, records failure and returns from its `finally` block. Gate/anchor handles are local variables; the retained records contain numeric identities and statuses, not transferred ownership. Setup failures similarly unwind at lines 814–844.
- **Adapter exit:** its main exception path rethrows at lines 1523–1525. The finalizer attempts bounded client termination/reaping, logs any failure, closes sockets and restores handlers at lines 1526–1544. It does not retain an active ownership service or transfer unresolved child handles before process exit.

Consequently, a stalled or unsuccessful cleanup can leave runtime files and unresolved processes after the controller and adapter have exited. A surviving adapter temporarily retains authority over its own direct children even after its parent exits; parent exit alone does not destroy those handles. The problem is that the adapter itself subsequently unwinds and exits on uncertainty. The outer diagnostic establishes neither its continued lifetime nor its remaining usable authority.

The outer runner also loses its own direct-child reaping relationship when it exits. The shell wrapper cannot acquire that relationship by reading a PID or ledger. Reaping by the OS after reparenting is not the reviewed custody handoff required by this contract.

**Timing does not close this gap.** The runner’s 585/600-second values remain unchanged. The controller starts its separate 600-second clock later and can wait until that deadline during cancellation. Removing SIGKILL eliminates the prior approximately-599-second destruction, but permits the controller to continue beyond the outer runner’s deadline and then exit after an unsuccessful wait. The adapter’s already-expired closure deadline supplies no additional cleanup budget.

This is the same ownership finding, not a second escalation cause. It directly matches the correction brief’s prohibition on dropping KILL and returning while abandoning authority.

| Requirement | Disposition |
|---|---|
| Remove outer forced custodian destruction | Source correction achieved |
| Honest nonzero status and retained runtime on uncertainty | Preserved |
| Retain or transfer actual ownership through unresolved closure | Not achieved |
| Mandatory passing native controls | Still required; not established |
| Native-launch readiness | Blocked by the unresolved source contract |

The smallest missing mechanism is an explicit retained-owner state in the actual adapter, preserving unresolved child handles and the permitted shutdown state, with controller/outer lifetime or an acknowledged handoff that cannot discard that ownership. Any retained state must stop normal launches and remain a failed case under the original bounds. It cannot silently append a new successful-cleanup budget.

Escalation09 remains applicable: it permits honest bounded failure **with retained runtime and owner**, while requiring complete closure for passing controls. This correction implements retention of files and removal of forced destruction, but not that owner guarantee. No new escalation or allowance reset is needed.

**Regression evidence covers removal of KILL, not ownership retention.** The changed tests at lines 1462–1481 and 1515–1545 use a mock permanently reporting a live child. They verify one signal, bounded waits and failure status. They do not exercise controller timeout/exit, adapter finalization, surviving handles or custody handoff. The test names therefore claim more than their assertions establish.

I read the correction CLI transcript: it records the focused RED, eventual four-test GREEN and 94-test GREEN. The immutable `source-green-94.log` also records 94 tests passing, but predates this correction. These are source/mock evidence; I ran no tests.

Previously accepted adapter, reader, observer-overlay and measurement source conclusions remain applicable because this range does not change those implementations. They do not establish the missing retained-owner failure behavior.

The native prerequisites remain unchanged: Darwin registration and signal delivery, wait/list ABI behavior, setup/build interruption, unfinished Managed dual-stream capture, exact child reaping, complete escaped-leaf/group absence and runtime removal. Passing paths remain structurally possible when cleanup completes in time, but cannot establish the missing failure contract. Whole-runner SIGKILL bypasses Python cleanup; neither exact outer death nor terminal-group destruction has a reviewed ownership-survival proof here.

OCR preview failed on sandbox-denied Apple Git cache diagnostics. I stopped that path without retrying. OCR rule mapping is unavailable; direct immutable coverage was:

| Changed files | Reviewed | Skipped | Coverage |
|---:|---:|---:|---:|
| 3 | 3 | 0 | 100% |

The range’s whitespace check passed. Relevant working files matched the target revision. No edits, tests, builds, native/process controls, installs, descendants, push or merge were performed; no report file was written.

Cause09 history and outer finding count **1** remain unchanged: Unix **84** consumed, measurement **85** unlaunched, four controls unallocated, launch guard **false**.