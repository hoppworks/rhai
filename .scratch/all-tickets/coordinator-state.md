# Coordinator state: all tickets

## Mode
Continue authorized strict implementation and private-fork integration for `docs/sys-package-plan.md` §§6.7–6.8. No Goal creation/reactivation.

## Decisions
- Commit/push only to `https://github.com/hoppworks/rhai.git` `main`; never public upstream, release, or deploy. User requested only remote `main` at completion. Atomic lowercase `hoppworks` attribution with configured email.
- Verification strict; push and merge automatic under prior explicit user direction. These do not authorize production/release.
- Agent-Skills installed symlinks resolve to central checkout HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`. This differs from previously advertised `35ba734135a64100b891f422d4ced9d76795ab57`; content hash is not equal. Current global/project/campaign/e2e-proof/resource rules were loaded. No sync; other Sessions/machines not presumed identical.
- Preserve dirty `tests/fixtures/sys_process_shared_child_contract.rs`, unrelated scratch, foreign branches/worktrees/processes. Package B no-primary route remains closed; never use native110.

## Current step
X18 is accepted (`17021f5d`). X31 Linux blocking-entry is integrated at `05320c2c9` for reviewed named rows. X31 Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0 now has READY combined review for `testing-environ,sys,sync` and `testing-environ,sys,sync,no_float`, source `05320c2c9`; proof is `.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-02/proof.md`, review is beside it. Crosswalk records only this partial slice. X31 and A–F remain incomplete.

## Next action
Check this state, crosswalk, review and evidence; stage only the X31 Darwin package, state and exact journal archive; commit and atomically push the fast-forward to private `origin/main`; verify remote has only matching `main`. Then inspect the remaining matrix and advance the next independently runnable open criterion without repeating accepted proof.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 with applicable proof/review; integrate to private `main`; read back that remote has only `main`; preserve unrelated work.

## Done when
Every criterion has strict applicable proof/review; accepted work is on the fork; remote readback has only `main`; unrelated work remains intact.

## Steps
1. Integrate the reviewed Darwin X31 slice to private `main` and verify remote.
2. Advance open Ticket 03 behaviors and platform/feature/MSRV criteria using smallest real-OS packages and valid proof reuse.
3. Change product code only for demonstrated failures; review each coherent package once; reconcile branches only after verified integration and preservation checks.

## Done steps
- Linux X36 Rust/Cargo 1.77.2 `47035986`; Darwin X36 kernel denial `471cf269`.
- Darwin X14/X16/X17 `bcb524b8`; X18 `17021f5d`; X20 `c644085c`.
- X30 Linux applicability `5b99bb069`; X31 Linux blocking-entry 1.97.1 `5c3deeb7` and 1.77.2 `05320c2c9`.

## Accepted evidence
- Original matrix/contracts: `docs/sys-package-plan.md` §§6.7–6.8 and crosswalk.
- X36 `.scratch/all-tickets/x36-managed-scope-setup/`; X14/X16/X17 `.scratch/all-tickets/darwin-io-contracts-20261008/` plus Linux controls; X18 `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/` and Linux options; X20 `.scratch/all-tickets/darwin-x20-20261008/`.
- X30 `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06/`.
- X31 Linux `.scratch/all-tickets/linux-shared-child-proof.md`, `linux-wait-entry-proof.md`, `linux-wait-entry-review.md`, raw evidence and `.scratch/all-tickets/linux-shared-child-evidence-87/blocking-entry-current/`; Darwin proof/review under `.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-02/`.

## Retained resources
Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`; private `origin/main` baseline `05320c2c9`. Remote readback previously showed only `main`. No reusable build; X31 scopes/runtimes removed after proof export. Future builds use unique `~/.local/share/agent-builds/rhai/<session>` and `tools/run_scoped.py` with scoped `TMPDIR` and `AGENT_RUNTIME_DIR`. Do not stage the dirty fixture or other untracked scratch.

## Cause history
- Package B: three pre-assertion infrastructure stops, zero assertions; no-primary route closed. See journal/evidence; consumption retained.
- X18: attempt01 wrong cwd/pre-Cargo (~7s); attempt02 valid intended RED/status 101 missed by parser due `--nocapture` interleaving; attempt03 GREEN. Clean build 39.70s plus 0.11s test was avoidable; combined review READY; no rerun.
- X20 one scoped RED/GREEN. X30 attempt06 wrong-count RED/restored GREEN; review reused proof without duplicate build.
- X36 attempt08 missing parent/recovered once; attempts09/10 intended RED controls.
- X31 Linux initial preflight lacked root lock; compatible lock enabled one 1.97.1 run. Reviewer resolved label mismatch from exact cleanup readbacks; no retest. 1.77.2 applicability reused.
- X31 Darwin attempt01 (23s): malformed assertion mutation failed compilation before test; setup failure, not RED. Attempt02: both features had expected status-101 assertion RED and status-0 restored GREEN, wait-entry/nonterminal, cancellation/wakeup and exact PID ESRCH. Combined review READY; no rerun.

## Open escalations
X31 other OS, non-sync blocking-entry, MSRV/features; X32/X33 native Windows; X34/X35/X37 wider platform/fault/scope rows; remaining X36/X38; remaining Ticket 03 and §§6.7–6.8. Windows X30/X32/X33 and Package B limits/decisions remain in prior state/journals.

## Budgets
- Known totals: X30 one Workhorse run, 2 Cargo jobs, 31.534s, sampled RSS 910,152 KiB/storage 1,284,764 KiB. X36 attempts08/09: 600s bounds, 2 jobs, 20/28s; attempt09 sampled peak 3 GiB. Attempt10 Darwin: 600s, 1 job, 41.36s, peak unsampled. X14/X16/X17 one scoped run, 2 jobs, 28.31s, peak unsampled.
- X18 attempt02 ~40s; attempt03 39.70s build + 0.11s test; free disk samples ~90.6/91 GiB, pressure 44%/40%, peak unsampled. X31 Linux 1.97.1 Cargo 7.87s, max RSS 948,644 KiB, pre-cleanup target 564,396 KiB/Cargo cache 161,508 KiB. X31 Darwin attempt01 compile-failed Cargo 23s; attempt02 rows 23/3s and 9/1s, target 823844 KiB/Cargo home 80052 KiB pre-cleanup, peak unknown. Review cost unknown. Other historical totals and per-run causes remain in `.scratch/all-tickets/journal/` and raw evidence.
- Prior approvals, proof decisions, detailed budgets and causes remain in `.scratch/all-tickets/journal/` and raw evidence.

## History
This rewrite archives the exact prior state. Earlier states, approvals, consumed work and correction history remain in the journal and evidence paths cited above.
- Previous state: journal/state-7c49daac14e94c3c96b4d1a1d9e1226b.md

## Retrospective
Reuse current-source proof where applicable; classify setup errors separately from assertion RED; combine review per acceptance package; retain exact resource ownership and leave foreign work untouched.
