# Core Rust 1.66 compatible resolution proof

## Goal and starting boundary

- Scope: prove the integrated core crate's default library build at Rust 1.66.0, then execute one real Engine evaluation with an independent expected result.
- Source: coordinator `c4646230e5c757beafab93b3978ab5afc6b15c6f`.
- Recorded start: 2026-09-30 12:37:46 UTC.
- Prior diagnostic read before any launch: `.scratch/core-msrv-check/proof.md` and `cargo-check.log`. That unlocked run used another source revision and stopped while parsing `thin-vec 0.2.20` (edition 2024), before Rhai compilation; it is not counted as a core source failure or compatible-resolution attempt.
- Approved boundaries: keep core `rust-version = 1.66.0`; sys/net and optional-package MSRVs are out of scope; preserve exact resolved lock as evidence; no install, global Cargo configuration, remote operation, push or merge.

## Attempts

This is an independent proof against the frozen coordinator source. Registry packages and index data were copied into each invocation's private `CARGO_HOME`; no home config or toolchain installation was changed. The source manifests/workspace are unmodified.


## Launch 1 (setup boundary)

- Scoped invocation: `python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 900 -- python3 .scratch/core-msrv-compatible-resolution/run-proof.py`.
- Job-limit evidence: neither this command line nor `run_scoped.py` sets `CARGO_BUILD_JOBS` (`run_scoped.py` adds only `AGENT_RUNTIME_DIR` and private `TMPDIR`/`TMP`/`TEMP`). The helper copied the inherited environment and did not set this variable. Its exact inherited value at launch was not captured, so compliance with the requested two-job limit is unverified; do not infer it from the successful build. No rebuild is authorized for this evidence correction.
- Result: helper setup failed before any Cargo command because it pre-created `CARGO_HOME/git` before `shutil.copytree` copied the existing local Git cache. This is a harness/setup error, not a resolver or source failure.
- Scoped runtime printed by the wrapper: `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-t82z8zpu`; cleanup readback confirmed (`test -e` returned 1).
- Correction: let `copytree` create the private Git cache destination. The next bounded invocation will repeat private cache/source preparation and make the first Cargo attempt.

## Launch 2 (old-Cargo compatibility boundary)

- Private caches/source copy and offline lock preparation completed; modern Cargo generated a v4 lock with `resolver.incompatible-rust-versions="fallback"`, then the proof normalized the lock schema marker to v3 for Cargo 1.66.
- Lock selection: `thin-vec 0.2.18`; modern resolver announced “Locking 120 packages to latest Rust 1.66.0 compatible versions.” This lock spans workspace and inactive target/optional edges, some of which remain above 1.66 and are out of this default-core acceptance scope.
- Cargo 1.66 accepted the v3 lock, then `cargo metadata --offline --locked` over the full workspace failed at `web-time 1.1.0 -> js-sys 0.3.106`: the wasm-only dependency asks for a feature using optional-dependency syntax unknown to Cargo 1.66. This is an inactive target/full-workspace resolution boundary. Exact attempted lock retained as `workspace-attempt.lock`; logs retained in `resolve.log` and `old-cargo-metadata.log`.
- The metadata diagnostic is not accepted as the requested build result. Next launch directly invokes `cargo +1.66.0 check --lib --offline --locked` against the same full source/manifest copy to identify whether that boundary affects the actual native default library gate.

## Launch 3 (direct core gate boundary)

- With the original full workspace and manifests preserved, the requested direct `cargo +1.66.0 check --lib --offline --locked` also exits 101 before compiling Rhai. It reproduces the inactive wasm `web-time -> js-sys 0.3.106` conflict caused by the latter's `dep:` feature declaration; exact output is `core-check.log`, lock retained as `cargo-check-boundary.lock`.
- This concrete resolver incompatibility justifies a precise Cargo.lock selection: set `js-sys` to 0.3.91 (whose registry metadata predates the conflicting `dep:` feature syntax) while leaving every manifest and workspace member unchanged. The crate is wasm-target-specific and is not built in this Darwin native default-feature gate; this does not prove the wasm target's compiler MSRV.
- Next launch regenerates the full-resolution lock, applies only this precise lock update, normalizes the lock schema to v3, and retries Cargo 1.66 with the exact source manifest.

## Launch 4 (lock downgrade dependency boundary)

- Modern Cargo could not apply only `js-sys 0.3.91`: that release requires exact `wasm-bindgen 0.2.114`, while unchanged packages in the current lock still selected `wasm-bindgen 0.2.129` and descendants. Cargo reported a version conflict before any old-Cargo build; no package source was compiled.
- The full workspace lock remains intact as `lock-before-compatible-update-2.lock`; exact solver output is `compatibility-lock-update-boundary.log`.
- Next attempt unlocks only the four exact locked `wasm-bindgen` family packages so Cargo can choose the `js-sys 0.3.91` dependency closure. The source remains unchanged.

## Launch 5 (update-command boundary)

- The attempted `cargo +stable update --offline --recursive -p js-sys --precise 0.3.91` was rejected by Cargo itself because `--recursive` and `--precise` cannot be combined. No lock resolution or old-Cargo check occurred; this is a command-shape/setup failure.
- Exact command output and pre-command lock retained as `recursive-flag-error.log` and `recursive-flag-error.lock`.
- Next attempt removes only the four locked `wasm-bindgen` family entries in the private generated lock, then lets Cargo re-resolve that family while applying the exact `js-sys 0.3.91` update. All source manifests stay unchanged; the exported final lock must be re-read by Cargo 1.66 before compilation.

## Launch 6 (local cache boundary)

- Original offline registry archives lacked `js-sys 0.3.91` / `wasm-bindgen 0.2.114`, while the previously locked newer family blocked a direct precise update. Parent authorization allowed fetching public registry inputs into the private scoped Cargo home; the next attempt did so instead of narrowing the manifest.

## Launch 7 (compatible lock and native core acceptance)

- Scoped invocation: `python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 900 -- python3 .scratch/core-msrv-compatible-resolution/run-proof.py`.
- Modern Cargo 1.93 generated the complete workspace lock with `resolver.incompatible-rust-versions="fallback"` (“Locking 133 packages to latest Rust 1.66.0 compatible versions”), including many optional/inactive packages with higher MSRVs. It initially selected `js-sys 0.3.82` and `wasm-bindgen 0.2.105`. The proof then unlocked only the four wasm-bindgen family lock entries and ran `cargo +stable update -p js-sys --precise 0.3.91`, selecting `js-sys 0.3.91` plus the complete `wasm-bindgen 0.2.114` family. This is lock-only resolution; no manifests were modified. The exact final lock is included as `Cargo.lock`.
- The lock schema marker was set to v3 for Cargo 1.66.0. Exact command `cargo +1.66.0 check --lib --locked --target aarch64-apple-darwin` succeeded (exit 0); `core-check.log` shows Rhai and codegen compile. It ran on Darwin arm64. This establishes the default-feature core library check on the host triple, not all features, other targets, or full workspace tests.
- A temporary example in the private source copy ran the actual `rhai::Engine` on `40 + 2`; observed `42`, matching the separately specified expected result (exit 0). Exact output is `engine-positive.log`.
- The same example's wrong-result control changed only its expected value to 43; it panicked with left 42/right 43 and exited 101, confirming the check is sensitive to a wrong result. Exact output is `engine-wrong-control.log`.
- Sampled private runtime storage (`du -sk` after each command) peaked at 1,317,696 KiB, below the 2 GiB limit. Wrapper cleanup readback: `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-5yr5quw3` no longer exists (`test -e` returned 1). These are sampled post-command totals, not a continuous peak measurement.

## Conclusion and remaining scope

The prior diagnostic's exact boundary was Cargo 1.66 rejecting the `edition = "2024"` manifest in unlocked `thin-vec 0.2.20` before Rhai compilation. On the frozen coordinator source, a complete compatible Cargo.lock selection avoids that and additionally resolves the full workspace's old-Cargo `js-sys` feature-syntax incompatibility. With this lock, Cargo 1.66.0 compiles the default core library and the real Engine smoke check returns the expected value. No production lock or manifest was changed; evidence lock is private proof output. The wasm target, optional package features, and workspace tests remain outside this bounded default-core proof.
