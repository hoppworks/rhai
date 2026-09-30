# Core Rust 1.66 check

- Source: `a6241621b3fc15a151a2e41a0f60e04943bd79ee` (integrated source, clean at start).
- Contract: `Cargo.toml` declares `rust-version = "1.66.0"`; default features are `std` and `ahash/runtime-rng`.
- Host: Darwin 27.0.0, arm64 (`aarch64-apple-darwin`). `rustc +1.66.0 --version --verbose` reports rustc 1.66.0 (69f9c33d7, 2022-12-12); `cargo +1.66.0 --version --verbose` reports Cargo 1.66.0 (d65d197ad, 2022-11-15).
- Command: `cargo +1.66.0 check --lib` with default features, run from a private copy by `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 300 -- ...`; `CARGO_HOME` and `CARGO_TARGET_DIR` were inside `AGENT_RUNTIME_DIR`.
- Result: exit status 101; the library did not compile. Resolution selected `thin-vec v0.2.20` from the declared `thin-vec = "0.2.13"` semver range. Cargo 1.66 failed parsing its manifest because it uses edition 2024, which Cargo 1.66 does not support. This is an unsupported resolved dependency boundary for the advertised minimum, not an infrastructure failure. No lockfile was present or supplied; the check used the then-current unpinned resolution. Resolution stopped before creating a usable lockfile.
- Exact Cargo output is in [cargo-check.log](cargo-check.log).
- Scoped cleanup readback: runner runtime `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-60t9_tg7` no longer existed after exit (`test -e` returned 1). No retry was run.
- Scope: this proves neither runtime/E2E behavior nor sys/package features or a release matrix. Existing native sys evidence was not rerun.
