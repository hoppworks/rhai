# Native Windows timeout attempt18: real failing report

This bounded run used 439 source files at manifest SHA-256
`029608b30341c1f4b11d096c96ad1e2d3b674dc6c9d698b6b136cf59a0a9c3d0`,
candidate lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`,
and the accepted public runner/driver build. The Windows-target Rust 1.77.2
cross-check for this test source is in `../../windows-timeout-20261028/cross-check.log`;
native Cargo/Rust was 1.93.0 with `testing-environ,sys,metadata`.

Native compilation succeeded. The real public Engine timeout test observed
its child-written PID, opened the exact Windows process handle, and observed
that handle signal with exit code 1 after five seconds. The returned error
matched `SysError::Process` with `ProcessCause::Timeout`, but the report's
`timed_out` flag was false, so the test's correct assertion failed. The wrong
expectation branch did not fail at its intended assertion; this is a real
failing product-report observation, **not** an accepted wrong-expectation RED.
The original test did not print the cleanup diagnostics before asserting, so
the specific underlying cleanup branch is unknown. Broken-pipe handling and
lost successful overlapped-read bytes are separately visible code defects,
but their relationship to this particular failure is an inference until
further diagnostic evidence.

The Driver exited 2 after 91.093 seconds because the expected control marker
was absent. Its original 157,497-byte COM1 segment has SHA-256
`123cf4a8381b74ad2dd3aebdecc34bdee8c58c8471a2cd3842e90f4638585a78`,
101 ordered frames and nine length/hash-verified files. Four journal record
lengths and CRC32s pass; no completion grammar or native acceptance is claimed.
The observer reports Driver exit, drained pipes, disposed handle, no pending
custody and stopped owned executables. Guest originals remain retained for
exact evidence-first retirement. Host sdc was restored and the exact owned
host stage and ISO were retired after hash and all-domain reference checks.
