# Native Windows Rhai process attempt11

The source packet contains 439 manifest-pinned files (dirty HEAD
`6f052eb3835bd3fd5f2911dea9593c6b97c3085c`), source manifest SHA-256
`99fd445ee238abee7d2c5a0bcff4de3e5de2964801c80e9dcd6dad60cd78d599`,
archive SHA-256 `a98d16a4c35bd3e63ed6bb135c256759cd051c0fcee0805853488c7772f6bef0`,
and `Cargo.lock` SHA-256 `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The public BuildOnly manifest is `63145b571f26bdfb4c482231259374557f87c1b9a1b48ddbd51b6f98377dab7c`
with original expiry 2026-10-26 11:40 UTC. The independent pre-execution source
review found and rechecked two scope-path corrections and one host ISO-path
correction before any guest launch. `binding.json` and `host-pre-enter.json`
pin the final medium and serial offset.

On Windows 11 Pro build 26300 with native Rust/Cargo 1.93.0, one bounded Driver
ran `cargo test --locked --features testing-environ,sys,metadata --test
sys_process_windows --test sys_process_report`. The packet's
`RunRhaiContract.cmd` built both targets, ran the named wrong-exit assertion RED,
then restored and ran both full targets. The compile took 1m42s; RED reused its
build in 0.19s and GREEN in 0.14s. The RED failed at the intended assertion with
one failed test. GREEN passed 7 `sys_process_report` and 2
`sys_process_windows` tests. The public Engine result was checked against
child-written records and separately opened native process handles, which
observed exact child exits 0 and 7.

The Driver exited 0 after 117.434 seconds, drained its pipes, observed its
executables stopped, and removed its exact runtime. The original COM1 capture is
349,870 bytes, SHA-256 `116b72482ab15b538162cb9f384ae05953b83c0a691e5e80688dad14a6b4a9c1`.
The 204 ordered frames exported 13 original files (174,327 bytes); their hashes
were checked during reconstruction. `independent-verification.json` additionally
checks source/lock/build pins, all eight journal CRCs and phases, artifact hashes,
RED/GREEN summaries and the independent OS readback. The VM's sdc is restored to
its original `monitor-fixture02.iso`; sdb was untouched. Own host and guest scopes
still await exact evidence-first retirement. The public BuildOnly guest artifact is
retained only until its original expiry for related Windows process checks.

Combined independent review: [combined-review.md](combined-review.md). Timeout
range correction and all broader process/release criteria remain open.
