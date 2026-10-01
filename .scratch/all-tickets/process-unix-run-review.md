# Unix process execution review and accepted partial proof

Reviewed immutable source: `06865bd500138edf2fe39d33a8f5e75cb04964d7`, baseline `c19e90d4b5be95f8598ec53dbcf497e09583f3eb`. Author and committer independently confirmed `hoppworks <daniel@hoppworks.de>`. An initial unpublished incorrect attribution was corrected without source changes. Fork branch `task/process-unix-run` independently read back at this exact ref. Production integration is held for the deadline findings below.

## Coverage

OCR delegate range preview: 18 distinct paths, eight reviewable source/harness/test paths and ten default-excluded state/log paths. Reviewed all eight source paths, including the held-directory helper, registration/dependency changes, complete Unix adapter, self-reexec tests and scoped verification wrapper/harness. Reviewed ten retained state/evidence paths for applicability and attempt/provenance consistency; older compile/setup failures do not establish behavior. Total18, reviewed18, skipped0. Default OCR rules applied; this is a partial implementation review, not final ticket acceptance.

## Accepted real-system evidence

Canonical raw log: `.scratch/process-unix-run/evidence/implementation-run-5.Gevixh` in the immutable source commit. Actual macOS27 arm64, Rust/Cargo1.77.2. `cargo test --locked --features testing-environ,sys,metadata --test sys_process -- --nocapture`: five passed (including the fixture no-op entry); report target seven passed. The named wrong stdout-byte assertion returned101 and showed actual65 versus expected66; byte-for-byte restored sys_process suite passed five again. All eight input hashes in original, private-copy and final tested manifests independently match committed blobs. Compatible lock reused with only the direct rhai/libc edge; exact graph change is retained in raw log.

Closed requirements: exact raw stdout/stderr and full lossy text, success/nonzero result data, stdin-unit immediate EOF, capability-held cwd after root pathname replacement, confined symlink denial before fixture start, and decoded UTF-8 expansion producing a catchable output-limit report rather than truncated successful text. Fixture-written PID/exit records independently read after raw and text calls, with ESRCH after return; the decoded-limit case now also reads its record/reaping. No broader timeout or error cleanup claim follows.

Root independently checked exact run7 runtime `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-9286nfbi` absent. Responsible wrapper terminal receipt reports runner0/cleanup0. Sampled maximum1,072,664KiB describes observed readings only, not continuous peak or a mathematical storage ceiling.

## Blocking production findings and next contract

1. `supervise` routes an ordinary deadline through `fail`, which always returns an error. The accepted public `run` result-map contract requires `timed_out:true` after successful termination/reaping. A failed cleanup must remain catchable with its primary cause and diagnostics.
2. `parse_options` rejects explicit `timeout:()`, although the accepted API specifies no deadline for this value, including override of a host default.
3. `read_ready` drains until EAGAIN or overflow without a per-step work bound. Continuously readable output with a large host cap can postpone deadline/input/other-stream observation. Bound work per supervision step while retaining ready overflow precedence.
4. The current failure report marks timed_out solely from its cause even if kill/reap diagnostics show unsuccessful cleanup. It must not certify successful timeout cleanup in that case. Exceptional reap failure currently has no retained cleanup owner; full ownership/lifecycle acceptance remains open.

Responsible context continues these related fixes test-first under a new30-minute planning checkpoint and unchanged each-run600s/jobs2/private-resource/watchdog constraints. Seven previous scoped launches and cumulative cause/Expert history remain. No additional Expert chain or safety-cap increase. Parent contract still requires large bidirectional I/O, limit boundaries/precedence, spawn/shared handles/drop, managed scope, descendants, failure ownership, native Linux/Windows and release features/MSRV. No parent ticket completion or final release claim.
