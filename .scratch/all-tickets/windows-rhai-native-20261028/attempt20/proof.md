# Native Windows stdin tracer: failing baseline

Attempt20 froze 439 source files at manifest SHA-256
`bb942f9c60989ff7a5293b430fff1206b7e517b707eda03b34a134ed7137aedc`,
candidate lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`,
and the accepted public runner/driver build. The native Cargo/Rust 1.93.0
`testing-environ,sys,metadata` test compiled and then failed at
`stdin must support concurrent transfer` with an `ErrorRuntime` carrying
`SysError`; its independent observer found no child readiness record. The
frozen Windows parser accepts `env`, `env_clear`, `timeout` and `max_output`,
but rejects the test's `stdin` key before spawn. That source inspection
explains the failure; the original Debug rendering did not print the enclosed
error message, so the exact runtime error text is not independently logged.

The outer script incorrectly required that hidden error text and exited before
its expected-RED marker. Driver exit was 2 after 113.324 seconds. The original
155,994-byte COM1 segment has SHA-256
`0c3554b792e2fc200784f13c3035a1534054ebc681253d6f6692d5e72fbfc4d5`,
100 ordered frames and nine length/hash-verified files. Four journal lengths
and CRC32s pass; the run has no completed-runner receipt. The observer reports
exact Driver exit, drained pipes, disposed handle, no pending custody and
stopped owned executables. Guest originals remain retained for exact
evidence-first retirement. Host sdc was restored and the exact owned host
stage and ISO were retired after hash and all-domain reference checks.

This is a failing behavioral baseline and a wrapper-matching error, not a
passing acceptance or a reason to rerun the unchanged trace. A corrected
implementation must separately pass the real child/pipe/readback contract and
the wrong round-trip expectation control.
