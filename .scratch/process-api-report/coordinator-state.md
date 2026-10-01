# Process API report implementation state

Goal: implement the approved immutable process report/error representation and Engine accessors; no process spawning. This closes the representation prerequisite only; the full production process API and native lifecycle proof remain open.

Implementation is committed at `ad50147bb96305ea6bded9709e8a99e30be21721` (`Add process report representation API`). The commit changes `src/packages/sys/config.rs`, `src/packages/sys/error.rs`, `src/packages/sys/mod.rs`, `src/packages/sys/process.rs`, and `tests/sys_process_report.rs`; its Rust/test source matches the source tested immediately before commit. Worktree was clean after commit. Correction to verification documentation is now the only active change and will be committed separately without rebuilding.

Completed implementation:
- `ProcessScope` and default `DirectChild` configuration plus builder and host accessor.
- Public owned `ProcessReport`, `ProcessExit`, `ProcessDiagnostic`, and `ProcessCause`; script-facing report getters are read-only copies, with Blob/Array getters gated under `no_index` and indexed scalar diagnostic access kept available.
- Additive `SysError::Process`, preserving existing variants and using primary cause for classification/display; script `process` getter returns unit for prior error variants.
- Real Engine tests cover host-raised and caught causes, exact cause classification, error display, old error compatibility, report exit/status/completeness/timeout/diagnostics, mutation of copied blobs/collections on the same snapshot, no_index scalar/method behavior, and sync Send+Sync plus cross-thread sharing.

Verification outcomes: Rust/Cargo 1.77.2 with the accepted lock (`.scratch/core-msrv-compatible-resolution/Cargo.lock`, SHA-256 `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa`) copied into private source and used `--locked`. `testing-environ,sys,metadata`: 7/7; wrong Timeout display control failed, restored expectation passed 7/7. `testing-environ,sys,sync,no_index`: final synchronized version 8/8. `testing-environ,sys,metadata,serde`: 7/7. `testing-environ,sys,only_i32,no_float`: 7/7. Logs: `verification-final.log` and `verification-feature-matrix.log`. The exact CLI argument vector, tool version stdout, and private source snapshot digest were not captured; see `verification-index.md` for provenance limits.

Scoped-resource record: latest runner ID `agent-build-y4u6vsh7`; final runtime size 1,797,533,949 bytes (~1.67 GiB), below 2 GiB. Earlier sampled maximum was 1,593,047,263 bytes, which was lower than final; therefore report the larger final measurement as the largest recorded size and do not claim it is the true instantaneous peak. A post-run filesystem check independently found both `agent-build-y4u6vsh7` and `agent-build-6ri77dr5` runtime paths absent. No process/PID cleanup receipt was retained. No runner is live. See `verification-index.md`.

Remaining/unverified: negative `no_object`/`no_std`/wasm feature combinations and native Linux/macOS/Windows process lifecycle proofs. No production spawn/supervisor API is included. The parent is coordinating subsequent lifecycle work.

Launch history: the first 1.77.2 attempt failed setup due unlocked dependency resolution; diagnosis led to the accepted lock. A later attempt exposed the `i32` Dynamic mismatch and Engine catch harness issues, which were fixed. The accepted-lock run passed; a follow-up synchronized the final Send+Sync test and covered serde/integer-only feature gates. Earlier diagnostics remain in the referenced logs; this evidence correction did not launch a build.
