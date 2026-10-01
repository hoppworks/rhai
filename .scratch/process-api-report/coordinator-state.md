# Process API report implementation state

Goal: implement the approved immutable process report/error representation and Engine accessors; no process spawning. This closes the representation prerequisite only; the full production process API and native lifecycle proof remain open.

Checkpoint started 2026-10-01 07:39 UTC (repository work; approximate); latest checkpoint at 07:58 UTC, about 19 minutes elapsed of the 30-minute active-work planning checkpoint. The grouped follow-up was one scoped launch, with a 600-second timeout, two Cargo jobs, and a hard 2 GiB private runtime-storage cap. No runner is live. Latest runtime `agent-build-y4u6vsh7` was cleaned by the runner at completion. Observed peak private storage 1,593,047,263 bytes (~1.49 GiB); final pre-cleanup size 1,797,533,949 bytes (~1.67 GiB), under cap. Source/toolchain/Cargo home/target/temp were private; accepted lock SHA-256 `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa` copied into private source only.

Completed implementation:
- `ProcessScope` and default `DirectChild` configuration plus builder and host accessor.
- Public owned `ProcessReport`, `ProcessExit`, `ProcessDiagnostic`, and `ProcessCause`; script-facing report getters are read-only copies, with Blob/Array getters gated under `no_index` and indexed scalar diagnostic access kept available.
- Additive `SysError::Process`, preserving existing variants and using primary cause for classification/display; script `process` getter returns unit for prior error variants.
- Real Engine tests cover host-raised and caught causes, exact cause classification, error display, old error compatibility, report exit/status/completeness/timeout/diagnostics, mutation of copied blobs/collections on the same snapshot, no_index scalar/method behavior, and sync Send+Sync plus cross-thread sharing.

Verification chronology and evidence:
- TDD RED attempt is retained in `.scratch/process-api-report/verification-redgreen.log`; initial 1.77.2 resolution failure (`thin-vec 0.2.20` requires newer Cargo manifest support) was infrastructure, not an assertion failure. A later meaningful test failure exposed the integer dynamic representation and was fixed; prior concrete harness failures and diagnoses are in `harness-failures.md`.
- With accepted compatible lock, Rust 1.77.2 `testing-environ,sys,metadata`: 7/7 passed. The deliberate wrong Timeout display control failed the intended test; restored expectation passed 7/7. `testing-environ,sys,sync,no_index`: 7/7 passed in the first run. Full log: `verification-final.log`.
- Follow-up run synchronized the final source (including the sync assertion/thread test), formatted only edited files with private Rust 1.77.2 rustfmt, then reused a single private target. `testing-environ,sys,sync,no_index`: 8/8 passed, including compile-time Send+Sync assertions and actual Arc sharing across a thread. `testing-environ,sys,metadata,serde`: 7/7 passed. `testing-environ,sys,only_i32,no_float`: 7/7 passed. Maximum observed storage stayed under cap. Log: `verification-feature-matrix.log`.
- `git diff --check` passed after formatting. No source/build runner is live.

Remaining for this scoped step: final review, record the exact final command and source files, and commit atomically using `hoppworks <daniel@hoppworks.de>`. Do not push or merge. Negative `no_object`/`no_std`/wasm combinations and native Linux/macOS/Windows lifecycle proofs remain unverified/out of scope; no production spawn/supervisor API is included. The parent is coordinating subsequent process lifecycle work.

Launch history: the first 1.77.2 attempt failed setup due the unlocked dependency resolution; diagnosis led to reuse of the known accepted lock. A later stable attempt uncovered source/test issues that were corrected. The accepted-lock implementation run passed; one follow-up run was needed to synchronize the final sync assertions and cover serde/integer-only feature gates. Detailed command output is retained in the referenced logs.
