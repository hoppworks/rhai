# Coordinator state: all-tickets

## Mode
Continue authorized implementation and strict acceptance; do not create/reactivate a Goal.

## Decisions
- Verification strict; push/merge automatic when explicitly eligible. Current user authorization: atomically commit and push to private fork `origin` (`https://github.com/hoppworks/rhai.git`) `main`; never public upstream. No release/deployment.
- Commit author exactly `hoppworks`, configured email `daniel@hoppworks.de`. Worktree/branch `task/all-tickets-environment-recovery`; final remote only `main`.
- Preserve dirty X29/fixture work, all untracked evidence/journals, and foreign Sessions/processes. This docs commit stages only state and plan.

## Current step
X26–X28 Darwin crosswalk is reviewed READY; compact state and plan, then commit/push only those two files. HEAD `d3281a779edac9666bd43bc094c872a6a41806f3`.

## Next action
Inspect exact X29 Darwin source, prior logs and evidence for applicability; run only the smallest uncovered strict Darwin row if no usable proof exists. Preserve dirty fixture. One combined independent review for this coherent package. Before push, recheck status and remote ancestry; push `HEAD:main` once and verify exact head and sole branch.

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 with applicable strict proof and combined review at the integrated revision.

## Done when
All original criteria have valid applicable proof, authorized changes are integrated on fork `main`, and readback confirms `main` is the only remote branch. No public-original writes, release or deployment.

## Steps
1. Close remaining B/C/D/F and ticket 03 criteria in coherent acceptance packages, reusing valid proof.
2. Review each coherent package once; integrate and read back exact fork-main head.
3. Confirm only remote `main` remains; preserve unrelated branches/work.

## Done steps
- A Linux/Rust 1.77.2 first-cause semantics accepted at `d4fc2890…`; E metadata/docs `04d9a797…`, Darwin alias `ad980d80…`.
- F23/sys-net coexistence and X22–X25 named Darwin rows reviewed; refs in plan.
- X26 repeat-kill and direct X27 final-drop: expected RED/GREEN and combined review READY at arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`.
- X27 managed final-clone-drop and X28 direct/managed `kill_on_drop=false`: historical e5/macOS 27.0 logs; reviewer confirmed relevant X28 logic/tests/helpers applicable through d3281a7. No fresh 27.0.1 claim.

## Accepted evidence
Full requirements/crosswalk in `docs/sys-package-plan.md` §§6.7–6.8. X26/X27 proof `.scratch/all-tickets/darwin-x26-x27-20261008/proof.md`; X26–X28 combined review `/tmp/darwin-x26-x28-crosswalk-review-20261008.md`. X29 Linux proof `.scratch/all-tickets/x29-script-throw-20261007-9aec531ea61d42359544757b363f2422/proof.md`; Darwin row not yet accepted. X30 Linux row accepted. Other OS/feature/MSRV criteria remain open.

## Retained resources
X25–X27 scoped runtimes cleaned with process absence recorded. Preserve remaining evidence and resources until own identity/inactivity proven. New runs: unique `~/.local/share/agent-builds/rhai/<session-id>/`, scoped `TMPDIR`, `tools/run_scoped.py`, outputs/caches under `AGENT_RUNTIME_DIR`, measure actual filesystem capacity. No global cleanup or foreign process interruption.

## Cause history
- B: three Workhorse `SESSION_SCOPE` pre-assertion stops; one follow-up consumed, zero Rust assertions. Do not retry that path/use native110.
- E native3: three pre-assertion failures, follow-up exhausted; Darwin attempts 11/12 reusable, 12a stopped before Cargo.
- F23 attempts 01/02 dependency stops before assertions; 03 passed online. No repeat absent invalidation.
- X22/X24 intended RED/GREEN valid; wrapper status-1 was post-Cargo libtest-format validation, independently reviewed.
- X25 intended RED 101/restored GREEN passed; outer timeout bound lacked raw launcher transcript. X26/X27 runner could not write outer `runner.exit-code` because `status` is reserved; Cargo, hashes, restore and cleanup/readbacks are recorded. No rerun justified.
- Detailed causes, approvals and limits preserved in archived states and plan §§6.7–6.8.

## Open escalations
None. Closed X24 cause 25 answer: `.scratch/all-tickets/escalations/25-darwin-x24-libtest-output-shape.answer.md`.

## Budgets
Known elapsed: X22 75.10s; X24 34.48s; X23 41.284s; Darwin sys/net ~45s; X25 RED 35.47s + GREEN 0.78s; X26/X27 shared duration in proof. Historical B/E/F23 counts/limits unchanged. Aggregate time, peak resources and cost/tokens unknown when not recorded; never reset counts.

## History
Central Agent-Skills HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`, includes requested Main `35ba734135a64100b891f422d4ced9d76795ab57`, no relevant uncommitted changes. Global, project `AGENTS.md`, campaign and e2e-proof reread. Resource-lifecycle project doc absent. X26–X28 reviewer loaded current rules; no agents active. Other Sessions' loaded revision unknown. Previous states/journals and detailed proof refs retained under `.scratch/all-tickets/journal/` and plan §§6.7–6.8.
- Previous state: journal/state-c58be6b6132c4108b560a17132134849.md

## Retrospective
X26/X27 shared one scoped RED/GREEN build. Reused applicable historical X28 proof; no redundant full-suite run, wrapper, or process restart.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic
