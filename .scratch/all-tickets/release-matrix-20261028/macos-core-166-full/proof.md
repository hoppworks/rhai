# macOS Rust 1.66 default core library test

Status: **accepted for the default-feature `cargo test --locked --lib` slice on macOS arm64 with Rust/Cargo 1.66.0**. This does not close the wider release matrix or Windows process work.

The test-only change in `src/tests.rs` replaces an exact 48-byte `LexError` assertion with a maximum of 56 bytes. The initial full core attempt compiled at source commit `8d8bf84febebb182ca65f2307f96676f05858eb2` and lock SHA-256 `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`, then failed the original assertion: actual 56 versus expected 48 (`attempt01/`). A focused layout probe independently observed 56 bytes with Rust 1.66.0 and 48 bytes with stable on this arm64 host (`layout-probe/`).

The first corrected attempt used a private offline Cargo cache; `ahash v0.8.12` was absent, so Cargo stopped before any test (`attempt02/`). The final bounded run allowed Cargo to fetch the missing crate. Its `result.json` binds the same source commit and lock to the current test overlay SHA-256 `3949a1ea368a1408ad9b410b0573194402146f5fd519f087728359ac62f942e2`. Rust and Cargo reported 1.66.0; `cargo test --locked --lib --target aarch64-apple-darwin` exited 0 with 1 passed, 0 failed (`command-*.log`). The owned source, Cargo home, target and downloads stayed inside the scoped runtime; the exported logs and manifest precede cleanup. The empty session scope was retired with `rmdir`.

One independent combined Standards/Spec review passed the scoped change and evidence binding. Its coverage is limited to this core test slice. The previously accepted Engine example and other unchanged matrix proofs remain applicable at their recorded source scopes; no broad rerun was inferred from this test-only change.
