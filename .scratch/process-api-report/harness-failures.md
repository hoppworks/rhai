# Test harness and setup correction record

The first Rust 1.77.2 attempt did not reach the test assertions: unlocked resolution selected `thin-vec 0.2.20`, whose manifest requires Cargo edition2024 support. The later runs used the approved compatible lock copied into the private source tree with `--locked`; no dependency change was made.

A test build exposed `i32` report getters as Rhai custom `i32` values, which did not compare with script integers. Changed both getters to `Dynamic::from_int`; final Rust 1.77.2 Engine runs passed for all recorded feature selections. The false-green control intentionally changed the expected Timeout message and failed the relevant assertion, then the restored expectation passed.

Earlier Engine catch tests incorrectly attempted to use `try` as an expression, first returning unit and then producing a parse error after a harness-only rewrite. The scripts were changed to initialize a boolean, assign it inside `catch`, and return it. The corrected catch harness is covered by the final passing results in `verification-final.log` and `verification-feature-matrix.log`; these were harness errors, not implementation regressions.

More complete verification provenance and explicit limits are in `verification-index.md`.
