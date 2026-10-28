# macOS combined `no_index,sync,metadata` profile — bounded acceptance slice

The reviewed scope is macOS 27.2 arm64, Rust/Cargo 1.77.2, features
`testing-environ,sys,net,no_index,sync,metadata`, lock SHA-256
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The base checkout was `a131c6c9678f986c22b8ce2ea25bd81ccb5ab481`.
The attempt64 source manifest (`ddbb88a05802f02e83d4d1c5a613b3a8040f3d7bf2007acb6955523d76868319`)
and archive (`3a671bbdeaebb068fc264e924f63af497eb8e94c4bffcf69e9fe63f000e9f26a`)
covered 448 source files. Before each run the runner compared every relevant
checkout file to that manifest and extracted an owned source copy inside
`AGENT_RUNTIME_DIR`. Attempts 02/03 overlaid only `tests/sys_process.rs`; the
final overlay SHA-256 is `cce4c03768a74cbb391fbc3369c4daf16b35a7f5a9b4eea071aca6b73a2ade31`.
Cargo target, home, lock and generated files remained inside the disposable
runtime; all logs and `run.json` files were exported here before cleanup.

## Results

- Attempt 01: `cargo +1.77.2 metadata --locked --no-deps --format-version 1`
  and eight-target `cargo +1.77.2 test --locked --features
  testing-environ,sys,net,no_index,sync,metadata --test combined_sys_net
  --test sys_fs --test net_reads --test net_writes --test sys_policy
  --test net_metadata --test sys_process_report --test sys_process --no-run`
  both exited 0. The exact combined test with
  `RHAI_COMBINED_WRONG_EXPECTATION=1` exited 101 at its independent fresh host
  filesystem readback assertion; actual payload differed from the deliberately
  wrong expectation. The full eight-target invocation exited 101 after six
  completed target suites passed: combined (1), net metadata (2), reads (8),
  writes (10), sys fs (24), sys policy (28). The next `sys_process` test failed
  before its intended assertion because the test named `/bin/true`, absent on
  this macOS; `sys_process_report` was not reached. The full invocation is
  **not** a green acceptance result. See `macos-noindex-sync-metadata-attempt01/`.
- The test path was corrected to `/usr/bin/true` on macOS while preserving
  `/bin/true` on Linux. Attempt 02 compiled and passed the affected process
  (2/2) and report (8/8) targets. It established the correction before the
  assertion control was added; it is retained as causal history, not the final
  acceptance source. See `macos-noindex-sync-metadata-attempt02/`.
- Attempt 03 compiled the final test source. The exact public no-argument
  process selector with `RHAI_SYS_NO_INDEX_WRONG_EXPECTATION=1` exited 101 at
  `public no-index run exit code` (actual 0, deliberately expected 1; one test
  failed). Restored execution in the same private scope passed process 2/2 and
  report 8/8. The scalar process fixture also recorded its child PID and
  independent `ESRCH` reaping observation; the no-argument case used the real
  system `true` executable. See `macos-noindex-sync-metadata-attempt03/`.

Only `tests/sys_process.rs` changed between attempt 01 and final attempt 03;
the six completed first-run suites and combined wrong-expectation control retain
their source, feature, lock and OS applicability. The final process target has
its own wrong-expectation control. This combines 83 named green tests across
the unchanged and affected targets; it does not imply one eight-target green
invocation or full release acceptance. Independent combined Standards/Spec
review and focused follow-up returned PASS at this exact scope.

The POSIX runner supervised each invocation with a 1200-second outer limit;
individual compile/test steps had finite limits in the preserved runner files.
Its private runtime was removed on exit. Each of the three exact owned session
scopes was read back empty and retired with `rmdir`; foreign scopes were not
touched. Further native Linux/Windows, other features and the core MSRV gates
remain open.
