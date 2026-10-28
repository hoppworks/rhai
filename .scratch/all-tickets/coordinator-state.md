# Current Rhai implementation state

## Mode

Implementation active by owner instruction. A–F, Ticket03 and release remain open.

## Decisions

Use current central agent-skills `d6024420` plus applicable local edits and project `AGENTS.md`. Strict public Rhai→Engine→host→OS proof needs independent readback and assertion sensitivity. One combined independent review per coherent package with focused recheck of corrections. Push/merge only to `https://github.com/hoppworks/rhai.git` main, never upstream; author/committer exactly `hoppworks`, configured email, no coauthors/signatures or remote task branches. Preserve foreign work, original VM media, human limits and owned scoped cleanup. No Linear. Choose heavy runs from live capacity. Existing authorization persists; old pending labels do not revoke it. Prefer GPT-6.1 Terra for suitable new agent tasks; Luna rarely.

## Current step

Fork-main includes reviewed Windows X35, POSIX `f32_float`, native Windows Rust/Cargo1.77.2, a combined sys/net case and the Windows `only_i32,no_float` profile. A–F/Ticket03/release remain open.

## Next action

Run the next missing Windows feature/fault row under bounded custody, using the retained source/toolchain where applicable. Bind the exact linker/SDK files for full release; preserve accepted rows.

## Goal

Implement all accepted Rhai sys/net/process/file/release ticket requirements on the fork.

## Done when

Every P/E/F/X/R and six-ticket criterion in `docs/sys-package-plan.md` has applicable strict real-OS proof, independent review, source/feature/MSRV binding, safe cleanup and fork-main integration; production release remains a separate owner decision.

## Steps

Close Windows Managed faults and argument/IO gaps; finish native three-OS feature/MSRV matrix; integrate verified slices on fork main. Details remain in `docs/sys-package-plan.md`.

## Done steps

Fork main contains accepted Windows sys policy/env/fs, net targets, Direct process/input/lifecycle, X32/X33 argument/search and bounded Managed cases. Earlier Linux/Darwin/core/WASM/MSRV rows retain listed scopes.

## Accepted evidence

MacOS27.2 arm64/Rust1.77.2 `no_index,sync,metadata`: six first-run suites and combined wrong101; corrected `/usr/bin/true` test passed process/report 2/2+8/8 and exit-code wrong101. Combined review PASS: `.scratch/all-tickets/release-matrix-20261028/proof.md`.

MacOS27.2 arm64/Rust1.77.2 `testing-environ,sys,net,only_i32,no_float`: 11 targets compiled, combined wrong101, restored 135/0/1ignored, independent combined review PASS. Only named behaviors accepted; `.scratch/all-tickets/release-matrix-20261028/macos-onlyi32-nofloat-proof.md`.

Workhorse Linux7.2.11 x86_64/Rust1.77.2 matching integer-only profile: pinned source/lock, compile0, combined wrong101, restored 135/0/2ignored, combined review PASS; owned stage/scope retired. `.scratch/all-tickets/release-matrix-20261028/linux-onlyi32-nofloat-proof.md`.

MacOS27.2 arm64/Rust1.77.2 combined `metadata,serde`: 11 targets 160/0/1ignored, host wrong101; targeted Dynamic JSON wrong101/restored Serde25/0. Source binding, cleanup, combined review/focused recheck PASS: `.scratch/all-tickets/release-matrix-20261028/macos-metadata-serde-proof.md`.

Workhorse Linux7.2.11 x86_64/Rust1.77.2 combined `metadata,serde`: 12 targets compiled, host/Serde wrong101 each, restored 193/0/3ignored, combined review PASS. `.scratch/all-tickets/release-matrix-20261028/linux-metadata-serde-proof.md`.

POSIX Rust1.77.2 combined `unchecked`: macOS 151/0/1ignored, Linux 160/0/3ignored across 11 targets, four wrong101 controls each. Review corrected a one-shot TCP cap oracle; EOF read plus widened-cap RED101 and restored `net_reads`7/7 passed on both. Combined review PASS: `.scratch/all-tickets/release-matrix-20261028/posix-unchecked-proof.md`.

POSIX Rust1.77.2 combined `f32_float`: macOS and Linux three intended wrong101 assertions each; restored 11-target suites 159/0/1ignored and 167/0/3ignored. Mac attempt01 parser stopped after valid RED; same-source attempt02 passed GREEN. Combined review PASS: `.scratch/all-tickets/release-matrix-20261028/posix-f32-float-proof.md`.

Attempts36–39 exposed false Job closure; attempts50–58 covered batch injection, membership, retry, lifecycle and CWD search. Attempt59 fixed a missed exact-child fallback after permanent Job refusal: wrong101/GREEN0, 299 refusals, owner retained. Attempt60 reused identical source for final-drop wrong101/101 and GREEN0 with parent/worker/sentinel readbacks. Combined review READY. Actual OS faults, other features/toolchains and release remain open. Detailed source, lock and causes: Windows `attempt59/` and `attempt60/` proof folders.

Attempt61 freezes current base plus X33 test (`160a37ef...`, same lock) and passes native Windows Managed child-PATH-over-parent-CWD wrong101/GREEN0, 31/31 suite and independent child executable readback. Observer Driver0 in 104.824s, 202 frames/14 hash-checked files, eight valid journal transitions through REMOVED; own host stage/ISO retired, guest outer scope retained. Combined independent review PASS. Proof: `.scratch/all-tickets/windows-rhai-native-20261028/attempt61/`.

Attempt62 freezes `edfca43e` plus one test-only X35 run-closure control (`ec2e7eac...`, same lock). Native Windows1.93 `testing-environ,sys,metadata`: run descendant, run sentinel and spawn/wait closure wrong101 each, restored run/spawn GREEN0 with exact process-handle and sentinel readbacks. Driver0/85.052s, 208 frames/16 hash-checked files, eight valid journal transitions through REMOVED. Own host ISO/stage removed and original sdc restored; guest outer scope retained. Combined review PASS with a documentation precision correction. Proof: `.scratch/all-tickets/windows-rhai-native-20261028/attempt62/`.

Attempt63 DirectChild timed out before assertion; captured-handle inheritance remains a possible cause. Attempt64 clears/reads back fixture handle inheritance and passes wrong101/GREEN0 with parent/worker readback and valid custody journal. Review PASS: Windows `attempt63/` and `attempt64/` proof folders.

Windows MSRV bootstrap attempt04: native Driver0, exact Rust/Cargo1.77.2, 36 ordered COM1 frames/11 hash-checked originals, eight CRC-valid journal records through REMOVED, independent retained-binary hashes and runtime absence. Combined review PASS; current-source Cargo release tests open. `.scratch/all-tickets/windows-rhai-native-20261028/msrv-bootstrap-20261028/proof.md`.

Windows1.77.2 combined `testing-environ,sys,net`: same committed source/lock, native compile, host-file wrong101/GREEN0, independent TCP/file readback, Driver0, 203 frames/15 hash-checked files, eight valid journal records and combined review PASS. Own scope/ISO/stage retired; SDK and other rows open. `.scratch/all-tickets/windows-rhai-native-20261028/release-msrv-20261028/proof.md`.

Windows1.77.2 `only_i32,no_float`: HEAD701 plus Windows test overlay, host-file wrong101, restored 12-target suite124/0/0ignored including 31 native process tests; two targets ran zero. Driver0/156.02s, rotated COM1 old/new segments reassembled to219 frames/15 hash-checked files, eight valid journal records. Review PASS; own scope/ISO/stage retired. Windows Kit Lib10.0.26100.0 inventoried; exact linker unknown. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/onlyi32-nofloat-attempt01/proof.md`.

## Retained resources

Workhorse VM `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`: original sdc restored, foreign sdb untouched; own bootstrap ISOs/stage and successful guest verification scope retired. Retained guest `C:\Users\RhaiTest\.local\share\agent-builds\rhai\n-a7e54f39\toolchain-home`: Rhai coordinator, Windows1.77.2 release gate, 423,724,103 bytes, ceiling2GiB, expiry 2026-11-01 00:00 UTC; no quota. Public native BuildOnly expires 2026-10-30 12:00 UTC. Guest evidence scopes52–64 remain; old36/48 need exact retirement. Details in proof.

## Cause history

Attempt18 false timeout unresolved; attempt26 expired before RED/GREEN; attempts36–39 exposed false Job closure; attempt48 expected RED incorrectly; attempt50 showed batch injection. Review corrected retry in attempts55–56. Attempt57 Driver parser sought wrong log; attempt58 corrected it. Attempt59 fixed shared-deadline fallback; attempt60 final-drop passed. MSRV bootstrap: attempt01 absent F: preflight; attempt02 `findstr` exit77 plus null parser; attempt03 invalid `run-verify` custody root; attempt04 passed with retained toolchain. Earlier causes/limits in proof folders/history.

## Open escalations

Managed closure requires exact handles and fail-closed completion; retry corrections were rechecked. No pending approval or outcome decision.

## Budgets

Windows attempts52–62 each used one bounded Driver; detailed consumption remains in original proof folders. No budget reset. Future limits derive from actual capacity. Release-profile attempts used finite owned scopes; their timings and cleanup are in their proof folders.

## History

`docs/sys-package-plan.md`, `.scratch/all-tickets/coordinator-history-20261015.md` and original attempt proof folders retain decisions, prior state, causes and accepted evidence.
- Prior snapshots: `journal/state-*.md`.

## Retrospective

Pending campaign completion. Available per-run times are above; aggregate role cost/token usage is unknown.
