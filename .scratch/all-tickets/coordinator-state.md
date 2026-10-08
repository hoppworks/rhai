# Coordinator state: all tickets

## Mode
Authorized implementation, strict verification, and private-fork main integration for `docs/sys-package-plan.md` §§6.7–6.8. Do not create or reactivate a Goal.

## Decisions
- Private fork only: `https://github.com/hoppworks/rhai.git`; preserve history and only remote `main`. No public-upstream writes, release, or deployment.
- Commit author/committer name exactly `hoppworks`; retain configured email. Use command-local override; do not change config.
- User-designated Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57` is contained in central HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`. Global, project, campaign, e2e-proof, and central resource-lifecycle rules were reloaded. Central repo has only untracked `.scratch` artifacts, no tracked rule edits.
- Preserve the dirty fixture `tests/fixtures/sys_process_shared_child_contract.rs`, unclassified scratch, foreign worktrees, and running processes. Package B's stopped no-primary route stays closed; do not use native110.

## Current step
Ticket 03 X18 is complete. Its strict proof covers named Linux/Rust 1.77.2 rows and Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`. Attempt02 proves intended wrong-EOF RED (0 passed, 1 failed, exit 101); attempt03 restored source passed (1/1). Public Engine `run_raw` with `stdin: ()` launched a real child; exact stdout, child-written record, and direct-child ESRCH were read independently. Source SHA-256 `7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017`; lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. Cleanup readback passed. Combined review READY; doc findings corrected. Commit `17021f5d3976501cd8e04dfe56aeb7e00967c431` was pushed atomically and read back as the only `origin/main` branch.

X20 Darwin attempt01 proves the exact inverted-`timed_out` assertion RED (exit101) and restored GREEN (1/1) for `run_io_contract_empty_output`, public Engine, real `/bin/sh`, child-record readback and ESRCH. Test source and accepted lock hashes match the prior Darwin proof. An output matcher missed libtest's interleaved failure/success lines; raw logs prove both outcomes, so no rerun was made. Combined review READY; proof: `.scratch/all-tickets/darwin-x20-20261008/attempt-01/proof.md`.

## Next action
Mark only the named Darwin X20 row partial accepted, then commit/push this package atomically to private `origin/main` and read back the sole remote branch. No further X20 build/test. Keep raw logs unchanged; do not clean unclassified scratch or touch the dirty fixture.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 with applicable proof/review; integrate verified packages to private `origin/main` and retain only remote `main`.

## Done when
Every criterion has strict applicable proof/review; verified work is on private `main`; remote has only `main`. Preserve foreign and unmerged work.

## Steps
1. Advance uncovered Ticket 03 rows with small real-OS acceptance packages, reusing applicable proof.
2. Advance other open platform, fault, feature, and MSRV criteria; change product code only for demonstrated failures.
3. Integrate coherent reviewed packages atomically to private `main`; read back remote state and report remaining gates.

## Done steps
- Linux X36 Rust/Cargo 1.77.2 accepted; commit `47035986d03aabe202b749b983973ed256ae0c37` is on private `main`.
- Darwin X36 attempt10 accepted for named arm64/macOS 27.0.1 kernel-denial row; commit `471cf2698dce1571c6e875c093c2cd2c9ffd6093` is on private `main`.
- Darwin X14/X16/X17 passed 3/3; combined review READY. Commit `bcb524b866103f9a684b8da41725c802a00d2458` was atomically pushed. Remote readback confirmed only `main`.
- X18 Darwin partial acceptance, combined review READY, committed as `17021f5d3976501cd8e04dfe56aeb7e00967c431`; atomic push/readback confirmed it is the only remote `main`.

## Accepted evidence
- Requirement inventory and applicability: `docs/sys-package-plan.md` §§6.7–6.8.
- X36 causes/evidence: `.scratch/all-tickets/x36-managed-scope-setup-20261008/proof.md`, attempts 01–10.
- X14/X16/X17 Darwin: `.scratch/all-tickets/darwin-io-contracts-20261008/attempt-01/proof.md`; Linux controls: `.scratch/all-tickets/process-io-contract-evidence/attempt-01/proof.md`.
- Linux X18: `.scratch/all-tickets/linux-process-options-proof.md` and `linux-process-options-evidence-90/`.
- X20 Darwin partial proof, combined review READY: `.scratch/all-tickets/darwin-x20-20261008/attempt-01/`.
- Darwin X18: `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/proof.md`, attempts 01–03 and manifests.

## Retained resources
No build output is reusable; scoped runtimes/scopes were removed after export. Current worktree is `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`, based on remote `main` `bcb524b866103f9a684b8da41725c802a00d2458`; remote readback shows only `main`. Future POSIX runs use a new absent `~/.local/share/agent-builds/rhai/<session-id>` scope as `TMPDIR`, `tools/run_scoped.py`, and route real caches/outputs under `AGENT_RUNTIME_DIR`.

## Cause history
- Package B: three pre-assertion infrastructure stops, zero assertions, one consumed post-escalation follow-up; preserve the no-primary stop.
- X18 attempt01: wrong cwd, one pre-Cargo stop (~7s). Attempt02: one bounded invocation (~40s; Cargo 37s, RED 0.11s); wrapper same-line matcher missed libtest `--nocapture` interleaving, but raw output proves intended RED. Attempt03: one bounded invocation; Cargo 39.70s, GREEN 0.11s. No further X18 test is needed.
- X20 Darwin attempt01: one scoped RED/GREEN invocation. Wrapper's same-line matcher missed `--nocapture` interleaving; raw log shows the exact inverted timeout assertion and green summary. Restored source hash checked before GREEN; do not rerun.
- X36 attempt08 first launch stopped pre-Cargo for missing parent; corrected six-test run passed. Attempts09/10 REDs were intended controls. Full cause history remains in linked proofs and journal snapshots.

## Open escalations
Windows X30/X32/X33; broader X34/X35/X37; remaining X36/X38 rows; Package B; remaining Ticket 03 and other §§6.7–6.8 criteria. No active escalation.

## Budgets
X36 attempts08/09 each used one 600s Workhorse run, two jobs, observed 20/28s; attempt09 peak was estimated 3 GiB. Attempt10 used one 600s Darwin run, one job, 41.36s; estimated 3 GiB, actual unsampled. X14/X16/X17 used one scoped run, two jobs, 28.31s (25.35 setup/build, 0.27 tests), peak unsampled. X18 details above; attempt02 disk sample ~90.6 GiB free, attempt03 launch ~91 GiB free and 40% memory pressure, actual peak unsampled. Review time/cost unavailable. Token/cost totals unavailable; earlier totals and Package B counts remain archived.

## History
`state.py rewrite` archives each exact predecessor under `.scratch/all-tickets/journal/`. Retain prior states and linked detailed attempts, approvals, causes, proof, and budgets; this file is the compact current state.
- Previous state: journal/state-0e16241958e74a06ad60f534a0fe86b1.md
- Previous state: journal/state-d6ea2a3c26aa4037b0c352c4ef77d7f6.md
- Previous state: journal/state-fab2d7423de54d3ba62530d508641109.md
- Previous state: journal/state-a54d3bc5d0994a19a04bd6154f4566a7.md
- Previous state: journal/state-686ee74e26784324beae577601fff39a.md

## Retrospective
X14/X16/X17 reused applicable Linux controls and one combined review. X18 reused valid raw RED instead of repeating it; attempt03 ran only restored GREEN. One combined review found and closed a documentation-only reference/status issue; no follow-up build or duplicate review was needed. No unclassified files or foreign resources were removed.
