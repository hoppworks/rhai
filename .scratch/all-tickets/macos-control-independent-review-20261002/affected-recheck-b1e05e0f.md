# Affected finite-control correction recheck

**Changes required: findings 1–3 are closed; finding 4 remains high and blocking for valid active Managed capture injection.** This is the affected-only independent recheck of immutable `b1e05e0f80b62f7a16dfe356da35fda184f0e144`, parent `43fa6a0588196b3c827f2a9ac77d6fc5734d6d97`. The original combined review in `review.md` remains applicable to unaffected source and dependencies. No new broad review or native acceptance was performed.

## Four-finding disposition

| Finding | Result | Evidence and applicability |
| --- | --- | --- |
| 1: Python `-c` bootstrap resolves wrong argv | Closed | BOOTSTRAP now executes `sys.argv[1]` with `sys.argv[1:]`. Original injected bootstrap regression passes against immutable correction. |
| 2: pending signal loses created custodian | Closed | `_spawn_registered` calls `register_adapter(proc)` while blocked, publishing the enclosing cleanup slot before mask restoration. Pending delivery at restoration now reaches exact child TERM/reap. Original injected regression passes. |
| 3: Managed not-ready publishes null | Closed | `owned_command` skips publication when observation returns None. Preliminary noncompanion probes and missing artifacts remain bounded not-ready states. Original injected regression passes. |
| 4: capture can finish before host KILL | Partially corrected; remains high | Fresh action observation and receipt binding reject loss before the fresh observation, but leave a runnable observation-to-signal interval. |

## Remaining material finding

- Path: `.scratch/all-tickets/run-macos-process-overhead-scoped.py`, lines 305–308; affected observation lines 405–416, command callback lines 766–777 and finalization lines 1108–1124.
- Category: test / acceptance correctness. Severity: high. Same original finding 4, not a new cause or review chain.

The new callback takes two native censuses, validates live fixture topology and capture progress, compares the fresh event with the published event, then calls `signal_unreaped_managed_host`. The host and fixture remain runnable throughout. The fixture can finish after its last lookup or after the comparison and before SIGKILL. The companion can still be alive draining/reporting, so its direct-child status can be SIGKILL. Passive candidate and group absence will subsequently succeed. The receipt still contains the earlier positive counters and live snapshot, and finalization checks their structure and equality rather than an injection boundary guarantee. Thus an inactive capture can still produce accepted active-capture evidence.

A pure deterministic interleaving test, `test_managed_action_boundary.py`, schedules fixture completion immediately after the valid comparison and before the mocked exact kill. `service_controller` returns a Managed interruption action and fresh readiness receipt despite that completion. `managed-action-boundary-red.log` records the intended single AssertionError. All select/read/signal operations are mocked; no socket, process, native API, control, build or measurement is launched. This test establishes the source acceptance gap, not the frequency of that schedule on the live system.

Use the existing Expert09 permitted route: stop the exact directly owned unreaped host without consuming its child identity, establish the stop non-consumingly, then recheck the live fixture/capture precondition while host capture cannot advance, and KILL the exact host. Preserve pinned anchored-group authority and one group signal/reap order. The source argument must establish why the frozen fixture cannot complete between the stopped-host recheck and KILL; a STOP alone is not sufficient without that implication. A lost live precondition must fail the single attempt, never be retried or counted as proof. Bind that stopped/action boundary and resulting native readback into the receipt. Leave the measured timer and frozen fixture unchanged.

## Source readiness versus native outcomes

This remaining injection-precondition gap is a concrete source blocker. It can be corrected and checked without first running native controls. The shared `require_launch_readiness` currently gates controls and measurement through the same six source fields and `CUSTODY_IMPLEMENTATION_FROZEN=False`; those fields must be interpreted by evidence scope, not populated with unsupported native claims.

Retain the accepted source ABI/layout/SDK audit `4aa1988`, selected tool/PATH/Xcode/graph confinement evidence identified by root at `b5245`, and prior sole-custodian/passive finite-leaf source reviews by their original receipts. Earlier report caveats about incomplete helper confinement are superseded where those later accepted source checks apply; this recheck does not repeat that audit. Live ABI access, actual helper behavior, group closure, dual capture at injection, escaped-leaf absence and runtime removal are native control outcomes, not a requirement to have already passed native controls before allocating their first attempt. Successful native controls remain a prerequisite to measurement.

One related source implication remains conditional in the existing root state at lines 818–819 and adapter `validate_managed_snapshot`: four fixture tasks are necessary but do not identify the two writers. Positive counters were published once and can remain after writer completion. Safe active-capture identification needs a reviewed source-bound thread/stream model or another supported fail-closed witness; do not silently equate aggregate task count with active writers. This is part of the same original active-injection requirement, not a reopened broad ABI audit. It cannot be discharged by a closure result that would also pass after ordinary fixture completion. Actual installed native sampling behavior can be proven during the control once the source implication and injection boundary are sound.

This report neither opens gates nor authorizes native controls or measurement. Root determines the finite control allocation after source correction/review, preserving count84 and the separately allocated one-shot85.

## Coverage and receipts

OCR deterministic commit selection and rule resolution completed for exact correction. Three selected Python files were reviewed fully within their affected diff/call paths; three excluded source RED/GREEN logs were manually read. Total files 6, reviewed 6, skipped 0, coverage 100%; OCR subset 3/3. Receipts: `correction-ocr-preview.json`, `correction-ocr-rules.json`, `correction-coverage.json`, `correction.diff`.

Affected dependencies include registration callback/unmask/cancellation cleanup, preliminary readiness loop, Managed observer/native snapshot comparison, exact-child signal, action receipt persistence, anchored cleanup and control finalization. The correction finalizer rejects absent/malformed/differing fresh receipts and binds identities/evidence to the original event. That is useful narrower receipt integrity, but cannot eliminate the scheduling gap. Unaffected bootstrap/socket/deadline/source-pin/tool/resource conclusions remain those of `review.md`.

Committed `source-red.log` includes intended bootstrap/null/ownership failures, pre-implementation callback errors and three `/var` alias setup failures. Corrected tests resolve paths rather than weakening exact-path validation. Committed `affected-green.log` reports 7/7; `full-source-suite-green.log` reports 78/78. These are pure source receipts. I independently ran only the three original injected regressions against files extracted from the immutable commit: 3/3 pass in `correction-regressions-green.log`. The new scheduling boundary regression fails as described. No repeated broad source suite was run.

All seven loaded instruction files hash-identically match the original load, including global/project rules, OCR/campaign/E2E skills, roles and updated Expert template; agent-skills revision remains `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. `correction-instruction-check.json` records this. Owner HEAD is exact correction and reviewed source paths match it; review execution uses an immutable extracted source snapshot under this report directory, without owner edits or uncommitted foreign material.

Process invocation count84, allocated85 unlaunched, measurement guardfalse, Expert09/cause history, cumulative resources and real hard caps remain unchanged. No native/build/Cargo/control/fixture85/measurement launch, production or owner edit, extra reviewer, push or merge occurred. Return this single residual finding to the existing responsible context; keep findings1–3 closed and recheck only the new stopped-host action/receipt dependencies after the next immutable correction.
