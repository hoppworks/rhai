# Coordinator state: all-tickets

## Mode
Continue authorized implementation and strict acceptance; do not create or reactivate a Goal.

## Decisions
The owner authorized atomic commits and pushes to private fork `origin` (`https://github.com/hoppworks/rhai.git`) `main`, and earlier authorized consolidation to only that branch. Never write to public upstream; no release or deployment. Commit author exactly lowercase `hoppworks`, preserving configured email. Verification strict; push/merge automatic only within the authorized fork scope. Preserve the dirty fixture, unrelated scratch evidence/journals, foreign Sessions and processes. Stage only reviewed package files; do not recreate remote task branches.

## Current step
X29 named Darwin row is accepted after combined independent review READY on 2026-10-08. The exact public-Engine/OS process integration test ran on arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`; expected RED=101 and GREEN=0 prove challenge liveness, public `try_wait()==()`, wrong-message rejection and exact-child ESRCH. Reviewer confirmed overlay applicability against committed fixture. Linux x86_64 rows at 1.93.0 and 1.77.2 remain accepted.

## Next action
Finish the X29 proof, crosswalk and this state update; stage only those three files, inspect staged diff, commit atomically and push once to fork `main`. Read back exact head and sole remote branch. Then inspect existing source/logs against open criteria to select the simplest next package with reusable proof before considering a new build.

## Goal
Close every original criterion in `docs/sys-package-plan.md` §§6.7–6.8 with applicable strict proof and combined review at the integrated revision.

## Done when
All original criteria have applicable proof, authorized work is integrated on fork `main`, and readback confirms `main` is the only remote branch. Unverified rows stay open; no public-original writes, release or deployment.

## Steps
1. Close remaining process/API/platform-feature and Ticket 03 criteria in coherent packages, reusing valid proof.
2. Review each coherent package once; integrate and read back exact fork-main head.
3. Verify only remote `main` remains; preserve unrelated branches/work.

## Done steps
A Linux/Rust 1.77.2 first-cause semantics accepted at `d4fc2890…`; E metadata/docs `04d9a797…`; Darwin alias `ad980d80…`; F23/sys-net and named X22–X28 rows as cross-referenced in plan. X29 corrected Linux rows accepted at Rust/Cargo 1.93.0 and 1.77.2. Darwin X29 exact RED/GREEN and combined review READY; only named Darwin row closes.

## Accepted evidence
X29 proof `.scratch/all-tickets/x29-script-throw-20261007-9aec531ea61d42359544757b363f2422/proof.md`; Linux receipts `.scratch/all-tickets/x29-live-gate-20261007-2300z/` and `.scratch/all-tickets/x29-linux-msrv-20261007-c941b397/`; Darwin receipts `.scratch/all-tickets/darwin-x29-20261008/attempt-01/`. Darwin overlay `14a0808a…` applies to committed fixture `1faf45c5…`, confirmed by review; no rerun. X26/X27 proof `.scratch/all-tickets/darwin-x26-x27-20261008/proof.md`; review `/tmp/darwin-x26-x28-crosswalk-review-20261008.md`. Other named reviews and original criteria remain referenced in plan §§6.7–6.8. Public Engine → package → OS with independent readback and meaningful RED is required; no UI layer applies to process integration. Other OS/features/MSRV, Windows X30/X32/X33, X34–X38 gaps and remaining ticket criteria remain open.

## Retained resources
Darwin X29 used `tools/run_scoped.py` with unique scope `~/.local/share/agent-builds/rhai/x29-darwin-20261008-7ae23c07`, private Cargo home/target and TMPDIR. Runner removed private runtime; exact empty scope removed and read back absent. No reusable build remains. Preserve proof and unrelated resources.

## Cause history
B: three Workhorse `SESSION_SCOPE` pre-assertion stops; one follow-up consumed, zero Rust assertions. Do not retry route/use native110. E native3: three pre-assertion failures, follow-up exhausted; Darwin attempts 11/12 reusable, 12a stopped before Cargo. F23 attempts 01/02 dependency stops pre-assertion; 03 passed online. No repeat absent invalidation. X22/X24 wrapper status-1 was post-Cargo libtest-format validation; corrected proof reviewed. X25 outer timeout lacked raw launcher transcript; X26/X27 could not write outer status receipt due reserved name. Existing evidence remains; no rerun justified. X29 old-source gate could accept zombies; corrected fresh challenge + public `try_wait` fixes it. Earlier responder mismatch corrected; Darwin review READY.

## Open escalations
None. Closed X24 cause 25 answer: `.scratch/all-tickets/escalations/25-darwin-x24-libtest-output-shape.answer.md`.

## Budgets
Known Cargo time: X22 75.10s; X23 41.284s; X24 34.48s; Darwin sys/net ~45s; X25 RED 35.47s + GREEN 0.78s; X29 Darwin initial 37.91s + RED 3.06s + incremental 0.73s + GREEN 0.04s, one bounded invocation/one Cargo job. Other peak/process-wide costs and token totals are unknown where unrecorded. Preserve hard limits and cumulative counts in archived states/proof.

## History
Central Agent-Skills HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`; requested Main `35ba734135a64100b891f422d4ced9d76795ab57` is its ancestor. Later campaign/e2e-proof edits remove fixed machine-wide heavy-run counts; use actual capacity and binding limits. No tracked central changes; unrelated untracked `.scratch` files remain. Global, project, campaign, e2e-proof and ocr-delegate rules loaded. All involved reviewers complete and reported current rules; no active subagent needs updating. Other Sessions' loaded revision unknown. Earlier states/journals and details remain in `.scratch/all-tickets/journal/` and plan §§6.7–6.8.
- Previous state: journal/state-d089f3cc25174882bdf13fc5d6d347c5.md
- Previous state: journal/state-bdcd72d1a9704a6e9c186b1461d516b7.md

## Retrospective
Reuse applicable Linux X29 proof and run one uncovered Darwin X29 target. It passed once; review accepted it. No duplicate full-suite run, wrapper, process restart or retry.

## Workflow choices
- Verification: strict
- Push: automatic within explicit private-fork authorization
- Merge: automatic within explicit private-fork authorization
