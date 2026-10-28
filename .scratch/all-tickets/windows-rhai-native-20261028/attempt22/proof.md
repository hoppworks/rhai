# Native Windows direct-child stdin contract cases

Attempt22 binds 440 source files (manifest SHA-256
`c86e88162af31e50c0b13c4cef2010fe65414a2ed3b4d32b1c53437ad500d6aa`,
archive `0dd79f766997b295f31287f17bf54575eb6dc083480b16b309e650956f0100a7`),
candidate lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`
and the accepted public runner/driver build. Native Cargo/Rust 1.93.0 ran
`testing-environ,sys,metadata` on the Rhai Windows guest.

The public `run_raw` test sent a varied 1 MiB Blob to a real child that first
wrote 256 KiB to each output stream. It compared both captured streams and
independently read and asserted the child-written input file, and observed
exit 0 through an exact Windows process handle. The public `run` scalar test
similarly checked a 41-byte non-ASCII UTF-8 string, an empty string and `()`;
the child completed its input read and wrote an empty file for the latter two
within the configured deadline. Exact child-handle exit 0 was independently
observed for each. The child-written files were read and asserted by the tests;
their contents were not exported as separate artifacts.

The intentionally wrong Blob, string, empty-string and unit expectations each
failed at the named assertion with Cargo exit 101. Restored full
`sys_process_report` and `sys_process_windows` GREEN passed 7 + 12 tests, with
no failures or ignores. Existing attempt21 helper-unit evidence remains
applicable: the production and unit-test source files and lock are unchanged,
and the independent reviewer checked that binding. Windows-target Rust 1.77.2
compilation for this test source passed in `../../windows-stdin-contract-20261028/cross-check.log`;
this is not native Windows 1.77.2 acceptance.

The bounded Driver exited 0 in 86.931 seconds, with exact exit, drained and
disposed pipes, no pending custody, stopped owned executables and the exact
runtime removed. The original 376,017-byte COM1 segment has SHA-256
`004373ff79f726437a8bfcc17b2ce27de0a3a2e0ba539d1114f8d41a4f592a62`;
all 223 frames were ordered and all 16 exported files passed length/SHA-256
readback. The coordinator independently validated eight journal lengths,
CRC32s and state order through `REMOVED`. Host sdc was restored and the exact
owned stage and ISO retired after hash and all-domain reference checks; the
guest outer scope awaits exact retirement.

Combined independent review: [combined-review.md](combined-review.md). These
results accept only the named direct-child cases at this source/lock/profile.
Public pending-write cancellation, early child close and injected fault paths,
managed Jobs, aggregate unchecked input-memory limits, other native feature
and MSRV rows, Ticket03 and release remain open. The 15-second timeout bounds
the test; the EOF case does not promise a scheduler-independent latency.
