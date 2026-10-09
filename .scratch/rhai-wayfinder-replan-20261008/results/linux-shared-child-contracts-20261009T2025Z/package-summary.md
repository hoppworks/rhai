# Linux shared Child lease/wait contracts

## Scope

Accepted source archive revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`, archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644`, accepted lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, `tests/sys_process.rs` SHA-256 `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`, committed shared fixture SHA-256 `1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217`. Native Linux x86_64 Workhorse, Rust/Cargo 1.77.2. Features: `testing-environ,sys` and `testing-environ,sys,sync`.

## Attempt history

`attempt01` built the standard profile and ran the blocked-stdin wait-snapshot exact selector. It produced the intended RED (actual exit code 17 against deliberately mutated expectation 18), printed its RED control marker, and verified panic cleanup/reap (`reap=ESRCH`, `fixture_closure=verified`, `production_reap=true`). The runner then stopped in its result parser: it required the test name and `FAILED` on one line, although `--nocapture` placed fixture diagnostics between the libtest prefix and final status. No product assertion or cleanup failed. Its private scope was retired exactly.

`attempt02` corrected only the parser. It checks process exit status, exact selected test prefix, intended RED marker, and the final libtest result summary as separate evidence. One `run_scoped.py` invocation (600 s ceiling; two Cargo jobs) completed the profile RED/GREEN selectors. Both profile builds returned 0. The blocked-input, nonfinal-clone, script-throw and sync-wait REDs have their intended markers and final `FAILED. 0 passed; 1 failed`; the corresponding restored-source GREEN logs have final `ok. 1 passed; 0 failed`. Its final-drop RED was not valid: the nonfinal `one` mutation failed before the intended `two` assertion. The final-drop GREENs are valid, and `restored-fixture.sha256` matches the committed fixture SHA. Overall runner status 0, elapsed 36 seconds, `retired_exact_empty_scope=true`. The launch staging mismatch before the run was recorded in `pre-run-launch-error.txt`; the launcher was corrected within the same attempt directory before any runner/build started.

`attempt03` corrects this specific RED gap. Its `kill_on_drop=true` `one` mutation is conditional, so the `kill_on_drop=false` scenario retains a passing `one` probe. The `two` assertion is inverted and emits the target control marker. Exact final-drop RED has exit 101, one failed libtest test, watchdog fixture closure and exact PID ESRCH in both standard and sync profiles. Its GREEN is reused from attempt02 because the same exact selector passed in both profiles on the same source, lock, toolchain, features and restored fixture SHA. Attempt03 runner status is 0 and its exact empty scope was retired.

`attempt04` stopped in mutation preparation because the anchor occurred in both policy branches; no Cargo build/test ran and the exact scope was retired. `attempt05` reached the selected test, but its inverse ESRCH assertion ran before asynchronous reaping; the test correctly returned 0, so that is not RED evidence. Attempt05 scope was retired. `attempt06` places the inverse ESRCH assertion after the fixture's bounded exact-PID `wait_for_pid_gone`. In standard and sync, the nonfinal `one` challenge succeeds, final-client release reaps the PID, and only the deliberately inverted post-reap assertion fails (exit 101, one failed test); the controller and fixture reapers then verify ESRCH. The corresponding GREENs are reused from attempt02 on the unchanged source, lock, toolchain, feature profiles and restored fixture SHA. Runner status 0; elapsed 31 seconds; exact empty scope retired.

The new sync waiter selector passed its own RED/GREEN but its before-call notification alone does not establish wait-entry. The separate historical X31 Linux blocking-entry proof remains applicable for Linux x86_64 Rust/Cargo 1.77.2 `sync` and `sync,no_float`: exact test-function byte identity at production source `c644085ccf65160bd3d39f5353e8b933310ffe03`, unchanged lock, expected RED/restored GREEN, counter/mutex Condvar-entry observation, nonterminal child, public cancellation/wakeup and exact cleanup. See `.scratch/all-tickets/linux-wait-entry-proof.md`, `.scratch/all-tickets/linux-wait-entry-review.md` and `docs/sys-package-plan.md` X31 reconciliation. X31 remains partial overall; these named Linux rows do not close other platforms, features or MSRVs.

## Selectors

- `shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable`
- `shared_child_contract::nonfinal_child_clone_drop_keeps_the_real_child_available`
- `shared_child_contract::final_drop_honors_both_kill_on_drop_policies`
- `shared_child_contract::script_throw_drops_and_reaps_a_live_child`
- `shared_child_contract::sync_waiter_can_be_cancelled_through_another_shared_child_handle` (sync profile only)

These results close only the corresponding Linux standard/sync acceptance rows on the bound source/toolchain/environment. They do not establish Darwin/Windows behavior or close all X23-X31/A-F requirements. Combined independent review accepted the narrow packet after reconciliations in attempts03 and 06: `.scratch/rhai-wayfinder-replan-20261008/results/linux-shared-child-contracts-20261009T2025Z/combined-review.md`.
