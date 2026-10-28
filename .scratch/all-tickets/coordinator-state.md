# Current Rhai implementation state

## Mode

Implementation active by owner instruction. A–F, Ticket03 and release remain open.

## Decisions

Use current central agent-skills `d6024420` plus applicable local edits and project `AGENTS.md`. Strict public Rhai→Engine→host→OS proof needs independent readback and assertion sensitivity. One combined independent review per coherent package with focused recheck of corrections. Push/merge only to `https://github.com/hoppworks/rhai.git` main, never upstream; author/committer exactly `hoppworks`, configured email, no coauthors/signatures or remote task branches. Preserve foreign work, original VM media, human limits and owned scoped cleanup. No Linear. Choose heavy runs from live capacity. Existing authorization persists; old pending labels do not revoke it. Prefer GPT-6.1 Terra for suitable new agent tasks; Luna rarely.

## Current step

Fork-main includes reviewed Windows X35 and the POSIX combined `f32_float` slice at `59a8754d`. The latter passed native macOS/Linux runs and independent review. A–F/Ticket03/release remain open.

## Next action

Inventory installed toolchains inside the running Workhorse Windows guest through the existing bounded native custody path; determine whether Rust1.77.2 is present before selecting its release gate. Existing Windows proof pins only Rust1.93.0. Retire guest scopes only after identity/inactivity checks.

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

Attempts36–39 exposed false Job closure. Attempts50–58 cover batch injection/fix, exact membership, bounded retry, public Managed lifecycle, parent-CWD resolution, full 31-test Windows process target and assertion controls under their documented bindings. Attempt57 is diagnostic RED only. New attempt59 manifested a real missed exact-child fallback after a permanently refused Job exhausted the shared 30-second deadline. The correction preserves finite Job retry and grants at least five seconds each for exact-child and I/O fallback. Native Windows Rust/Cargo1.93.0, `testing-environ,sys,metadata`, manifest `34686903...`, lock `12084a90...`: synthetic permanent-refusal wrong101/restored GREEN0 with 299 refusals, exact child stopped and retained owner; two neighboring unit tests green. Attempt60 reused byte-identical source and passed public final-drop kill/retain wrong101/101 and GREEN0, with independent parent/worker/sentinel readbacks. Combined Terra review READY for the bounded package. Actual OS faults, live descendants under permanent refusal, other features/toolchains and release remain open. Proof: `.scratch/all-tickets/windows-rhai-native-20261028/attempt59/` and `attempt60/`.

Attempt61 freezes current base plus X33 test (`160a37ef...`, same lock) and passes native Windows Managed child-PATH-over-parent-CWD wrong101/GREEN0, 31/31 suite and independent child executable readback. Observer Driver0 in 104.824s, 202 frames/14 hash-checked files, eight valid journal transitions through REMOVED; own host stage/ISO retired, guest outer scope retained. Combined independent review PASS. Proof: `.scratch/all-tickets/windows-rhai-native-20261028/attempt61/`.

Attempt62 freezes `edfca43e` plus one test-only X35 run-closure control (`ec2e7eac...`, same lock). Native Windows1.93 `testing-environ,sys,metadata`: run descendant, run sentinel and spawn/wait closure wrong101 each, restored run/spawn GREEN0 with exact process-handle and sentinel readbacks. Driver0/85.052s, 208 frames/16 hash-checked files, eight valid journal transitions through REMOVED. Own host ISO/stage removed and original sdc restored; guest outer scope retained. Combined review PASS with a documentation precision correction. Proof: `.scratch/all-tickets/windows-rhai-native-20261028/attempt62/`.

Attempt63 DirectChild timed out before assertion; captured-handle inheritance remains a possible cause. Attempt64 clears/reads back fixture handle inheritance and passes wrong101/GREEN0 with parent/worker readback and valid custody journal. Review PASS: Windows `attempt63/` and `attempt64/` proof folders.

## Retained resources

Workhorse VM `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19` has original sdc restored; foreign sdb untouched. Native public BuildOnly expires 2026-10-30 12:00 UTC. Guest outer evidence scopes from attempts52–64 remain, including `n-c50a944f`/`n-87438574`; exact host stages/ISOs were removed. Prior attempt36/48 guest runtimes require exact evidence-first retirement. Clean only proven owned inactive resources; previous full scope list is in the state history.

## Cause history

Attempt18 false timeout unresolved; attempt26 expired before RED/GREEN; attempts36–39 exposed false Job closure; attempt48 expected RED incorrectly; attempt50 showed batch injection. Review corrected background retry under uncertainty/accounting in attempts55–56. Attempt57 reached product RED but its Driver parser sought the wrong log; attempt58 corrected CWD search and passed strict proof. Attempt59 source review found the shared-deadline bug; the fixed synthetic control and public attempt60 final-drop now pass. Earlier causes and limits remain in original proof folders and `.scratch/all-tickets/coordinator-history-20261015.md`.

## Open escalations

Managed closure requires exact handles and fail-closed completion; retry corrections were rechecked. No pending approval or outcome decision.

## Budgets

Windows attempts52–62 each used one bounded Driver; detailed consumption remains in original proof folders. No budget reset. Future limits derive from actual capacity. Release-profile attempts used finite owned scopes; their timings and cleanup are in their proof folders.

## History

`docs/sys-package-plan.md`, `.scratch/all-tickets/coordinator-history-20261015.md` and original attempt proof folders retain decisions, prior state, causes and accepted evidence.
- Previous state: journal/state-bcabcf9b41cc471697b1ef6f9c7d838d.md
- Previous state: journal/state-36d9d212bc8f4fd9ba8357358d32cbd5.md
- Previous state: journal/state-79ee5a69313a46528355cc548d34cdb5.md
- Previous state: journal/state-ecb05fc1a10645dbbb818b951102673c.md
- Previous state: journal/state-2080b890fbff42e48dc3f2e4c0da76e2.md
- Previous state: journal/state-a7c5e579478b4d88834ca4569117d9ec.md

## Retrospective

Pending campaign completion. Available per-run times are above; aggregate role cost/token usage is unknown.
