# Bounded streaming file reads

## Goal

Implement bounded `read_string([len])` and `read_blob([len])` for shared file handles with strict UTF-8, exact blob bytes, EOF and cursor behavior, negative-length rejection before allocation/movement, checked Engine caps and host caps in all builds. Preserve no_index omission and do not change whole-file APIs.

## Done when

Real Engine scripts against private files prove the requested behavior. The sys_fs suite passes base, sync/no_index and unchecked profiles; false-green control fails at its intended assertion. The approved public config is implemented, reviewed, and committed locally with evidence retained.

## Done

- Worktree `/Users/hoppworks/projects/rhai-file-reads`, branch `task/file-reads`, base `e365008a`.
- Read the feature brief, project AGENTS.md, handle compatibility report, release proposal, open review and relevant implementation. Sent public cap proposal; coordinator approved before implementation.
- Added `SysConfig::max_file_read(usize)`, default 8 MiB. Zero returns zero bytes. Checked nonzero Engine string/array cap lowers the host cap; unchecked reads retain the host cap. No whole-file API or public close.
- Added bounded `read_string` and `read_blob` overloads. Negative lengths fail before cursor access; positive requests use a single capped `Read::read`; omitted/zero reads use a capped `read_to_end` only when Engine limit is zero, matching pinned upstream behavior. Strict UTF-8 errors map to InvalidData; blobs preserve bytes and are cfg-omitted under no_index.
- Added real-script coverage for cursor sharing, host/Engine caps, `INT::MAX`, explicit zero, zero host cap, EOF empty values, negative string/blob lengths and cursor preservation, read errors, malformed UTF-8 and boundary truncation, blob fidelity, and no_index omission.

## Decisions and limits

- Actual start 2026-09-30 12:51:28 UTC; hard stop 13:51:28 UTC. Final clock read 13:12:39 UTC. No publication, push or merge.
- Strict project verification. Each scoped invocation used `--timeout 900`, `CARGO_BUILD_JOBS=2`, serial test threads, and placed source copy, Cargo home, target and temp under `AGENT_RUNTIME_DIR`. The 2 GiB private-storage peak and 16-file/handle ceiling were not measured; compliance with those two caps is unverified.
- Pinned upstream `rhai-fs` source at `1c1455c26ab1070d65fd3ad5dc363095eed6dc3f` establishes omitted/zero + unlimited Engine as `read_to_end`, while explicit positive and nonzero Engine-limited reads issue one read. No speculative repeated OS reads beyond the requested cap.

## Scoped launches and evidence

- Launches 1–3 built the red test. Launches 1–2 exposed assertion compile issues; launch 3 produced the expected `ErrorFunctionNotFound("read_string (FileHandle, i64)")`. Log: `initial-red.log`. Exact launch wrapper arguments for these early runs were not retained in the logs/state.
- Launch 4 false-green control setup initially failed because `format!` parsed Rhai braces. Launch 5 stopped on Rhai `let mut` syntax. Corrected both as test-source issues.
- Launch 6 base suite exposed zero-prefill bytes in the EOF path; fixed the implementation to reserve without resizing for `read_to_end`.
- Launch 7 passed all read cases but a write-only error test expected platform-specific `PermissionDenied` where this OS reports `Uncategorized`. Changed the assertion to the portable `SysError::Io` class.
- Launch 8: false-green control failed at its deliberately wrong expected value. Full sys_fs passed: base 34/34, sync+no_index 24/24, unchecked 32/32. Logs: `false-green-control.log`, `sys-fs-base.log`, `sys-fs-sync-no-index.log`, `sys-fs-unchecked.log`.
- Launch 9 stopped at test compile because `assert_eq!(Vec<u8>, [])` left the empty array type ambiguous. Fixed the assertion type.
- Launch 10 targeted changed tests passed: base blob 1/1, sync+no_index omission 1/1, unchecked blob 1/1. Logs: `final-read-base.log`, `final-read-no-index.log`, `final-read-unchecked.log`.
- Recorded scoped invocation commands:
  - Matrix runs: `python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 900 -- bash .scratch/file-reads/run-matrix.sh`.
  - Final changed-test run: `python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 900 -- bash .scratch/file-reads/run-final-read-tests.sh`.
  - The scripts archive `HEAD` to `$AGENT_RUNTIME_DIR/source`, overlay the three changed source/test files, set `CARGO_HOME=$AGENT_RUNTIME_DIR/cargo`, `CARGO_TARGET_DIR=$AGENT_RUNTIME_DIR/target`, and `CARGO_BUILD_JOBS=2`, and export logs here. Test commands and feature flags are recorded in the scripts.
- Host observed during this post-run record update: macOS Darwin 27.0.0, arm64 (`aarch64-apple-darwin`); `rustc 1.93.0 (254b59607 2026-01-19)`, Cargo 1.93.0, Python 3.9.6. These were queried after builds; build logs themselves do not record complete OS/Rust version output.
- Runtime paths found in retained build logs: `/private/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-87yr753w`, `.../agent-build-_1qfzah0`, and `.../agent-build-b0d3b2m_`. Exact-path existence checks after completion found these paths absent. Other `agent-build-*` directories existed under the shared temp root; they were not attributed to this task or touched. This is an independent existence check for the retained paths, not proof that every launch path was recorded.
- The retained `.scratch/file-reads/` directory measured 60 KiB at record time. Peak private runtime storage was not measured, so compliance with the 2 GiB cap remains unverified; fixture count/peak handles likewise were not instrumented.
- Local commit `7131f25337bc4830b225f842af0f1cbf6e42ddb2` (`Add bounded file handle reads`) contains only `src/packages/sys/config.rs`, `src/packages/sys/fs.rs`, and `tests/sys_fs.rs`. Working source tree is clean; `.scratch/file-reads/` retains state and proof logs outside the commit.

## Remaining

- None within this subtask. No push or merge requested.
