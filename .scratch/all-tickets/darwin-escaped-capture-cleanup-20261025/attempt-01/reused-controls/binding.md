# Reused expected-RED controls

The exact named test-function bodies are byte-identical between source commit
`9042ee19628e9794ff37d5814386406a894a0c0d` and current candidate
`2cb6b67a9b13c2b5f363e2d2767ac6ec40898038`:

- `managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes` — SHA-256 `0b422b5f4c4c4be41bdd115699981ef784e98e7561af5a47ad073804a719e678`.
- `managed_spawn_post_reap_cancel_bounds_escaped_capture` — SHA-256 `282cd43fe8b89611707d1dda1461461041f794ad2e230fff328c227f5a54fba1`.

The only `src/packages/sys/process/unix.rs` delta from 9042 to the current candidate is a `cfg(not(feature = "unchecked"))` guard inside an internal unit test. The integration-test runtime implementation is unchanged. The original RED logs bind the named assertion, status 101, Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2, `testing-environ,sys`, and lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

The cleanup correction changes only fixture cleanup support and adds an exact-identity cleanup contract test. It does not change either tested public assertion or the Unix process implementation. The restored GREEN selectors are re-run on the integrated candidate after this correction; the two original expected-RED controls are retained without rebuilding.

The old and current `uname` host labels differ (`Daniels-MBP-2.fritz.box` versus
`Daniels-MacBook-Pro-2.local`); both report Darwin kernel 27.0.0, arm64, the same
macOS 27.0.1 build and Rust/Cargo 1.77.2. The selectors use unique scoped
temporary roots and do not depend on the hostname. This difference is retained
explicitly rather than claiming identical machine metadata.
