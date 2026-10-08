# X29: Rhai throw while a public child is live

Status: partial. The corrected Workhorse Linux x86_64 rows at Rust/Cargo 1.93.0
and 1.77.2, plus the native Darwin arm64 / macOS 27.0.1 row at Rust/Cargo 1.93.0,
are accepted with `testing-environ,sys`. Windows, other feature combinations,
and remaining MSRV rows remain open. Superseded old-source Linux runs are retained
as execution history, not accepted proof of a live child at throw time.

## Scope and result

The intended acceptance runs Rhai through the public `Engine` and registered `sys` package. The script starts the real test executable through public `spawn`, waits for an OS fixture to report readiness, and throws while the child remains live. The original outer gate only used `kill(pid, 0)`, which can succeed for a zombie; the fixture's 18-second deadline was also shorter than the outer 24-second watchdog. Thus the old output does not establish that the throw preceded fixture exit. The corrected test requires a fresh exact challenge response before opening the gate and requires public `child.try_wait()` to return unit immediately before the intended throw. The returned Rhai error must still contain the intended message, and the wrong-message control must still be rejected. After evaluation unwinds and drops the script-owned `Child`, the outer harness independently observes exact-PID `ESRCH`.

This is a backend/OS integration test; no UI layer applies. The named Linux and
Darwin rows are accepted; Windows, other feature combinations, and other MSRV
rows remain open.

## Review finding and correction

Combined independent review found that `process_exists(pid)` wraps `kill(pid, 0)`
and therefore treats an unreaped zombie as present. Since the fixture may exit
after 18 seconds while the parent watchdog waits 24 seconds, the parent could
release the script throw after the fixture had stopped executing. The corrected
gate requires a fresh exact challenge response and public `child.try_wait() == ()`
immediately before the intended throw.

The follow-up review found one source/evidence mismatch: the tested GREEN snapshot
handled the `script-throw` challenge, while the current fixture's `hold` loop did
not. The source now includes that exact responder. The current X29 code matches
the already-tested GREEN snapshot; remaining whole-file changes do not alter X29
behavior. The runner explicitly overlaid that hash-pinned GREEN snapshot before
both successful commands, so the hash-verified Linux results remain applicable
without another build. The Darwin row is accepted separately below. The initial
NOTREADY review and this targeted correction are retained; no test assertion or
infrastructure failure occurred in the corrected run.

## Corrected Linux runs (two named rows accepted)

- Machine: Workhorse, Linux 7.2.8, x86_64; features: `testing-environ,sys`.
- Source base: `b7dfa020ef59be748b1f0f69545f997ef20dead2`; the run overlaid only the isolated X29 fixture snapshots and reused the accepted X30 `Cargo.lock` (SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`).
- The test first produced the intended RED: Rust 1.93.0 compiled and ran the exact test, which failed because the fixture did not yet answer the new `script-throw` challenge. This is the false-green control for the strengthened gate, not a product failure.
- The corrected fixture then passed the exact test on Rust/Cargo 1.93.0 and 1.77.2. Both outputs show `challenge_response=verified`, `pre_throw_try_wait=unit`, `wrong_expectation_rejected=true`, and an independent `reap=ESRCH verified=true` observation. Each command exited 0 (1 passed, 0 failed; 59 filtered).
- The single bounded runner used two Cargo jobs, a shared private target across the sequential toolchains, 900-second per-command timeouts, and a 2,700-second runner timeout. The fresh preflight at `2026-10-07T21:09:08Z` reported no active heavy process groups, 87,667,536 KiB available memory and 668,487,200,768 bytes free; admission required 16 GiB available memory and 20 GiB free disk (16 GiB reserve plus 4 GiB estimated additional peak).
- Inputs are pinned in `.scratch/all-tickets/x29-live-gate-20261007-2300z/input/manifest.json` and `input.sha256`. The full tracked-source transfer archive SHA-256 is `d3dc6b1152e268dfaa80e082737355ac8f9939d1cb5a952edd693febda2e25d4`; RED and GREEN fixture snapshot hashes are `d7dadb1e5d468c2fbc703f7c51f3cbdd41edbbbf27875ad9c6c6625939d53331` and `1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217`.
- Raw command output, tool versions, preflight receipt and remote output manifest are in `.scratch/all-tickets/x29-live-gate-20261007-2300z/out/attempt-01/`. The copied files all passed `sha256sum -c remote-output.sha256`; the successful runner exit cleaned its private runtime. `.scratch/all-tickets/x29-live-gate-20261007-2300z/out/attempt-01/remote-cleanup-readback.txt` records verified hashes and removal of the exact Workhorse scope after export.

The combined independent review confirmed that the current X29-relevant source
matches the tested GREEN snapshot; the controller cleanup change preserves the
reviewed ESRCH and receipt condition. The existing hash-verified runs therefore
apply to exactly these two named Linux rows without a repeat build. The Darwin
row is accepted separately below; Windows, other feature combinations and other
MSRV rows remain open.

## Historical runs (old source; not acceptance)

- Machine: Workhorse, Linux 7.2.8, x86_64.
- Toolchain: Rust/Cargo 1.93.0.
- Features: `testing-environ,sys`.
- Command: `cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process shared_child_contract::script_throw_drops_and_reaps_a_live_child -- --exact --nocapture --test-threads=1`.
- Result: exit status 0; the exact test passed (1 passed, 0 failed; 59 filtered out), but review later found the live-child assertion insufficient.
- Preflight passed with no active heavy process groups, 88,186,324 KiB available memory and 671,314,255,872 bytes free. The admission reserves were 16 GiB each for memory and disk; the conservative additional storage estimate was 2 GiB.
- After local copies were verified against Workhorse SHA-256 readback, the exact owned Workhorse session scope was removed. The scoped runner had already cleaned its private runtime.

## Evidence and input identity

- `out/attempt-02/preflight.json` records machine, toolchain, capacity and input hashes.
- `out/attempt-02/cargo.combined` contains the exact test result, readiness/liveness gate, wrong-message rejection and ESRCH receipts.
- `out/attempt-02/cargo.status` is `0`; `out/attempt-02/command.txt` and version files record the command and toolchain.
- Source revision: `acbffcc84763b160576337ee6602e6a839c880fe`; the source archive overlays only the X29 fixture and reuses the accepted X30 `Cargo.lock`.
- Source archive SHA-256: `a49ea6ef5cde41db9dc2eee17debf1d5aecc3338a306660e1b44fe834316f5fc`.
- X29 fixture SHA-256: `2925f184b84ae830bed5478be0cec0b4dd93b6eb6824ce87062883c53d08a579`.
- Combined test output SHA-256: `c9f831623cf4726fc3c0ea85e3d3481653d601891f42d83bf6ce8d63fce89bfa`.
- Preflight output SHA-256: `404e2a16e51b7b324ee441e24f7b3b35e66fd38e1bec0b2c25294df39d09a1a3`.

## Setup history

Two pre-assertion setup issues were corrected and retained in the attempt logs: the first admission found the owned scope root at mode 0755 instead of 0700; the first runner attempt then invoked Cargo from the wrong working directory and stopped before compiling or running the test. The runner now changes to the frozen source directory. Neither setup stop exercised or failed an X29 product assertion. The subsequent Rust/Cargo 1.93.0 run passed; no product correction or acceptance retry was needed.

## Additional MSRV run: Workhorse Linux, 2026-10-07

- Exact test: `shared_child_contract::script_throw_drops_and_reaps_a_live_child`; same features and assertions as the accepted 1.93.0 row.
- Toolchain: privately installed Rust/Cargo 1.77.2 (`rustc 1.77.2 (25ef9e3d8 2024-04-09)`, `cargo 1.77.2 (e52e36006 2024-03-26)`). The bounded launch script is `.scratch/all-tickets/x29-linux-msrv-20261007-c941b397/input/launch.sh`; exact command and outputs are in `.scratch/all-tickets/x29-linux-msrv-20261007-c941b397/out/remote-attempt-01/`.
- Result: exit status 0; exact test passed (1 passed, 0 failed; 59 filtered), but the PID check can accept a zombie. `.scratch/all-tickets/x29-linux-msrv-20261007-c941b397/out/remote-attempt-01/cargo.combined` preserves the historical receipts.
- Inputs: committed source revision `b7dfa020ef59be748b1f0f69545f997ef20dead2`; full tracked-source transfer archive SHA-256 `c2bb976f3911646415104cefa410fc3331331410acb80242cd889086e85c6e32`; source `Cargo.toml` SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`; fixture SHA-256 `17647607b6d042eff58f1e5c61cc1afc2288ef40f9461dbcd1a697ff1b63f26a`. The repository has no root lockfile; the accepted X30 lock was reused from `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06-input/Cargo.lock.accepted`, SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Canonical runner: Workhorse `run_scoped.py`, SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`. It used a private runtime for Rustup, Cargo cache and target, two Cargo jobs, a 585-second runner timeout and a 540-second test timeout.
- Preflight at `2026-10-07T22:45:14+02:00`: 87,789,108 KiB available memory; 671,092,006,912 bytes free on `/var`; no active Cargo, rustc, scoped-runner or compiler process matched. Admission required 16 GiB available memory and 18 GiB free disk (16 GiB reserve plus the 2 GiB conservative additional-storage estimate). The scoped runtime was removed at exit.
- Evidence/readback: all files under `.scratch/all-tickets/x29-linux-msrv-20261007-c941b397/out/remote-attempt-01/` match remote manifest `.scratch/all-tickets/x29-linux-msrv-20261007-c941b397/out/attempt-01/remote-output.sha256`; `.scratch/all-tickets/x29-linux-msrv-20261007-c941b397/out/attempt-01/remote-input-readback.txt` and `remote-launch-readback.txt` pin uploaded inputs. `cleanup-readback.txt` records the exact owned Workhorse session scope absent after cleanup. No compiled build is reusable.
- The scoped invocation took about 18 seconds from local SSH launch to completion (the local command returned after a 1-second initial wait and a 16.8-second completion wait). No setup failure, assertion failure, correction, or retry occurred in this run.

This additional run closes only the Linux x86_64/Rust 1.77.2/`testing-environ,sys`
row. The transfer archive and duplicate lock copy were temporary inputs; the
source revision and accepted lock remain available in Git/evidence.

## Darwin run: arm64 macOS, 2026-10-08

- Exact test and features: `shared_child_contract::script_throw_drops_and_reaps_a_live_child`; `testing-environ,sys`; command and assertions are recorded in `.scratch/all-tickets/darwin-x29-20261008/run-darwin-x29.sh`.
- Host/toolchain: arm64 macOS 27.0.1 / Darwin 27.0.0; Rust/Cargo 1.93.0 (`254b59607` / `083ac5135`). One scoped invocation used one Cargo job, the private runtime for Cargo home and target, and a 1,800-second outer timeout.
- Source inputs: Git base `7ae23c07b9bd84eb6df12467458c059195e73ad3`, archive SHA-256 `c28f0a9c49b5dc54f74a0bd28e85c571afbfb781cd3f67d3877bcae298258b76`; accepted lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The run overlaid the current worktree fixture, SHA-256 `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`; the committed fixture at the base is `1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217`. Their diff is retained at `attempt-01/worktree-fixture.diff`; the combined review confirmed the overlaid X29 behavior applies to the committed fixture and checked the controller cleanup condition.
- The exact RED exited 101 because the incomplete fixture did not answer the fresh `script-throw` challenge; its test failed at the intended challenge wait. This is the expected sensitivity control, not a product failure. The restored GREEN exited 0 (1 passed, 0 failed; 47 filtered). Its output records a fresh challenge response with the fixture PID present, `pre_throw_try_wait=unit`, rejection of the wrong-message expectation, and exact-PID `reap=ESRCH verified=true` after the script throw and child drop.
- The bounded runner exited 0 after validating both statuses and all GREEN markers. Preflight, exact hashes, RED/GREEN logs, and runner output are under `.scratch/all-tickets/darwin-x29-20261008/attempt-01/`. The private Cargo runtime was absent after runner exit; the exact empty session scope was removed and read back absent in `cleanup-readback.txt`. No build is retained or reusable.
- Cargo reported 37.91 seconds for the initial build/test, 3.06 seconds for RED, 0.73 seconds incremental for GREEN compilation, and 0.04 seconds for GREEN. One invocation was consumed; no retry was needed. The combined review returned READY on 2026-10-08 after checking all 20 package files manually, including the runner, source applicability, exact RED/GREEN assertions, hashes, and cleanup readback. This accepts only the named Darwin row; no additional build was needed.
