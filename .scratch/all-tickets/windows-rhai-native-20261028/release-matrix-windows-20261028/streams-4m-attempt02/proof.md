# Windows 4-MiB interleaved process streams: X13

At committed base `6dc2565bebe137063c218cc90fa748d24559d1a5`, the sole
test overlay `tests/sys_process_windows_streams.rs` had SHA-256
`0039528cba8117ca93e488d8f093880b6974c9afd63ee95b03c63c3939216838`.
Native Windows 11 x86_64 MSVC, Rust/Cargo 1.77.2 and
`testing-environ,sys,net` used lock SHA-256
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The [manifest](media-input/source-manifest.json) binds the 451 frozen source
files; [the command](media-input/RunRhaiContract.cmd) uses one locked Cargo
build from its explicit source directory.

For each of DirectChild and Managed, public Rhai `run`, `run_raw`, and `spawn`
executed a real child that alternated 512 flushed 8-KiB writes to each stream.
The parent checked exact four-MiB contents for both streams, complete capture,
the independently written child receipt, and the exit signal/code of an exact
process handle identified by PID and creation time. Captured stdout also
included the 16-byte libtest prefix. The full target passed 7/0/0.

Twelve separate controls inverted the stdout or stderr expectation for each
mode. Every original control exited 101 with the intended named assertion,
failed libtest result and exact-child readback. The restored target passed in
the same native build. Original logs and observer are in [the export](original-export/);
the [combined review](combined-review.md) confirms this scoped conclusion.

The bounded Driver exited 0 in 63.282 seconds; observer custody was closed and
the runtime removed. The [journal](journal-readback.json) has eight
length/CRC-validated states through `REMOVED`. The serial export contained 254
ordered frames and 27 hash-checked original files. After readback, the exact
guest scope was removed ([receipt](guest-retire-result.png)); [host cleanup](host-cleanup.json)
removed the owned stage and ISO, restored original `sdc` and preserved foreign
`sdb`.

The [first attempt](../streams-4m-attempt01/proof.md) did not reach the intended
controls: the Engine limit incorrectly accounted for just one stream although
Rhai sums both map fields. The corrected test raises only its aggregate Engine
limit; the per-stream `max_output` is unchanged. Both attempts and their causes
remain preserved. This acceptance is limited to the stated OS/toolchain/features
and data; it does not close X13 across all configurations, the overall process
ticket, or release acceptance.
