# Combined sys/net acceptance state

## Goal
Prove same-Engine sys+net registration, real filesystem and TCP send/receive, typed structured errors, and the bounded accepted feature matrix on native macOS. Source authority: `.scratch/all-tickets/briefs/combined-package-proof.md`; release contract: `.scratch/all-tickets/release-proposal.md`.

## Done when
New combined integration contract passes with an independently observed wrong-expectation RED; all feasible matrix rows have exact commands/logs and applicable suite statuses; evidence and exact runner cleanup are read back; atomic commit has author and committer exactly `hoppworks`.

## Steps
1. Add combined public-Engine integration test. Done when wrong expectation fails for host readback and restored expected value passes on actual filesystem and TCP peer.
2. Run package matrix serially under scoped runner. Done when each applicable target and feature combination has recorded status or exact uncompleted rows.
3. Export proof, verify cleanup and commit. Done when proof paths exist, runtime is absent, and commit identity matches.

## Current step
1-2. Test authored; source review identified package APIs. No test invocation yet.

## Decisions and constraints
- Fixed window 15:36:00–16:06:00 UTC inclusive; immutable handoff by 15:59 UTC. No extension.
- Scoped runner `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py`, copied source, private Cargo home/target, jobs 2, serial test commands, <=2 GiB sampled storage, <=16 owned handles, <=900 sec per invocation.
- No push or merge; author and committer name exactly lowercase `hoppworks`; configured email retained.
- Existing unchanged proof reused by reference: `.scratch/all-tickets/combined-sys-proof.md`, `.scratch/tcp-connect/proof.md`. No process, Linux, Windows, MSRV, or no_object sys compatibility claim.

## Done steps
- Source instruction/release/evidence review: this state file and references above.

## Launch history
- None yet.

## Next action
Review test source, then run one bounded scoped baseline including false-green control.

## Open escalations
- None.

## Current step update
- First launch on 15:38 UTC failed at compile time due a typo in the new test helper's nested generic delimiter and incorrect assumption that `Dynamic::try_cast` returns `Result`; all repeated feature rows reproduced the same harness compile errors, so invocation was interrupted. No behavior ran. Runner cleanup was confirmed by absence of exact runtime path. Cause is one local harness authoring error; correction applied once in `tests/combined_sys_net.rs`.
- No implementation correction or infrastructure recovery has failed.

## Launch history update
- Launch 1, 2026-09-30 15:38 UTC: `run_scoped.py --timeout 900 -- bash .scratch/combined-package-proof/run-matrix.sh`; compile failed on harness source in every started feature row. Interrupted after common cause established. Exact private runtime absent afterwards.

## Next action update
Run only the targeted false-green control followed by target GREEN under a scoped runner with private source/Cargo directories. If that closes the integration contract, proceed to remaining matrix within deadline.

## Launch history update
- Launch 2, 15:41 UTC: targeted scoped control and GREEN attempt. The test compiled, but the peer accepted socket remained nonblocking on this host; peer `read_exact` returned `WouldBlock`, and script read timed out. Control was correctly rejected because the intended readback assertion was not reached. No package defect is inferred. Correction explicitly switches the accepted peer stream to blocking before setting finite I/O timeouts.

## Next action update
Run the serial full matrix in one scoped invocation (timeout 900s), with storage sampling; false-green control now also requires the exact intended assertion. Commit at the latest 15:58 UTC if matrix evidence is partial or complete.

## Launch history update
- Launch 3, 15:42 UTC: corrected scoped serial matrix. False-green failed at intended independent host-file readback. Rows 1-7 passed. A 10-second storage sample reached 2,675,624 KiB, exceeding the 2-GiB cap, so the invocation was interrupted before row 8 completed. Exact runtime absence confirmed. This is a resource-cap breach; actual peak is unmeasured. State was preserved in logs. No process coverage is claimed.

## Next action update
Run only the missing `f32_float` full target row in its own fresh scoped runtime, sample every 5 seconds, and stop if storage approaches 2 GiB. Reuse the unchanged false-green proof and rows 1-7 by reference. Then package proof and commit by 15:59 UTC.

## Current step update
- Rows 1-7 passed all eight targets. The false-green control failed at the deliberately wrong independent filesystem readback, and the baseline restored expectation passed.
- Row 8 (`f32_float`) was interrupted under the first matrix run. Its captured partial output shows the combined test and four net targets passed; no full-row acceptance. A separately started runtime was immediately interrupted on the parent Coordinator's instruction and had no test results.
- Hard cap was exceeded: max 10-second sample 2,675,624 KiB. Actual peak not measured. No more launches permitted. Exact matrix runtime and immediate f32 runtime paths were confirmed absent.

## Done steps update
- Combined integration behavior and false-green control: closed for the seven completed feature combinations; exact evidence is in `proof.md` and logs.
- Matrix: partial only; `f32_float` remains incomplete.

## Decisions and constraints update
- Parent Coordinator directed stopping all further launches after the sampled hard-cap breach. No more tests/builds or scoped launches are authorized for this package task. Preserve partial evidence and report the cap breach. Do not claim release acceptance.

## Next action update
Prepare atomic local commit of test and proof artifacts for root review. No push or merge.


## Newly approved release-verifier follow-up (2026-09-30)
- Owner explicitly approved the combined package described in `/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/briefs/release-verifier-followup.md`. Actual dispatch 18:53:29 UTC; hard finish 19:23:29 UTC including root review; execution cutoff 19:18:29 UTC. Preserve prior cause/budget totals above; this package gets exactly one invocation, at most 600 seconds, and reserves five minutes for root review.
- Only the missing native macOS `f32_float` full eight-target row runs in the private runtime. Reuse the unchanged test source from `c2c76a1fac0ed48c5f7bae189c1eb0569ff7d756` and the seven completed profiles plus wrong-value control/restored baseline from the previous incomplete evidence package. No other feature row/control reruns, product changes, public upstream writes, or merge.
- Harness-only repair: preserve PID/start identity rows from the exact original `ps` snapshots (no second query to recapture sampled PIDs). Whole-runtime `du -sk` may have one immediate bounded rescan only if every diagnostic names a disappeared file beneath this invocation's exact private Cargo target. Record both raw observations; all other first errors and every second error stop. One-second samples remain sampled maxima, not continuous peak enforcement.
- Use the same private archive, generated/exported lock, Cargo home/target/tmp, jobs=2, debug=0, incremental=0, serial tests, 1.5-GiB sampled guard, 2-GiB hard limit and <=16 owned descendants. Independent post-launch readback must cover exact runtime, process group and all known PID/start identities; missing identities fail proof.
- The prior package stopped at 18:17:36 UTC with status89 when a transient Cargo-object ENOENT caused the fail-closed sampler to stop; this was an infrastructure measurement failure, not a product assertion failure. Its cleanup readback found runtime/group/launcher/runner absent but finalizer status1 due 81 unavailable distinct sampled PID start identities. Preserve that failure and raw report. This newly approved package is one fresh slot, not a reset of the earlier attempt.
- Current action: source-only measurement-harness correction and immutable root review. No new invocation until root accepts the gate; first unexpected result, cutoff or cap stops, with no rerun.

## Retrospective
The first test compile caught a harness generic-type typo. The first runtime then exposed inherited nonblocking mode on the accepted peer socket; setting it explicitly to blocking made the bounded exchange deterministic. The false-green control verified the independent host readback assertion. The matrix harness did not enforce a storage stop automatically, so it overshot the 2-GiB sampled cap; the invocation was stopped when observed and exact cleanup was checked. The f32 requirement remains open under the hard stop.


## Source review correction (2026-09-30)
- Root review identified that source commit `679e7d7f` used TCP `read_string`, which performs a single read and can return a shorter chunk than the full peer reply.
- Updated the script to `read_to_end_string` with the same cap. The independent peer writes its response and then closes when its thread returns, so the script read reaches EOF.
- This is a source-only correction. Static formatting and diff checks are permitted; builds, tests, or other runtime launches remain stopped by the storage-cap decision.
- Prior seven-row/control logs apply only to source `679e7d7f`; corrected source is unverified and must not be presented as accepted. A separately authorized bounded follow-up is required for that assertion.


## Approved bounded follow-up package (2026-09-30)
- Owner authorized `.scratch/all-tickets/briefs/combined-package-followup.md`; actual dispatch 17:54:18 UTC, hard end 18:24:18 UTC inclusive of root review, execution cutoff 18:19:18 UTC. Source preparation/review handoff target 17:59:18 UTC. One private scoped invocation only, max 600 seconds, after root reviews the immutable commit.
- Source-only changes allowed: corrected same-Engine integration and assertion-sensitive control matching; no production edits. Preserve original sampled-cap breach (2,675,624 KiB, peak unmeasured) and retained fragmented-TCP correction. Prior seven individual target rows remain reusable where unchanged; corrected combined contract requires all eight profiles, plus the full eight-target f32 profile. One wrong fresh-file expected value must exit 101 at the exact test and exact actual/expected values, followed by restored baseline.
- Invocation limits: private complete archive, private Cargo home/target/tmp, jobs=2, dev/test debug=0, incremental=0, serial tests, one-second whole-runtime samples including staging/archive, terminate the scoped process group at sampled 1.5 GiB, 2 GiB hard cap, <=16 owned descendants plus fixture handles within the approved bound, no runtime retry. Stop on assertion/resource/deadline failure. Absolute UTC timestamps and per-case logs exported outside runtime.
- Reuse the accepted native macOS proof driver's `ps` ancestry, process identity, fail-closed sampler and post-wrapper cleanup-readback patterns at `/Users/hoppworks/projects/rhai-all-tickets/.scratch/macos-sys-release-proof.py` and `finalize-macos-sys-release-custody.py`. Use a private generated lockfile, export it immediately and at completion, and pass `--locked` to every test. Launcher computes min(600 seconds, remaining absolute deadline); the driver checks the same UTC deadline before and during every case.
- Require readback of exact launcher/run_scoped/supervisor group, every recorded PID/start identity, runtime absence after cleanup, archive/lock identity and exported case outcomes. The independent finalizer runs only after the launcher exits, so its own PID does not contaminate the cleanup readback. Root review of immutable source/proof gate precedes the sole launch. No push/merge/production change.
- Source gate `1be277f22ef3f1ceb459386c5634b431fd54d7c1` was reviewed and released by root. One invocation completed successfully; see the final result below.

## Authorized f32 completion result (2026-09-30)
- Exactly one owner-approved invocation ran 19:09:11–19:09:34Z through immutable gate `1be277f22ef3f1ceb459386c5634b431fd54d7c1`; execution cutoff remained 19:18:29Z and hard finish 19:23:29Z. No retry or source change occurred after gate review.
- Missing `f32_float` row over all eight targets passed, status 0, all 96 tests. Logs/statuses and environment are in `.scratch/combined-package-proof/f32-followup/`; archive source is `c2c76a1fac0ed48c5f7bae189c1eb0569ff7d756`, archive SHA-256 `559fde41f983b87ec2a23feeebc4a71637101e78072c19b15d80f20d01536b5d`.
- Root independently verified all eight logs/counts; finalizer status 0: 49 known PID/start rows, zero unavailable, all identities absent; launcher and run_scoped absent; PGID 91223 empty; exact runtime absent. Sampled maximum 313,856 KiB; maximum sampled owned descendants 7. Generated/final lock SHA-256 `4aa2e32287d33184c12e98c7a86a17574dbf3a2361c968c76e9611bfd4396cc3`.
- Prior wrong-value control/restored baseline and prior completed non-f32 matrix profiles remain in `.scratch/combined-package-proof/followup/README.md`; the prior f32 partial remains explicitly incomplete. This run closes only the f32 row. No non-UTF8 filesystem claim on macOS due to the recorded EILSEQ fixture limitation.
- Current action: generate/check the complete raw evidence manifest, commit local proof/state/evidence, then hand immutable revision and paths to root for final review. No additional runtime work is authorized or needed.
