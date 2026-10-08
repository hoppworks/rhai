# Coordinator state: all tickets

## Mode
Authorized implementation, strict verification and private-fork integration for `docs/sys-package-plan.md` §§6.7–6.8. Do not create or reactivate a Goal.

## Decisions
- Write only to `https://github.com/hoppworks/rhai.git` `main`; never public upstream, release or deploy. User wants only remote `main` when complete.
- Commit/push authorized; author and committer exactly `hoppworks` with configured email. Preserve lowercase attribution.
- Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57` in central HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`; global, project, campaign, e2e-proof and resource rules loaded. All reviewers used here confirmed the same Main revision. No active agents remain.
- Preserve dirty `tests/fixtures/sys_process_shared_child_contract.rs`, unrelated scratch, foreign branches/worktrees/processes. Package B no-primary route stays closed; never use native110.

## Current step
X18 is accepted and committed (`17021f5d`); X31 Linux blocking-entry is accepted for reviewed 1.77.2 `sync`/`sync,no_float` and current-source 1.97.1 `sync`, integrated at `05320c2c9`. X31 native Darwin attempt02 now has both expected assertion RED and restored GREEN for `sync` and `sync,no_float`; source, lock, toolchain, environment and exact child PID readbacks are recorded in `.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-02/proof.md`. Combined review is pending. X31 and A–F remain incomplete.

## Next action
Obtain one combined independent Standard review of the X31 Darwin requirement crosswalk, source/lock/features/environment binding, four status+assertion+result classifications, wait-entry/cancel/reap receipts, restoration and scoped cleanup. Do not rerun X18, accepted Linux rows or this Darwin package if review is READY. On READY, update the plan/proof crosswalk, integrate the reviewed slice into private fork `main`, verify remote main, then continue with the next uncovered Ticket 03 criterion.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 with applicable proof/review, integrate to private `main`, leave only remote `main`, preserve unrelated work.

## Done when
Every criterion has strict applicable proof/review; verified work is on the fork; remote readback has only `main`; unrelated work remains intact.

## Steps
1. Advance uncovered Ticket 03 rows with small real-OS packages and valid proof reuse.
2. Cover remaining platform, fault, feature and MSRV criteria; change product code only for demonstrated failures.
3. Integrate coherent reviewed packages to private `main`, read back, then safely reconcile branches.

## Done steps
- Linux X36 Rust/Cargo 1.77.2 `47035986`; Darwin X36 kernel denial `471cf269`.
- Darwin X14/X16/X17 `bcb524b8`; X18 `17021f5d`; X20 `c644085c`.
- X30 Linux applicability `5b99bb069`; X31 Linux blocking-entry 1.97.1 `5c3deeb7` and 1.77.2 source-applicability/evidence package `05320c2c9`.

## Accepted evidence
- Matrix and original requirements: `docs/sys-package-plan.md` §§6.7–6.8.
- X36 `.scratch/all-tickets/x36-managed-scope-setup/`; X14/X16/X17 `.scratch/all-tickets/darwin-io-contracts-20261008/` plus Linux controls; X18 `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/` and Linux options; X20 `.scratch/all-tickets/darwin-x20-20261008/`.
- X30 `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06/`.
- X31 base `.scratch/all-tickets/linux-shared-child-proof.md`; 1.77.2 `.scratch/all-tickets/linux-wait-entry-proof.md`, `linux-wait-entry-review.md`, raw evidence and outer cleanup folders; 1.97.1 `linux-shared-child-evidence-87/blocking-entry-current/`.

## Retained resources
No reusable build. X31 scopes/runtimes were removed with exact readbacks. Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`; private `origin/main` verified at `05320c2c9`; remote readback showed only `main`. New runs use unique `~/.local/share/agent-builds/rhai/<session>`, scoped `TMPDIR` and `AGENT_RUNTIME_DIR` outputs via `tools/run_scoped.py`.

## Cause history
- Package B: three pre-assertion infrastructure stops, zero assertions; no-primary route closed; keep consumption.
- X18: attempt01 wrong cwd, stopped pre-Cargo (~7s). Attempt02 valid intended assertion RED/status 101; parser missed interleaved `--nocapture` output, so GREEN was skipped. Attempt03 restored GREEN; 39.70s build, 0.11s test. Combined review READY; no rerun. This extra clean build is recorded as avoidable overhead.
- X20 one scoped RED/GREEN. X30 attempt06 wrong-count RED/restored GREEN; review avoided duplicate build.
- X36 attempt08 missing parent, recovered once; attempts09/10 intended RED controls.
- X31 initial host preflight stopped before runner due to missing root lock; compatible lock and `cargo metadata --locked` enabled one 1.97.1 run. Reviewer resolved f4b preflight/f4c run label mismatch through exact cleanup readbacks; no retest. Existing 1.77.2 rows reused after source applicability review.
- X31 Darwin attempt01 (2026-10-08): 23-second Cargo test command ended 101 during compile because the harness inserted two assertion message arguments; intended test/assertion never ran. Scope/runtime were cleaned, raw log retained at `.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-01/`. This is one unsuccessful setup recovery, separate from prior lock/preflight cause; no X31 Darwin acceptance.
- X31 Darwin attempt02 (2026-10-08): corrected only the test assertion mutation, then both `sync` and `sync,no_float` produced status-101 intended REDs and status-0 restored GREENs, with wait-entry/nonterminal and exact PID ESRCH receipts. Raw evidence/proof are under `attempt-02/`; one combined review is pending. No product source changed.

## Open escalations
Windows X30/X32/X33; wider X34/X35/X37; remaining X36/X38; remaining Ticket 03 and §§6.7–6.8. No active escalation. X31 Darwin blocking-entry is the next focused reuse check.

## Budgets
- X30 Workhorse: one run, 2 Cargo jobs, 31.534s aggregate; sampled RSS 910,152 KiB/storage 1,284,764 KiB.
- X36 attempts08/09: 600s bounds, 2 jobs, 20/28s; attempt09 sampled peak 3 GiB. Attempt10 Darwin: 600s bound, 1 job, 41.36s, unsampled.
- X14/X16/X17: one scoped run, 2 jobs, 28.31s, peak unsampled.
- X18 attempt02 ~40s; attempt03 39.70s build + 0.11s test; disk samples ~90.6/91 GiB free, pressure 44%/40%, peak unsampled.
- X31 1.97.1 Cargo 7.87s, max RSS 948,644 KiB; pre-cleanup target 564,396 KiB/Cargo cache 161,508 KiB. Darwin attempt01 Cargo 23s, compile failed before assertion. Attempt02 rows 23/3s and 9/1s; target 823844 KiB, Cargo home 80052 KiB before cleanup, peak unknown. Review cost unknown. Older totals and details remain in journal/evidence.

## History
All prior states, approvals, budgets, proof decisions and cause details are retained under `.scratch/all-tickets/journal/`; this rewrite archives the exact predecessor.
- Previous state: journal/state-17df735b5187473c8978fdd0bdf6099d.md
- Previous state: journal/state-f124e02a7b5845fca64a21a3ead97cbb.md
- Previous state: journal/state-1febae780db94a6c974fbf6cc05a266f.md
- Previous state: journal/state-58be344669484a47a0b4092f0c8a8969.md
- Previous state: journal/state-b488f6e0acc849a195f2bb25268a2463.md
- Previous state: journal/state-80e16d392c284a46b62ed7387bd372fb.md

## Retrospective
Reuse valid proofs after current-source applicability review; combine review around acceptance requirements; avoid duplicate builds. Preserve expected RED, infrastructure stops and correction history distinctly. Keep foreign work untouched.
