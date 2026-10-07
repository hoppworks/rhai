# Coordinator state: all-tickets

## Mode
Continue already-authorized implementation and strict acceptance; do not create/reactivate a Goal.

## Decisions
Owner authorized atomic commits by lowercase `hoppworks`, pushes and coordinator merges to private fork `https://github.com/hoppworks/rhai.git` `main`, and eventual fork-only branch consolidation. Never write to public upstream; no release/deployment. Verification strict; own pushes and coordinator merges automatic. Current worktree/branch: `task/all-tickets-environment-recovery`.

## Current step
F23 attempt-01 evidence and source-pin correction integrated at fork `main` `055a068`; only the macOS sys-policy slice is closed. At the same source, combined Darwin sys/net coexistence target passed 1/1 in attempt-02 after reusing attempt-01 locked metadata and expected RED. Combined review returned READY on 2026-10-08. Private runtime is absent. Plan limits acceptance to this slice.

## Next action
The READY review and stale-state correction are now recorded; `state.py check` reports 57 lines/935 words. Commit only `docs/sys-package-plan.md` and this state as lowercase `hoppworks`, push to private fork `main` and read back exact head. Then map the smallest still-open native Darwin process/lifecycle criterion to existing source, tests and proof before choosing any new build. Reuse only evidence with matching inputs/assertions/environment.

## Goal
Close every original ticket criterion with strict applicable proof and review at the tested revision, integrate to authorized fork `main`, then finish fork-only remote consolidation.

## Done when
All original and crosswalk criteria in plan §§6.7–6.8 have applicable strict evidence at integrated revision; only then consolidate authorized fork branches so remote `main` is the sole branch. No public-upstream write, release or deployment.

## Steps
1. Close remaining B/C/D/F criteria in smallest coherent packages; done only at applicable strict proof.
2. Review each coherent package once, integrate to private fork main and read back exact head; done when review and proof apply to integrated revision.
3. Classify and consolidate only safely mergeable fork branches; done when verified remote main is sole branch.

## Done steps
Package A is accepted only for Linux/Rust 1.77.2. X22, X24, X29, X30 and X14/X16/X17 have scoped Linux proof at plan rows. Package E metadata/docs integrated at `04d9a797...`; Darwin alias assertions at `ad980d80...`. F23 sys-policy slice integrated at `055a068`; combined sys/net coexistence now has READY-reviewed Darwin proof at the same source.

## Accepted evidence
F23: `.scratch/all-tickets/darwin-f23-sys-policy-20261008/attempt-01/`; native Darwin arm64/macOS 27.0.1, Rust 1.93.0, `testing-environ,sys`, lock SHA-256 `4ff0a7de...`; expected-RED at permission assertion and restored 26/26, including five root-path cases. Closes only macOS sys-policy slice. Combined sys/net: `.scratch/all-tickets/combined-sys-net-darwin-20261008/attempt-01/` and `attempt-02/`; exact source `055a068...`, identical manifest/test pins, same Rust/lock, `testing-environ,sys,net`; expected RED reached host-byte readback assertion, green exact target passed 1/1. Real Engine, host file readback, independent TCP peer byte readback and typed errors. Review READY; exact private scopes absent. See plan §§6.6–6.9.

## Open escalations
Ticket-03 B lifecycle/cancellation; C Darwin process/lifecycle, TCP and feature matrix; D Windows custody/native behavior; F integrated compatibility/release matrix; full F23 remaining platform/feature rows. Preserve original P/E/F/X/R and local contracts in plan §§6.7–6.8. Do not reopen exhausted Workhorse/Windows routes or touch another Session's guest.

## Retained resources
Re-use Package E metadata/docs and Darwin process/example proof only while source, assertions, lock, toolchain and environment pins match. Reuse combined sys/net metadata and expected RED; no repeat of the green target without invalidation. Attempt private build/runtime scopes were exported then removed. For future builds use unique `~/.local/share/agent-builds/rhai/<session>` and `tools/run_scoped.py`, set TMPDIR and actual outputs/caches under `AGENT_RUNTIME_DIR`; measure capacity on actual filesystems first. Clean only exact owned inactive scopes. Preserve modified `tests/fixtures/sys_process_shared_child_contract.rs`, X29 proof, foreign Tauron work, and all unrelated `.scratch` artifacts; do not stage them or stop processes.

## Cause history
F23 attempts 01/02 stopped before assertions on incomplete offline Cargo caches (`rustyline`, then `zerocopy 0.8.61`); attempt 03 was online locked correction with accepted inner gates and parent-shell status caveat. Combined sys/net attempt-01 used ~23s: metadata/compile passed, intentional RED reached the host-readback assertion, then wrapper rejected Rust's separate `FAILED` line before green. This was validator formatting, not product failure; exact scope cleaned. Attempt-02 reused valid RED/metadata and spent ~22s for green 1/1; no repeat justified. Package B had three Workhorse `SESSION_SCOPE` pre-assertion stops and its one follow-up is consumed. Package E native3 had three pre-assertion failures and exhausted follow-up; attempts 11/12 provide reusable Darwin proof; 12a stopped before Cargo. Never reset history or retry without changed inputs/new diagnosis.

## Budgets
F23 attempts 01/02 ~29.4s total, attempt 03 ~45s; current F23 run bounded at 900s with actual time in logs. Package E known active work ~482s plus unmeasured setup; attempts 11/12 ~48/25s and 12a stopped before Cargo. Combined sys/net ~23s + ~22s. Older aggregates unavailable. Agent-selected ceilings are not user hard caps; preserve consumption and do not invent totals.

## Rule state
Central Agent-Skills HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2` contains requested Main `35ba734135a64100b891f422d4ced9d76795ab57`. Coordinator reloaded global/project AGENTS and relevant campaign, e2e-proof, tdd, ocr-delegate and resource rules. Combined reviewer independently confirmed the same HEAD/revision and READY. No active subagents; prior completed reviewers' loaded revisions are recorded in retained history. Other Sessions' rule state is unknown. Project `docs/agents/resource-lifecycle.md` is absent; use project AGENTS fallback.

## History
`campaign/scripts/state.py rewrite` archives each replaced state under `.scratch/all-tickets/journal/`; detailed prior approvals, evidence, cause and budget history remain there. Plan §§6.6–6.9 retain proof applicability and original requirement coverage. Side-branch `2f795ece...` is not an ancestor of integrated fork main; its old lock/source pins are not validated here and it is not the current route.
- Previous state: journal/state-c59b0860a80842f7ae245a2697ca855d.md

## Retrospective
The prepared sys/net contract on side branch `2f795ece...` is not an ancestor of integrated fork main and its old pins are unvalidated here; do not revive that route. The direct current-source target produced one scoped coexistence proof; no repeated build or wrapper layer is justified without invalidating evidence.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic
