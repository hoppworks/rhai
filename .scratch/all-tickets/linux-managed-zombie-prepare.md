# Linux managed-zombie MSRV proof preparation

Status: run94 reached the intended first wrong-assertion control: status 101, named assertion, exact typed boundary, and independent fixture cleanup all matched. The source-only recipe then rejected its outer libtest summary because nested fixture output interrupted the test status line. Exported failure evidence is preserved at `.scratch/all-tickets/linux-managed-zombie-failed94-evidence/`; run94 runtime and scope were confirmed absent after cleanup. Corrected run95 recipes are prepared for independent review; run95 stage and scope remain unallocated. No SSH/build/launch occurred for this repair.

## Frozen inputs and route

- Worktree/source revision: `257edf695f953271adf17b12dcc70c4287ae76b5`; archive SHA-256 `ea085b4d28ee5ce3c7b998044242a50c755d9e9252638dbcf28c036b3df7c922`.
- Rust lock SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; accepted Linux base helper SHA-256 `59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06`.
- Test source SHA-256: `8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b`.
- Contract: `.scratch/stdlib-wayfinder/issues/03-process-contract.md`. Relevant prior evidence: `.scratch/managed-unix-scope-close/launch-74-evidence/full-sys-process.log` and `.scratch/all-tickets/coordinator-state.md` (native74 held-zombie typed timeout, direct `exit=Some(0)`, cleanup; native80 ordinary Linux suite). These prove prior behavior at their recorded source/toolchain, not this Rust 1.77.2 revision.
- The source delta from `1241a5f8` is limited to Darwin unit-test program selection (`/usr/bin/true`) in `src/packages/sys/process.rs` and `src/packages/sys/process/unix.rs`; there is no Linux production-path change. This makes native74 relevant prior proof while leaving the Rust 1.77.2 current-revision test as the uncovered criterion.

## One bounded criterion

Run only `managed_run_reports_while_fixture_reaper_holds_stopped_zombies`, one exact test, one feature row `testing-environ,sys`, on native Linux x86_64 with private Rust 1.77.2. The test is already gated on Linux and `not(no_index)` / `not(no_float)`; this row leaves default float/index features enabled. Do not add baseline, patched-feature, or helper tests.

The validator requires the actual immutable test receipt to show host live at return; leader already reaped; worker and leaf held as zombies in the recorded process group; all three acquired PIDFD records with exact PID/start/PPID/PGID and the worker→leader/leaf→worker parent links; exact typed `observe_process_group_closure` timeout with diagnostic, complete streams and direct leader `exit=Some(0)`; held fixture-reaper PID/start and successful reaper status. The formatter emits `cause_details={:?} cleanup_diagnostics={:?}` after `diagnostic=true`, then the API record newline and a leading space before `held=...`; both parsers allow that real newline while requiring the debug-field labels and exact held record. After fixture release, it independently checks each leader/worker/leaf/host/reaper PID+start identity for absence (a reused PID with a different start tick is allowed), and checks the exact group has no remaining process members.

Two temporary controls append a deliberately wrong assertion after the test's existing boundary and cleanup receipts: successful report while stopped zombies are held, and direct exit `Some(7)`. Each must fail at its named assertion with test status 101, while retaining its own boundary, reaper success and independently verified process cleanup. The helper restores `tests/sys_process.rs` byte-for-byte after each control and validates one final exact green invocation. No altered mock result or modified production outcome is used.

## Custody and bounds

- Prospective owned stage: `/root/rhai-linux-managed-zombie-20261003-257edf69-95`.
- Prospective private scope: `/root/.local/share/agent-builds/rhai/linux-managed-zombie-20261003-257edf69-95`.
- One outer run, one feature row, three exact test invocations (two expected assertion failures + one pass), three private toolchain setup commands; six helper commands total.
- Reuse the accepted Linux runner with Rust 1.77.2, 540 s total helper deadline including the 30 s export reserve (510 s work), runner timeout 585 s, outer wait 600 s, Cargo jobs 2, max descendants 16, 1 s sampling, and the same 1.5 GiB preemptive / 2 GiB RSS and storage hard bounds. No limit has been raised.
- Stage fingerprints source archive, lock, base helper, proof helper, process contract, stage and launch recipes, and runner support files into `input-identities.sha256`; `source.sha256` pins the archive. The run95 collector accepts only the exact paths and expected-zero outer run status, checks per-control status 101 plus stdout-only final outer result and stderr panic source/assertion, rechecks fixture identities/group and both controls, exports a selected hash-verified evidence set, and offers fresh-inventory/hash-gated exact stage cleanup only after export. It does not clean the private scope.

## Remaining gap

Current-revision real-OS Rust 1.77.2 acceptance is not yet established. Run95 is unallocated pending parent review. The test intentionally retains its existing broad recognized-outcome behavior; this proof narrows only its evidence acceptance to the revised typed-zombie boundary. This one case does not close the broader Linux process matrix, other managed paths, macOS/Windows, or release acceptance. The existing `managed_run_closes_worker_after_leader_exit_and_preserves_sentinel` normal-success fixture (test1766) still assumes the foreign fixture reaper does not reap the leader first; that assumption remains an open contract/test robustness gap. The held-zombie boundary proof does not resolve or claim coverage for normal-success behavior under foreign reaping, and the full managed-process matrix remains required.

## Recipe integrity pins

- Proof helper: `bc2650660bb1c3a576a6f33507f87b8254c74a9e17f7053e7e1f754238eb417d`.
- Stage recipe: `33125b53871f658df8943b41fd8ddbdbf9ef9888f0221a7b292746ba11496805`; launch recipe: `687ac9ca540de8349547a580e1b3fb38237a272d00f7a9505cbfb59acc3f1eab`.
- Contract source: `f8c7520d931144f8e72e90b782455b1e6c32d4c3eb47c392ea7a74f8d3168ec7`; collector: `771a94722e9aa26346aa2cc299d4eee33718c074114412e086b0ca71abf94d7b`.
- Frozen test source remains `8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b`.
- Pure harness checks: `.scratch/all-tickets/linux-managed-zombie-purechecks.json`: actual run94 first-control stdout/stderr is accepted by both outer-result validators and the unchanged strict boundary parser; both validators reject five corruptions (wrong test prefix, missing summary, wrong failure list, wrong panic source, wrong assertion). A terminal-only green summary model is accepted for parser coverage; no green native outcome is claimed.
