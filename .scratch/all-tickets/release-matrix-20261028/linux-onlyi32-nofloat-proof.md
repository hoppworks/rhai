# Workhorse Linux combined integer-only profile — native acceptance slice

At fork-main source `272c8a8000a2ce2f63dd073187f55567d8c27129`, native
Workhorse Linux kernel 7.2.11 x86_64, glibc 2.43 and Rust/Cargo 1.77.2, the
combined `testing-environ,sys,net,only_i32,no_float` profile compiled and ran
in one bounded owned POSIX runtime. The local source preflight matched all 447
non-overlay files in the attempt64 448-file manifest to the current checkout;
`tests/sys_process.rs` was the only difference and its current SHA-256
`cce4c03768a74cbb391fbc3369c4daf16b35a7f5a9b4eea071aca6b73a2ade31`
was transferred as an exact overlay. The remote runner verified every archived
file against the manifest and the transfer hashes, then copied source and
Cargo.lock into its private runtime. The lock SHA-256 was
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The exact runner, binding and exported raw evidence are at
`run-linux-onlyi32-nofloat.py` and `linux-onlyi32-nofloat-attempt01/`.

`cargo +1.77.2 test --locked --features
testing-environ,sys,net,only_i32,no_float` compiled the 11 named targets in
`run.json` with `--no-run` (exit 0). The exact public combined sys/net selector
with `RHAI_COMBINED_WRONG_EXPECTATION=1` exited 101 at its fresh host
filesystem readback assertion. The restored 11-target suite exited 0 with
135 passed, 0 failed and 2 ignored. `net_metadata` compiled but ran zero tests
because this profile omits `metadata`; it is not counted as a metadata proof.
The outer `sys_process` target passed 31 tests with 2 ignored. Its captured
nested fixture output contains expected `FAILED` lines for intentional negative
controls; the parent assertions and final target exit passed.

The combined test independently reads the host file and observes a TCP peer;
named process cases also record child output and reaping. This is evidence for
the executed Linux feature-profile slice, not exhaustive `only_i32` overflow,
`no_float` surface, other features, platforms, core MSRV or release acceptance.
One independent combined Standards/Spec review returned PASS at this scope;
the wrong control calibrates the combined filesystem assertion only. The
read-only reviewer relied on the recorded scope/stage cleanup readback.
The outer scoped-runner limit was 1200 seconds; compile, control and suite took
17.188, 0.064 and 13.029 seconds. Each exported step log was hash-checked
against `run.json` before and after transfer. The runner removed its private
runtime; the exact session scope was read back empty, then retired with
`rmdir`. The owned remote input/output stage and local transfer stage were
removed after evidence export and hash verification; foreign resources were
not touched.
