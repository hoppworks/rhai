# Coordinator state: all tickets

## Mode
Continue the authorized strict Ticket03/sys-package campaign in `docs/sys-package-plan.md` §§6.7–6.8. Do not create/reactivate a Goal.

## Decisions
- Commit, push and integrate only to private `https://github.com/hoppworks/rhai.git` `main`; never public upstream, release or deploy. User requested only remote `main` at completion and explicitly authorized atomic commit/push of verified work.
- Use lowercase `hoppworks` author/committer and configured email. Preserve unrelated dirty work, branches, worktrees and processes.
- Strict verification; push and merge automatic under prior explicit authorization. This does not authorize production.
- Installed Agent-Skills HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`, differing from advertised `35ba734135a64100b891f422d4ced9d76795ab57`; no sync. Project `AGENTS.md`, campaign, e2e-proof and resource rules loaded. Do not infer other Sessions' revisions.
- Keep dirty `tests/fixtures/sys_process_shared_child_contract.rs` and unrelated scratch unstaged. Package B no-primary route is closed; never use native110.

## Current step
X18 RED attempt02 and GREEN attempt03 are already accepted: same source `bcb524b866103f9a684b8da41725c802a00d2458`, lock SHA `2ba4b3a0…`, `testing-environ,sys`, native Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, same exact test and assertion contract. RED is the intentional wrong-byte equality assertion (status 101); GREEN passes (status 0). Both manifests verify. No rerun.

X31 Darwin 1.77.2 is accepted for only `sync` and `sync,no_float` blocking-entry rows after attempt05 and combined review READY. Crosswalk/proof updated; evidence SHA manifest verifies.

## Next action
Atomically commit the exact reviewed X31 attempt05 evidence, crosswalk, current state and its archived predecessor. Push only as a fast-forward to private `origin/main`, verify the remote head and sole-branch list. Then continue with the next open native process criterion: X32/X33 Windows are open; use the existing native guest route and establish the already-required guest process-tree custody before a build.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 with applicable proof/review; integrate only to private fork `main`; read back that remote has only `main`; preserve unrelated work.

## Done when
Every criterion has strict applicable proof/review; accepted work is on fork `main`; remote readback shows only `main`; unrelated work is intact.

## Steps
1. Commit/push the READY X31 Darwin 1.77.2 package atomically.
2. Advance remaining Ticket03 behaviors and platform/feature/MSRV criteria with reusable proof and smallest coherent native packages.
3. Continue remaining Ticket04/05/06 requirements; change product code only for demonstrated failures; review each coherent package once.

## Done steps
- Linux X36 Rust/Cargo 1.77.2 and Darwin X36 kernel denial; X14/X16/X17; X18; X20.
- X30 Linux applicability and X31 Linux blocking-entry; X31 Darwin Rust/Cargo 1.93.0 blocking-entry rows.
- X38 Linux escaped-reader and named Darwin assertion row.

## Accepted evidence
- X36: `.scratch/all-tickets/x36-managed-scope-setup-20261008/`.
- X14/X16/X17: `.scratch/all-tickets/darwin-io-contracts-20261008/` and Linux controls; X18: `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/`; X20: `.scratch/all-tickets/darwin-x20-20261008/`.
- X30: `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06/`.
- X31: Linux `.scratch/all-tickets/linux-shared-child-proof.md`, `.scratch/all-tickets/linux-wait-entry-proof.md`; Darwin attempts 02/05 in `.scratch/all-tickets/darwin-x31-wait-entry-20261008/`.
- X38: `.scratch/all-tickets/linux-managed-escaped-pipe-proof.md` and `.scratch/all-tickets/darwin-x38-20261008/attempt-03/`.

## Open requirements
- X31: remaining OS, non-sync blocking-entry, features and MSRVs.
- Native Windows X32 embedded-quote argv and X33 `.exe`/PATH behavior; guest custody prerequisites apply.
- X34/X35/X37 broader platform/fault/scope rows; remaining X36/X38 and Ticket03 requirements.
- Ticket04/05 C/D/F native, feature and MSRV gaps; Ticket06 R1–R7 and release-proposal checks. Full requirement mapping is in `docs/sys-package-plan.md` §§6.7–6.8.

## Retained resources
Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`, HEAD `7bee1fd8be643ab08e7424cb42b0f7c3b2db15d7`; live `origin/main` matches and the remote advertises only `main`. Preserve other dirty/untracked files and foreign worktrees. No reusable build remains; X31 scopes were cleaned after exporting proof. Future POSIX runs use unique `~/.local/share/agent-builds/rhai/<session>` as TMPDIR, `tools/run_scoped.py`, and Cargo home/target below `AGENT_RUNTIME_DIR`.

## Cause history
- X18 attempt01 wrong cwd; attempt02 valid RED missed by the `--nocapture` parser; attempt03 GREEN. Extra clean build cost 39.70s plus 0.11s test and was avoidable. See X18 evidence.
- X31 Darwin attempt01 failed compilation before assertion; attempts03/04 failed unfiltered metadata before test. Expert escalation26 identified target-inactive WASI metadata as cause. Attempt05 directly ran locked targeted RED/GREEN for both feature rows in 46s total, one Cargo job, 600s bound; target 544,160 KiB and Cargo home 40,132 KiB before cleanup; peak RSS unknown. No product source/lock changed.
- Package B three pre-assertion infrastructure stops; no-primary route closed. X20 one scoped RED/GREEN; X30 attempt06 wrong-count RED/restored GREEN; X36 attempts08–10 recovery/controls. Detailed causes, expert history and original outputs remain in journals and linked evidence; counts are not reset.

## Open escalations
Escalation26 is answered and applied in attempt05. No unanswered escalation blocks the current package.

## Budgets
Current X31 attempt05 used 46s of a 600s bound and one Cargo job; 544,160 KiB target and 40,132 KiB Cargo home before cleanup; peak RSS unknown. Historical per-requirement elapsed times, limits and observed resource samples remain in `.scratch/all-tickets/journal/` and raw evidence; do not reset them.

## History
`state.py rewrite` archives the exact prior state in `.scratch/all-tickets/journal/`; older approvals, limits, evidence and cause/budget detail remain there.
- Previous state: journal/state-9434b80d1913475ebd1ffd753b2b2eb1.md

## Retrospective
Reuse proof while source, assertions, lock, features and environment remain applicable. Classify setup failures separately from expected assertion RED. Set explicit cwd and evaluate expected failures by exit status, assertion marker and test result. Preserve foreign work and exact resource ownership.
