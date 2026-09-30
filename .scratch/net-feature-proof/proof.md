# Native macOS TCP feature proof

**Result:** The four requested feature slices passed on the native macOS host. `no_object` required a real additive API correction: registered getter properties were inaccessible by explicit function calls, even though dot syntax is intentionally unavailable in that feature. The correction preserves existing properties and exposes matching free-function aliases. Existing dot-syntax suites under `no_object` were compile-checked; the dedicated Engine/real-peer suite exercises the supported explicit-call API.

## Source and environment

- Starting revision: `59d583f2381efb355349962ac3742bec46aab460`.
- Final revision: recorded after local commit in `state.md`.
- Host: Darwin 27.0.0, `aarch64-apple-darwin`; rustc 1.93.0 (LLVM 21.1.8).
- Scoped runner: `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py`; each run used a copied checkout, private `CARGO_HOME` and `CARGO_TARGET_DIR`, `CARGO_BUILD_JOBS=2`, and a 900-second runner limit. Full suites used `--test-threads=1`.
- Final run sampled private source + Cargo home + target storage once per second. Peak sample was **1,258,436 KiB** (below 2 GiB). Peak memory was not measured.
- Final runtime: `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-cqnsd01l`; verified absent after runner completion. Other scoped runs likewise removed their private runtime. See the runtime-path checks in state.

## Final-source results

| Feature combination | `net_connect` | `net_listen` | `net_reads` | `net_writes` |
|---|---:|---:|---:|---:|
| `net,only_i32,no_float` | 4 passed | 7 passed | 7 passed | 10 passed |
| `net,no_index,sync,metadata` | 4 passed | 8 passed | 8 passed | 10 passed |
| `net,f32_float` | 4 passed | 7 passed | 7 passed | 10 passed |

Exact final logs: `logs/only_i32-no_float-final.log`, `logs/no_index-sync-metadata-final.log`, and `logs/f32_float-final.log`. All statuses are zero. The first `only_i32,no_float` attempt exposed two test expectations hard-coded to `i64`; using `rhai::INT` fixed the portability mismatch. The final run passed all 28 tests for that combination.

For `net,no_object`, all four legacy integration targets are guarded out because their suites depend on dot syntax that `src/parser.rs` intentionally omits under this feature. The combined command reports zero tests for those four targets and 3/3 for the dedicated target; see `logs/noobj-final-guarded.log`. The earlier pre-guard compile check also succeeded (`logs/noobj-final-compile.log`). Thus the legacy method-syntax suites are explicitly excluded from no_object runtime proof. A dedicated target ran 3/3 through public `Engine` registration and real local TCP peers:

- Explicit free calls connect, read, write, half-close, and close a stream; peer reads exact `ping`, while script reads peer `reply` and validates `peer_addr` and `closed` calls.
- Explicit free calls listen, accept, write, half-close, and close; peer reads exact `pong`, while script validates `local_addr` and stream/listener `closed` calls.
- A real denied connect is caught as a `NetError`; script free calls validate all six fields: `kind`, nonempty `message`, unit `io_kind`, `op`, exact `target`, and zero `partial_bytes`.

`JoinOnDrop` ensures peer threads are joined even if a script assertion unwinds. Peer connect/read paths have bounded deadlines.

## Assertion controls

- `logs/noobj-peer-wrong.log` deliberately expects `pang` from the independent peer. It fails at the peer byte assertion with actual `ping` (`[112,105,110,103]`) versus expected `pang` (`[112,97,110,103]`). The correct expectation then passes in `noobj-final-green.log`.
- `logs/f32-wrong-byte.log` deliberately expects `[0,254,65]` from the independent peer. It fails at that assertion with actual `[0,255,65]`. `logs/f32-correct-byte.log` reruns the same test with the correct bytes and passes 1/1.

These are runtime assertion failures, not compilation failures.

## Changes supporting the proof

- `src/packages/net/error.rs`, `stream.rs`, and `listener.rs`: each existing getter now registers both its property form and an explicit free-call alias. Normal object syntax remains available in ordinary configurations.
- `src/packages/net/mod.rs`: documents the explicit call form when `no_object` disables dot syntax.
- `tests/net_no_object.rs`: dedicated real-peer coverage of stream/listener APIs and all error getters, including false-green peer expectation.
- `tests/net_connect.rs`, `net_listen.rs`, `net_reads.rs`, `net_writes.rs`: guard the dot-syntax suites out under `no_object`; the dedicated target above covers explicit calls. `net_connect.rs` also checks `Duration::MAX` is rejected for all four host timeout settings. Existing checks cover zero host deadlines and catchable zero/negative script timeouts.
- `tests/net_writes.rs`: uses `rhai::INT` for output assertions so tests work with both i64 and `only_i32` configurations; existing blob exact-byte check supplies the new false-green control.

## Duration and remaining coverage

Timeout APIs take `crate::INT` milliseconds, not floating-point values. The `f32_float` matrix includes positive finite shorter-than-host timeouts, zero/negative rejection, and `Duration::MAX` host configuration rejection. Huge representable host durations are rejected by `Instant::checked_add`; no floating-point duration API is exposed by this package.

This proof is native macOS only. Combined `sys` gates and Linux, Windows, and MSRV runs remain outside the approved matrix. Under `no_object`, existing integration targets were compiled but not executed as written because they use intentionally unsupported dot syntax; the dedicated explicit-call suite proves the named public surface but does not duplicate every assertion from those four suites.
