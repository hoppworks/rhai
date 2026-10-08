# Coordinator state: all-tickets

## Mode
Continue already-authorized implementation and strict acceptance; do not create or reactivate a Goal.

## Decisions
Atomic commits use lowercase `hoppworks`. Pushes and coordinator merges are authorized only to private fork `https://github.com/hoppworks/rhai.git` `main`; never write to public upstream. No release/deployment. Verification strict; automatic push/merge selected. Current worktree/branch `task/all-tickets-environment-recovery`, source HEAD `846d4ff0aa2aa1ded90dfe761a515f3f301979ec`. Preserve unrelated dirty shared-child fixture, X29 edits/evidence, foreign Tauron work and processes.

## Current step
Darwin X24 native row is accepted by combined independent review and recorded in `.scratch/all-tickets/x24-darwin-trywait-20261008/attempt-02/proof.md` and `docs/sys-package-plan.md`. No source/test change was needed. Package C and the wider X24 matrix remain open.

## Next action
Inventory existing Darwin process/lifecycle tests and accepted native evidence against the still-open Package C criteria; select the smallest real gap and reuse applicable proof before proposing any new run. Do not rerun X24 unless relevant inputs/assertions/environment are invalidated.

## Goal
Close every original ticket criterion with applicable strict proof and combined review at the integrated revision, then complete authorized fork-only remote consolidation.

## Done when
All original/crosswalk criteria in plan §§6.7–6.8 have applicable proof; after integration, safely consolidate authorized fork branches so remote `main` is sole branch. No public-upstream write, release or deployment.

## Steps
1. Close remaining B/C/D/F criteria in coherent packages with real applicable proof.
2. Review once per coherent package, integrate to private fork main and read back exact head.
3. Consolidate only branches proven safely mergeable; verify only remote main remains.

## Done steps
Package A: Linux/Rust 1.77.2 only. X22, X24, X29, X30 and X14/X16/X17 have scoped Linux evidence at plan rows. Package E metadata/docs integrated at `04d9a797...`; Darwin alias assertions at `ad980d80...`. F23 sys-policy slice integrated at `055a068...`; default-feature Darwin sys/net coexistence accepted at that source. X24 now also has one accepted Darwin row at `846d4ff...`.

## Accepted evidence
F23 `.scratch/all-tickets/darwin-f23-sys-policy-20261008/attempt-01/`: Darwin arm64/macOS 27.0.1, Rust 1.93.0, `testing-environ,sys`, RED plus 26/26 target tests; only macOS sys-policy slice. Combined sys/net `.scratch/all-tickets/combined-sys-net-darwin-20261008/{attempt-01,attempt-02}/`: source `055a068...`, same manifest/test/lock pins, Rust 1.93.0, `testing-environ,sys,net`, Engine file/TCP readbacks and typed errors; READY review; only default-feature coexistence slice. X24 Darwin `.scratch/all-tickets/x24-darwin-trywait-20261008/attempt-02/proof.md`: native public Engine, live child, pending unit, direct terminal result, cached wait, independent ESRCH; expected RED and GREEN; READY review. Adds only Darwin arm64/macOS 27.0.1, Rust 1.93.0, `testing-environ,sys`. Other platforms/features/MSRV and remaining Ticket 03 behavior remain open.

## Open work
Ticket 03 B lifecycle/cancellation; C remaining Darwin process/lifecycle, TCP and feature rows; D Windows custody/native behavior; F integrated compatibility/release matrix; remaining F23 platform/feature rows. Preserve local contracts and original P/E/F/X/R requirements in plan §§6.7–6.8. Do not reopen exhausted Workhorse/Windows paths or drive another Session's guest. Release readiness is not publishing/deploy authorization.

## Open escalations
No active escalation. Cause 25 is closed by READY review and the record-only acceptance update; answer path is `.scratch/all-tickets/escalations/25-darwin-x24-libtest-output-shape.answer.md`. Cause 11 has its separate historical answer and is not reopened.

## Retained resources
X24 attempts 01/02 export raw logs, source/lock/toolchain pins, validator outputs and exact scope-cleanup receipts; private scopes were removed. Build time recorded: 14.44+0.06s RED and 19.95+0.03s GREEN; 34.48s reported phases, not total active work or peak. No build is retained. Reuse prior artifacts only while source, assertions, lock, toolchain and environment match. Future builds require unique `~/.local/share/agent-builds/rhai/<session>`, canonical `tools/run_scoped.py`, scoped `TMPDIR` plus outputs/caches under `AGENT_RUNTIME_DIR`, and actual-filesystem capacity measurement. Clean only exact owned inactive disposable resources.

## Cause history
X24 cause `darwin-x24-libtest-output-shape`: attempt-01 reached deliberate `wait_code 0→7` assertion RED, Cargo 101; wrapper status 1 because it expected same-line test/status tokens. Attempt-02 exact target was green, Cargo 0 / 1 passed, with same-PID lifecycle markers and ESRCH; wrapper again returned 1 from the same parser assumption. Both `scope-cleanup.txt` receipts say PASS. These are two record-validator failures, not product/correction failures. Escalation 25 review READY and one record-only follow-up completed; answer `.scratch/all-tickets/escalations/25-darwin-x24-libtest-output-shape.answer.md` accepts the named Darwin row and distinguishes cached-wait sensitivity from direct try-wait assertions. Preserve erroneous `test-result.json` unchanged; proof supersedes only its classification. No third build or parser wrapper. Earlier split-stream cause 11 remains a separate answered issue; do not reopen it.

## Budgets
X24's two launches used 34.48s of recorded compile/test phases; total active time and peaks unknown. Expert #25 completed before its 30-minute planning checkpoint; exact time/cost/tokens unknown. F23 attempts 01/02 stopped before assertions on incomplete offline Cargo caches (`rustyline`, then `zerocopy 0.8.61`); attempt 03 was online locked correction. Combined sys/net used about 23s RED and 22s GREEN. Package B had three Workhorse `SESSION_SCOPE` pre-assertion stops; follow-up consumed. Package E native3 had three pre-assertion failures and exhausted follow-up; attempts 11/12 provide reusable Darwin proof and 12a stopped before Cargo. Preserve all original counts and accepted evidence; never reset history. Older aggregate active time unavailable.

## Rule state
User supplied Main `35ba734135a64100b891f422d4ced9d76795ab57`; central repo HEAD is descendant `0e846bfc577a51bd1a98a5606966aecda40320c2`, with no relevant uncommitted rule changes. Coordinator read global/project AGENTS plus campaign, e2e-proof, tdd, ocr-delegate and resource rules. Fresh Expert independently read the specified commit, current descendant and current applicable rules; the applicable later change removes fixed heavy-run counts only. No other active subagents; other Sessions' loaded revisions are unknown. Project `docs/agents/resource-lifecycle.md` is absent; project AGENTS fallback applies.

## History
`campaign/scripts/state.py rewrite` archives replaced state under `.scratch/all-tickets/journal/`. Prior approvals, limits, criteria, proof and cause history remain there; detailed criterion map is plan §§6.7–6.8 and prior states. Side-branch `2f795ece...` is not an ancestor of integrated fork main and its old source/lock pins are invalid for this route.
- Previous state: journal/state-d85ccd4c90904a87a6242cbef6e3b877.md

## Retrospective
The Darwin target passed; two wrapper failures shared one same-line output assumption. Preserve raw outcomes and correct the derivative classification once. Do not rebuild or add a parser layer for this record-only issue.

## Workflow choices
- Verification: strict
- Push: automatic
- Merge: automatic
