# Finite macOS control package review

**Verdict: changes required before native control dispatch.** Four high-severity findings affect launch, cancellation custody, Managed protocol dispatch, and the validity of Managed interruption evidence. This is one combined correctness, rules and acceptance review of immutable commit `43fa6a0588196b3c827f2a9ac77d6fc5734d6d97`. It grants no native acceptance or measurement permission.

## Findings

### 1. The bootstrap executes `-c`, so no selected control can start its custodian

- Path: `.scratch/all-tickets/run-macos-process-overhead-control-package.py`, line 30 (with `registered_exec_argv`, lines 70–75).
- Category: bug. Severity: high. Blocking.

`registered_exec_argv` constructs `[python, '-c', BOOTSTRAP, *target]`. For this Python invocation, `sys.argv` is `['-c', *target]`. The bootstrap executes `os.execv(sys.argv[0], sys.argv)`, attempting to execute the relative file `-c`, rather than the requested Python interpreter and custodian script. In an ordinary checkout this fails before the custodian announces its socket, so setup, build, Managed and deadline controls all fail at startup. A coincidental executable named `-c` in the working directory would be an even worse departure from the exact target contract.

Use the actual target vector after the `-c` sentinel (`sys.argv[1]`, `sys.argv[1:]`), and test bootstrap execution with the actual interpreter argument layout. The added mock launch test slices `argv[3:]` itself and never interprets `BOOTSTRAP`; its green result cannot catch this defect.

Non-native regression: `test_bootstrap_executes_target_vector_after_python_c_option` in `test_source_regressions.py`. All exec and signal-mask operations are patched. It fails because the captured exec target is `-c`.

### 2. A pending interruption can lose the newly spawned custodian handle

- Path: `.scratch/all-tickets/run-macos-process-overhead-control-package.py`, lines 223–228; affected caller line 294 and cleanup lines 328–337.
- Category: bug. Severity: high. Blocking.

The helper creates `proc` while INT/TERM are blocked, then restores the mask in its `finally` before returning that handle. The outer assignment `adapter = _spawn_registered(...)` has not happened yet. A pending INT/TERM can run the installed handler during mask restoration; that handler raises `ControlCancelled`. The helper exits without returning, leaving outer `adapter` as `None`, so the cancellation path neither signals nor reaps the already-created custodian. Blocking signals around the helper's local assignment does not register ownership in the enclosing cleanup owner.

Publish the exact child into the caller's durable ownership slot before unblocking, or make cancellation record a request until that publication is complete. Preserve the rule against killing the custodian with SIGKILL. The bootstrap fix alone does not close this race; after it is fixed, this race can leave a custodian continuing a control after the orchestrator has exited.

Non-native regression: `test_pending_signal_leaves_created_child_available_for_cleanup`. A fake Popen child is created and fake mask restoration delivers `ControlCancelled`. The expected TERM/reap actions never occur. No OS child or real signal is created.

### 3. Managed probes publish `null` while not ready

- New affected entry point: `.scratch/all-tickets/run-macos-process-overhead.sh`, lines 13–14 and 39–40, which now dispatch Managed controls.
- Dependency: `.scratch/all-tickets/run-macos-process-overhead-scoped.py`, lines 728–735; `observe_managed_case_ready`, lines 342–363.
- Category: bug. Severity: high. Blocking.

For a Managed control, the custodian passes its selected control context through every preliminary tool query, archive/extraction operation and build. `observe_managed_case_ready` intentionally returns `None` for commands other than the companion, and also returns `None` before the companion's readiness/progress artifacts exist. `owned_command` nevertheless treats every nonexceptional return as a readiness event and sends `json.dumps(None) + '\n'`. The controller rejects that frame because an event must be an object. Thus, once bootstrap launch is repaired and the source gate is deliberately opened, Managed can fail during preliminary tool queries before the actual capture injection is reachable.

Only persist and publish a validated non-None readiness event. Keep a not-ready observation as a bounded probe, without sending a protocol frame or marking a selected command readiness record. Add a regression covering both preliminary Managed commands and missing companion artifacts.

Non-native regression: `test_managed_not_ready_probe_emits_no_controller_frame`. Spawn, waitid, readiness, group cleanup, sleep and mask operations are patched. It observes `[b'null\n']` instead of no controller event.

### 4. Managed injection accepts cached readiness after the live capture may have ended

- New affected entry point: Managed enablement in `.scratch/all-tickets/run-macos-process-overhead.sh`, lines 13–14 and 39–40.
- Dependency: `.scratch/all-tickets/run-macos-process-overhead-scoped.py`, lines 274–288 and 725–738; Managed finalization lines 1067–1075.
- Category: test / acceptance correctness. Severity: high. Blocking for the active-capture control.

The two native snapshots establish fixture topology and both read counters before publishing `case-ready`. The controller then takes a separate socket round trip to send its interruption request. After readiness is cached, the adapter stops probing and `service_controller` validates only the request/event fields and the owned host PID, then kills the host. It does not recheck fixture identity/liveness, capture completion, or capture state at injection. The observer publishes its positive byte counters only once, so that artifact remains positive after the fixture exits.

A concrete losing schedule is: both readiness snapshots pass; the finite fixture finishes while the controller handles the event; the host remains alive draining/reporting; the request kills the host before its completion marker/normal exit. Host wait status is SIGKILL and eventual candidate/group absence passes, so finalization can accept even though there was no live fixture at injection. This proves abrupt host death after earlier capture activity, rather than the specified interruption of an active fixture with both capture streams active.

Make the action stage preserve and revalidate the live injection precondition, rejecting a lost readiness race. The existing Expert09 route explicitly permits freezing the exact directly owned host when needed and rechecking live capture before KILL; retain the frozen fixture and measurement timer. Record that recheck in the receipt. Do not reinterpret a lost race as a passing case or retry the one-attempt native case. Add a pure regression for fixture completion between published readiness and the action request; native confirmation still remains necessary.

## Coverage and evidence

OCR ran in commit mode against the user's own fork (`origin` is `https://github.com/hoppworks/rhai.git`) using the installed pinned binary. Its rules were resolved before review. Receipts are `ocr-preview.json`, `ocr-rules.json`, and `ocr-version.txt`; the complete immutable diff is `package.diff`.

| Changed file | Status | Review |
| --- | --- | --- |
| `.scratch/all-tickets/run-macos-process-overhead-control-package.py` | added | Entire file, ownership/cancellation, socket selection, deadlines and receipts reviewed |
| `.scratch/all-tickets/run-macos-process-overhead.sh` | modified | Diff and complete wrapper reviewed, including affected runtime-path parser |
| `.scratch/all-tickets/test-macos-process-overhead-source.py` | modified | All changed tests reviewed against implementation and affected control paths |
| `.scratch/all-tickets/macos-finite-control-package-20261002/source-red.log` | added; OCR excluded `unsupported_ext` | Entire log manually reviewed: missing implementation attributes, not native evidence |
| `.scratch/all-tickets/macos-finite-control-package-20261002/source-green-final.log` | added; OCR excluded `unsupported_ext` | Entire log manually reviewed: 73 pure tests and syntax check, no native acceptance |

OCR reviewable total: 3; reviewed: 3; skipped: 0; coverage: 100%. Complete changed-file total: 5; manually reviewed including exclusions: 5; skipped: 0; coverage: 100%.

Affected dependencies reviewed: controller selection/action/status protocol; adapter readiness, command registration, single anchored-group signal, exact-child reap, client disconnect and finalization; nonspawning harness setup and direct Cargo argument paths; frozen source/archive/lock and candidate Cargo source-graph checks; tool/environment pins; Managed companion and private observer hook; Darwin passive identity/candidate reader; wrapper runtime-path parser. Existing source-audit and Expert09 decisions were read by reference. This is impact-path review, not a new exhaustive audit of all locked registry/toolchain source.

The source keeps its measurement gate false and readiness record `not-ready`. The frozen measurement revision, archive digest, accepted lock digest and edge-only private lock digest remain pinned; the Managed observer uses a separate source overlay. Candidate Cargo tree/metadata checks are expressly approximate source coverage, not an exact compilation-unit or native confinement certificate. Installed SDK/kernel behavior, actual selected tools, native interruption closure, full capture injection, and benchmark results remain unverified. Opening the source gate requires the root's explicit prerequisite reconciliation; this report does not supply it.

The orchestrator has a single selected case, no retry loop, a maximum 585-second adapter argument and a 600-second outer budget with a 15-second wrapper/readback reserve. Adapter work, closure and readback deadlines reserve time within that envelope. Synchronous native calls cannot guarantee return at a wall-clock bound, as already documented in Expert09 and the reader. The report does not reinterpret that known limitation as successful custody or permit extending real caps.

Review-only check: `python3 -B /tmp/rhai-macos-control-review-20261002/test_source_regressions.py` ran three injected tests in 0.003 seconds; all three failed for the concrete intended defects. Its first run needed a local test-path correction because macOS `/tmp` resolves to `/private/tmp`; that was a review-test setup correction, not a product correction or a native allocation. The final output is `source-regressions-red.log`. Tests launch no OS child, Cargo, fixture, control workload, measurement or native process API.

## Rules, custody and next action

Loaded current global rules, project `AGENTS.md`, OCR delegation skill, campaign and E2E rules, repair/calibration references, `roles.toml` and updated escalation/Expert template from agent-skills revision `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. Project verification is strict. This one independent source review does not replace full-stack native acceptance and does not create another Expert09 escalation chain.

Root context: `/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/coordinator-state.md` and its `escalations/09-macos-overhead-custody.answer.md`. Preserve process invocation count **84**, allocated **85 not launched**, the false measurement guard, cumulative resources, original hard caps and cause09 history. No count was consumed by this review. No owner source, production source, process, branch or worktree was changed; no Cargo/native/control/measurement, push or merge occurred. Owner HEAD remained `43fa6a0588196b3c827f2a9ac77d6fc5734d6d97`; status before/after is identical, recorded in the status receipts. Unrelated owner scratch changes were preserved.

Return these four findings as one fix batch in the responsible existing context. Recheck the failing regressions and affected bootstrap/registration/Managed action dependencies against this baseline; retain unaffected review coverage. Do not restart broad review or add another reviewer without a new risk. Keep native dispatch and measurement blocked until the corrected source and remaining prerequisites are independently accepted under the existing finite package.
