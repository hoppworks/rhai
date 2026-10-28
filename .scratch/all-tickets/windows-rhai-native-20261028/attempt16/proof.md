# Windows text-process attempt16: product checks passed, runner cleanup failed

The 439-file source archive and manifest match the current product/test source;
manifest SHA-256 is `11796d3683c8c4951819266e4643bb15b93e446cece90f1d42383419b347cb50`,
archive SHA-256 is `e82060a9b200a449b1d7908e4c12693c878490bd74b785ac8e445527ccc45010`,
and the candidate lock remains `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The accepted public BuildOnly binaries were reused with exact manifest pin.
Original COM1 bytes are preserved as `serial-original.bin` (172,214 bytes,
108 ordered frames, SHA-256
`26fa7a9ef3e3441d687ddbf6b40a6110f26150d5890b78880971038925e4a434`);
all nine exported files passed the bounded hash readback.

Native Cargo compiled the two integration targets. The wrong text-exit,
wrong decoded-expansion, and deadline assertions each produced the intended
failing RED, with exit 101 and matching assertion/FAILED markers. Restored
deadline GREEN passed. The full `sys_process_report` target passed 7 tests and
`sys_process_windows` passed 6, including text and raw output, typed decoded
`OutputLimit` with original byte report, and independent exact Windows process
handle observations for exit 0 and 7. Those test results are present in the
original payload `stdout.log`. `cargo clean` removed 775 files / 339.1 MiB.

The following read-only attribute helper then rejected the runtime because
its copied script still required the earlier `n-12566106` session root. This
was a packet path error after product assertions. The native Driver exited 2
after 81.646 seconds; the original four journal records have valid lengths
and CRC32s but no completion grammar. The observer reports exact Driver exit,
drained pipes, disposed handle, no pending custody, no observer kill and stopped
owned executables. Its `product_test_run=false` field is the final acceptance
gate, not a claim that the logged tests did not run. **The native package is not
accepted from attempt16.** Guest originals remain retained for exact later
retirement. Host sdc was restored; the exact owned host stage and ISO were
retired after original export, hash checks and all-domain reference checks.

The attempt17 correction changes only that helper's exact root and its
dependent packet hashes. It reuses the same source archive, lock, public build
and product test contract. A complete bounded native runner receipt and
independent review are still required.
