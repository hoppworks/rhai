# Combined independent review: Windows stdin contract cases

**PASS** for the named native Windows Rust/Cargo 1.93.0,
`testing-environ,sys,metadata` direct-child cases: non-ASCII string input,
1 MiB Blob with 256 KiB on each output stream, and empty-string/unit EOF.
The reviewer checked the test and packet before launch and then validated the
440 current source hashes, four intended REDs, restored 7 + 12 GREEN, exact
child-handle readbacks, Driver custody and all 16 exported file hashes/lengths.
The child-written input files are read and asserted by the tests, not exported.

The coordinator separately checked all eight journal lengths, CRC32s and state
order, restored original sdc, and retired the exact owned host medium/stage.
The reviewer did not repeat that journal check. Attempt21's production and
unit-test sources and lock are unchanged, so its named helper evidence remains
applicable at its original profile. Public pending-write cancellation and early
close, injected faults, managed scope, other features/toolchains and the release
matrix remain unverified.
