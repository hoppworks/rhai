# Coordinator state: all-tickets

## Mode
Continue authorized implementation and strict acceptance; do not create/reactivate a Goal.

## Decisions
- Strict verification. Automatic push/coordinator merge selected. Commit and push only to private fork `https://github.com/hoppworks/rhai.git` `main`; never public upstream. No release/deployment.
- Commit author name exactly `hoppworks`; preserve configured email. Current worktree/branch: `task/all-tickets-environment-recovery`; do not create a remote task branch. Remote `main` is the sole final branch.
- Preserve dirty X29/fixture changes, other Sessions' work, all evidence/journals and foreign processes. Stage only intended package files.

## Current step
Ticket 03 / X25 has one READY Darwin row at source `cacbf76f5be82b86f37a8d9f08bd0012f07d90a9`: managed public-Engine spawn → kill → bounded wait; leader/worker/leaf ESRCH, unrelated sentinel survives and is exactly reaped. Profile: arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`. Proof/review: `.scratch/all-tickets/darwin-x25-kill-20261008/{proof.md,review.md}`. No product source changed.

## Next action
Commit the X25 plan and state update atomically with author `hoppworks`, push fast-forward to fork `main`, and read back the exact remote head. Then map X26–X28 against existing shared-child/Darwin proofs, preserving dirty fixture work; run only for a remaining uncovered row.

## Goal
Close every original criterion in plan §§6.7–6.8 with applicable strict proof and combined review at the integrated revision.

## Done when
All original criteria have valid proof, verified changes are integrated on authorized fork `main`, and remote `main` is the sole branch. Never write public upstream, release or deploy.

## Steps
1. Close remaining B/C/D/F criteria in coherent packages without dropping requirements.
2. One combined independent review per coherent package; integrate and read back exact fork-main head.
3. Consolidate only safely mergeable fork branches; verify remote `main` alone remains.

## Done steps
- A: committed-child first-cause semantics, Linux/Rust 1.77.2 only; six controls and READY at `d4fc2890…`.
- E metadata/docs at `04d9a797…`; Darwin alias assertions at `ad980d80…`.
- F23 Darwin policy slice and default Darwin sys/net coexistence have READY reviews at recorded sources.
- X22, X23, X24 and X25 each have reviewed named Darwin rows; full applicability and refs are in plan §6.8. X29 accepted Linux rows remain separate from dirty fixture/proof work.

## Accepted evidence
Full requirement crosswalk: `docs/sys-package-plan.md` §§6.7–6.8. Reuse only while relevant source, assertions, lock, toolchain and environment apply. Package A: plan §6.3. F23/sys-net and X22–X25 proof refs are in the plan and `.scratch/all-tickets/`.

## Retained resources
X25 RED/GREEN shared one scoped build; runtime, target, Cargo home and exact empty session scope were removed and recorded. No X25 process remains. Preserve all other evidence, journals and foreign resources. Future runs use a unique `~/.local/share/agent-builds/rhai/<session>`, scoped `TMPDIR`, `tools/run_scoped.py` and outputs/caches under `AGENT_RUNTIME_DIR`; check actual filesystem capacity. `docs/agents/resource-lifecycle.md` is absent; project `AGENTS.md` governs.

## Cause history
- B: three Workhorse `SESSION_SCOPE` pre-assertion stops; one follow-up consumed, zero Rust assertions. Do not retry that path or use native110.
- E native3: three pre-assertion failures and exhausted follow-up; Darwin attempts 11/12 remain reusable, 12a stopped before Cargo.
- F23 attempts 01/02 stopped before assertions on dependencies; attempt 03 passed online. No repeat absent invalidation.
- X24/X22: intended RED and GREEN valid; wrapper status-1 errors were libtest output-format checks after Cargo, confirmed by independent reviews. No repeat.
- X25: intended RED 101 and restored GREEN 0/1 passed; no product failure. Reviewer noted timeout bound was recorded from invocation because runner transcript is empty; no rerun warranted.

## Open escalations
None active. X24 cause 25 is closed; answer `.scratch/all-tickets/escalations/25-darwin-x24-libtest-output-shape.answer.md`. Earlier causes and limits remain in archived states and plan.

## Budgets
Known run phases: X22 75.10s total; X24 34.48s; X23 41.284s; Darwin sys/net about 45s; X25 RED 35.47s + GREEN 0.78s in one invocation. Historical B/E/F23 counts and limits remain unchanged. Total active time, peak resources and exact cost/tokens are unknown where not recorded; never reset counts.

## History
Previous states, decisions, exact limits and detailed causes are preserved in `.scratch/all-tickets/journal/` and plan §§6.7–6.8. Current installed rule state: central Agent-Skills HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`, containing requested Main `35ba734135a64100b891f422d4ced9d76795ab57`, no relevant uncommitted changes. Current task and X25 reviewer reloaded global/project/campaign/E2E rules. No agents active; other Sessions' rule state is unknown.
- Previous state: journal/state-6448318765cf469da250d779aad0ca4b.md

## Retrospective
X25 used one staged source, one Cargo runtime and one RED/GREEN invocation; the independent review accepted only its named row. No extra wrapper, rebuild, process restart or unrelated cleanup.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic
