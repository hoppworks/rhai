# macOS combined metadata/serde profile — native acceptance slice

At fork-main source `3e19f6711110d06124e4407dd04496c4fc60ff22`, macOS 27.2
arm64 and Rust/Cargo 1.77.2, the combined
`testing-environ,sys,net,metadata,serde` profile compiled and ran in one
bounded owned POSIX runtime. The runner `run-macos-metadata-serde.py` verified
the 448-file attempt64 source manifest against the checkout, with only the
current `tests/sys_process.rs` overlay at SHA-256
`cce4c03768a74cbb391fbc3369c4daf16b35a7f5a9b4eea071aca6b73a2ade31`.
The pinned Cargo.lock SHA-256 was
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
Source, target and cache were private to `AGENT_RUNTIME_DIR`; exported raw
logs and `run.json` are under `macos-metadata-serde-attempt01/`.

The bounded `cargo +1.77.2 test --locked --features
testing-environ,sys,net,metadata,serde` command compiled 11 named targets
with `--no-run` (exit 0). The exact public combined sys/net selector with
`RHAI_COMBINED_WRONG_EXPECTATION=1` exited 101 at the independent fresh host
filesystem readback assertion. Restored execution of the same 11-target suite
exited 0: 160 passed, 0 failed, 1 ignored. Two `net_metadata` tests parsed
public JSON function metadata and checked documented TCP types, signatures
and operations; the `sys_policy` target also checked sys metadata. The
`serde` feature was enabled throughout. The later targeted run below checks
a distinct Dynamic serialization round-trip; other serialization semantics
are not inferred.
The outer `sys_process` target passed 52 tests with 1 ignored. Its captured
nested fixture output includes an expected child-harness `FAILED` line for
an intentional negative control; the parent assertions and final target passed.

The independent review of attempt 01 found that no distinct Rhai Serde
round-trip had run. A test-only wrong-expectation switch was added to the
existing `tests/serde.rs::test_serde_json` assertion. Attempt 02 overlaid that
test at SHA-256 `377d9d1c055085557aff1f9c5951978f58ea9211182d8d4f355730bcac0fc305`
alongside the unchanged process test; every other archived file and the lock
matched attempt 01. The exact Serde selector with
`RHAI_SERDE_JSON_WRONG_EXPECTATION=1` exited 101 at the integer-map
round-trip assertion (actual 123, deliberately expected 124). Restored
`--test serde` passed 25/25 in the same private scope. This targeted addition
does not turn attempt 01 into one twelve-target invocation; its other targets
remain applicable because only the previously unselected Serde test changed.
Raw logs and command bindings are in `macos-metadata-serde-attempt02/`.
The combined independent review and focused recheck returned PASS for these
named cases. The Serde control proves the Rust `Dynamic` JSON round-trip
assertion; it does not establish a Rhai-script serialization scenario.

The combined test independently reads a host file and observes a TCP peer;
named process cases use child-written records and reaping observations. This
slice does not close other features, OS, core MSRV or full release acceptance.
The outer scoped-runner limit was 1200 seconds; compile, wrong control and
suite took 16.533, 0.379 and 12.213 seconds. All three exported step logs
match their `run.json` hashes. The runner removed its private runtime; the
exact session scope was read back empty and retired with `rmdir`. Attempt 02's
compile, wrong control and Serde suite took 17.393, 0.443 and 0.145 seconds;
its three logs were hash-checked and its exact empty scope was also retired.
