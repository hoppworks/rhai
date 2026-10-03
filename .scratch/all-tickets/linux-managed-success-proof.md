# Native Linux managed success and held-zombie proof

**Status:** ACCEPTED by the same combined reviewer: prompt-success and held-zombie boundaries across four Linux current-MSRV rows. Full process/release tickets remain open.

**Entry point:** Real Rhai script through Engine and registered host process API, in Cargo integration target sys_process.

**Stack exercised:** Public script API -> host managed process owner -> real Linux child/process group, pipes and exit/reaping; independent fixture reaper and outer PIDFD/proc/group readback.

## Inputs and execution

Frozen source003da06421fbd11c26e0c96ab5013416c0939a1d, tests/sys_process.rs SHA e0034cf3a69ccf6107a9dfbc0854c0147ec2d93fdda8acf5ed6b07e683e1dc14, archivef62ea7430f8a92db7210055373f9e96b2d850d3564c4962844c80056b7294d1a, accepted lock2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425. Frozen helper83e84145/stage67e13bdd/collector01068eee/launcher27e1ee59; full hashes in originals and reviewed preparation. Source review and single post-escalation receipt/custody repair READY at linux-managed-success-review.md; two earlier correction failures and escalation14 preserved.

Run96 used private Rust/Cargo1.77.2 x86_64-unknown-linux-gnu on Linux7.2.7-ogc1.1.fc44.x86_64. Stage and launcher commands are original stage.sh/launch.sh. Existing scoped runner uses TMPDIR below /root/.local/share/agent-builds/rhai/linux-managed-success-20261003-7d045f21-96 with actual Cargo/Rust/Python outputs private. No shared service reset.

| Feature row | Exact restored tests | Result |
|---|---|---|
| testing-environ,sys | prompt success and held zombies | 2 passed |
| testing-environ,sys,sync,metadata | same | 2 passed |
| testing-environ,sys,f32_float | same | 2 passed |
| testing-environ,sys,unchecked | same | 2 passed |

Exact names: managed_run_succeeds_after_fixture_reaper_reaps_descendants and managed_run_reports_while_fixture_reaper_holds_stopped_zombies. Three setup commands status0; seven Cargo commands comprised three controls101 and four GREEN0, eight restored exact tests total. Last stdout-only outer summaries confirm two real tests per row, no ignores. Nested fixture stdout is not counted as the outer result.

## Assertion sensitivity and restoration

The first control forces the prompt fixture into known-broken held mode and fails its successful-zero-report assertion. Two after-cleanup controls demand exit7 and false sentinel-at-return respectively, each fails its named assertion. Original stderr/stdout/status files and control-results.json preserve the reasons; these are expected assertion RED, not correction failures. Every overlay restores original source bytes; source-restoration.json records restored=true, exacte003 and error=null before final original rows.

## Independent readback and cleanup

The actual collector REMOTE revalidates complete success/held receipts, disjoint acquired identities, eleven closure files, expected statuses and source restoration, then freshly reads /proc identities and ps groups separately from the test. independent-readback.json records62 fixture PID/start rows,146 owned helper/supervisor/descendant rows,2 launcher rows and13 groups. These are recorded row counts, not a claim of210 unique PID numbers. All210 recorded identities absent and13 groups empty in fresh post-cleanup readback. Prompt success binds code0, complete captures, direct leader absence, exact foreign reaping, live sentinel at API return and its later reaping. Held case retains typed TimedOut closure diagnostic while host is alive, complete captures and stopped zombies before exact fixture cleanup.

All72 original exported files were independently byte-hashed against remote inventory before cleanup. local export and directory inventory verified before exact remote retirement. remote-cleanup.json confirms72files/6dirs removed, stage/scope absent and fresh identity/group absence. Runtime removed by runner. No retained build.

Initial local export with system Python3.9.6 failed at unsupported tarfile.extractall(filter); only the newly created empty owned destination was removed with rmdir. Unchanged collector succeeded under existing /opt/homebrew/bin/python3.12 (3.12.14). This one infrastructure recovery consumed no new native launch or correction. The original outer log contains one harmless /proc stat disappearance during runner polling; status/readbacks independently confirm0 and absence, so no hidden retry or suppressed product failure.

## Limits and measurements

Unchanged limits600s outer/585s runner/540s helper including30s export reserve; jobs2, descendants16, preemptive storage1572864KiB, RSS/storage hard2097152KiB. Original export elapsed51.765s includes helper work/export, not full campaign cost. One-second observed sample maxima: RSS953840KiB, storage967628KiB, descendants9; not continuous peaks or reservations. Cumulative Unix96 consumed; cost/token usage unavailable.

## Evidence and applicability

Originals: linux-managed-success96-evidence/proof-evidence/ (all seven command stdout/stderr/status, source restoration, closure JSON), outer-evidence/ (launcher identities/status/cleanup/outer log), independent-readback.json, export-manifest.json and remote-cleanup.json. Source input and recipe hashes are in input-identities.sha256 and contract.md. No reused native assertion control for the new prompt-success behavior; all three run96 controls are new. Original95 held proof remains valid independently; run96 adds these four feature rows. Integration must preserve exact test/production bytes and record applicability; unrelated documentation/recipes do not invalidate prior proof.

**Unverified:** no_float/no_index excluded by fixture gates; wider managed deadline/overflow/kill/final-drop/escape/setup/drop-false/performance contracts, native macOS/Windows and final current-source release matrix. This proves two selected Linux paths, not all process functionality or release readiness.

Integration applicability: merge92146c604e3a248aa2d961d59f33be195b373875 has exactly the frozen003da non-scratch tree (git diff empty), including exacte003 test bytes. Source/production/native proof inputs are unchanged; documentation and recipe commits require no duplicate build.

Evidence integrity note: original libtest stdout trailing spaces/blank lines and the remote collector-created bytecode are hash-bound original inventory. They are preserved verbatim; documentation/source whitespace checks pass separately. No accepted evidence bytes were normalized.
