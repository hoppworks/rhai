# Coordinator state: all tickets

## Mode
Authorized implementation, strict verification, and private-fork integration for `docs/sys-package-plan.md` §§6.7–6.8. Do not create/reactivate a Goal.

## Decisions
- Fork only: `https://github.com/hoppworks/rhai.git`; integrate reviewed work to `main`. Never write to public upstream, release, or deploy. User wants only remote `main` when campaign is complete.
- Commit author/committer exactly `hoppworks`, configured email retained. Current explicit authorization covers commit/push/integration.
- Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57` is in central HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`; local/global, project and applicable campaign/e2e-proof/resource rules loaded. X31 reviewer confirmed same revision before first review and affected-delta recheck. No active agents remain.
- Preserve dirty fixture `tests/fixtures/sys_process_shared_child_contract.rs`, unclassified scratch, foreign branches/worktrees and processes. Package B's stopped no-primary route remains closed; never use native110.

## Current step
X31 is partially accepted. Existing reviewed Linux 1.77.2 shared-child rows remain valid. New Workhorse Linux x86_64/Rust-Cargo 1.97.1 `testing-environ,sys,sync` proof directly observed entry into public blocking `wait`, cancellation wakeup and exact PID reaping. Combined review READY 2026-10-08. Exact distinct preflight/run scopes and their cleanup readbacks reconciled in the proof folder. No product/test edits or reusable build.

## Next action
Check current private `origin/main` and divergence before integrating the X31 plan/evidence/state package; commit/push atomically only after basing it safely on current fork main. Then advance the next uncovered criterion, starting with whether native Darwin X31 blocking-wait evidence can reuse existing artifacts; launch no duplicate Linux test.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic

## Goal
Close all original criteria in `docs/sys-package-plan.md` §§6.7–6.8 with applicable proof/review, integrate verified work on private `main`, leave only remote `main`, and preserve unrelated work.

## Done when
Every criterion has strict applicable proof/review; verified work is on private fork `main`; remote branch readback shows only `main`; unrelated work is preserved.

## Steps
1. Advance uncovered Ticket 03 rows with small real-OS packages and applicable proof reuse.
2. Advance remaining platform, fault, feature and MSRV criteria; change product code only for demonstrated failures.
3. Integrate coherent reviewed packages to private `main`; verify readback and report remaining gates.

## Done steps
- Linux X36 Rust/Cargo 1.77.2: `47035986`.
- Darwin X36 kernel-denial row: `471cf269`.
- Darwin X14/X16/X17: `bcb524b8`; X18: `17021f5d`; X20: `c644085c`.
- X30 Linux 1.93 applicability and plan record: `5b99bb069`; no duplicate run.
- X31 Linux blocking-wait row: proof and review READY; integration pending.

## Accepted evidence
- Requirement matrix: `docs/sys-package-plan.md` §§6.7–6.8.
- X36 `.scratch/all-tickets/x36-managed-scope-setup/`; X14/X16/X17 `.scratch/all-tickets/darwin-io-contracts-20261008/` and Linux IO controls; X18 Linux options and Darwin stdin proofs; X20 `.scratch/all-tickets/darwin-x20-20261008/`.
- X30 `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06/`; current-source review/plan at `5b99bb069`.
- X31 base `.scratch/all-tickets/linux-shared-child-proof.md`; current blocking-entry package `.scratch/all-tickets/linux-shared-child-evidence-87/blocking-entry-current/`; combined review confirmed READY.

## Retained resources
No reusable build. X31 successful run scope/runtime were removed after export; preflight-only scope was separately removed and exact-path readback retained. Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`; last known integrated commit `5b99bb069`. Fetch/read current `origin/main` before integration. New builds use unique `~/.local/share/agent-builds/rhai/<session>`, scoped `TMPDIR`, and outputs/caches under `AGENT_RUNTIME_DIR` via current `tools/run_scoped.py`.

## Cause history
- Package B: 3 pre-assertion infrastructure stops, zero assertions; no-primary route closed; preserve consumed follow-up.
- X18: 1 pre-Cargo cwd stop, 1 bounded intended RED, 1 restored GREEN; no rerun. X20: one RED/GREEN; raw logs avoided rerun.
- X36: attempt08 pre-Cargo missing parent, recovered by one six-test pass; attempts09/10 were intended RED controls.
- X30: attempt06 intended wrong-count RED and restored GREEN; applicability review avoided duplicate build.
- X31: first host preflight stopped before runner because no root `Cargo.lock`; no build/assertions. Reused compatible lock, `cargo metadata --locked` passed, one scoped run passed. Reviewer initially found f4b/f4c label mismatch; exact preflight readback and corrected distinct labels resolved it. No test rerun.

## Open escalations
Windows X30/X32/X33; wider X34/X35/X37; remaining X36/X38; remaining Ticket 03 and §§6.7–6.8. No active escalation.

## Budgets
- X30 Workhorse one bounded run, 2 Cargo jobs, aggregate 31.534s; sampled RSS 910,152 KiB/storage 1,284,764 KiB; review/build cost unknown.
- X36 attempts08/09 each one 600s Workhorse run, 2 jobs, observed 20/28s; attempt09 sampled peak 3 GiB. Attempt10 one 600s Darwin run, 1 job, 41.36s, unsampled.
- X14/X16/X17 one scoped run, 2 jobs, 28.31s; peak unsampled. X18 two runs (~40s and 39.70s), X20 one scoped RED/GREEN; details in journal.
- X31 one unlaunched preflight scope (no build), one Linux run: Cargo wall 7.87s, max RSS 948,644 KiB; before cleanup target 564,396 KiB/Cargo cache 161,508 KiB. Review/build cost unknown. Historical package budgets and totals remain in archived states; token/cost totals unavailable.

## History
- Preserve all prior campaign history in `.scratch/all-tickets/journal/`; this rewrite archives exact current predecessor. Earlier budget/cause detail in predecessor journal refs.
- Previous state: journal/state-7d24d05f204944c49d84b0bfd955187f.md

## Retrospective
Reuse valid proof after source-applicability review; combine requirement review; avoid duplicate builds. Preserve expected RED, infrastructure-stop, and correction histories distinctly. Do not delete unclassified files or foreign resources.
