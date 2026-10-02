Source review complete for immutable commit `dd2a44fc53452b82dea55af102fc1a3842b9e4fb`. **No new correctness defect found in the activation changes.** The planned native proof has a pre-existing `no_float` compilation blocker and fixture evidence gaps described below. This is source acceptance only.

Loaded rules: agent-skills revision `958a4538b0191c53f2ccb2cd00d96c15045fbf68`; `roles.toml` updated `2026-09-30`; current Codex Expert agent/profile templates; global and project `AGENTS.md`; and `ocr-delegate`. The loaded global instructions and OCR skill match their agent-skills source copies. Global instructions SHA-256: `373f36f813b65fa1f0d2016a5a2d93e2bd56694e2d6a683707937a5c2a34fc95`; project instructions: `d1f6f0da5edfe418579c92f7c2f905db879e71cdd830ffbf9e808f1bc2bee58f`.

OCR v1.12.9 preview and rules succeeded. I reviewed independently, without delegation, file writes, installation, Cargo, or native test execution, within the 30-minute checkpoint.

**Findings relevant to the planned proof**

1. **High — pre-existing test compilation blocker under `no_float`.**  
   [tests/sys_process.rs:42](/Users/hoppworks/.codex/worktrees/process-shared-child-activation/rhai/tests/sys_process.rs:42) excludes `DIRECT_DROP_CHALLENGE_ENV` when `no_float` is enabled, but [line 154](/Users/hoppworks/.codex/worktrees/process-shared-child-activation/rhai/tests/sys_process.rs:154) references it inside `process_fixture`, whose gate excludes only `no_index`. Consequently, the planned `testing-environ,sys,sync,no_float` test target contains an unresolved identifier. A test-name filter cannot avoid compiling that function. I confirmed this mismatch exists in the commit’s parent; it is not introduced by this patch.

2. **Medium — pre-existing exceptional cleanup does not establish fixture closure.**  
   [ControllerGuard::drop:393](/Users/hoppworks/.codex/worktrees/process-shared-child-activation/rhai/tests/fixtures/sys_process_shared_child_contract.rs:393) kills/reaps the controller before releasing a surviving fixture. Killing the controller also removes the process containing its direct-child reaper. The guard then waits up to three seconds and merely logs `absent=false` if the fixture remains present; `FixtureDir::drop` subsequently removes the synchronization directory. This is not verified exceptional-path cleanup, particularly for foreign-parent zombies. The scoped runner must provide independently verified custody and honest incomplete-cleanup reporting. Successful scenario paths do assert fixture ESRCH; this finding concerns failure/watchdog paths.

3. **Medium — pre-existing successful-controller output is discarded.**  
   [run_bounded_controller:345](/Users/hoppworks/.codex/worktrees/process-shared-child-activation/rhai/tests/fixtures/sys_process_shared_child_contract.rs:345) captures controller output but prints it only on failure. Successful runs therefore omit the inner consumed-input, snapshot and cancellation diagnostics, and fixture files are subsequently removed. Assertions still execute, but the planned preservation of public Engine readback and child records needs an explicit evidence-export mechanism. This behavior predates activation.

**All-file coverage**

| Changed file | OCR treatment | Review result |
|---|---|---|
| `tests/sys_process.rs` | Reviewable; Rust rules | Registration, enclosing gates and affected fixture context reviewed |
| `tests/fixtures/sys_process_shared_child_contract.rs` | Excluded by `default_path`; Rust rules requested explicitly | Entire fixture and changed wait scripts reviewed |
| `.scratch/process-unix-run/shared-child-contract-activation.md` | Excluded by `unsupported_ext`; default rules requested explicitly | Entire note and cited historical evidence reviewed |

Total files: **3**; reviewed: **3**; skipped: **0**; coverage: **100%**. All three working files match the reviewed commit.

**Affected context and source conclusions**

- Registration is correct: the target’s `sys + unix` gate combines with the module’s `!no_index` gate. The fixture requires array arguments. The cancellation case, imports and scenario arm consistently require `sync`.
- Existing package gates reject `sys` with `no_std`, `no_object` and WASM. This Unix registration provides no Windows coverage.
- Both exact self-reexec names match the registered module: `shared_child_contract::scenario_entry` and `shared_child_contract::fixture_entry`.
- Calls exercise the public `Engine` and registered `SysPackage`: global `spawn`, `child.id`, `wait`, `try_wait` and `kill`. I checked package registration, the sys-only parser allowance, argument/options handling, shared `ClientLease`, retained OS ownership and snapshot construction.
- The new `no_float` scripts match the integer wait overload: `wait(0)` performs an immediate nonterminal poll; `wait(10)` supplies a ten-second timeout. **`wait(0)` does not exercise positive-duration blocking wait behavior.** Floating builds retain the existing floating-point calls.
- No newly activated fixture syntax or standard-library API appears to require Rust newer than optional MSRV 1.77.2. This is a source assessment, not compiler or dependency compatibility proof.
- The blocked-input assertions independently check child readiness, transferred bytes and contents, exit record, captured output, cached snapshots, mutation isolation, repeated post-completion kill and ESRCH. Clone/drop cases use fresh OS challenge replies and final absence checks.
- **The sync start channel does not prove entry into blocking wait.** It sends before `eval_with_scope`; cancellation can precede the wait call. The assertion checks successful evaluation, without requiring a terminal waiter map. The separate internal Condvar-entry test is relevant context, but its existence does not close this integration fixture’s limitation.

**Evidence applicability and remaining native acceptance**

The activation note correctly leaves current acceptance pending. The cited `shared-child-first-green.0la0r5` records an injected module on macOS using Rust 1.93, floating-point features and a private lock adjustment. Its fixture hash differs from the current fixture. Its recorded wrong-control removes public `spawn`; it does **not** establish the planned wrong cached-exit-code assertion control.

That historical run supports development context only. It does not accept this immutable registration, the integer scripts, Rust 1.77.2, or the native release matrix.

Current acceptance still requires the registered tests on native Rust 1.77.2, serial scoped execution, the intended cached-code failing control followed by restored passing assertions, both recorded feature sets, preserved readback and exact cleanup identities. Resolve the inherited `no_float` compile blocker first. Blocking-wait entry, exceptional cleanup, broader managed/escaped-descendant lifecycle, and native Linux/macOS/Windows release acceptance remain open.