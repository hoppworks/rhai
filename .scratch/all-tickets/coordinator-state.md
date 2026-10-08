# Coordinator state: all tickets

## Mode
Authorized implementation, strict verification, and private-fork main integration for `docs/sys-package-plan.md` §§6.7–6.8. Do not create or reactivate a Goal.

## Decisions
- Verification: strict; Push: automatic; Merge: automatic (project `AGENTS.md`). User-authorized repository target is the private `origin/main` only; public upstream is excluded. Preserve the fork's existing history and leave only remote `main`.
- Commit author/committer name must be exactly `hoppworks`; retain configured email. No deployment or release.
- Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57` is an ancestor of central repo HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`. Global, project, campaign, e2e-proof, resource-lifecycle and repo-reconcile rules were reloaded. Active X36 reviewer also confirmed the Main revision before its review; other listed subagents are complete, with no pending work.

## Current step
X36 attempt10 has combined review READY for only Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`, kernel-generated `setpgid` denial. Proof and plan crosswalk now reflect that bounded result. Linux 1.77.2 remains accepted; X36 overall is partial.

## Next action
Fetch private `origin`; verify it is still the authorized fork and inspect `origin/main`. Stage only the owned X36 attempt10 evidence, its proof, the X36 crosswalk row, and this state plus its newly archived predecessor. Review that exact staged diff, make one atomic `hoppworks` commit and push atomically to `origin/main`; read back the exact remote head and verify `main` is the sole remote branch. Then advance the next open acceptance criterion without repeating unaffected proof.

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 at a revision with applicable proof. Preserve the crosswalk's original requirement scope.

## Done when
Every criterion has strict proof and independent review as applicable; own accepted changes are on private `origin/main`; the remote has only `main`. Local consolidation must preserve foreign, dirty and unmerged work.

## Steps
1. Integrate reviewed Darwin X36 kernel-denial evidence as one atomic package; keep other Darwin X36 fault points open.
2. Continue remaining X30–X38, Ticket 03 and §6.7–6.8 requirements in coherent acceptance packages; change product code only for demonstrated product failures.
3. Reuse unchanged applicable proof; review each changed package once; commit/push and read back the private remote.

## Done steps
- Linux X36 Rust/Cargo 1.77.2 expected mutation RED/restored GREEN and readbacks accepted; commit `47035986d03aabe202b749b983973ed256ae0c37` is on private `origin/main`.
- Darwin X36 attempt10 ran once; expected RED=101/restored GREEN=0, independent exact PID/group readback, 16 evidence hashes and exact owned-scope cleanup verified. Combined review READY; no product source changed.
- Last remote reconciliation found only `main`; current fetch/readback is the next action.

## Accepted evidence
- Requirement inventory and remaining applicability: `docs/sys-package-plan.md` §§6.7–6.8.
- X36 evidence and full cause history: `.scratch/all-tickets/x36-managed-scope-setup-20261008/proof.md`, attempts 01–10. Attempt06 source archive SHA-256 `ad869e2f338e432a246fec6ce13d102c6b49a5a8c2d062306e98e1eb88601215`; archived manifest inputs and current `unix.rs` hash match. Attempt10 only supports the named Darwin 1.93.0 kernel-denial row. Other evidence remains linked from the crosswalk; do not infer wider coverage.

## Retained resources
No build output is reusable. Attempt10's exact session scope and private runtime were removed after proof export. Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`, was at `origin/main` 4703598 before integration. Preserve modified foreign fixture `tests/fixtures/sys_process_shared_child_contract.rs`, other unclassified `.scratch` artifacts, dirty/foreign worktrees and active processes. Future runs use `~/.local/share/agent-builds/rhai/<unique-session-id>` as `TMPDIR` for `tools/run_scoped.py`; route real outputs/caches through `AGENT_RUNTIME_DIR` with project flags.

## Cause history
Attempts 01–10, their preparation/product classifications and recovery history are in X36 `proof.md` and archived states. Attempt08 first stopped before Cargo due to a missing parent; its corrected six-test run passed. Attempts09/10 REDs were intended sensitivity controls, not product failures. Package B's three pre-assertion infrastructure failures and no-wrapper diagnosis remain in §6.8/escalation history.

## Open escalations
No active escalation. Open scope remains in the plan: Windows X30/X32/X33; additional X34/X35/X37 platform/fault rows; X36 other Darwin fault points, platforms, feature combinations and MSRVs; uncovered X38 rows; Ticket 03 and remaining §6.7–6.8 criteria.

## Budgets
Attempts08/09 used one 600-second Workhorse invocation each, two Cargo jobs, observed 20/28 seconds; attempt09 estimated 3 GiB peak. Attempt10 used one 600-second Darwin invocation, one Cargo job, 41.36 seconds environment-to-result, estimated 3 GiB additional peak (actual peak unsampled). Earlier campaign consumption remains in history; do not reset it. Token/cost totals are unknown. No foreign process was stopped or changed.

## History
Each `state.py rewrite` archives the exact predecessor under `.scratch/all-tickets/journal/`. This is current state, not an append log. The archive retains prior decisions, proof applicability, causes and budgets.
- Previous state: journal/state-390e5d477305412f868ae52b41f5384e.md

## Retrospective
Attempt10 reused the immutable attempt06 source archive and avoided a redundant six-test group. It produced no product-source changes. The combined review reused execution evidence and required no second build. No unrelated artifact was cleaned because its ownership/activity was not established.
