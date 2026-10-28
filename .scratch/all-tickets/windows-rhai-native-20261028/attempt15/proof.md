# Windows text-process attempt15: pre-assertion failure

The reviewed packet contained 439 source files at manifest SHA-256
`c4d9705cdaac18adb434f0aa3ecf6b4d676730ca00c056db4394c31ce7180e90`
and candidate lock SHA-256 `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
It reused the accepted public BuildOnly binaries, pinned by manifest
`8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1`.
The host preflight, original COM1 segment and hash-verified nine-file export are
preserved here. The original serial segment has 101 ordered frames and SHA-256
`d996703218608d2a01f261e45c1430f0fc1020ddc6976fb28fa5912a062e8c71`.

Native Cargo compiled the library and both integration targets in 72 seconds.
The first intended text RED then failed before invoking the host process:
`ErrorParsing(LiteralTooLarge("Size of array literal", 4))`. The test had set
`max_array_size(4)` while its script contains a four-element argument literal.
Its independent observer timed out because no child readiness record was
created. This is a test preparation error, **not** a valid product RED or a
product failure. The bounded Driver exited 2 after 82.193 seconds. Its original
four journal records have valid lengths and CRC32s; no completion grammar or
product acceptance is claimed. The observer reports exact Driver exit, drained
pipes, disposed handle, no pending custody, no observer kill and stopped owned
executables. Failed-run guest originals remain retained for exact later
retirement. Host sdc was restored to its original medium; the exact owned host
stage and ISO were retired after original export, hash checks and all-domain
reference checks (`host-cleanup-readback.json`).

The focused correction raises the test array limit to 16, above the literal
length while below the raw child-output length. It leaves product code and
the accepted attempt14 `run_raw` scope unchanged. A new bounded native run is
required to establish the text RED and GREEN at the corrected test source.
