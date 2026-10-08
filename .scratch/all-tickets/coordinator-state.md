# Coordinator state: all-tickets

## Mode
Continue previously authorized strict implementation; do not create/reactivate a Goal.

## Decisions
- Commit author `hoppworks` (lowercase), configured email; push only to private `origin/main`, never public upstream, deploy or release.
- Preserve the fork's sole remote branch `main`, foreign dirty/unclassified work and unrelated evidence.
- Workflow choices: strict verification; automatic push of own commits; coordinator merge after checks.

## Current step
X36 kernel-generated Linux `setpgid` denial and affected setup recheck both pass on Workhorse x86_64, Rust/Cargo 1.97.1, `testing-environ,sys`. Proof and crosswalk now include exact scope, mutation, test and cleanup evidence; X36 remains partial.

## Next action
Run final diff/static checks and one combined independent review of this coherent X36 source/evidence/crosswalk package; then commit and push only its exact files to fork `main`, verify remote head and sole branch, and continue remaining requirements.

## Goal
Close every original requirement in `docs/sys-package-plan.md` §§6.7–6.8 with applicable evidence and combined review at an integrated revision.

## Done when
Every original criterion has applicable proof; fork `main` is read back at the integrated head and remains its only remote branch. Partial/open criteria stay open.

## Steps
1. Complete the current X36 Linux kernel-denial package and integrate it.
2. Continue X34–X37 remaining fault/platform rows and native Windows X30/X32/X33.
3. Close all other open §6.7–6.8 requirements with grouped acceptance and retain platform/feature/MSRV gaps until proved.

## Done steps
- Linux first-cause semantics; E metadata/docs; Darwin alias, F23/sys-net and named X22–X29 slices.
- X29 named Linux Rust 1.93.0/1.77.2 and Darwin rows reviewed READY at `a42d234073d773066b8f9dc7ef8772b9a1073767`.
- X36 pre-setpgid row; X36 pre/post-setpgid cleanup; X36 real fchdir `EBADF` cleanup. Prior accepted heads are `397761661b87e8ab452bb752af16fdc7ca155c85` and `edb197b4df39ab27fcfe00612b6658b9a3f739ab` on private `main`.
- Darwin X38 named assertion-sensitivity row reviewed READY; related evidence retained.

## Accepted evidence
`docs/sys-package-plan.md` §§6.7–6.8; `.scratch/all-tickets/x29-script-throw-20261007-9aec531ea61d42359544757b363f2422/proof.md`; `.scratch/all-tickets/darwin-x26-x27-20261008/proof.md`; `.scratch/all-tickets/linux-managed-escaped-pipe-proof.md`; `.scratch/all-tickets/darwin-x38-20261008/attempt-03/`; `.scratch/all-tickets/x36-managed-scope-setup-20261008/proof.md` and attempts 01–07. Reuse only when source, assertions and environment match.

## Open requirements
Windows X30/X32/X33; X34–X37 remaining platform/fault behavior; other OS, feature and MSRV rows; remaining Ticket 03 and all other open §6.7–6.8 criteria. Original denominator remains unchanged.

## Retained resources
Worktree `.worktrees/all-tickets-environment-recovery`, branch `task/all-tickets-environment-recovery`, base `edb197b4df39ab27fcfe00612b6658b9a3f739ab`. Preserve dirty foreign `tests/fixtures/sys_process_shared_child_contract.rs` and unclassified `.scratch` outputs; stage only this reviewed package. X36 attempt 01–07 evidence is retained after exact remote scopes/private runtimes were removed; no compiled output is reusable or active.

## Cause history
X36 attempt 01 pre-assertion helper import failure; 02 expected ignored-error RED; 03 expected disabled-setpgid RED then GREEN; 04 expected fchdir sensitivity RED then GREEN; 05 narrow changed-source GREEN; 06 expected denial-hook mutation RED then GREEN; 07 six related tests GREEN. Earlier prep failures are recorded in proof and occurred before product assertions/build. Do not count expected RED as product failure or prep stops as acceptance. Detailed earlier causes remain in journal.

## Open escalations
None.

## Budgets
Attempts 02–05: one scoped Workhorse invocation each, 600-second ceiling/two Cargo jobs; 03 elapsed 19.2s; 04/05 compile 15.02s/14.76s. Attempt 06: one scoped invocation, 600s/two jobs; elapsed unknown. Attempt 07: one scoped invocation, 600s/two jobs, elapsed 17s. Cumulative cost/tokens/active work remain unknown; do not infer totals.

## Rules and history
Core and relevant skills were reread for Agent-Skills Main `35ba734135a64100b891f422d4ced9d76795ab57`; central HEAD was `0e846bfc577a51bd1a98a5606966aecda40320c2`, tracked files clean, unrelated central scratch preserved. Project `AGENTS.md`, campaign, tdd, e2e-proof, ocr-delegate and resource-lifecycle rules were loaded. The repo resource-lifecycle detail file is absent; current global rules govern. Existing X36 reviewer read the same rules and found the source candidate READY; no agents are active. The configured email is preserved while commit author follows the explicit lowercase name. Fork `origin` previously read back as sole branch `main`.

## History
Previous current-state version archived separately by `campaign/scripts/state.py rewrite`; earlier cause/budget history remains in `.scratch/all-tickets/journal/`.
- Previous state: journal/state-b48021391cf54955b64261e3fe76d252.md

## Retrospective
X36 uses one source review, one focused mutation/acceptance batch and one helper-affected recheck; attempt 07 was prompted by a shared helper change. Evidence was exported before exact-scope cleanup. No unrelated build, session, foreign dirty file or unclassified output was changed.
