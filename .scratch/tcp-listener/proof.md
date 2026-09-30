# TCP listener slice proof

Environment: macOS 27.0 arm64 (`Darwin 27.0.0 arm64`), `rustc 1.93.0 (254b59607 2026-01-19)`. The final commands used the scoped runner with a private source copy, isolated `CARGO_HOME`/`CARGO_TARGET_DIR`, `CARGO_BUILD_JOBS=2`, 900-second invocation limit, and serial tests to bound fixture sockets.

## Acceptance

- `cargo test --features net --test net_listen --test net_connect -- --test-threads=1`: passed, `net_connect` 4/4 and `net_listen` 6/6. Output: [accept-net.log](logs/accept-net.log); exit code 0: [accept-net-exit.txt](logs/accept-net-exit.txt).
- `cargo test --features net,sync --test net_listen --test net_connect -- --test-threads=1`: passed, `net_connect` 4/4 and `net_listen` 7/7, including close during an observed waiting accept. Output: [accept-net-sync.log](logs/accept-net-sync.log); exit code 0: [accept-net-sync-exit.txt](logs/accept-net-sync-exit.txt).
- The script bound explicitly granted `127.0.0.1:0`; a separate OS `TcpStream` connected. Script `accept` returned the peer address matching the client's independently read `local_addr`.
- Denied endpoint/ephemeral-port and invalid address/port cases were catchable. A pre-existing independently bound listener still accepted and identified its peer after denials.
- A failed bind followed by a retry proved bind errors release quota. Two bounded no-peer accepts with `max_handles(2)` proved timeout releases its reserved slot. A separate package engine could not connect while listener and accepted stream consumed quota 2, then connected after final drop; the independently accepted socket observed EOF after script close.
- Closing either Rhai listener clone closed shared state and allowed OS rebind; dropping the final live clone allowed OS rebind. The sync test uses a second cloned listener to observe quota pressure while accept waits, closes a clone, then receives the catchable close error and joins the worker within bounded waits.
- Zero and negative script timeouts are rejected; zero host `accept_timeout` is rejected at package construction.
- Wrong-peer control: `RHAI_NET_WRONG_PEER_EXPECTATION=1 cargo test --features net,sync --test net_listen authorized_listener_accepts_an_independent_peer -- --exact --nocapture` failed as intended (exit 101), comparing actual independently observed peer to deliberately false `127.0.0.1:1`. Output: [accept-wrong-peer-control.log](logs/accept-wrong-peer-control.log); exit code: [accept-wrong-peer-control-exit.txt](logs/accept-wrong-peer-control-exit.txt).
- Final scoped runtime tree end size was 861980 KiB in [accept-storage-kib.txt](logs/accept-storage-kib.txt). This is an end measurement, not peak use.

## Scope limits

Native proof covers this local macOS target and `net` plus `net,sync` configurations. It does not prove Windows/Linux, Rust 1.66 core MSRV, other feature combinations, release gates beyond connect/listen acceptance, data-transfer operations, or no_std/WASM diagnostics. Parent full-stack strict suite remains coordinator-level acceptance.

## Bounded retry follow-up

After review identified that the sync test worker's ResourceLimit retry needed its own finite bound, the retry moved to a host-side monotonic `Instant` helper. Each native accept attempt is bounded to 5 seconds for the close regression; the whole retry budget is 6 seconds and the result channel waits at most 12 seconds (retry deadline plus one native-call allowance and margin). The worker retries only actual `ResourceLimit`, treats only catchable `Io` with op `accept` as the expected close result, and returns `QuotaRetryDeadline` distinctly. Cleanup still closes before joining, with assertions after join.

- Real OS quota-expiry check: listener consumes `max_handles(1)`, retries observe at least one actual `ResourceLimit`, then reach the distinct retry-deadline result; closing releases its bound endpoint. [deadline-expiry.log](logs/deadline-expiry.log), exit 0 in [deadline-expiry-exit.txt](logs/deadline-expiry-exit.txt).
- Bounded sync clone-close check passed after the host deadline correction: [bounded-close.log](logs/bounded-close.log), exit 0 in [bounded-close-exit.txt](logs/bounded-close-exit.txt).
- One scoped follow-up tree end size: 493888 KiB (not peak) in [bounded-followup-storage-kib.txt](logs/bounded-followup-storage-kib.txt).
- The prior final full `net` and `net,sync` runs and wrong-peer control remain applicable; only the sync close test fixture and the new host-only expiry test changed.
