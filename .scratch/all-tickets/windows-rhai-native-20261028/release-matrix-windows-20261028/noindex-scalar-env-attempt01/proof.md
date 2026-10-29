# Native Windows no_index scalar process proof

Status: **accepted for named cases after combined independent review**, not the full R3 or release matrix.

At base `e0ec6fae0161a743b1f7e8ede9892f4f89787c87`, [preparation](preparation.json) binds 448 base source files plus the sole new scalar test overlay. The original Cargo.lock SHA-256 is `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`. The [command](media-input/RunRhaiContract.cmd) uses native Windows 10.0.26300.0, Rust/Cargo 1.77.2, `testing-environ,sys,net,no_index`, and compiles once. Driver exit 0 in 95.3711583 seconds; bounded Driver/observer deadlines are 180/185 seconds.

Rhai scalar `run(program)` executes native `hostname.exe` under DirectChild and Managed. Its child stdout matched `GetComputerNameW` independently: both observed `RHAI-WIN11`. Separate deliberately wrong Direct and Managed assertions exited 101. The `env_remove` option yields the expected typed unavailable-option Denied for both scopes; each has its own deliberately wrong assertion and exit 101. The unfiltered target then passed **3 tests, 0 failed, 0 ignored**, including the unregistered `run_raw` check. All controls and GREEN were executed in one scoped build.

The native observer reported closed custody and removed runtime. [Serial binding](serial-capture-binding.json) reconstructs the original contiguous export across the observed rotation. [Original export](original-export/), [export readback](original-export-readback.json) and [journal readback](journal-readback.json) verify 225 ordered frames, 19 hash-checked originals and eight CRC-valid records through REMOVED. The [guest](guest-retire-result.png), [host cleanup](host-cleanup.json) and [host readback](host-postcleanup-readback.json) show the owned scope/ISO/stage absent and original sdc/foreign sdb preserved.

The [review](combined-review.md) accepts only this ASCII-machine feature row. Hostname encoding/name-form variants, independent exact-handle/reaping and no-spawn evidence, array overloads, separate raw-absence calibration, other feature/OS/MSRV combinations and the complete R3/release acceptance remain open.
