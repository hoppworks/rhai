# Coordinator state: all tickets

## Mode
Authorized implementation, strict verification, and private-fork main integration for `docs/sys-package-plan.md` §§6.7–6.8. Do not create or reactivate a Goal.

## Workflow choices
- Verification: strict
- Push: automatic (authorized integrated work to private `origin/main` only)
- Merge: automatic (same fork only; no public upstream)

## Decisions
- Preserve fork history and leave only remote `main`. Commit author/committer name must be exactly `hoppworks`; retain configured email. No deployment or release.
- Reloaded the user-designated Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57`, global rules, project `AGENTS.md`, and relevant campaign, e2e-proof, resource-lifecycle and repo-reconcile rules. Local central HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2` contains Main; later central changes remove its inherited fixed heavy-run convention, consistent with the current global instructions. Review agents are complete and were notified to reload before any future action; none is active.

## Current step
X36 attempt10 remains reviewed READY only for arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`, kernel-generated `setpgid` denial. Ticket 03 X14/X16/X17 are partially accepted for Linux x86_64 and Darwin arm64/macOS 27.0.1, both Rust/Cargo 1.93.0 with `testing-environ,sys`. Darwin's three public-Engine tests passed; the combined review returned READY after confirming assertion-control reuse, exact cleanup, no live child PIDs and five valid hashes. Proof and plan crosswalk name only these rows. Private `origin/main` is at `471cf2698dce1571c6e875c093c2cd2c9ffd6093` pending this package push.

## Next action
Review the exact owned staged diff, commit the accepted Darwin X14/X16/X17 proof/crosswalk/state with committer name `hoppworks`, and push atomically only to private `origin/main`; read back the remote head and confirm `main` remains its sole branch. Then advance an open criterion by reusing applicable existing proof before considering any new build. Preserve all other platform, feature and MSRV gaps. Keep Package B's three infrastructure stops and exhausted post-escalation follow-up; do not rerun its no-primary path or use native110.

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 with applicable proof; preserve the original requirement scope.

## Done when
Every criterion has strict proof and review as applicable; accepted work is on private `origin/main`; remote has only `main`. Preserve foreign, dirty and unmerged local work.

## Steps
1. Map Package B gaps to source/test/proof; keep stopped routes closed.
2. Advance open platform, fault, feature and Ticket03 criteria in coherent acceptance packages; change product code only for demonstrated failures.
3. Reuse valid proof; combine related acceptance and review once; push integrated packages and read back remote state.

## Done steps
- Linux X36 Rust/Cargo 1.77.2 sensitivity/restored test accepted; commit `47035986d03aabe202b749b983973ed256ae0c37` is on private `main`.
- Darwin X36 attempt10 evidence, proof, crosswalk and state committed as `471cf2698dce1571c6e875c093c2cd2c9ffd6093`, authored/committed `hoppworks`; atomic push and remote readback succeeded.
- Attempt10's 16 evidence hashes match; exact PIDs/groups were independently absent; owned runtime/scope were removed. No product source changed.
- Darwin X14/X16/X17 one-command run passed 3/3 on arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`; combined review READY. Five evidence hashes and cleanup/PID readback verified. No product source changed.

## Accepted evidence
- Requirement inventory and open applicability: `docs/sys-package-plan.md` §§6.7–6.8.
- X36 evidence and cause history: `.scratch/all-tickets/x36-managed-scope-setup-20261008/proof.md`, attempts 01–10. Attempt06 immutable archive SHA-256 `ad869e2f338e432a246fec6ce13d102c6b49a5a8c2d062306e98e1eb88601215`; relevant inputs match. Attempt10 supports only its named Darwin kernel-denial row. Other valid proof remains linked in the crosswalk.

## Retained resources
No build output is reusable. Attempt10's exact scope/runtime were removed after export. Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`, was at origin/main 471cf after push. Preserve modified foreign `tests/fixtures/sys_process_shared_child_contract.rs`, other unclassified `.scratch`, dirty/foreign worktrees and active processes. Future runs use `~/.local/share/agent-builds/rhai/<unique-session-id>` as `TMPDIR` for `tools/run_scoped.py`; route real outputs/caches via `AGENT_RUNTIME_DIR` and project flags.

## Cause history
Attempts 01–10 and preparation/product classifications are in X36 `proof.md` and archived states. Attempt08's first launch stopped before Cargo for a missing parent; corrected six-test run passed. Attempts09/10 REDs were intended controls, not product failures. Package B's three pre-assertion infrastructure failures and no-wrapper diagnosis remain in §6.8/escalation history.

## Open escalations
No active escalation. Open criteria remain: Windows X30/X32/X33; additional X34/X35/X37 platform/fault rows; X36 other Darwin faults/platforms/features/MSRVs; uncovered X38 rows; Package B/Ticket03 and other §6.7–6.8 requirements.

## Budgets
Attempts08/09: one 600-second Workhorse run each, two Cargo jobs, observed 20/28 seconds; attempt09 estimated 3 GiB peak. Attempt10: one 600-second Darwin run, one job, 41.36 seconds environment-to-result, 3 GiB estimated additional peak (actual peak unsampled). Earlier consumption remains archived; do not reset. Cost/token totals unknown. No foreign process changed.
Darwin X14/X16/X17: one scoped Cargo invocation, two jobs, 28.31 seconds overall, 25.35 seconds Cargo build/test setup and 0.27 seconds tests; actual peak unsampled. Launch sample: 53% memory free on 32 GiB, 96,307,252 KiB disk free, load 12.47/11.28/10.21, no Cargo/rustc active; one unrelated E2E active. Cost/tokens unknown. No foreign process changed. This review/update adds no build or repeated review.

## History
`state.py rewrite` archives each exact predecessor under `.scratch/all-tickets/journal/`. Detailed attempts, decisions and budgets remain in proof/journal references; this is current state, not an append log.
- Previous state: journal/state-5b54f5be86174d67b588c60ca265c20e.md

## Retrospective
Attempt10 reused the immutable attempt06 source and avoided a redundant six-test group. Review needed no rebuild. No unrelated artifacts were removed because their ownership/activity was unclassified.
