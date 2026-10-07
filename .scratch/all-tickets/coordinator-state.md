# Coordinator state: all-tickets

## Mode
Continue the already-authorized all-tickets implementation under strict acceptance. No new Goal or status mutation. Current Agent-Skills revision: `35ba734135a64100b891f422d4ced9d76795ab57`.

## Decisions
- User authorized implementation, atomic commits/pushes and consolidation into `main` on `https://github.com/hoppworks/rhai.git`; never write to public upstream. Keep only fork `main` remotely after verified integration and cleanup.
- Git author and committer name must be lowercase `hoppworks`; retain configured email. No co-author trailers.
- Local accepted ticket requirements and `docs/sys-package-plan.md` §§6, 6.7 govern. Strict backend proof uses public Engine → real OS → independent readback; UI proof is inapplicable.
- Preserve unrelated/foreign work. Do not stage current `tests/net_metadata.rs`, `tests/sys_policy.rs`, unrelated fixture formatting, or other `.scratch` evidence.

## Current step
X29 test passed on one named Workhorse Linux x86_64 / Rust-Cargo 1.93.0 / `testing-environ,sys` row. Plan row and local proof note now report partial applicability only. The exact Workhorse scope was removed after local evidence hashes matched remote readback.

## Next action
Review is READY with no findings. Run cheap scope/whitespace checks, commit the X29 fixture, plan row, proof and compact state as `hoppworks`, push only to fork `main`, and read back its head. Then continue the next open requirement in §6 without broad rebuilds.

## Goal
Implement every approved local stdlib ticket and release gate.

## Done when
Each platform/feature/MSRV requirement has applicable strict proof and review, integrated work is on fork `main`, and remote branch cleanup leaves only `main`; no upstream write.

## Steps
1. Review and integrate the current X29 Linux partial package.
2. Continue remaining ticket and release-matrix criteria in `docs/sys-package-plan.md`, reusing applicable proof.
3. Verify fork `main`, then consolidate remote branches only after verified integration.

## Done steps
- Previously accepted scoped rows and evidence remain listed in §6.7 and under Accepted evidence below.
- X29 test passed for one Linux/Rust/features row; the combined independent review is READY with no findings.

## Accepted evidence
- Crosswalk: `docs/sys-package-plan.md` §6.7; retain each row's scope and partial status.
- X29 details and hashes: `.scratch/all-tickets/x29-script-throw-20261007-9aec531ea61d42359544757b363f2422/proof.md` and sibling `out/attempt-02/`.
- X24: `.scratch/all-tickets/process-try-wait-evidence/x24-try-wait-20261007-1705z-6a92d/attempt-03/`.
- X30: `.scratch/all-tickets/process-fd-stability-evidence/x30-fd-stability-20261007-1530z/attempt-06/`.
- Other named partials remain as listed in §6.7. Existing Rust-controller panic evidence proves only that narrower scenario.

## Retained resources
- Local X29 source snapshot and attempt logs remain under `.scratch/all-tickets/x29-script-throw-20261007-9aec531ea61d42359544757b363f2422/` for review and proof. Workhorse's exact owned scope is cleaned; no compiled build is reusable.

## Cause history
- Exact test `shared_child_contract::script_throw_drops_and_reaps_a_live_child` passed once; 1 passed, 0 failed, 59 filtered. Wrong-message control was rejected. Outer harness confirmed the fixture PID live before the throw gate and then independently recorded ESRCH after drop.
- Input snapshot revision `acbffcc84763b160576337ee6602e6a839c880fe`; only the X29 fixture was overlaid, with the accepted X30 lockfile. Workhorse preflight had no active heavy groups and passed 16 GiB memory/disk reserves. Logs/source/output hashes are in `proof.md`.
- Two pre-assertion setup stops: first admission found the owned scope at mode 0755; first runner invoked Cargo from the wrong CWD and stopped before compilation/test. Both causes were corrected; zero X29 product failures, one accepted test run. These are distinct setup issues, not correction attempts.
- All approved tickets and the release platform/feature/MSRV matrix remain open except exact accepted rows in §6.7. Do not infer ticket closure from X29's Linux partial.
- Package B no-primary `Child.wait`: 3 infrastructure stops, 0 assertions; sole Expert follow-up consumed. Package E API metadata: 3 infrastructure stops, 0 assertions; sole Expert follow-up consumed. Preserve histories; changed names or Sessions do not reset them.
- Darwin/C and Windows/D retain prior owners/bounds; do not disturb Windows guest work. Full causes/budgets and earlier accepted evidence are in `.scratch/all-tickets/journal/state-b21551dc8cf742f7ac893d26b97e94ca.md` and the referenced evidence.

## Open escalations
No active escalation. Preserve earlier consumed Expert/recovery decisions in the archived state; do not reset by changing Session or route names.

## Budgets
- Heavy-run concurrency remains MacBook 1, Workhorse/LLLM up to 3 subject to pressure; inspect activity/capacity before any next heavy run. Current time/cost/token totals are unknown where source records say unknown.

## Retrospective
This state keeps current decisions, X29 result and next action together. Detailed ticket causes, budgets and proof remain in the journal and evidence paths, avoiding another tracking layer.

## Rules and agents
Global AGENTS hash `a6b21edff45b489def01af636bfba11c85e0e6555a189235ac4f4c24c4fe43bb`; project AGENTS hash `06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c3f7ce119d7c5de`. Relevant campaign, TDD, strict e2e-proof, OCR review and resource rules were reloaded from revision 35ba734. The central Agent-Skills checkout is at that commit with unrelated untracked `.scratch` material preserved. The X29 reviewer confirmed reloading and completed READY/no-findings. Two idle MSRV agents were told to reload before any next action; confirmation is pending and neither is assigned work.

## History
The previous coordinator state is archived at `.scratch/all-tickets/journal/state-b21551dc8cf742f7ac893d26b97e94ca.md`. Keep detailed proof, cost and cause history there and in the evidence paths; do not duplicate it here.
- Previous state: journal/state-3401eae431a4419d9f59df0405402644.md
