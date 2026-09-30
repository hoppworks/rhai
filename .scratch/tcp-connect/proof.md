# TCP connect slice proof

## Scope and source

This proof applies to the local `task/tcp-connect` source at commit `e45c675c` plus this slice: `Cargo.toml`, `src/packages/mod.rs`, `src/packages/net/{mod.rs,config.rs,error.rs,stream.rs}`, and `tests/net_connect.rs`. It covers the public Rhai script API, package policy and handle lifecycle for outgoing TCP connect, and real-peer observations. It does not accept the full TCP package or release proposal.

## Verification

- Meaningful public-API tests first compiled with the `net` feature gate and no implementation. `initial-red.log` records the intended `E0583` missing-module compile failure. The harness source and import were fixed before treating this as API RED. The earlier wrapper status was not reliable because its shell pipeline returned success despite Cargo failure; the compiler log is the evidence.
- Accepted command, run through `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py` from a copied source tree with private `AGENT_RUNTIME_DIR` CARGO_HOME/TARGET, `CARGO_BUILD_JOBS=2`, and `CARGO_PROFILE_DEV_DEBUG=0`: `cargo test --features net --test net_connect`. `scoped-run-5.log` records 4 passed, 0 failed.
- The same scoped invocation ran a false-green control against the exact `authorized_connect_is_observed_and_clone_close_is_shared` test with `RHAI_NET_WRONG_EXPECTATION=1`. It failed specifically at the deliberately inverted independently observed peer EOF assertion; diagnostic is in `false-green-control.log`. The normal expectation then passed in the full suite.
- `cargo test --features 'net,sync' --test net_connect` passed 4/4 (`net-sync.log`). After adding final-drop coverage, the affected net and net,sync suites passed 4/4 each (`final-drop-net.log`, `final-drop-sync.log`); the wrong-expectation control failed at the actual peer EOF assertion (`final-drop-control.log`). All invocations stayed within the 15-minute and 2-GiB caps and runner cleanup removed private runtimes after exporting logs.
- `rustfmt --check` on the changed Rust files and `git diff --check` passed.

## Observed contracts

The tests use actual ephemeral loopback listeners and independent peer reads. They show that an exact granted endpoint connects; `close()` is idempotent and shared by cloned script handles; the peer observes EOF; a wrong-port grant, default-denied access, malformed hostname and invalid ports do not reach the listener; errors can be caught and inspected in Rhai; an OS connect failure releases a reserved handle slot; a package clone shared across two Engines enforces one global configured handle limit; quota denial makes no peer connection; and close releases the slot for a subsequent connection. A separate case drops a `Scope` holding an unclosed stream, then successfully connects again through the package clone registered in the second Engine; the independent peer observes EOF for both the dropped stream and the subsequent connection.

All sockets/listeners are locally created fixtures; connect waits, peer reads, and nonblocking accepts are bounded. No child processes or external services are created. The observed host was `aarch64-apple-darwin`, Darwin 27.0.0, rustc 1.93.0 (`rustc -Vv`); this is one host observation, not a native platform matrix.

## Remaining gates

Listener bind/accept policy, inbound lifecycle, byte transfer, broader resource/release tests, existing sys regressions, Rust 1.66/1.77 MSRV, and native Linux/macOS/Windows matrices remain open. The current tests do not claim those requirements complete. No remote publication or merge was performed.

## Launch history

`coordinator-state.md` records every scoped launch and diagnosis, including compile/setup failures, harness corrections, post-commit quota-proof correction, and accepted runs. `final-drop-run.sh` is the exact bounded runner invocation used for the correction. Detailed raw outputs are kept alongside this file in `.scratch/tcp-connect/`.
