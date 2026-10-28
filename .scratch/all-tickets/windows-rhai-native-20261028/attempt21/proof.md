# Native Windows direct-child stdin and concurrent output

Attempt21 used 440 source files (manifest SHA-256
`318bbbe84a4e3b9f778aa9db37990a461d2c1ce9c79388d0180969f552c35620`,
archive `cc3e1416e362d34c0578bbc505ae95a66bfb96aaf73554daa3c4d2b3361a99a0`),
candidate lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`
and the accepted public runner/driver build. Native Cargo/Rust 1.93.0 ran
`testing-environ,sys,metadata` on the Rhai Windows guest.

The public `run_raw` test sent a varied 128 KiB Blob to a real child that
first wrote 64 KiB to each output stream. The test independently opened the
exact child process handle, observed exit 0, read and asserted the complete
child-written input file, and compared both captured output streams with their
known bytes. The file contents themselves were not exported. The deliberately
wrong round-trip expectation failed at its named assertion; restored GREEN
passed. A separate public test observed timeout, exact child exit and a clean
report when a child did not read supplied input. Its wrong timeout expectation
also failed as intended. That test does not observe a pending write and does
not prove public pending-write cancellation.

Nine native Windows units passed, including a real-pipe test that observes an
outstanding write before bounded cancellation, a chunked write/EOF test and a
pipe-closure/zero-progress classifier. These are helper-level observations;
they do not establish public early-close, partial-completion race, injected
failure or retained-custody behavior. Existing overlap wrong-expectation RED
and restored unit GREEN also passed. Full `sys_process_report` and
`sys_process_windows` targets passed 7 + 11 tests with zero failures/ignores.

The bounded Driver exited 0 in 116.255 seconds, with exact exit, drained and
disposed pipes, no pending custody, stopped owned executables and the exact
runtime removed. The 373,022-byte original COM1 export is SHA-256
`1a74dd7c45b0149eff8947880a76b8f4a583f8b5031dea289d7fb19dacbe0bf0`.
The serial log rotated during export: the original old inode from the recorded
offset and the new inode were concatenated, preserving 222 ordered frames;
`serial-rotation-readback.json` records the boundary. All 16 original files
passed length/SHA-256 readback. The coordinator independently validated eight
journal record lengths, CRC32s and state order through `REMOVED`. Host sdc was
restored and the exact owned host stage/ISO retired after all-domain checks;
the guest outer scope awaits exact retirement.

The final source also passed Windows-target Rust 1.77.2 compilation checks for
standard, `no_index`, and `unchecked` profiles (`../../windows-stdin-20261028/`);
those checks do not establish native platform acceptance. The bounded writer
uses one full input vector per active owner and a bounded write chunk; there
is no separate host input-size cap, so an aggregate memory limit under
`unchecked` is not claimed. String and empty/unit input, public pending-write
cancellation, early child closure, partial completion races, failure/unwind,
managed Jobs, other native profiles/toolchains, Ticket03 and release remain
open. Attempt20's real failing baseline and wrapper-matching failure are
preserved in its sibling proof; no repeated baseline was needed.

Combined independent review: [combined-review.md](combined-review.md).
