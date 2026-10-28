# Native Windows direct-child text process acceptance

Attempt17 binds 439 source files (manifest SHA-256
`11796d3683c8c4951819266e4643bb15b93e446cece90f1d42383419b347cb50`,
archive `e82060a9b200a449b1d7908e4c12693c878490bd74b785ac8e445527ccc45010`),
candidate lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`,
and the accepted public BuildOnly manifest
`8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1`.
The package source differs from fork-main `2bdb8ea05` only in the two
product/test files recorded by the manifest. The retained public runner and
driver binaries were hash-checked before native execution. The Windows guest
used Cargo/Rust 1.93.0 and `testing-environ,sys,metadata`.

The bounded native Driver exited 0 in 108.851 seconds without observer kill.
It reported exact process exit, drained/disposed pipes, stopped owned
executables, no pending custody, completed cleanup and absence of the exact
runtime. The original COM1 segment (`serial-original.bin`) is 370,148 bytes,
SHA-256 `26fed44610205ab9c13cf00104a2b6e48e8ebff81dc8ca16c0afcee296f9eac3`.
All 220 frames were in sequence; all 16 original files passed length/SHA-256
readback. Independent journal validation checked all eight record lengths and
CRC32s: `INTENT`, `IDENTITY`, `STAGED`, `LIFECYCLE`, `EVIDENCE`, `OUTCOME`,
`REMOVE_INTENT`, `REMOVED`.

The intentionally wrong text-exit and decoded-expansion expectations each
failed with the named assertion and `test result: FAILED. 0 passed; 1 failed`.
The existing deadline wrong-expectation RED and restored unit GREEN also
passed. Restored full-target GREEN passed all seven `sys_process_report` and
six `sys_process_windows` tests with zero failures/ignores. The public Rhai
script ran through the Engine and host package to real Windows children;
independent exact process handles showed exits 0 and 7. The new text result
returns lossy strings, respects the engine string limit instead of the array
limit, and raises typed `OutputLimit` after invalid UTF-8 expansion while
preserving the raw byte report. The raw path and the no-child timeout-range
guard remain GREEN. The test independently reads and asserts the child-written
records; the exact-handle PID/exit readbacks appear in the original `green.log`,
with RED and full output in the other original logs.

Combined independent review PASS is in [combined-review.md](combined-review.md).
This accepts the four-argument direct-child `run(program, args, options)` text
path at this native source/lock/profile, plus the affected raw regression
target. Other overloads, native `no_index`, Windows MSRV, managed Jobs,
`spawn`, stdin, real short-timeout cancellation, output overflow, exceptional
and descendant cleanup, Ticket03 and the release matrix remain open. A
Windows-target Rust 1.77.2 cross-check earlier in this package establishes
compilation only for its then-current source; it is not native MSRV acceptance.

Attempt15 stopped before a product assertion because the test's array limit
equaled its four-element literal. Attempt16 passed the product assertions but
its copied attribute helper still pinned an old session path, leaving a
four-record incomplete runner journal. Their original exports and causes are
retained in sibling folders; neither is the accepted completion. Attempt17
corrected only that helper's exact owned scope and hash chain while retaining
the identical product source, lock and public binary pins from attempt16.
Host sdc was restored to the original medium; this attempt's exact host stage
and ISO were retired after original export, hash and all-domain reference
checks (`host-cleanup-readback.json`). Guest outer scopes remain pending exact
evidence-first retirement; attempt17's inner runtime is absent.
