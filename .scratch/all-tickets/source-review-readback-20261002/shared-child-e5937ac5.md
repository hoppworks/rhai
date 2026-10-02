**Source disposition: accepted for the three requested source corrections. No remaining material defect found in this affected review. Native dispatch remains closed pending external custody prerequisites.**

Reviewed immutable `e5937ac5532da3d4029935851f2853e6fbd00315` against `58dbf90f671281fc9a8845f7546f23f225c34b4b`. Relevant tracked working files match the reviewed revision.

Confirmed agent-skills revision **`958a4538b0191c53f2ccb2cd00d96c15045fbf68`**. Read current global/project AGENTS, `ocr-delegate`, `config/roles.toml`, both Codex Expert templates, and the complete previous review summary and fix result. This response contains the full review for CLI output capture; no file write was attempted.

| Prior material finding | Source recheck | Disposition |
|---|---|---|
| **High: expected-panic regression accepted success or unrelated panic** | Fixture lines **419–443** explicitly reject successful completion when panic is expected. Failed completion must report the intended payload and scenario cleanup event, an exited fixture record, exact ESRCH, and an exact receipt matching scenario, controller PID, fixture PID and root. Lines **142–149** add successful-controller and unrelated-panic rejection controls. | **Corrected in source.** Controls remain unexecuted. |
| **Medium: cleanup missed late PID publication** | Fixture lines **504–515** release both exact owned synchronization paths unconditionally, then refresh the PID during the five-second grace. Line **539** refreshes again after controller cleanup. Unknown PID or missing closure evidence remains unverified. Only the owned `ControllerChild` receives termination. | **Corrected in source.** Publication after the final observation remains outside this guard’s custody guarantee; records are retained rather than treated as proof. |
| **Medium: normal receipt provenance was misstated** | Fixture lines **437–442** identify the normal receipt as an outer observation after controller completion and fixture ESRCH. The panic receipt is controller-issued at **49–53**, with exact identity comparison at **429–431**. Activation-note lines **66–74** distinguish these sources and explicitly deny custody from files alone. | **Corrected in source.** Normal production-reap inference still depends on the successful scenario assertions and controlled ownership path. |

The production lifetime path supports the panic handler’s approach. `ClientLease::drop` at `src/packages/sys/process/unix.rs:196` requests cancellation only when `kill_on_drop=true`. Both panic scenarios use `false`, so unwind drops script handles without killing the held fixture. Package destruction marks `CleanupService` closing at line **327**; the worker retains its registry and OS child records independently.

`spawn_child` adopts the exact OS child before pipe setup. `attach_spawned` transfers it into retained service ownership. The worker pumps that record and calls production `Child::try_wait`; retirement requires reap and completion conditions. Consequently, observing fixture ESRCH inside the controller’s catch handler, before `resume_unwind`, supports production-reap inference for this controlled fixture. It does **not** establish worker retirement or recovery after forcibly terminating the controller.

The receipt consumers deserve a precise limitation: `FixtureDir::drop` uses receipt field-presence/substrings plus current fixture ESRCH, and `ControllerGuard::drop` uses receipt existence plus ESRCH. These are not independent provenance validators. In this fixture’s fresh, uniquely owned root, the reviewed writers and successful-scenario assertions supply that context; panic acceptance additionally compares the complete receipt. Neither consumer can serve as external custody proof.

The two new negative controls are meaningful source regressions. The success control requires rejection at the explicit “expected controller panic” assertion. The unrelated-panic control requires rejection at the intended-payload assertion, rather than accepting any cleanup-producing panic. Original scenario failures remain failures through `resume_unwind`. No native result is inferred from these test definitions.

The late-publication correction removes the identified immediate-kill race: release and grace no longer depend on an initial PID record. It cannot guarantee fixture publication or reap after controller force-death. The final reread improves accounting without claiming descendant ownership or signalling a numeric fixture PID. Permission errors remain excluded from ESRCH success.

The timeout description now correctly distinguishes:

- Hold mode’s single 18-second deadline.
- Blocked-input mode’s two separate 18-second waits and blocking stdin read.
- The outer 24-second polling deadline, followed by five-second cleanup grace and potentially blocking `wait_with_output`.

The 24-second adjustment is reasonable for hold-mode recovery, but is not a whole-package hard bound. The older “all fixture waits are bounded” wording and superseded repair description must be read with the explicit current limitations at activation-note lines **76–84**.

Earlier affected corrections remain present: successful controller stdout/stderr is emitted before fixture removal, and `DIRECT_DROP_CHALLENGE_ENV` retains the matching `unix && !no_index` gate. Sync notification at fixture lines **325–334** still occurs before evaluation and does **not** prove entry into blocking wait.

Coverage: **8 changed files reviewed, 0 skipped, 100% direct changed-file coverage**:

- `tests/fixtures/sys_process_shared_child_contract.rs`
- `.scratch/process-unix-run/shared-child-contract-activation.md`
- `shared-child-cleanup-repair.md`
- `.scratch/process-unix-run/shared-child-cleanup-fix-batch.md`
- `.scratch/process-unix-run/shared-child-cleanup-fix-result.md`
- `.scratch/process-unix-run/shared-child-cleanup-fix-summary.md`
- `.scratch/process-unix-run/shared-child-cleanup-review-brief.md`
- `.scratch/process-unix-run/shared-child-cleanup-review-summary.md`

Affected production ownership, service, registration and feature gates were also inspected in `src/packages/sys/process/unix.rs`, `src/packages/sys/process.rs`, `src/packages/sys/mod.rs` and `tests/sys_process.rs`.

`git diff --check` passed for the immutable range. The known OCR preview failure was not retried: Apple Git cache diagnostics remain present under the sandbox. No current OCR rule mapping was obtained; the available historical Python rules do not apply to this Rust/document package. Coverage was determined directly from the immutable Git diff, with current instructions applied manually.

No Cargo, compiler, native fixture, build, descendant-agent, installation, configuration or edit operation was performed. Compiler/MSRV compatibility, failing/restored controls and native acceptance remain unverified. Review completed before the 30-minute checkpoint.

Preserve **exactly 1 failed source cleanup correction**. This source recheck adds no failed correction or native launch. Accounting remains **84 consumed / 85 allocated but unlaunched**, with hard budgets unchanged. No new escalation chain was opened.

**Next concrete action:** prepare the existing bounded external-custody control package for forced controller death, hard scoped-watchdog expiry and whole-runner interruption, then obtain its source review before execution. Require exact ownership, termination/reaping read-back and evidence export before runtime deletion. Sync blocking-wait entry remains a separate open requirement.