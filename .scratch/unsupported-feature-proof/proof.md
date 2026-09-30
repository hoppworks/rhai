# Unsupported feature compiler-gate proof

## Source change

`Cargo.toml` moves the existing optional `cap-std = { version = "4.0", optional = true }` dependency under `cfg(not(target_family = "wasm"))`. The `sys` feature still enables `dep:cap-std`; native dependency version and feature semantics are unchanged. This prevents an unsupported WASM `sys` build from failing inside the errno dependency before Rhai's own feature guard can be diagnosed.

## Compiler gates

The accepted exact diagnostics, all from nonzero compiler exits, are recorded in `results.tsv`; raw logs are under `logs/`.

- `sys,no_std`: exit 101 and one intended diagnostic, verified by the single affected-only recovery after its first log was overwritten. Command: `cargo check --locked --no-default-features --features sys,no_std`.
- `net,no_std`: exit 101 and one intended diagnostic.
- `sys,no_object`: exit 101 and one intended diagnostic. The private-copy guard-removed control exits 101 but has zero intended diagnostics and is rejected by the matcher; restoring the guard yields the intended diagnostic again.
- On both installed WASM targets, `wasm32-unknown-unknown` and `wasm32-wasip1`, `sys` and `net` individually produce their intended Rhai package diagnostic. The combined `sys,net` case produces both diagnostics exactly once. These target checks are all retained in the corresponding raw logs.

Rust toolchain: rustc 1.93.0, cargo 1.93.0, host `aarch64-apple-darwin`. Installed targets were `aarch64-apple-darwin`, `wasm32-unknown-unknown`, `wasm32-wasip1`, and `x86_64-unknown-linux-gnu`. No target was installed for this proof.

The base-revision manifest boundary is retained in `logs/prechange-sys-wasm-unknown-boundary.log`: `sys` on `wasm32-unknown-unknown` fails in errno with its unsupported-target diagnostic before the Rhai `sys` guard. The first harness wrapper returned 1 because its separate boundary wording predicate expected `it is` where the compiler printed `it's`; this was a matcher wording issue. The raw compiler outcomes and exact package diagnostics are preserved. The corrected matcher was syntax-checked, but the full matrix was not rerun. See `attempt-history.md` for the overwritten-log recovery and why no other results were rerun.

## Native dependency smoke

`native-smoke-results.tsv` records a targeted existing `sys_fs` test. With the changed manifest, the correct expectation passes (one test); a wrong expected value fails at the fixture assertion with the observed value in the log; restoring the correct expectation passes. This proves the optional `cap-std` dependency remains available to a native `sys` package build.

## Resource bounds and cleanup

Checks ran in private `run_scoped.py` runtimes with a private Cargo home and target directory, jobs=2, dev/test debug info disabled, and incremental compilation disabled. The original completed invocation sampled runtime storage every second and enforced a preemptive 1.5 GiB ceiling; see `metrics.txt` and `resource-samples.tsv` (52.146 seconds, sampled peak 405,528,576 bytes). The targeted recovery also enforced the same ceiling; see `attempt3-metrics.txt` and `attempt3-resource-samples.tsv` (12.542 seconds, sampled peak 124,112,896 bytes). Every exact runtime, including the interrupted and setup-only attempts, is listed in `attempt-history.md` and checked absent after cleanup.

The exact captured lockfile used by both the completed invocation and targeted recovery is preserved as `scoped-Cargo.lock`. SHA-256 for that lockfile: `4aa2e32287d33184c12e98c7a86a17574dbf3a2361c968c76e9611bfd4396cc3`.

## Scope

This proves the specified compiler feature guards, the native `sys` dependency smoke, and matcher behavior on the existing fixture control. It does not claim broad runtime behavior, all platforms, Windows, MSRV coverage, or a full strict application E2E test.
