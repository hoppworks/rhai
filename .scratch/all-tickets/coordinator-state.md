# Current Rhai implementation state

## Mode

Implementation active by owner instruction. A–F, Ticket03 and release remain open.

## Decisions

Use central agent-skills `d6024420` plus local edits and project `AGENTS.md`. Require public Rhai→Engine→host→OS proof, independent readback, assertion sensitivity and one combined review per package. Push/merge only to `https://github.com/hoppworks/rhai.git` main, never upstream; author/committer `hoppworks`, configured email, no coauthors/signatures or task branches. Preserve foreign work, original VM media, human limits and owned cleanup. No Linear. Choose heavy runs from live capacity; prior authorization persists. Prefer Terra; Luna rarely.

## Current step

Fork-main includes reviewed Windows X35, POSIX `f32_float`, native Windows1.77.2 sys/net, `only_i32,no_float`, `metadata,serde`, `unchecked` and `f32_float` profiles. A–F/Ticket03/release remain open.

## Next action

Linker path/hash proved in attempt01; attempt02 did not retain `/LINKREPROFULLPATHRSP` output. Before another Cargo build, run one small supervised native linker control with pre-cleanup response-file readback and execution marker. Then bind exact SDK paths/hashes. Preserve accepted rows.

## Goal

Implement all accepted Rhai sys/net/process/file/release ticket requirements on the fork.

## Done when

Every P/E/F/X/R and six-ticket criterion in `docs/sys-package-plan.md` has applicable strict real-OS proof, independent review, source/feature/MSRV binding, safe cleanup and fork-main integration; production release remains a separate owner decision.

## Steps

Close Windows Managed faults and argument/IO gaps; finish native three-OS feature/MSRV matrix; integrate verified slices on fork main. Details remain in `docs/sys-package-plan.md`.

## Done steps

Fork main contains accepted Windows sys policy/env/fs, net targets, Direct process/input/lifecycle, X32/X33 argument/search and bounded Managed cases. Earlier Linux/Darwin/core/WASM/MSRV rows retain listed scopes.

## Accepted evidence

MacOS27.2/Rust1.77.2 `no_index,sync,metadata`: six suites, combined wrong101; corrected process/report2/2+8/8 and exit-code wrong101. Review PASS: `.scratch/all-tickets/release-matrix-20261028/proof.md`.

MacOS27.2/Rust1.77.2 `only_i32,no_float`: 11 targets, wrong101, suite135/0/1, review PASS; named cases only. `.scratch/all-tickets/release-matrix-20261028/macos-onlyi32-nofloat-proof.md`.

Linux7.2.11/Rust1.77.2 `only_i32,no_float`: wrong101, suite135/0/2, review PASS, own scope retired. `.scratch/all-tickets/release-matrix-20261028/linux-onlyi32-nofloat-proof.md`.

MacOS27.2/Rust1.77.2 `metadata,serde`: suite160/0/1, host/JSON wrong101, Serde25/0, review PASS. `.scratch/all-tickets/release-matrix-20261028/macos-metadata-serde-proof.md`.

Linux7.2.11/Rust1.77.2 `metadata,serde`: suite193/0/3, host/Serde wrong101, review PASS. `.scratch/all-tickets/release-matrix-20261028/linux-metadata-serde-proof.md`.

POSIX Rust1.77.2 `unchecked`: macOS151/0/1, Linux160/0/3, wrong101 controls and corrected TCP cap oracle, review PASS. `.scratch/all-tickets/release-matrix-20261028/posix-unchecked-proof.md`.

POSIX Rust1.77.2 `f32_float`: wrong101 controls; macOS159/0/1, Linux167/0/3, review PASS. `.scratch/all-tickets/release-matrix-20261028/posix-f32-float-proof.md`.

Attempts36–39 exposed false Job closure; 50–58 covered batch, membership, retry and lifecycle. Attempt59 fixed exact-child fallback after 299 Job refusals; attempt60 verified final-drop/sentinel readbacks. Review READY; OS faults/release open. Details: Windows `attempt59/`, `attempt60/`.

Attempt61: native Windows Managed X33 PATH precedence wrong101/GREEN0, child executable readback, Driver0, original export/custody and combined review PASS; guest outer scope retained. Proof: Windows `attempt61/`.

Attempt62: native Windows1.93 X35 run/spawn closure, three wrong101 controls and restored GREEN0, exact process/sentinel readbacks, Driver0, original export/custody and combined review PASS. Guest scope retained; host media restored. Proof: Windows `attempt62/`.

Attempt63 DirectChild timed out before assertion; captured-handle inheritance remains a possible cause. Attempt64 clears/reads back fixture handle inheritance and passes wrong101/GREEN0 with parent/worker readback and valid custody journal. Review PASS: Windows `attempt63/` and `attempt64/` proof folders.

Windows MSRV bootstrap attempt04: native Driver0, exact Rust/Cargo1.77.2, 36 ordered COM1 frames/11 hash-checked originals, eight CRC-valid journal records through REMOVED, independent retained-binary hashes and runtime absence. Combined review PASS; current-source Cargo release tests open. `.scratch/all-tickets/windows-rhai-native-20261028/msrv-bootstrap-20261028/proof.md`.

Windows1.77.2 combined `testing-environ,sys,net`: same committed source/lock, native compile, host-file wrong101/GREEN0, independent TCP/file readback, Driver0, 203 frames/15 hash-checked files, eight valid journal records and combined review PASS. Own scope/ISO/stage retired; SDK and other rows open. `.scratch/all-tickets/windows-rhai-native-20261028/release-msrv-20261028/proof.md`.

Windows1.77.2 `only_i32,no_float`: HEAD701 plus test overlay, host-file wrong101, suite124/0/0, process31; two targets zero. Driver0/156s, 219 frames/15 files, journal8, review PASS; owned resources retired. Kit Lib10.0.26100.0 inventory. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/onlyi32-nofloat-attempt01/proof.md`.

Windows1.77.2 `metadata,serde`: HEADb98 source/lock, host/JSON wrong101, suite153/0/0, process32. Driver0/116s, 225 frames/16 files, journal8, review PASS; owned resources retired, original sdc restored. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/metadata-serde-attempt01/proof.md`.

Windows1.77.2 `unchecked`: HEAD26bf source/lock, host/cap wrong101, widened-cap0, suite121/0/0. Driver0/146s, 255 frames/17 files, journal8, review PASS; owned resources retired, original sdc restored. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/unchecked-attempt01/proof.md`.

Windows1.77.2 `f32_float`: HEAD eea5 source/lock, host/f32 timeout wrong101, suite126/0/0. Driver0/106s, 223 frames/16 files, journal8, review PASS; owned resources retired, original sdc restored. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/f32-float-attempt01/proof.md`.

Windows1.77.2 SDK-link attempt01: HEAD9ff selected source/lock, native `cargo rustc --print=link-args` exited0; trace names MSVC14.44.35207 `link.exe`, post-run guest hash `A364AF80...`; `/VERBOSE:LIB` yielded no resolved SDK paths. Traced binary differs from host-file wrong101/GREEN0 control binary. Driver0/164.90s, 217 frames/15 checked files, journal8/8, exact guest/host cleanup; combined review PASS only for diagnostic. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/sdk-link-trace-attempt01/proof.md`.
Windows1.77.2 SDK-link attempt02: installed linker lists `/LINKREPROFULLPATHRSP`; Cargo rustc exited0 and printed absolute option, but retained response file absent. Observer accepted=false; Driver0/148.87s, 218 frames/15 files, journal8, exact guest/host cleanup. Combined review: no SDK acceptance; cause unconfirmed. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/sdk-link-trace-attempt02/proof.md`.

## Retained resources

Workhorse VM `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`: original sdc restored, foreign sdb untouched; own bootstrap ISOs/stage and guest scope retired. Retained guest `C:\Users\RhaiTest\.local\share\agent-builds\rhai\n-a7e54f39\toolchain-home`: Rhai coordinator, Windows1.77.2 release gate, 423,724,103 bytes, ceiling2GiB, expiry 2026-11-01 00:00 UTC; no quota. Public native BuildOnly expires 2026-10-30 12:00 UTC. Guest scopes52–64 remain; old36/48 need exact retirement. Details in proof.

## Cause history

Attempt18 false timeout unresolved; attempt26 expired before RED/GREEN; attempts36–39 exposed false Job closure; attempt48 expected RED incorrectly; attempt50 showed batch injection. Review corrected retry in attempts55–56. Attempt57 Driver parser sought wrong log; attempt58 corrected it. Attempt59 fixed shared-deadline fallback; attempt60 final-drop passed. MSRV bootstrap: attempt01 absent F: preflight; attempt02 `findstr` exit77 plus null parser; attempt03 invalid `run-verify` custody root; attempt04 passed with retained toolchain. SDK-link attempts01–02: no verbose resolution output, then no retained RSP despite printed option; cause unconfirmed, exact SDK unknown. Earlier causes/limits in proof folders/history.

## Open escalations

Managed closure requires exact handles and fail-closed completion; retry corrections were rechecked. No pending approval or outcome decision.

## Budgets

Windows attempts52–62 each used one bounded Driver; detailed consumption remains in original proof folders. No budget reset. Future limits derive from actual capacity. Release-profile attempts used finite owned scopes; their timings and cleanup are in their proof folders.

## History

`docs/sys-package-plan.md`, `.scratch/all-tickets/coordinator-history-20261015.md` and original attempt proof folders retain decisions, prior state, causes and accepted evidence.
- Prior snapshots: `journal/state-*.md`.

## Retrospective

Pending campaign completion. Available per-run times are above; aggregate role cost/token usage is unknown.
