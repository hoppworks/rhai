# Pending stdin `Ok(0)` proof

Criterion: when spawned-child stdin still has pending bytes and `Write::write`
returns `Ok(0)`, report `io::ErrorKind::WriteZero`; do not mark pending bytes
transferred. The existing spawned-child error path retains the first cause and
requests owned cleanup. This is a narrow injected-writer criterion, not proof
that a real OS pipe returns zero or that the full macOS stdin contract passes.

- Platform: Darwin arm64, macOS 27.0.0; rustc/cargo 1.77.2.
- Features: `testing-environ,sys`.
- Lock: pinned accepted Cargo.lock SHA-256
  `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Tested source `src/packages/sys/process/unix.rs` SHA-256:
  `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`.
- Test: `packages::sys::process::unix::tests::pending_stdin_zero_write_reports_write_zero`.
- RED: `red.status` is 101; the intended assertion failed because the pre-fix
  helper returned `Ok(0)`; summary `0 passed; 1 failed; 26 filtered out`.
- GREEN command: `cargo +1.77.2 test --locked --features testing-environ,sys --lib packages::sys::process::unix::tests::pending_stdin_zero_write_reports_write_zero -- --exact`.
- GREEN: `green.status` is 0; `1 passed; 0 failed; 0 ignored; 26 filtered out`.
- RED log SHA-256:
  `61324d4b9ca37573ee7b30f9af685a849c7906ce065eba23f1968b2ab64ec274`.
- GREEN log SHA-256:
  `7b1da096f23a2010aa193d25467fe1867b9b0e198639e6c31567505f29f36c2d`.
- Combined independent Standards/Spec review passed. It confirmed the error
  reaches the existing first-cause/cleanup path, the offset advances only for a
  positive write, and `run`/`run_raw` are unchanged.
- Build used the project-scoped runner with an owned source copy and private
  target/Cargo caches. The exact session scope was empty and retired after the
  run; no compiled artifact is retained.

This proof complements the independently accepted real Linux BrokenPipe
criterion. It does not close other OS, feature, lifecycle, or A–F requirements.

## Native Linux regression follow-up on the integrated commit

After commit `0c6c51b98f57cb2e3ca3c8a56a64ea84f93981e3`, the full unfiltered
`sys_process` target was rerun on Workhorse Linux x86_64 with Rust/Cargo 1.77.2
and `testing-environ,sys`. It passed 60 tests, failed 0, ignored 3, and the
real public-Engine `spawn_retains_error_when_child_closes_stdin_with_unsent_input`
regression passed. The independent fixture log reports a typed `BrokenPipe`
cause with operation `write child stdin`, child reaped, managed group empty,
host identity unchanged, sentinel alive at return then reaped, and both capture
markers present. This revalidates the real-OS sibling path after the shared pump
change; it does not turn the injected `Ok(0)` test into an OS-generated zero
write.

- Source SHA-256: `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`.
- Cargo.lock SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Log SHA-256: `dd5b4e9fdfe668769d2305da1a2c733667e1370592de5ce9105bddb89fbbe57f`.
- Run metadata SHA-256: `0230ebc22dbad2808b23db7e2d70c1836185c9182e5a59bcc16ab4ab090f0e69`.
- The project runner removed its private runtime; logs and metadata were copied
  back and independently hash-read before the exact owned session scope was
  retired. No owned build artifact remains.

## Native Darwin `sys_process` verification

At source commit `8da9a8750e38709551a6db31736cc869a60fc3f5`, the full unfiltered
`sys_process` integration target passed on Darwin arm64/macOS 27.0.0 with
Rust/Cargo 1.77.2 and `testing-environ,sys`: 48 passed, 0 failed, 1 ignored.
The test runner's expected nested panic control is reported as a passing outer
test. This broad native regression run includes the public blocked-stdin/spawn
snapshot test, but the actual early-close/BrokenPipe fixture remains Linux-only;
therefore this run does not close native Darwin stdin-error acceptance.

- `sys-process.status` is 0.
- Log SHA-256: `11ca29f2e1fd4f9865f6c78f88b3fd9b6a42042aa678ddcdd10383e867ccb698`.
- Run metadata, source and lock SHA-256 are in `run-info.txt`; source and lock
  match the Workhorse run above.
- The scoped runner removed its private runtime. The evidence log was hashed
  locally, and only the exact owned session scope was retired.

## Native Darwin real-pipe BrokenPipe acceptance

The focused public-Engine test
`spawn_retains_error_when_child_closes_stdin_with_unsent_input_darwin` now
passes its expected RED and restored GREEN on native Darwin arm64/macOS 27.0.1
(kernel 27.0.0), Rust/Cargo 1.77.2, features `testing-environ,sys`. The test
runs a real Rhai script through `Engine` and `spawn` to the OS. It sends 4 MiB
through the actual child stdin pipe; the active SDK declares `PIPE_SIZE=16384`
and `BIG_PIPE_SIZE=65536`, and the child independently reported 65,536 unread
bytes via `FIONREAD` before closing fd 0. The parent independently observed fd
0 open before close and absent after close with `/usr/sbin/lsof`, while binding
the child to PID, parent, process group and start time through `/bin/ps`.

The expected RED used only a private source-copy revert of the `BrokenPipe`
arm to its pre-fix behavior. The exact public first bounded `Child.wait`
returned `Ok(())` despite the closed pipe and unsent bytes; the same child was
independently still live. The nominated assertion failed with status 101 only
after bounded fallback kill/wait, direct-child reaping, process-group absence,
unchanged host/sentinel identity, and explicit sentinel termination/reap.
Restored GREEN returned 0 and retained typed `BrokenPipe` with operation
`write child stdin`, complete stdout/stderr captures, repeated wait/try_wait
cause retention, idempotent kill, exact child/group closure, unchanged host and
sentinel, and sentinel cleanup. GREEN's close readback observed the child in
zombie state while managed cleanup completed; this is why the exact live-child
assertion is required on the known-broken RED branch after close and first wait,
while GREEN records the same identity as live/zombie/absent at the independent
fd-closed snapshot.

- Base integrated revision: `d1170c2d51fbb0dec072182f5232a6132b26550d`.
- Current test source SHA-256: `d5031a7717d541cc2249103e95fbb89a26b9c741fb9e01556f9fa191a43b5b4`.
- Current Unix product source SHA-256: `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`.
- Exact lock SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- SDK `sys/pipe.h` SHA-256: `db3b7f2d82cf0bc758ba3016f0fc69f332b2d574e2fd4709e7964b3a7b89cf19`.
- RED status 101 and GREEN status 0. Logs, run metadata, script and input hashes are in `darwin-stdin-closure-20261009T204536Z/darwin-run-03.SHA256SUMS`; outer runner status 0 and exact-scope retirement are separately recorded there.
- Combined independent Standards/Spec review passed after the final test-harness correction. The earlier run's valid RED and failed GREEN harness observation are preserved as `baseline-green-run-02.*`; it is not counted as acceptance.
- One cold build plus incremental GREEN used the project-scoped runner and exact owned source copy. The exact TMPDIR scope and private runtime were retired; no compiled cache was retained.

This accepts the named Darwin `testing-environ,sys` real BrokenPipe row only. It does not close Ticket 03, Package B, other Darwin features, Windows, or A–F.
