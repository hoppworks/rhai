# X31 Darwin arm64 Rust/Cargo 1.77.2 — named rows

## Scope and binding

This attempt covers only native Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2, source commit 05320c2c9bf3d4396956632e0cc1706e96c94b15, lock SHA-256 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425, and features testing-environ,sys,sync plus testing-environ,sys,sync,no_float. The exact test is packages::sys::process::unix::tests::public_wait_is_cancelled_after_entering_condvar. Other platforms/features/MSRVs and non-sync blocking-entry remain open.

The staged Cargo.toml, src/packages/sys/process.rs, src/packages/sys/process/unix.rs, and lock match the pinned SHA-256 values in source-preflight.txt. The actual cwd was the staged archive under the unique owned runtime. Toolchain host was aarch64-apple-darwin. Cargo ran with one build job, a private CARGO_HOME/target, and the unchanged lock. Escalation 26's diagnosed cause was resolved by omitting only unfiltered cargo metadata; direct cargo +1.77.2 test --locked was used. No product or committed test source was changed.

## Assertion sensitivity and real behavior

For each feature row, the exact wait-entry predicate mutation produced Cargo status 101, the exact test ID, the expected 0-passed/1-failed libtest result, the unique X31 RED assertion marker, a positive nonterminal wait-entry checkpoint, and exact fixture-child ESRCH cleanup. Restoring the baseline source produced Cargo status 0, the exact test ID and 1-passed/0-failed result, a positive wait-entry/nonterminal checkpoint, public cancellation/wakeup, and ESRCH reaping.

The independent post-run readback confirms all four fixture PIDs are absent, the runtime cwd and exact session scope are removed, and runner status is 0. The attempt evidence manifest is SHA-256 checked. The build target occupied 544,160 KiB and private Cargo home 40,132 KiB immediately before cleanup. Run durations and raw outputs are preserved alongside commands, environment, hashes, mutation diff, restoration receipt, and cleanup receipts.

## Review status

The combined independent review returned READY on 2026-10-08 for the two named X31 Darwin Rust/Cargo 1.77.2 feature rows; see review.md. This does not close X31 globally or package A–F.
