# Combined sys/net package acceptance — partial

## Result for source commit `679e7d7f`

On macOS 27.0 arm64 with Rust/Cargo 1.93.0, the new same-Engine integration test passed with these seven feature sets: baseline `testing-environ,sys,net`; plus `sync`; plus `no_index`; plus `metadata,serde`; plus `only_i32,no_float`; plus `unchecked`; and `no_index,sync,metadata`. The required `f32_float` matrix row is incomplete, so the combined release requirement remains open.

The tested source at `679e7d7f` registered `SysPackage` and `NetPackage` in one `Engine`. It created a confined temporary directory, had a Rhai script write a file and exchange distinct known strings over TCP, read the file afresh through `std::fs`, and checked both sent and received bytes at an independent loopback peer. Review later identified that the test used `read_string`, a single TCP read that could validly return fewer bytes than the peer wrote. The current source changes that call to `read_to_end_string` with the same length cap; the peer writes then closes, bounding the read at EOF. That corrected source has not been built or executed and is not covered by the prior test results below.

## False-green control

The exact targeted control command was:

```sh
RHAI_COMBINED_WRONG_EXPECTATION=1 cargo test --features testing-environ,sys,net --test combined_sys_net -- --exact sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors --test-threads=1 --nocapture
```

It exited 101 at the independent host-file assertion: actual bytes were `filesystem-payload`, while the injected expected bytes were `incorrect filesystem expectation`. With the normal expectation restored, the same combined test passed in every completed row. See `logs/false-green-control.log` and each completed `logs/row-NN.log`.

## Matrix evidence

The shared command shape for every row was:

```sh
cargo test --features <row-features> --test combined_sys_net --test sys_env --test sys_fs --test sys_policy --test net_connect --test net_listen --test net_reads --test net_writes -- --test-threads=1 --nocapture
```

For source commit `679e7d7f`, rows 01–07 each completed with exit status 0 and all eight test targets passing. Exact feature strings, commands, and statuses are in `logs/matrix-status.txt`; per-target counts and raw output are in `logs/row-01.log` through `logs/row-07.log`. Those results do not establish behavior of the corrected current source.

The `f32_float` row started under the same command shape but was interrupted before all targets completed. Its partial log records successful combined, net_connect, net_listen, net_reads, and net_writes targets; it does not record completion for sys_env, sys_fs, or sys_policy. A subsequent scoped attempt to resume that row was stopped immediately and produced no test result. Do not treat this feature combination as accepted. See `logs/row-08.log`, `logs/f32-environment.txt`, and `logs/f32-storage-samples.txt`.

The macOS filesystem reports `EILSEQ` while trying to create the non-UTF8 fixture. In each applicable sys_fs run the test reports the fixture limitation and returns successfully; those runs do not prove non-UTF8 directory-entry behavior on this host.

## Runtime and limits

Each launch copied the checkout/test source into a private `run_scoped.py` runtime with private `CARGO_HOME` and `CARGO_TARGET_DIR`, two Cargo jobs, and serial test execution. The first full matrix runtime was sampled every ten seconds. Its largest recorded sample was **2,675,624 KiB**, above the 2-GiB cap. This is a sampled size, not a measured actual peak. The invocation was stopped, and its exact runtime directory was independently confirmed absent. A separately started f32 runtime was interrupted immediately on instruction; its exact directory was also confirmed absent. The remaining work stopped at the hard resource limit. No process behavior, Linux/Windows platform behavior, or MSRV behavior is claimed.

Existing unchanged package evidence is referenced at `.scratch/all-tickets/combined-sys-proof.md`, `.scratch/tcp-connect/proof.md`, and `.scratch/net-feature-proof/proof.md`. The independently reviewed release proposal is `.scratch/all-tickets/release-proposal.md`. The separate net `no_object` result remains covered by its accepted proof; sys `no_object` incompatibility remains explicit.

## Files

- New integration contract: `tests/combined_sys_net.rs`
- Exact matrix commands and per-row statuses: `logs/matrix-status.txt`
- Full test output: `logs/row-01.log` through `logs/row-08.log`
- False-green control: `logs/false-green-control.log`
- Environment and runtime observations: `logs/environment.txt`, `logs/storage-samples.txt`, `logs/f32-environment.txt`, `logs/f32-storage-samples.txt`
- Scoped invocation scripts: `run-matrix.sh`, `run-targeted.sh`, `run-f32.sh`


## Authorized corrected-source follow-up (pending root gate)

The follow-up is limited to the corrected same-Engine test source and bounded native macOS package matrix. The accepted proposal is `.scratch/all-tickets/briefs/combined-package-followup.md`. No follow-up runtime result is accepted until the immutable source gate is reviewed and the single scoped invocation completes within its limits. Required outcomes are the corrected combined test across all eight approved feature profiles; the complete eight-target `f32_float` row; and one exact wrong fresh-host-file expectation failure with status 101 followed by a restored passing baseline.

The new control matcher must establish the exact failing Rust test, host-readback assertion, actual bytes `filesystem-payload`, and injected expected bytes `incorrect filesystem expectation`, while accepting the optional Rust test-thread ID in the quoted panic name. Matching only status 101 or a panic phrase is insufficient. The launcher caps the sole scoped invocation at the smaller of 600 seconds and the remaining absolute deadline. The driver uses the accepted native macOS process ancestry, fail-closed one-second resource sampler, per-case UTC checks, private generated/exported lockfile with `--locked` tests, and independent PID/start/group/runtime cleanup readback. Prior seven full target rows remain applicable only to their unchanged targets and earlier source; they do not verify this corrected combined assertion.
