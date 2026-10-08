# Coordinator state: all-tickets

## Mode
Continue already authorized implementation and strict acceptance. Do not create or reactivate a Goal.

## Decisions
- Verification: strict. Push and coordinator merge: automatic for this campaign.
- Atomic commits/integration authorized only on private fork `https://github.com/hoppworks/rhai.git`; remote `main` is the sole final branch. Never write to public upstream. No release/deployment.
- Commit author name exactly `hoppworks`; preserve configured email. Worktree: `task/all-tickets-environment-recovery`; do not create a remote task branch.
- Preserve dirty X29/fixture changes, all evidence/journals, other Sessions' work and processes. Stage only intended files for this package.

## Current step
Ticket 03 X22 has a reviewed Darwin row at source `5f13da04b6ad4636c44cc0bb910c7d9fcccb71e7`, arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`. Public `Engine::eval::<Map>` invokes registered Rhai `run` and real `/bin/sh`; assertions cover SIGKILL, unit exit code, complete output, host-file PID readback and independent ESRCH. Cargo RED 101 (9 vs 10), GREEN 0 (1 passed); combined independent review READY. Evidence: `.scratch/all-tickets/darwin-signal-x22-20261008/{proof.md,review.md}`.

## Next action
Commit the X22 plan/state update atomically and fast-forward private fork `main`; verify the exact remote head. Then map the smallest open Ticket 03 Darwin lifecycle criterion against existing tests/proof and choose one real-OS acceptance that advances it. Reuse unchanged X22/X23/X24, F23 and sys/net proof; no repeated build without invalidation or an uncovered criterion.

## Goal
Close every original criterion in plan §§6.7–6.8 with applicable strict proof and combined review at the integrated revision.

## Done when
All original criteria have valid proof, verified changes are integrated on authorized fork `main`, and remote `main` is the sole branch. Never write public upstream, release or deploy.

## Steps
1. Close remaining B/C/D/F criteria in coherent packages; preserve every partial status and original requirement.
2. One combined independent review per coherent package; integrate and read back exact fork-main head.
3. Consolidate only safely mergeable fork branches; verify `main` alone remains.

## Done steps
- Package A: committed-child first-cause semantics, Linux/Rust 1.77.2 only; six controls and READY at `d4fc2890…`.
- Package E metadata/docs at `04d9a797…`; Darwin alias assertions at `ad980d80…`.
- F23 Darwin `sys_policy`, Darwin default sys/net, X23 Darwin example and X24 Darwin try-wait named rows have combined READY reviews (details in plan §§6.3, 6.7–6.8).
- X22 Linux x86_64/Rust 1.93.0 and 1.77.2 rows; Darwin row at source above. These remain partial outside named profiles.
- X29 is accepted only for named Linux/Rust 1.93.0 and 1.77.2 rows; dirty fixture/proof work remains outside this package and must be preserved.

## Accepted evidence
Full criterion crosswalk is `docs/sys-package-plan.md` §§6.7–6.8. Reuse evidence only while relevant source, assertions, lock, toolchain and environment remain applicable. X22 proof/review: `.scratch/all-tickets/darwin-signal-x22-20261008/`; X23/X24/F23/sys-net proof and exact limits are in the plan and referenced proof records.

## Open work
B: stdin/cached wait/kill/capture/owner/sentinel/reaping gaps; Workhorse SESSION_SCOPE route stopped. C: remaining Darwin lifecycle, TCP and feature rows plus other OS/MSRV rows. D: Windows custody/native behavior. F: integrated core/MSRV/platform/feature compatibility matrix and unsupported combinations. Preserve all criteria. Release readiness grants no publishing/deployment permission.

## Open escalations
None active. X24 cause 25 closed by READY review. X22's combined review accepted the named Darwin row; no follow-up build is justified.

## Retained resources
No X22/X23 build remains; proofs confirm private runtime and owned TMPDIR cleanup. Future builds use unique `~/.local/share/agent-builds/rhai/<session>`, `tools/run_scoped.py`, scoped TMPDIR and Cargo outputs/caches under `AGENT_RUNTIME_DIR`, with actual-filesystem capacity checks. Clean only proven owned inactive disposable resources. Project `docs/agents/resource-lifecycle.md` is absent; project `AGENTS.md` supplies the available project-specific route.

## Cause history
- B: three Workhorse `SESSION_SCOPE` pre-assertion infrastructure stops; one follow-up consumed, zero Rust assertions. Do not retry that path or use native110.
- E native3: three pre-assertion failures and exhausted follow-up. Darwin attempts 11/12 provide reusable proof; 12a stopped before Cargo.
- F23 attempts 01/02 stopped before assertions on unavailable dependencies; attempt 03 passed online. No repeat absent invalidation.
- X24 Darwin: expected RED and GREEN valid; two wrapper status-1 results were libtest output-shape checks after Cargo. No third build.
- X22 Darwin: same classes of outer-validator formatting errors; independent review confirmed raw Cargo outputs/readbacks. No third build.

## Budgets
Known Cargo/run time: X22 compile/test phases 36.25s + 38.85s = 75.10s; X24 compile/test 34.48s; X23 scoped run 41.284s; Darwin sys/net RED/GREEN about 23s + 22s. Expert #25 remained within its 30-minute planning checkpoint. Total active time, peak resources and exact cost/tokens are unknown. Existing B/E/F23 counts and limits remain as recorded in archived states and plan; no hard limit is raised/reset.

## Rule state
Required Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57` is an ancestor of central HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`; no relevant uncommitted rule changes. Coordinator and completed X22 reviewer re-read current global/project/campaign/E2E rules; reviewer confirmed the revision. No agents are active; other Sessions' rule states are unknown.

## History
`campaign/scripts/state.py rewrite` archives replaced states under `.scratch/all-tickets/journal/`. Previous decisions, limits and causes remain there and in plan §§6.7–6.8. Previous state: `journal/state-f37e1b5106b44fbda13eec8a94e583a7.md`.
- Previous state: journal/state-97eecb3b82fb4c9e9855fb56ed3dc831.md

## Retrospective
X22 passed intended RED/GREEN; two outer validators misread multiline libtest output. The accepted proof is reused; plan/state updated once; no extra wrapper or build.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic
