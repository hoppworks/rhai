# Affected finite-control source recheck

Reviewed immutable `5ed13c10a341250755372bf03445f0b597294848`, parent `29cfb009aa97ff5cb0b63d22a7714e745ea6bfda`, from `/Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai`. Result: the two outstanding manifestations of original finding 4 are closed at source level. No new material finding in the affected scope. This is independent source acceptance, not native acceptance or permission to launch.

## Scope and instructions

Current global/project instructions, OCR delegation, campaign/e2e rules, role mapping and Expert template were checked at the safe checkpoint against the saved seven instruction hashes. All were unchanged; loaded agent-skills revision is `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. Original load provenance is `loaded-instructions.json`; the earlier correction check is `correction-instruction-check.json`. No descendants or new Expert chain were used.

OCR deterministic selection and rule resolution are frozen in `cleanup-correction-ocr-preview.json` and `cleanup-correction-ocr-rules.json`. Coverage is four selected files, four reviewed, no exclusion or skip (`cleanup-correction-coverage.json`). The exact diff is `cleanup-correction.diff`; reviewed immutable contents are under `cleanup-correction-source/`. Scope: CONTROL observer overlay `unix.rs`, its harness hash pin, scoped adapter, and source tests; affected publication, failure cleanup, real observation, STOP/KILL callbacks and finalization dependencies were examined. Previously accepted unrelated paths were not broadly reviewed again. The finite orchestrator has no diff from the earlier reviewed correction.

## Outstanding findings and disposition

| Earlier result | Current disposition | Evidence and applicability |
|---|---|---|
| Findings 1–3: BOOTSTRAP argv resolution, pending-signal ownership publication, absent-readiness protocol | Remain closed | Corrections and unaffected proof from `affected-recheck-b1e05e0f.md` remain applicable. This diff does not change those paths. |
| Finding 4, status propagation setup blocker at 29cfb009 | Closed at source | `validate_managed_snapshot` now retains the independently validated host status separately as `managed_host_status`; `observe_managed_case_ready(require_stopped=True)` checks that value. It no longer looks for status in the reduced identity tuple. Original real-observer reproduction now passes. |
| Finding 4, stale capturing receipt after error teardown at 29cfb009 | Closed at source | `fail()` invalidates the public progress receipt before taking stdin/stdout/stderr. The real observer rejects `aborted` and nonpositive generation before census. An invalidation error cannot continue into teardown with the old receipt. |
| Per-read paired publication and one unpublished quantum bound | Remains accepted | Unchanged foreground reader ordering and 64 KiB budget. Successful reads publish before another read; publication errors enter the invalidating failure path. No larger unpublished read backlog was introduced. |

Relevant source locations in the frozen snapshot: overlay publisher/replacer around 2399–2450, `fail()` around 2997–3027; adapter witness around 131, post-KILL validation around 147, status retention around 221, controller around 408 and real observer around 498–554. The overlay pin independently matches SHA-256 `9f6b3612de139295b473a8070cc9ed16f3d744eee140f97b0baecf1db287a8e0`.

## Error and STOP boundaries

Invalidation uses the same atomic replacement primitive as paired progress publication: exclusive temporary file, complete write, file sync and rename, with only that temporary file removed on error. The invalid receipt is explicitly `stage=aborted`, `generation=0`, retaining host/fixture PIDs and byte totals for diagnosis. The adapter does not authorize from it.

If STOP wins before invalidation or during its preparation, the old `capturing` receipt may remain visible, but source cleanup has not yet closed capture endpoints or submitted fixture cleanup. With the host stopped, its reader cannot advance into teardown. The previously established read bound still supports a genuine unfinished capture interruption. If STOP wins after the rename, the fresh observer sees `aborted` and rejects before KILL. If STOP wins after endpoint teardown, invalidation already happened, so the same rejection applies. This ordering removes the reproduced state of closed endpoints with an action-eligible capturing receipt.

If invalidation fails, or there is no child handle to bind it, the CONTROL path immediately calls `std::process::exit(1)` before endpoint teardown. A STOP that wins before this exit leaves endpoints owned and the capture interrupted by the controller's exact KILL; an exit that wins cannot supply an exact live stopped host or accepted KILL status. The source does not continue with a closed-endpoint stale receipt. This conclusion is from source control flow and injected adapter protocol tests; no Rust execution, filesystem fault injection inside Rust, native signal scheduling or Darwin ABI behavior was performed.

The environment switch enabling the private progress receipt remains source-bound to the CONTROL companion and private feature. There is no intervening removal of that environment setting in the examined path. Ordinary successful completion cannot meet the unfinished-output witness once both frozen output totals have been captured; the completion marker is also rejected by readiness. Failure paths enter the invalidation barrier.

## Identity and action validity

The change preserves exact unreaped direct-host STOP, native full-identity STOP confirmation, a fresh stopped observation, strict paired output bounds, exact KILL, then independent fresh same-fixture PID/start/path/PGID live nonzombie readback. Absence, unknown state, identity reuse, exit before the post-KILL readback and incompatible topology remain rejection cases. The action stores the stopped observation/generation/output witness and post-KILL fixture row. Passive final closure and final receipt requirements remain applicable and unchanged.

The accepted witness is unfinished public Managed capture on both streams, not an assertion that writer syscalls are blocked. Positive published totals plus at most one unpublished 64 KiB read per stream must remain strictly below stdout 8,388,592 and stderr 8,388,608 bytes. Together with the source/fixture binding, exact stopped host and post-KILL live fixture, this meets the previously reconciled active-capture contract. No pipe capacity or PIPE_WANTW claim is made. A last capturing receipt plus live fixture alone still does not certify capture activity; the producer ordering, fresh stopped observation and numerical witness are essential.

## Evidence

Independent execution was pure Python with injected census, signal and controller interfaces. No native API, process workload, Cargo, build, control or measurement was launched.

- `test_cleanup_correction_original_observer.py` and `cleanup-original-observer-green.log`: original real-observer status regression, 1/1 GREEN against this frozen snapshot.
- `cleanup-correction-focused-green.log`: 6/6 GREEN, including real stopped observer, aborted observer, source invalidation ordering, fixture exit between compare and post-KILL, finalization binding, and independent actual observer-to-controller abort rejection.
- `test_cleanup_correction_abort_boundary.py` and `cleanup-abort-boundary-green.log`: saved runnable independent observer/controller regression, 1/1 GREEN. A previously published ready event followed by a real aborted receipt causes rejection after injected STOP; injected KILL and post-KILL validation are never reached.
- Owner supplied `recheck-focused-green.log` (3/3) and `recheck-full-source-suite-2.log` (88/88) under the owner's `.scratch/all-tickets/macos-managed-action-correction-20261002/` were read as supplied evidence. They are source-suite results, not native proof. The owner `recheck-red.log` has one test-selector error (`substring not found`) and is not a meaningful product regression or failed implementation correction.

Original `affected-recheck-29cfb009.md`, `test_action_correction_regressions.py` and `action-correction-regressions-red.log` remain untouched. Both original REDs remain meaningful evidence for that earlier revision. The old stale-receipt test fabricates callbacks for a state now excluded by producer ordering; replaying it unchanged would not establish applicability to this correction. The saved new test uses the real corrected observer to check the reachable invalidated state. Earlier review reports and all original regression receipts are retained.

## Readiness boundary and preserved history

No outstanding source blocker was found in this affected correction. Previously accepted source confinement/custody/census/ABI-layout work remains applicable by reference, rather than being repeated. Source safety readiness must be distinguished from live Darwin ABI behavior, actual STOP/readback, real dual-stream capture and passive closure: those remain outcomes for the finite controls to prove. This report does not require native proof as a prerequisite for the native controls themselves, and does not authorize controls or measurement.

The measurement-85 frozen overlay, timer and fixtures remain unchanged; changed observation is confined to the CONTROL overlay. Process count 84, measurement allocation 85 unlaunched, measurement guard false, finite one-attempt controls and all resource caps are preserved. Original Expert09/cause09 history, including the earlier failed correction and independent 29cfb009 result, is retained without reset or additional escalation. Owner worktree was read only; all new evidence is in the existing exact review directory.
