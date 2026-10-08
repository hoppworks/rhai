# Coordinator state: all tickets

## Mode
Authorized implementation, strict verification and private-fork integration for `docs/sys-package-plan.md` §§6.7–6.8. Do not create or reactivate a Goal.

## Decisions
- Write only to `https://github.com/hoppworks/rhai.git` `main`; never public upstream, release or deploy. User wants only remote `main` when complete.
- Commit/push authorized; author and committer exactly `hoppworks` with configured email. Preserve lowercase attribution.
- Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57` in central HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`; global, project, campaign, e2e-proof and resource rules loaded. All reviewers used here confirmed the same Main revision. No active agents remain.
- Preserve dirty `tests/fixtures/sys_process_shared_child_contract.rs`, unrelated scratch, foreign branches/worktrees/processes. Package B no-primary route stays closed; never use native110.

## Current step
X18 is already accepted and committed (`17021f5d`): attempt02 raw assertion RED plus attempt03 restored GREEN share source, lock, features and Darwin environment; combined review READY. X31 Linux blocking-entry is READY at 1.77.2 `sync`/`sync,no_float` by reviewed historical proof reuse, plus current-source 1.97.1 `sync`. Plan and crosswalk now record both; raw historical records are being integrated. No duplicate X18/X31 run or reusable build.

## Next action
Run state/reference and diff checks; stage only the X31 plan, state/archive and two reviewed evidence folders. Atomically commit/push to current private `main`, verify exact remote readback and sole branch. Then inspect whether Darwin X31 blocking-entry has reusable proof before considering a new run.

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
- X30 Linux applicability `5b99bb069`; X31 Linux blocking-entry 1.97.1 `5c3deeb7`. X31 1.77.2 reuse is ready, not yet integrated.

## Accepted evidence
- Matrix and original requirements: `docs/sys-package-plan.md` §§6.7–6.8.
- X36 `.scratch/all-tickets/x36-managed-scope-setup/`; X14/X16/X17 `.scratch/all-tickets/darwin-io-contracts-20261008/` plus Linux controls; X18 `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/` and Linux options; X20 `.scratch/all-tickets/darwin-x20-20261008/`.
- X30 `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06/`.
- X31 base `.scratch/all-tickets/linux-shared-child-proof.md`; 1.77.2 `.scratch/all-tickets/linux-wait-entry-evidence-88/` and `linux-wait-entry-outer-evidence-88/`; 1.97.1 `linux-shared-child-evidence-87/blocking-entry-current/`.

## Retained resources
No reusable build. X31 scopes/runtimes were removed with exact readbacks. Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`; private `origin/main` last verified at `5c3deeb71`. New runs use unique `~/.local/share/agent-builds/rhai/<session>`, scoped `TMPDIR` and `AGENT_RUNTIME_DIR` outputs via `tools/run_scoped.py`.

## Cause history
- Package B: three pre-assertion infrastructure stops, zero assertions; no-primary route closed; keep consumption.
- X18: attempt01 wrong cwd, stopped pre-Cargo (~7s). Attempt02 valid intended assertion RED/status 101; parser missed interleaved `--nocapture` output, so GREEN was skipped. Attempt03 restored GREEN; 39.70s build, 0.11s test. Combined review READY; no rerun. This extra clean build is recorded as avoidable overhead.
- X20 one scoped RED/GREEN. X30 attempt06 wrong-count RED/restored GREEN; review avoided duplicate build.
- X36 attempt08 missing parent, recovered once; attempts09/10 intended RED controls.
- X31 initial host preflight stopped before runner due to missing root lock; compatible lock and `cargo metadata --locked` enabled one 1.97.1 run. Reviewer resolved f4b preflight/f4c run label mismatch through exact cleanup readbacks; no retest. Existing 1.77.2 rows reused after source applicability review.

## Open escalations
Windows X30/X32/X33; wider X34/X35/X37; remaining X36/X38; remaining Ticket 03 and §§6.7–6.8. No active escalation. X31 Darwin blocking-entry is the next focused reuse check.

## Budgets
- X30 Workhorse: one run, 2 Cargo jobs, 31.534s aggregate; sampled RSS 910,152 KiB/storage 1,284,764 KiB.
- X36 attempts08/09: 600s bounds, 2 jobs, 20/28s; attempt09 sampled peak 3 GiB. Attempt10 Darwin: 600s bound, 1 job, 41.36s, unsampled.
- X14/X16/X17: one scoped run, 2 jobs, 28.31s, peak unsampled.
- X18 attempt02 ~40s; attempt03 39.70s build + 0.11s test; disk samples ~90.6/91 GiB free, pressure 44%/40%, peak unsampled.
- X31 1.97.1 Cargo 7.87s, max RSS 948,644 KiB; pre-cleanup target 564,396 KiB/Cargo cache 161,508 KiB. Review/build cost unknown. Older totals and details remain in journal/evidence.

## History
All prior states, approvals, budgets, proof decisions and cause details are retained under `.scratch/all-tickets/journal/`; this rewrite archives the exact predecessor.
- Previous state: journal/state-17df735b5187473c8978fdd0bdf6099d.md

## Retrospective
Reuse valid proofs after current-source applicability review; combine review around acceptance requirements; avoid duplicate builds. Preserve expected RED, infrastructure stops and correction history distinctly. Keep foreign work untouched.
