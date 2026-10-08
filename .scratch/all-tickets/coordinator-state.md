# Coordinator state: all-tickets

## Mode
Continue the already authorized implementation and strict acceptance. Do not create or reactivate a Goal.

## Decisions
Commit atomically and push only to private fork `origin/main`; never write to public upstream, deploy or release. Fork consolidation target is sole remote `main`. Commit author name exactly lowercase `hoppworks`; preserve configured email. Strict verification. Preserve foreign work and stage only this reviewed package.

## Current step
X36 Linux managed-scope setup failure has a passing named-row result, proof, and combined independent review READY with no blocking findings. The public Rhai `Engine` plus registered `SysPackage` exercised real `/bin/sh` through `run` and `spawn`; injected pre-exec `EPERM` produced no marker, exact PID/group absence and retired reservation. The injection occurs before `setpgid`, so partial OS membership cleanup is not claimed. Its reviewed package is committed locally and awaits push.

## Next action
The reviewed X36 package is committed locally and awaits integration. Atomically push current `HEAD` only to `origin:main`; read back the exact remote head and verify the remote has only `main`. Then choose the next uncovered original criterion in §§6.7–6.8. Do not rerun unaffected checks.

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 with applicable evidence and combined review at an integrated revision.

## Done when
All original criteria have applicable evidence and combined review at an integrated revision; exact private-fork `main` head is read back and the remote has only `main`. Keep partial/open criteria explicit.

## Steps
1. Finish remaining process/API/platform-feature and Ticket 03 criteria in coherent packages, reusing valid proof.
2. Combined independent review per coherent package; integrate to private fork `main`, read back its exact head.
3. Verify only remote `main` remains; preserve unrelated work.

## Done steps
Linux first-cause semantics; E metadata/docs; Darwin alias; F23/sys-net and named X22–X29 slices. X29 Linux Rust 1.93.0/1.77.2 and Darwin 27.0.1 passed expected RED/GREEN and review READY; integrated at `a42d234073d773066b8f9dc7ef8772b9a1073767`. Darwin X38 named assertion-sensitivity row accepted with review READY. X36 named Linux no-fallback/failed-child cleanup subcriterion passed; combined review READY.

## Accepted evidence
X29 `.scratch/all-tickets/x29-script-throw-20261007-9aec531ea61d42359544757b363f2422/proof.md`; X26/X27 `.scratch/all-tickets/darwin-x26-x27-20261008/proof.md`; Linux X38 `.scratch/all-tickets/linux-managed-escaped-pipe-proof.md`; Darwin X38 `.scratch/all-tickets/darwin-x38-20261008/attempt-03/`. X36 attempt 02 inputs/logs/readback/cleanup are under `.scratch/all-tickets/x36-managed-scope-setup-20261008/attempt-02/`; criterion-scoped summary is `.../proof.md`. Reuse only while relevant source, assertions and environment remain unchanged.

## Retained resources
No X36 remote build or scope remains; exact cleanup readback confirms both owned scopes absent and similarly named pre-existing scope preserved. No reusable compiled X36 target. Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`, base/fork main `49ad57a20043a3b22043a59331ba088ae2aa7751` remains active. Preserve foreign dirty fixture `tests/fixtures/sys_process_shared_child_contract.rs` and unrelated scratch.

## Cause history
X36 attempt 01 stopped pre-assertion after 6.9 seconds because a nested test helper omitted `RawFd`; corrected before attempt 02. Attempt 02 passed. No product-failure correction or allowance reset. Earlier causes remain in archived states and `.scratch/all-tickets/journal/`.

## Open escalations
None. Open requirements: Windows X30/X32/X33; X34–X37 platform/fault breadth, including X36 partial-setup cleanup and non-Linux rows; remaining OS, feature and MSRV rows and all other open criteria in §§6.7–6.8.

## Budgets
X36 attempt 02 used one bounded Workhorse `run_scoped.py` invocation (600-second ceiling, two Cargo jobs), baseline GREEN, one intended sensitivity mutation RED (exit 101), restored GREEN, exact PID/group readback. Elapsed total is not captured. Raw results are in the attempt-02 directory. Earlier campaign budgets remain in journal; these are not reset or newly imposed hard caps.

## History
Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57` is included in central checkout HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`; central tracked rules are unchanged, with unrelated untracked `.scratch`. Project `AGENTS.md`, `campaign`, `e2e-proof`, `tdd`, and resource-lifecycle instructions were reread. Other Sessions' installed revision is unknown. The X36 Expert reviewer reread the current rules and returned READY; no reviewer remains active. Any future reviewer must reread changed applicable rules before acting. Applicable project runner is Workhorse `tools/run_scoped.py`, SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`. Previous current states/history are archived in `.scratch/all-tickets/journal/`.
- Previous state: journal/state-da91887d638e453ab62ed41cc06aae87.md
- Previous state: journal/state-c94098dfe79d4cd08fed9d6316f668b3.md
- Previous state: journal/state-8d67d25610df4fe3bfcb414b756e5790.md

## Retrospective
Attempt 01 was a pre-assertion harness failure, not product RED. Attempt 02's intentional mutation RED confirmed assertion sensitivity; restored GREEN proves only the named Linux row. The combined review returned READY; no new test or build is needed for this documentation/state update. Broader X36 remains open. Full elapsed/cost/token totals across roles are unknown.
