## E2E proof: bounded TCP stream writes and directional half-close

**Source revision**: `44275bf83dc1cb7f4a9ba707ed73a6c27209d0fc` on local branch `task/tcp-stream-writes` (parent `e0dd28ec7844d2b5b88910387fca13447424d7d0`).

**Entry point**: A Rhai client calls `connect` or `accept`, then invokes `write_string`, `write_all_string`, `write_blob`, `write_all_blob`, `shutdown_read`, or `shutdown_write` on the returned `NetStream`.

**Stack exercised**: Rhai `Engine` and registered `NetPackage` -> `NetStream` methods -> real OS `TcpStream` -> independent localhost peer sockets. Peer threads read or write bytes independently of the script result.

**Steps performed**:
1. Confirmed the Engine-level RED in `.scratch-tcp-red-engine2.log`: `write_string` failed with `ErrorFunctionNotFound` before registration/implementation.
2. Ran the `net` integration matrix from a private source copy. The ten tests cover one-shot and write-all counts, exact outgoing peer bytes, blob bytes, input bounds and Engine limits, shorter script timeout under the host deadline, exact partial timeout count versus bounded peer readback, read/write half-close and idempotence, and accepted-stream write readback plus inherited limits. Results are in `evidence/final-matrix/net.log` (10 passed).
3. Ran `no_index`, `unchecked`, and `metadata` variants in that matrix (10, 9, and 10 passed respectively). The final corrected no-index method-omission test was also run separately against a private source copy; see `evidence/final-private/no-index.log` (1 passed). It supplies a host `Vec<u8>` argument matching the omitted blob overload and observes `ErrorFunctionNotFound` while string write remains functional.
4. Ran the sync close-during-write test after an internal test notifier observed an actual socket `WouldBlock`; the close then unblocked the write, and the peer's bounded drain count equaled the total complete-call bytes plus the final `NetError::partial_bytes`. The final fixture writes repeated 64 KiB chunks, capped at 64 MiB, so socket backpressure is established without assuming one 1 MiB call fills the OS buffer. Both affected sync fixture tests passed serially in `evidence/sync-saturation/sync.log` (2 passed).
5. Deliberately enabled `RHAI_NET_WRONG_WRITE_EXPECTATION=1`; the blob test failed as intended (exit 101) because expected `[0, 254, 65]` differed from peer bytes `[0, 255, 65]`. The normal exact-byte test passed in `evidence/post-matrix/correct-blob.log`.

**Evidence**:
- RED log: `.scratch-tcp-red-engine2.log`.
- Main feature matrix results: `evidence/final-matrix/status.txt`, `net.log`, `no-index.log`, `unchecked.log`, `metadata.log`, and `wrong-control.log`.
- Corrected final no-index and sync results plus exact runtime locations: `evidence/final-private/no-index.result`, `no-index.log`, `sync.result`, `sync.log`, and `runtime-paths.txt`.
- Final bounded saturation sync result and exact runtime locations: `evidence/sync-saturation/sync.result`, `sync.log`, and `runtime-paths.txt`.
- Earlier actual-WouldBlock single-test result: `evidence/sync-real/status.txt` and `sync.log`.
- Exact scoped-runtime cleanup readback: `evidence/cleanup-readback.txt`.
- Wrong-assertion control and restored correct blob result: `evidence/post-matrix/wrong-control.log` and `correct-blob.log`.
- Environment: macOS arm64, Darwin Kernel 27.0.0, `rustc 1.93.0 (254b59607 2026-01-19)`; see `evidence/final-matrix/environment.txt`.

**Reused proof (if any)**: Accepted receive/connect/listen proof from the preceding TCP read task is retained at `/Users/hoppworks/projects/rhai-all-tickets/.scratch/tcp-stream-reads/`, with the campaign acceptance recorded in `/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/coordinator-state.md`. This task independently tested outgoing and accepted-stream writes; its listener change only passes through the new host write configuration.

**Independent read-back**: Separate OS peer sockets read exact outgoing `hello world`, exact binary blob bytes, and successful accepted-stream `accepted` payload. For the bounded timeout and close-during-write cases, peer drain is capped at the fixture's byte ceiling and its count is compared to the API's actual returned/error partial count. Half-close tests also exchange bytes in the still-open opposite direction.

**False-green check**: The intentionally wrong blob assertion exited 101 and reported the differing expected and actual arrays. With the injected wrong expectation disabled, the same blob scenario passed with exact peer bytes. The initial final-matrix sync invocation used an inexact `--exact` filter and ran zero tests; it is not counted as proof. A later one-call sync fixture timed out waiting for `WouldBlock`, demonstrating that the write could fit in the OS send buffer; those diagnostics are retained in `evidence/final-private-serial/sync.log`. The bounded repeated-call fixture then observed real `WouldBlock` and passed both affected tests in `evidence/sync-saturation/sync.log`.

**Data reset**: Every E2E fixture binds its own ephemeral loopback listener, applies finite accept/read/write/channel deadlines, caps peer drains, and joins the peer. `connected()` joins the peer before rethrowing script panics. Accepted feature runs used `run_scoped.py` with a private copied source, `CARGO_HOME`, and target directory; exact runtime paths and post-run absence checks are retained in `evidence/cleanup-readback.txt`. One failed diagnostic rerun accidentally used the owned checkout as Cargo's source and created ignored `Cargo.lock` and `target/` at 2026-09-30 16:42 local time. The exact cleanup command was rejected by the shell safety hook, so those owned-checkout artifacts remain and are reported for the parent Session to classify; I did not work around the hook. The assertion control changes only one test-process environment variable. No shared or persistent application data was used.

**Verified**: One-shot versus write-all behavior; actual success counts; exact peer readback; default finite host write ceiling with optional shorter timeout; partial counts on timeout and close; input caps before I/O; checked Engine limits; accepted-stream write/config propagation; idempotent directional half-close; opposite-direction operation after shutdown; closed-stream behavior; feature registration/omission under `no_index`; and checked behavior under `unchecked`/`metadata` builds.

**Unverified**: Native Linux and Windows builds/runtime, project MSRV targets, and the broader release feature matrix remain release gates. This proof is from macOS arm64 with Rust 1.93.0. Peak runtime disk usage was not measured; the approved per-invocation private-storage limit was 2 GiB and Cargo jobs were limited to two for the accepted private runs.
