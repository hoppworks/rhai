# Coordinator state: all-tickets

## Mode
Continue already authorized implementation and strict acceptance; do not create/reactivate a Goal.

## Decisions
Commit atomically as `hoppworks` (preserve configured email); push only to private fork `origin/main`; never write to public upstream, deploy or release. Keep the fork with only remote `main`. Preserve foreign/unknown work.

## Current step
X36 Linux cleanup after successful `setpgid` is implemented and passed named Workhorse proof at base `eb0aae40c994cba46cf5dbe367dd155e486fa764` plus the `unix.rs` overlay. Review, commit and push are pending. This closes only the named Linux `testing-environ,sys` row before/after setpgid, not X36 or the campaign.

## Next action
Complete one combined independent review of code, plan, proof and attempt-03 evidence under current rules. If READY, run final targeted diff/state checks, atomically commit as `hoppworks`, push only to private `origin/main`, and read back exact head plus sole remote branch.

## Goal
Close every original requirement in `docs/sys-package-plan.md` §§6.7–6.8 with applicable evidence and combined review at an integrated revision.

## Done when
All original criteria have applicable proof; private fork `main` is read back at the integrated head and is the only remote branch. Partial/open criteria remain open.

## Steps
1. Finish coherent process/API/platform/feature criteria, reusing still-valid proof.
2. Review each coherent package once; push to private `main` and verify its head.
3. Confirm only remote `main` remains; preserve unrelated work.

## Done steps
Linux first-cause semantics; E metadata/docs; Darwin alias; F23/sys-net and named X22–X29 slices. X29 Linux Rust 1.93.0/1.77.2 and Darwin 27.0.1 passed named RED/GREEN and review READY at `a42d234073d773066b8f9dc7ef8772b9a1073767`. Darwin X38 named assertion-sensitivity row: review READY. X36 pre-setpgid row: accepted at `eb0aae40c994cba46cf5dbe367dd155e486fa764`. X36 post-setpgid cleanup row: Workhorse attempt-03 expected RED/GREEN and independent readback passed; review pending.

## Accepted evidence
`.scratch/all-tickets/x29-script-throw-20261007-9aec531ea61d42359544757b363f2422/proof.md`; `.scratch/all-tickets/darwin-x26-x27-20261008/proof.md`; `.scratch/all-tickets/linux-managed-escaped-pipe-proof.md`; `.scratch/all-tickets/darwin-x38-20261008/attempt-03/`; `.scratch/all-tickets/x36-managed-scope-setup-20261008/proof.md` and its `attempt-01/`, `attempt-02/`, `attempt-03/` provenance. Crosswalk: `docs/sys-package-plan.md` §6.7.

## Open requirements
Windows X30/X32/X33; X34–X37 remaining platform/fault behavior; other OS, feature and MSRV rows; remaining Ticket 03 and all other open §6.7–6.8 criteria. The crosswalk preserves the full denominator; no requirement is dropped.

## Retained resources
No reusable X36 build. Attempts 02/03 private runtimes and exact scopes are cleaned; attempt-03 cleanup readback is retained. Preserve raw attempts and earlier cause/budget history in `.scratch/all-tickets/journal/`. Current worktree: `.worktrees/all-tickets-environment-recovery`; preserve foreign dirty `tests/fixtures/sys_process_shared_child_contract.rs` and unclassified scratch outputs.

## Cause history
X36 attempt 01 stopped pre-assertion after 6.9 s because a nested helper lacked `RawFd`; harness-only. Attempt 02 expected ignored-error RED passed as designed. Attempt 03 expected setpgid-disabled RED failed at the intended child-PGRP assertion; restored tests passed. No X36 product failure in attempts 02/03. Earlier causes remain in journal.

## Open escalations
None.

## Budgets
Attempt 02 used one bounded Workhorse run (600 s ceiling, two Cargo jobs); exact elapsed/cost/tokens unknown. Attempt 03 used one 600 s bounded `run_scoped.py` invocation, two Cargo jobs, 19.2 s observed end-to-end. Cumulative actual time and cost/tokens remain unknown; preserve prior history.

## History
Central Agent-Skills HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2` contains requested Main `35ba734135a64100b891f422d4ced9d76795ab57`; tracked central files clean; unrelated central `.scratch` preserved. Project `AGENTS.md`, campaign, e2e-proof, tdd and resource lifecycle were reread. Prior completed reviewers confirmed `35ba734`; no other agent was active at the update. The next reviewer must reread applicable rules before action. Fork readback at prior `eb0aae4` showed only `main`. Earlier state versions are in `.scratch/all-tickets/journal/`.
- Previous state: journal/state-83446b48a3d44f3686d95e2dfd226a9a.md

## Retrospective
Expected RED is separate from infrastructure aborts; attempt 01 was infrastructure, attempts 02/03 mutation REDs were expected. Full cumulative elapsed/cost/token totals remain unknown; do not infer them from tool counts or wall time.
