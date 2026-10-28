# macOS combined integer-only profile — native acceptance slice

At fork-main source `ac902e52079b9179f8d1da2ef757a963608321bf`, macOS 27.2
arm64 and Rust/Cargo 1.77.2, the combined
`testing-environ,sys,net,only_i32,no_float` profile compiled and executed in
one bounded owned POSIX runtime. The runner
`run-macos-onlyi32-nofloat.py` verified all 447 unchanged source files against
the attempt64 manifest, overlaid the current `tests/sys_process.rs` at SHA-256
`cce4c03768a74cbb391fbc3369c4daf16b35a7f5a9b4eea071aca6b73a2ade31`,
and used pinned lock SHA-256
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The source and Cargo-generated files, target and cache were private to
`AGENT_RUNTIME_DIR`; exported `run.json` and raw logs are under
`macos-onlyi32-nofloat-attempt01/`.

The bounded `cargo +1.77.2 test --locked --features
testing-environ,sys,net,only_i32,no_float` compile of 11 named integration
targets (`--no-run`) exited 0. The exact public combined sys/net test with
`RHAI_COMBINED_WRONG_EXPECTATION=1` exited 101 at the fresh independent host
filesystem readback assertion, reporting actual `filesystem-payload` against
the deliberately incorrect expected value. Restored execution of the same
11-target suite exited 0: 135 passed, 0 failed, 1 ignored. The targets covered
combined coexistence, TCP connect/listen/read/write, sys env/fs/policy/process
and process-report behavior. `net_metadata` compiled but ran zero tests because
this profile does not enable `metadata`; it is not counted as a metadata proof.
The full `sys_process` harness reported 30 passed, 0 failed, 1 ignored; its
captured nested fixture output contains expected child-harness `FAILED` lines
for deliberate negative controls, while the parent assertions and target passed.

The real combined test independently reads the host file and observes the TCP
peer; the process target includes child-written records and reaping observations
at its named cases. These results establish this exact native feature-profile
slice and do not establish exhaustive `only_i32` overflow or `no_float` API
semantics, metadata, the ignored overhead test, other OS/feature/core-MSRV rows
or full release acceptance. One independent combined Standards/Spec review
returned PASS for this narrow result with those limits; the wrong-expectation
control calibrates its own filesystem assertion, not every suite assertion.
The scoped runner's outer limit was 1200 seconds; compile, wrong control and
suite took 17.554, 0.324 and 7.713 seconds. The private runtime was removed,
the exact session scope was observed empty and retired with `rmdir`. No foreign
scope was touched.
