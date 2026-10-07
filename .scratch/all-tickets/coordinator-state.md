# Coordinator state: all-tickets

## Mode
Continue authorized implementation and strict acceptance; do not create/reactivate a Goal.

## Decisions
Owner authorizes atomic commits as lowercase `hoppworks`, pushes/merges to private fork `https://github.com/hoppworks/rhai.git` `main`, and eventual fork-only remote consolidation. Never write to public upstream; no release/deployment. Verification is strict; own pushes and coordinator merges are automatic. Current branch: `task/all-tickets-environment-recovery`.

## Current step
F23 attempt-01 evidence and the corrected source-pin description passed independent review. The current test evidence is in `.scratch/all-tickets/darwin-f23-sys-policy-20261008/attempt-01/`; no test rerun is needed.

## Next action
Atomically commit/push the reviewed F23 plan/state to fork `main` without rerunning tests; verify the exact remote head. Then run the direct Darwin `tests/combined_sys_net.rs::sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors` target with a current source/lock/toolchain freeze and its existing wrong-expectation RED control; scope the claim to sys/net coexistence. Commit `2f795ece...` exists on side branch `task/current-darwin-sys-net-behavior` but is not an ancestor of integrated `main`; its contract/lock are not validated for this checkout, so do not use it as the execution route.

## Goal
Close every original ticket criterion with applicable strict proof/review at the tested revision, integrate to authorized fork `main`, then finish fork-only remote consolidation.

## Done when
All original and crosswalk criteria in plan §§6.7–6.8 have applicable strict evidence at integrated revision; only then safely consolidate authorized fork branches so remote `main` is the sole branch. No public-upstream writes or release/deployment.

## Steps
1. Finish remaining B/C/D/F criteria in coherent packages, reusing valid evidence.
2. Obtain one combined review per package; atomically commit/push to private fork `main` and read back exact head.
3. Classify fork branches and consolidate only exact safe targets after acceptance closes.

## Done steps
Package A accepted only for Linux/Rust 1.77.2. X22, X24, X29, X30 and X14/X16/X17 have scoped Linux proof at plan rows. Package E metadata/docs integrated at `04d9a797...`; two Darwin alias assertions at `ad980d80...`. F23 attempt-01 full sys-policy target now passes; its combined review and integration are pending.

## Accepted evidence
F23 attempt-01: `.scratch/all-tickets/darwin-f23-sys-policy-20261008/attempt-01/`; source is `ad980d80...`, Darwin arm64/macOS 27.0.1, Rust 1.93.0, features `testing-environ,sys`, locked Cargo metadata, lock SHA-256 `4ff0a7de6f504510af64092d446d411b86d95228b23a188b396bd188da367627`. Deliberately wrong outside-root expectation failed at permission assertion; restored `tests/sys_policy.rs` passed 26/26, including five root-path cases. Inner result PASS, `run-scoped.status=0`, exact private scope empty/removed. Closes only macOS F23 sys-policy slice. Attempt-03 alias proof remains valid without rerun while inputs unchanged. Package E attempts 11/12 provide Darwin process/TCP example/readback and metadata assertions in default-float and `no_float`; reusable host peers: `.scratch/tcp-docs-example/proof.md`, `.scratch/file-handle-docs/proof.md`. See plan §§6.6–6.9.

## Retained resources
Preserve modified `tests/fixtures/sys_process_shared_child_contract.rs`, X29 proof, journals and unrelated `.scratch`; do not stage them. Preserve Tauron/other Session work and do not stop processes or use its guest. Attempt-01 proof exported before removing its exact private build/cache/TMPDIR scope. Use unique `~/.local/share/agent-builds/rhai/<session>` with `tools/run_scoped.py` for future owned builds; clean only exact proven owned inactive resources.

## Cause history
F23 attempts 01/02 stopped before assertions on incomplete offline Cargo caches (`rustyline`, then `zerocopy 0.8.61`); attempt 03 was online locked correction, and its parent-shell status-file caveat was accepted with inner gates. Attempt-01 here is justified by remaining root spellings; one scoped target covered sensitivity and restored green. Package B had three Workhorse `SESSION_SCOPE` pre-assertion stops and one consumed follow-up. Package E native3 had three pre-assertion failures and exhausted follow-up; attempts 11/12 provide reusable Darwin proof; 12a stopped before Cargo. Never reset history or repeat without changed inputs/new diagnosis.

## Open escalations
Ticket-03 B lifecycle/cancellation semantics; C Darwin process/lifecycle and sys/net examples/features; D Windows custody/native behavior; F integrated compatibility/release matrix. Full F23 includes other platform/feature rows. Preserve all original P/E/F/X/R and local contract criteria in plan §§6.7–6.8. Do not reopen exhausted Workhorse/Windows routes or touch another Session's guest.

## Budgets
F23 attempts 01/02 consumed ~29.4s total, attempt 03 ~45s, current run bounded at 900s with actual elapsed in attempt logs. Package E known active work ~482s plus unmeasured setup; attempts 11/12 ~48/25s and 12a stopped before Cargo. Older aggregate totals unavailable. These agent-selected ceilings are not user hard caps; retain all consumed work and do not invent totals.

## History
Central Agent-Skills HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2` contains requested Main `35ba734135a64100b891f422d4ced9d76795ab57`. Global/project AGENTS and relevant campaign/e2e-proof/tdd/ocr-delegate/resource rules reloaded. No active subagents; prior reviewers confirmed the same revision. Other Sessions' rule state is unknown. Project `docs/agents/resource-lifecycle.md` absent; use repo AGENTS fallback. Older states and detailed proof/approval/cause records remain in `.scratch/all-tickets/journal/` and plan §§6.6–6.9.
- Previous state: journal/state-63ba03fa74ed49fe9b8293932a6e14e4.md
- Previous state: journal/state-24a42885376a4fa5b756dc3d857df690.md
- Previous state: journal/state-7d2794fea0744795ae9e2586d8af313c.md

## Retrospective
Prepared Darwin sys/net contract pins existing commit `2f795ece...` on an unmerged side branch; it is not an ancestor of current integrated `main` and its old lock/source are not validated for this checkout. Do not treat it as missing or repair its wrapper. Direct current `sys_policy` target produced this F23 slice with one owned scoped build. No new layer or repeated build is justified absent invalidation.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic
