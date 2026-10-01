# Verification provenance for the process representation patch

Implementation ref: `ad50147bb96305ea6bded9709e8a99e30be21721` (`Add process report representation API`). The checked Rust/test files in that commit are `src/packages/sys/config.rs`, `src/packages/sys/error.rs`, `src/packages/sys/mod.rs`, `src/packages/sys/process.rs`, and `tests/sys_process_report.rs`. The tests ran against the final formatted source before that commit; there were no Rust/test source edits between the final feature-matrix run and the implementation commit. The scoped Cargo output identifies the copied crate source under the private `.../agent-build-y4u6vsh7/src` runtime. No source snapshot manifest/hash was captured, so byte-for-byte identity of that removed copy is not independently re-verifiable.

The test session records Rust/Cargo 1.77.2 and the accepted compatibility lock from `.scratch/core-msrv-compatible-resolution/Cargo.lock`, SHA-256 `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa`. The lock was copied only into each scoped private source tree and used with `--locked`; no project lockfile or dependency was changed. The retained stdout does not include `rustc --version`, `cargo --version`, or the literal Cargo argument vector. Therefore the exact command line cannot be independently recovered from these artifacts. The target and feature selections below are the recorded selections, not reconstructed claims about a verbatim invocation:

| Evidence | Target and features | Result | Log |
|---|---|---|---|
| Final initial-source run and wrong-expectation control | `tests/sys_process_report.rs`, `testing-environ,sys,metadata` | 7/7; deliberately wrong Timeout message failed; restored expectation 7/7 | `verification-final.log` |
| Final synchronized no-index run | same target, `testing-environ,sys,sync,no_index` | 8/8, including Send+Sync assertions and Arc report read on a thread | `verification-feature-matrix.log` |
| Serde metadata run | same target, `testing-environ,sys,metadata,serde` | 7/7 | `verification-feature-matrix.log` |
| Integer-only run | same target, `testing-environ,sys,only_i32,no_float` | 7/7 | `verification-feature-matrix.log` |

All Cargo output is from the scoped copied source and private target, not from a shared project cache. The runner identifier was `agent-build-y4u6vsh7`; its runtime path was `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-y4u6vsh7`. The runner reported a sampled maximum of 1,593,047,263 bytes and a final pre-cleanup size of 1,797,533,949 bytes. Since the final measurement exceeds the sampled maximum, use 1,797,533,949 bytes (~1.67 GiB) as the largest recorded measurement; it is below the 2 GiB cap. This is not a claim about the true instantaneous peak between samples. After completion, an independent `test -e` check found both that runtime and the earlier `agent-build-6ri77dr5` runtime absent. No process/PID-level cleanup receipt or full runner transcript was retained.

The initial compatibility-lock failure and earlier harness/source findings are preserved in `verification-redgreen.log`, `verification.log`, and `harness-failures.md`. `verification-final.log` and `verification-feature-matrix.log` are retained run output; their section separators are harness-generated labels, not shell command transcripts.

Not covered by these representation tests: negative `no_object`, `no_std`, or wasm feature combinations, or native process lifecycle behavior on Linux/macOS/Windows. No production spawn/supervisor path was implemented here.
