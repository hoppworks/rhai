# Current Rhai implementation state

## Mode

Implementation active. A–F, Ticket03 and release remain open.

## Decisions

Use agent-skills `d6024420` plus local edits and project `AGENTS.md`. Require real-OS proof, readback, assertion sensitivity and combined review. Push/merge only to `https://github.com/hoppworks/rhai.git` main, never upstream; author/committer `hoppworks`, configured email, no coauthors or task branches. Preserve foreign work and limits. No Linear. Capacity-based heavy runs; prefer Terra.

## Current step

Fork-main includes reviewed Windows X35 and Windows1.77.2 profile slices. Sys/Net package-alone and three-OS `net,no_object` pass at recorded scopes; macOS core1.66 default `--lib` passes, including the reviewed full test after a compiler-dependent LexError size assertion fix; see `release-matrix-20261028/macos-core-166-full/proof.md`. Broad default `sys,net` passes macOS/Linux/Windows 157/165/125. POSIX Sys passes 126/134. Windows Managed kill/timeout/drop/overflow RED/GREEN reviewed; process suite 35/35. A–F/release remain open. Windows cwd is the active open criterion. An uncommitted Rust candidate currently supplies cwd for DirectChild and Managed run, run_raw, and spawn, but no Windows acceptance is claimed. A later API audit found that FILE_SHARE_READ cannot be assumed to block FILE_WRITE_ATTRIBUTES: Microsoft documents attribute requests as outside share-mode checks, and the archived cwd reparse probe successfully changed an open directory in place. The invalid pin-mutation denial assertion has been removed; source comments now state that pins block rename/deletion but not every in-place reparse mutation. The candidate remains unproven for capability/escape safety and is not accepted. The native scoped-runner gate is also open.

## Next action

Resolve the Windows cwd object-binding race and complete the scoped-runner custody gate before any Rhai guest build. The documented CreateProcessW cwd input is a pathname, and the FILE_SHARE_READ pin is not yet proven to prevent the archived in-place reparse mutation. Once a race-safe approach and the runner gate are established, run one bounded native package invocation for the validated cwd-binding approach and public run, run_raw, and spawn contract; prove wrong-expectation RED and restored GREEN, exact child cwd readback, missing-cwd NotFound/no child, outside-root Denied/no child, reparse/escape behavior appropriate to the accepted design, and cleanup. Reuse the pre-change unsupported-cwd RED in cwd-revised-baseline-attempt01/; it does not prove the new candidate. Review the code and resulting evidence together. Nested Managed membership remains open. Windows X13 passed in streams-4m-attempt02/.

## Goal

Implement accepted Rhai sys/net/process/file/release requirements on the fork.

## Done when

Every P/E/F/X/R and six-ticket criterion in `docs/sys-package-plan.md` has real-OS proof, review, source/feature/MSRV binding, cleanup and fork-main integration; production release is separate.

## Steps

Close Windows Managed faults and argument/IO gaps; finish native three-OS feature/MSRV matrix; integrate verified slices on fork main. See `docs/sys-package-plan.md`.

## Done steps

Fork main contains accepted Windows sys policy/env/fs, net, Direct process/input/lifecycle, X32/X33 argument/search and bounded Managed cases. Other rows open.

## Accepted evidence

macOS/Rust1.77.2 `no_index,sync,metadata`: six suites, combined wrong101; corrected process/report2/2+8/8 and exit-code wrong101. Review PASS: `.scratch/all-tickets/release-matrix-20261028/proof.md`.

macOS/Rust1.77.2 `only_i32,no_float`: 11 targets, wrong101, suite135/0/1, review PASS; named cases only. `.scratch/all-tickets/release-matrix-20261028/macos-onlyi32-nofloat-proof.md`.

Linux/Rust1.77.2 `only_i32,no_float`: wrong101, suite135/0/2, review PASS, own scope retired. `.scratch/all-tickets/release-matrix-20261028/linux-onlyi32-nofloat-proof.md`.

macOS/Rust1.77.2 `metadata,serde`: suite160/0/1, host/JSON wrong101, Serde25/0, review PASS. `.scratch/all-tickets/release-matrix-20261028/macos-metadata-serde-proof.md`.

Linux/Rust1.77.2 `metadata,serde`: suite193/0/3, host/Serde wrong101, review PASS. `.scratch/all-tickets/release-matrix-20261028/linux-metadata-serde-proof.md`.

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

Windows1.77.2 `no_index,sync,metadata` combined Engine/sys/net: wrong101/GREEN0, real host file/TCP peer, Driver0/62s, 208 frames/16 files, journal8, review PASS, own resources retired. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/noindex-sync-metadata-attempt01/proof.md`. Linux1.77.2 same profile: 11 targets/102 passed, combined wrong101, outer0, exact scope/stage retired, review PASS. `.scratch/all-tickets/release-matrix-20261028/linux-noindex-sync-metadata-attempt01/proof.md`.
Windows1.77.2 Managed kill/timeout/drop: four intended wrong101, suite32/0/0, OS readbacks, Driver0/154s, 225 frames/19 originals, journal8, review PASS, cleanup. Direct quote calibration reused. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/managed-controls-attempt01/proof.md`. DirectChild early stdin close: wrong101/GREEN0, child readback, Driver0/93s, review PASS, cleanup; `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/stdin-close-attempt01/proof.md`. Managed stdout overflow: wrong101, suite35/0/0, Driver0/107s, review PASS, cleanup; `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/managed-overflow-attempt01/proof.md`.
Windows SDK-link attempts01–04: see plan/proofs.
Windows SDK-link attempt05: native explicit-path probe and RSP PASS, Driver0/journal8, exact cleanup and review. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/sdk-link-trace-attempt05/proof.md`.
Windows SDK-link attempt06: Cargo/RSP export0, 6 Kit+MSVC paths and post-run guest hashes recovered/independently reviewed; Driver2/106.736s, journal4, 378 work files/74 directories, later exact guest/host cleanup. Runner/release/product remain open. `.scratch/all-tickets/windows-rhai-native-20261028/release-matrix-windows-20261028/sdk-link-trace-attempt06/proof.md`.

## Retained resources

Workhorse VM `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`: original sdc restored, foreign sdb untouched; own ISO/stage/scope retired. Retained guest `C:\Users\RhaiTest\.local\share\agent-builds\rhai\n-a7e54f39\toolchain-home`: Windows1.77.2 release gate, 423,724,103 bytes, ceiling2GiB, expiry 2026-11-01 00:00 UTC; Public BuildOnly expires 2026-10-30 12:00 UTC. Guest scopes52–64 remain; old36/48 need exact retirement. Details in proof.

## Cause history

Windows env_remove baseline reproduced Denied. Attempt01 wrong controls reached assertions; unsupported integer wait withheld the suite. Later bounded try_wait passed: env_remove 41/0, no_index scalar 3/0; scoped REDs and reviews PASS. Outer nested Managed membership remains open; own scopes retired. Proof: Windows `env-remove-fix-attempt04/`. Other no_index cases remain open.

Attempt18 timeout unresolved; attempt26 expired before RED/GREEN; attempts36–39 exposed false Job closure; attempt48 expected RED incorrectly; attempt50 showed batch injection. Retry fixed55–56. Attempt57 Driver parser sought wrong log; attempt58 corrected it. Attempt59 fixed fallback; attempt60 final-drop passed. MSRV bootstrap: absent F:, `findstr`/null parser, invalid custody root, then pass. SDK-link: no verbose paths, unretained attempt02 RSP, guard85, `%~dp0` mispath61, control PASS05. Attempt06 Cargo link and SDK selection recovered, but Runner finalization failed before EVIDENCE; cause unproven. Mac net-only attempt01 peer read returned WouldBlock; attempt02 fixed accepted-peer mode. Windows current COM1 rotation was reconstructed. Earlier causes/limits: proofs.

Managed closure requires exact handles and fail-closed completion.

## Budgets

Windows attempts52–62 used bounded Drivers; no budget reset. Windows package-alone: 85.161s/100.847s. Linux net-only/overlay: 13.96s/12.97s; macOS net-only failed 16.3s, passed 17s. Limits, causes and cleanup: proofs.

## History

`docs/sys-package-plan.md`, `.scratch/all-tickets/coordinator-history-20261015.md` and original attempt proof folders retain decisions, prior state, causes and accepted evidence.
- Snapshots: `journal/state-*.md`.

Cost unknown.
