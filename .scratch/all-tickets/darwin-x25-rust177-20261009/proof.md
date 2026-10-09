# Darwin X25 managed kill acceptance — Rust 1.77.2

This accepts the named Darwin X25 `testing-environ,sys` profile at Rust/Cargo
1.77.2. Through a real Rhai script, public `Engine`, and managed host package,
the test starts a leader/worker/leaf group, calls `child.kill()` and bounded
`child.wait(0.5)`, observes the unsuccessful non-unit report, independently
observes ESRCH for all three managed PIDs, confirms the unrelated sentinel is
still live at API return, then explicitly terminates/reaps that sentinel.

- Platform: Darwin arm64, macOS 27.0.1 (Darwin kernel 27.0.0).
- Toolchain: rustc/cargo 1.77.2.
- Features: `testing-environ,sys`.
- Integrated source revision: `76fdebd77cfcd5cc6e27df9cc95198a9cf030746`.
- `tests/sys_process.rs`: `a8fdc21e73b56bf12c82603c941b7c22b01c942a56d5f649ff2ec98b494c935c`.
- `src/packages/sys/process/unix.rs`: `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`.
- `Cargo.lock`: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Exact command: `cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel -- --exact --nocapture`.

Attempt 02 inverted only the final sentinel-reap expectation in an owned source
copy. Cargo ran the exact test and returned 101; the output records all managed
PIDs absent, the sentinel killed/reaped, then the deliberately wrong expectation
failing with `fixture must reap its exact sentinel`. Its wrapper returned 1
because its parser incorrectly required the Rust assertion expression despite
the test's custom panic message. This is a valid expected RED, not a product or
build failure. The reconstructed mutant source hash is recorded separately.
Attempt 03 restored the unmodified source and passed the same selector (Cargo
and scoped runner both 0), with independent ESRCH and sentinel readback in the
log. Attempt 01 stopped before Cargo because the first mutation anchor matched
multiple tests; no test ran.

The RED and GREEN bind the same revision, test/product source, lock, features,
toolchain and native environment. The exact private runtime and each empty
owned session scope were retired; no build cache remains. Combined independent
Standards/Spec review passed after cleanup. This adds one named profile to the
previously recorded Darwin Rust 1.93.0 and Linux rows; other OS, feature/MSRV,
Ticket 03 and A–F requirements remain open. The older 1.93 proof path still
listed in the plan is absent from this checkout and was not used for this result.

Raw evidence and statuses: `attempt-01/preparation.md`,
`attempt-02/{environment.txt,source-sha256.txt,red.log,red.status,runner.status}`,
and `attempt-03/{environment.txt,source-sha256.txt,green.log,green.status,runner.status}`.
