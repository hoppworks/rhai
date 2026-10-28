# Workhorse Linux combined metadata/serde profile — native acceptance slice

At fork-main source `20f1092db656f0037b817e4658feb3b828607e39`, native
Workhorse Linux kernel 7.2.11 x86_64, glibc 2.43 and Rust/Cargo 1.77.2, the
combined `testing-environ,sys,net,metadata,serde` profile compiled and ran
in one bounded owned POSIX runtime. The local preflight matched 446 current
files against the attempt64 source manifest; only `tests/sys_process.rs`
(SHA-256 `cce4c03768a74cbb391fbc3369c4daf16b35a7f5a9b4eea071aca6b73a2ade31`)
and `tests/serde.rs`
(`377d9d1c055085557aff1f9c5951978f58ea9211182d8d4f355730bcac0fc305`)
were overlaid. The remote runner `run-linux-metadata-serde.py` verified every
archived file and both overlays after transfer. Cargo.lock SHA-256 was
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The exact runner binding and raw exported results are in
`linux-metadata-serde-attempt01/`.

The bounded `cargo +1.77.2 test --locked --features
testing-environ,sys,net,metadata,serde` compiled 12 named targets with
`--no-run` (exit 0). The public combined sys/net selector with
`RHAI_COMBINED_WRONG_EXPECTATION=1` exited 101 at its independent fresh host
file readback. The `test_serde_json` selector with
`RHAI_SERDE_JSON_WRONG_EXPECTATION=1` exited 101 at the Dynamic JSON
integer-map round-trip assertion (actual 123, deliberately expected 124).
The restored 12-target suite exited 0: 193 top-level tests passed, 0 failed,
3 ignored. `net_metadata` passed two public TCP metadata JSON/signature tests;
the `serde` target passed 25 tests including the named round-trip. The outer
`sys_process` target passed 61 with 3 ignored. Nested `FAILED` lines in its
captured child-harness output are intended panic controls; the parent
assertions and target result passed.

The named tests use real host file/TCP peer observations and child-written
records/reaping. One independent combined Standards/Spec review returned PASS
for these paths. The two wrong controls calibrate their named assertions only;
the result does not establish exhaustive Serde behavior, ignored cases,
other feature/OS/core-MSRV rows or release acceptance.

The outer scoped-runner limit was 1200 seconds; compile, combined control,
Serde control and suite took 17.735, 0.064, 0.064 and 21.787 seconds. All four
exported logs matched `run.json` hashes before and after transfer. The runner
removed its private runtime; the exact session scope was read back empty and
retired with `rmdir`. The owned remote input/output stage and local transfer
stage were removed after evidence export and hash verification. Foreign
resources were untouched. The read-only reviewer relied on these cleanup
readbacks without independently querying remote state.
