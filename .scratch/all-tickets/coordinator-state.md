# Coordinator state: all tickets

## Mode
Authorized implementation, strict verification, and private-fork integration for `docs/sys-package-plan.md` §§6.7–6.8. Do not create/reactivate a Goal.

## Decisions
- Fork only: `https://github.com/hoppworks/rhai.git`; integrate verified work to remote `main`, keep only that remote branch. Never write to public upstream, release, or deploy.
- Commit author/committer exactly `hoppworks`; retain configured email and use command-local overrides.
- Agent-Skills requested Main `35ba734135a64100b891f422d4ced9d76795ab57` is contained in central HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`. Global/project/campaign/e2e-proof/resource rules were reloaded. No active subagents; completed X30 reviewer confirmed the same rule revision before review.
- Preserve dirty fixture `tests/fixtures/sys_process_shared_child_contract.rs`, unclassified scratch, foreign worktrees and processes. Package B's stopped no-primary route stays closed; never use native110.

## Current step
X30 is partially accepted for Linux x86_64, Rust/Cargo 1.93.0, `testing-environ,sys`. Attempt06 proves 200 public Engine `run` calls leave `/proc/self/fd` at 4; wrong-count RED and restored GREEN both passed their intended controls; tasks/cleanup workers returned to baseline. The 60-second parent deadline kills/reaps on timeout. Combined review READY (2026-10-08): test and census helpers are unchanged at `c644085ccf65160bd3d39f5353e8b933310ffe03`; intervening `run_map` managed-scope fault setup does not affect default DirectChild/no-fault/no-custom-cwd path. Plan narrative and crosswalk now record scoped applicability; other X30 rows remain open. No duplicate run or product fix.

## Next action
State is compressed and its exact predecessor archived. Commit only `docs/sys-package-plan.md`, this state, and the new journal archive, then `git push --atomic origin HEAD:refs/heads/main`; verify commit attribution and that remote has only `main`. Do not stage dirty fixture or unrelated scratch. Next, inspect the smallest uncovered Ticket 03 criterion (starting with X31 existing sync evidence) and reuse applicable proof before choosing any run.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic

## Goal
Close all original criteria in `docs/sys-package-plan.md` §§6.7–6.8 with applicable proof/review; integrate verified packages on private `main`; leave only remote `main`.

## Done when
Every criterion has strict applicable proof/review, verified changes are on private `main`, and remote branch readback shows only `main`. Preserve foreign and unmerged work.

## Steps
1. Advance uncovered Ticket 03 rows with small real-OS packages; reuse applicable proof.
2. Advance remaining platform, fault, feature and MSRV criteria; change product code only for demonstrated failures.
3. Integrate coherent reviewed packages atomically to private `main`; read back and report all remaining gates.

## Done steps
- Linux X36 Rust/Cargo 1.77.2 accepted on private `main`: `47035986d03aabe202b749b983973ed256ae0c37`.
- Darwin X36 attempt10 accepted for named arm64/macOS 27.0.1 kernel-denial row: `471cf2698dce1571c6e875c093c2cd2c9ffd6093`.
- Darwin X14/X16/X17 passed 3/3; combined review READY; atomic push confirmed sole `main`: `bcb524b866103f9a684b8da41725c802a00d2458`.
- X18 Darwin partial accepted and pushed after combined review: `17021f5d3976501cd8e04dfe56aeb7e00967c431`.
- X20 Darwin partial accepted with combined review; atomic push/readback confirmed sole `main`: `c644085ccf65160bd3d39f5353e8b933310ffe03`.

## Accepted evidence
- Requirement matrix: `docs/sys-package-plan.md` §§6.7–6.8.
- X36: `.scratch/all-tickets/x36-managed-scope-setup-20261008/proof.md`, attempts 01–10.
- X14/X16/X17: `.scratch/all-tickets/darwin-io-contracts-20261008/attempt-01/proof.md`; Linux controls: `.scratch/all-tickets/process-io-contract-evidence/attempt-01/proof.md`.
- X18 Linux: `.scratch/all-tickets/linux-process-options-proof.md`, `linux-process-options-evidence-90/`; Darwin: `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/proof.md`, attempts 01–03.
- X20: `.scratch/all-tickets/darwin-x20-20261008/attempt-01/proof.md`.
- X30: `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06/`; current-source combined review recorded in plan.

## Retained resources
No reusable builds; scoped runtimes were removed after proof export. Workhorse clean clone `/var/srv/workspaces/rhai` was at `c644085…` on `main`; this task's active worktree is `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`. Future POSIX runs need a unique absent `~/.local/share/agent-builds/rhai/<session-id>` scope, current central `tools/run_scoped.py`, `TMPDIR` set to that absolute scope, and real outputs/caches under `AGENT_RUNTIME_DIR` per project flags.

## Cause history
- Package B: three pre-assertion infrastructure stops, zero assertions; preserve no-primary stop and consumed post-escalation follow-up.
- X18 attempt01 wrong cwd, one pre-Cargo stop (~7s); attempt02 one bounded run (~40s, intended RED, wrapper missed interleaved `--nocapture` output but raw log proves it); attempt03 restored GREEN (Cargo 39.70s). No further X18 run.
- X20 one scoped RED/GREEN; matcher missed interleaved output, raw logs prove intended timeout assertion RED and GREEN. No rerun.
- X36 attempt08 missing parent stopped pre-Cargo; corrected six-test run passed. Attempts09/10 were intended REDs.
- X30 attempt06 completed intended wrong-count RED and restored GREEN; combined review found source applicability. No rerun.

## Open escalations
Windows X30/X32/X33; broader X34/X35/X37; remaining X36/X38 rows; Package B; remaining Ticket 03 and other §§6.7–6.8 criteria. No active escalation.

## Budgets
- X30 Workhorse: one bounded run, 2 Cargo jobs, 31.534s aggregate Cargo time; sampled maxima 910,152 KiB RSS and 1,284,764 KiB private storage (not continuous peaks); no sampler retry. Review/build cost unavailable.
- X36 attempts08/09: each one 600s Workhorse run, 2 jobs, observed 20/28s; attempt09 sampled peak 3 GiB. Attempt10 one 600s Darwin run, 1 job, 41.36s, unsampled.
- X14/X16/X17: one scoped run, 2 jobs, 28.31s (25.35 setup/build, 0.27 tests), peak unsampled.
- X18: attempt02 disk ~90.6 GiB free; attempt03 ~91 GiB free, memory pressure 40%, peak unsampled. Review time/cost unknown. Token/cost totals unknown; earlier totals and Package B counts remain in archived state.

## History
`state.py rewrite` archives each exact predecessor in `.scratch/all-tickets/journal/`; preserve existing journal refs plus the new archive. Linked attempts retain detailed approvals, proof, causes and budgets.
- Previous state: journal/state-f860df0fbb714048b94c235a3b940634.md

## Retrospective
Reuse valid X30 evidence after source-applicability review; no duplicate build/review. X14/X16/X17 shared Linux controls and one review. X18 reused expected RED; X20 raw output avoided another run. Prior doc finding was fixed without another build. Do not delete unclassified files or foreign resources.
