# Coordinator state: all-tickets

## Mode
Continue the user's already-authorized implementation under strict acceptance. Do not create/reactivate a Goal. Preserve unrelated work and foreign resources.

## Decisions
- User authorized implementation, atomic commits/pushes and eventual consolidation to only fork `main` at `https://github.com/hoppworks/rhai.git`; never write to public upstream.
- Commit author/committer name must be lowercase `hoppworks`; preserve configured email; no co-author trailers.
- Requirements/evidence crosswalk: `docs/sys-package-plan.md` §§6, 6.7. Backend strict proof uses public Engine → real OS → independent readback; UI is inapplicable.
- Keep dirty `tests/net_metadata.rs`, `tests/sys_policy.rs`, unrelated fixture formatting and other evidence out of this package.
- Agent-Skills Main `0e846bfc577a51bd1a98a5606966aecda40320c2` contains requested `35ba734135a64100b891f422d4ced9d76795ab57`. Global/project hashes `7a0f59e7…` / `06b73a9d…`; campaign, e2e-proof, tdd and ocr-delegate unchanged. Combined reviewer returned READY under this same revision. Refresh was sent to previously involved idle MSRV agents; no new work is assigned.

## Current step
X22 attempt-03 is accepted only for Workhorse Linux x86_64, Rust/Cargo 1.77.2, `testing-environ,sys`; together with existing attempt-02 it covers named Linux 1.93.0 and 1.77.2 rows. Combined review is READY. Other Unix and feature rows remain open.

## Next action
Map the remaining §6.7 rows to valid proof. First read-only candidate: X24 Linux x86_64/Rust 1.77.2. Verify its attempt-03 frozen source/test block and Cargo.lock against current inputs, and confirm the existing 1.93.0 sensitivity applies. If exact identity holds, prepare one focused Workhorse run after fresh resource admission; do not rerun X22. Preserve B/E stopped routes.

## Goal
Implement all approved local stdlib tickets and release-gate criteria.

## Done when
Every approved criterion has applicable strict proof and review, changes are verified on fork `main`, and final remote cleanup leaves only `main`; no public upstream write.

## Steps
1. Record and atomically push the reviewed X22 Linux partial acceptance to fork `main`.
2. Advance one coherent uncovered criterion/package at a time using valid proof and the smallest real acceptance route; retain all partial-scope labels.
3. Verify fork `main`; remove remote branches only after approved work is integrated and verified.

## Done steps
- X29 corrected real-child challenge passed expected RED and Linux x86_64 Rust/Cargo 1.93.0 and 1.77.2 GREEN; combined review READY. Only named Linux rows accepted. Commit `33fcfe2dce717f6df8c4d6f9dec248bce27c1a9b` is pushed/read back at fork `main`, author/committer `hoppworks`.
- X22 attempt-03 passed one focused 1.77.2 real SIGKILL test; signal 9, no timeout, complete output; independent `kill(pid,0)` returned ESRCH. Test block/archive/lock identities matched, all 13 output hashes verified, and the exact owned Workhorse scope was cleaned. Combined review READY; existing 1.93.0 and sensitivity evidence reused.

## Accepted evidence
See `docs/sys-package-plan.md` §6.7 and linked proof files. X22 is partial only for Workhorse Linux x86_64/Rust 1.93.0 and 1.77.2 with `testing-environ,sys`. Other Unix/feature rows remain open.

## Retained resources
No active owned X22 build remains. Shared Rust 1.77.2 toolchain is intact. Exact Workhorse scope `/var/home/workhorse/.local/share/agent-builds/rhai/x22-sigkill-msrv-20261007-7dac936ff957` was removed after export/hash readback; receipt confirms no active process and path absence.

## Cause history
- Package B (`Child.wait`) and Package E (API metadata): each three pre-assertion infrastructure stops, zero assertions, sole Expert follow-up consumed. Do not retry those routes. Details remain in journal/package evidence.
- X29: two earlier setup stops; corrected run expected RED plus two GREEN, zero product assertion failures. Review closed live-child observation gap without rebuild.
- X22 attempt-03: one scoped run, two Cargo jobs, GREEN; no correction retry. Tauron's resources were not modified; its QEMU ended before fresh admission. Authorized coordination message was sent.

## Open escalations
No active escalation. B/E stop decisions and prior Expert/recovery consumption remain binding; changing Session or route name does not reset them.

## Budgets
X22 fresh admission: 32 CPUs, load 0.77/0.70/0.30, 89,788,977,152 available RAM bytes, 663,682,400,256 free disk bytes; reserved 16 GiB each for RAM/disk plus 2 GiB expected peak. Runtime peak 1,267,691,988 bytes. Active elapsed/cost/token totals unavailable; do not infer. Preserve earlier cumulative records in journal.

## History
`state.py rewrite` archives each previous state in `.scratch/all-tickets/journal/`. Earlier approvals, causes, budgets and proofs remain there and under linked package evidence; do not reset.
- Previous state: journal/state-84b8bffb507346d2b136601292682578.md

## Retrospective
One targeted MSRV run completed X22's named Linux row. Existing 1.93.0 and sensitivity proof were valid, so no repeated execution was needed. Hash readback, independent process observation, cleanup and one combined review closed the row.
