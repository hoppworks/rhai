# Darwin X38 capture and post-reap cancellation — fixture cleanup correction

**Combined independent review passed.** This package accepts only the named Darwin base-profile
rows `managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes` and
`managed_spawn_post_reap_cancel_bounds_escaped_capture`, plus the fixture's exact
process-cleanup fallback test. It does not close X38, Ticket 03, or A–F across
platforms, feature profiles, or MSRVs.

## Candidate and applicability

- Integrated base: fork `main` commit `2cb6b67a9b13c2b5f363e2d2767ac6ec40898038`.
- The only implementation diff is in `tests/sys_process.rs`; production Unix
  process code is unchanged. Cargo.lock SHA-256 is
  `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Environment: Darwin arm64, macOS 27.0.1 (kernel 27.0.0), Rust/Cargo 1.77.2.
  Features: `testing-environ,sys`.
- `source-bindings.txt` records current Cargo.toml, lock, Unix source and complete
  test-file hashes. The two public-test function bodies have the same SHA-256 at
  the earlier RED source commit `9042ee19628e9794ff37d5814386406a894a0c0d` and
  current base; exact values and the unrelated source delta are explained in
  `attempt-01/reused-controls/binding.md`.

## Expected RED and restored GREEN

The assertion-mutated REDs are reused from `attempt-01` of the earlier Darwin
attempt. The X38 control exits 101 at the intentionally inverted unrelated-sentinel
assertion after the managed leader is absent, the escaped holder answers an
independent challenge, and the sentinel remains live. The post-reap control exits
101 at the intentionally inverted non-unit-report assertion after the direct leader
was reaped, uncancelled waits stayed pending, and the escaped holder remained live.
Both original logs include exact fixture cleanup and are checksum-verified in
`attempt-01/reused-controls/`. Reuse is justified by unchanged test-function hashes,
unchanged public Unix implementation, lock, features, and native environment; the
restored GREENs were rerun on the integrated candidate after the cleanup correction.

The current candidate passed both restored GREEN selectors (one test each). The
final bound run is `attempt-03`; its logs show the real Rhai `Engine`/`spawn`/`kill`/`wait` path, retained stdout and
stderr markers, incomplete capture flags, the escaped holder's post-return write
failing with Darwin `EPIPE` on both streams, direct-leader reap, and exact
leader/holder/sentinel cleanup.

## Cleanup correction

The independent review found that `ManagedEscapedPipeFixture::release_and_wait`
released its fixture processes and waited, but did not stop a recorded process that
remained after the bounded wait. The correction records a platform process-start
identity and process group, refuses cleanup when the current identity differs, and
uses `SIGKILL` only on the exact recorded PID after the graceful-release deadline.
It then performs a second bounded absence check. The owning parent explicitly
reaps its direct child; cleanup never signals the unrelated process group.

`managed_escaped_fixture_cleanup_signals_only_exact_process_identity` exercised the
timeout escalation with a real `/bin/sleep` child joined to the fixture sentinel's
group. It first proved a mismatched start identity is refused while the child stays
alive. The fixture then sent `SIGKILL` to the exact matching PID/group/start; the
test reaped the direct child, observed ESRCH, and confirmed the sentinel remained
alive. The `attempt-03` target log records `exact_identity_signal=true`,
`target_sigkill=true`, and `sentinel_alive=true`.

## Run and resources

`attempt-03/run.sh` archived the integrated commit into its private runtime, copied
the hash-verified lock, applied only the owned test diff, and ran the cleanup test
plus both restored GREEN selectors in one scoped invocation. One Cargo build took
about 21 seconds; the three selectors passed in 0.59, 0.26, and 0.63 seconds. Outer
`run_scoped` and each Cargo status were 0. Independent post-run `kill(pid, 0)`
readback confirmed ESRCH for all eight recorded target, leader, holder and sentinel
PIDs. The private runtime was removed by the runner and exact session scope
`/Users/hoppworks/.local/share/agent-builds/rhai/darwin-capture-cleanup-20261025-03`
was retired empty and absence-verified.

`attempt-01` is retained as preparation history: its first scoped build passed all
three then-current selectors, but its zsh wrapper tried assigning the reserved
read-only `status` variable and did not capture the outer return code. Its three
Cargo results were 0 and its runtime was removed. The cleanup test was then
strengthened to exercise the fixture timeout call path end to end in `attempt-02`.
A final API adjustment restored both existing named test bodies byte-identically to
the RED controls while retaining the richer cleanup result for the new fixture test;
`attempt-03` reran all three selectors. This is harness history, not a product failure.

## Remaining scope

This evidence covers only Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2, and the
base `testing-environ,sys` profile. Other X38 selectors, feature profiles, OS/MSRV
rows, native Windows custody, remaining Ticket 03 criteria, and A–F packages remain
open. The first combined review's cleanup finding is resolved in source and covered
by the targeted real-process test. The focused follow-up found no source or run
finding; its evidence-record correction was reconciled to `attempt-03` and the
review artifact was updated accordingly.
