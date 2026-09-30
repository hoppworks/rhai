# Rust 1.66 dependency diagnostic (baseline only)

## Scope and source identity

The one scoped Cargo invocation was run from a private copy of `a6241621b3fc15a151a2e41a0f60e04943bd79ee` (the then-current `main` checkout), not from the requested frozen `task/all-tickets` source. The requested source is `b031ce8dfc9d1624a8a2d14a85fd70c29fd413d3`. This evidence is therefore a baseline dependency-resolution diagnostic, not a check of the integrated source.

Both revisions declare `rust-version = "1.66.0"`, the same root `thin-vec = { version = "0.2.13", default-features = false }` dependency, and the same `[patch.crates-io]` override for `rustyline` at `https://github.com/schungx/rustyline`, branch `v15_fake`. `codegen/Cargo.toml` is unchanged. Thus the tested root manifest's thin-vec resolver input and patch policy match the requested source. The baseline resolver selected `thin-vec 0.2.20`; its manifest failed to parse under Cargo 1.66 because it uses edition 2024. This supports a narrow warning that the unchanged dependency declaration can resolve to a package Cargo 1.66 cannot parse in an unlocked resolution. It does not establish that the frozen integrated source resolves identically or fails at the same point.

The frozen source has other relevant changes absent from the tested revision: `cap-std = "4.0"` as an optional dependency; a `sys` feature enabling it; `sys` added to docs.rs features; new `src/packages/sys/**` implementation and registration changes in `src/packages/mod.rs`; plus sys tests and additional project files. None of those changes were part of the Cargo invocation. Their effect on default `cargo check --lib` and the integrated dependency graph remains untested.

## Invocation and result

- Host: Darwin 27.0.0, arm64 (`aarch64-apple-darwin`).
- Toolchain: rustc 1.66.0 (69f9c33d7, 2022-12-12); Cargo 1.66.0 (d65d197ad, 2022-11-15).
- Command: `cargo +1.66.0 check --lib`, default features, run from a private source copy by `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 300 -- ...`; Cargo home and target directory were private to the runner runtime.
- Exit status: 101, during dependency manifest parsing, before Rhai library compilation. Exact output: [cargo-check.log](cargo-check.log).
- No lockfile was supplied or created. The run used unlocked resolution and stopped before producing a usable lockfile.
- Scoped cleanup readback: runner runtime `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-60t9_tg7` did not exist after exit (`test -e` returned 1).

No Rust 1.66 compilation pass is established for either source revision. The integrated `task/all-tickets` default core behavior, sys/package features, runtime/E2E behavior, and release matrix remain unverified. The one-check limit was honored; no retry was run.
