# Project-local runner custody adapter

`run_scoped.py` is a local copy of the shared runner with its hidden `_supervise`/`Popen` child path removed. It requires a custodian-provided nonblocking Unix `SOCK_DGRAM` endpoint, a custodian-precreated runtime and `tmp`, and a finite timeout no greater than the custodian cap. It sends bounded JSON datagrams and receives three data-pipe descriptors with `SCM_RIGHTS`. The runner drives overlapping stdin/stdout/stderr activity and reports worker joins; it never falls back to local child spawning.

The source-level XNU protocol check is recorded in `evidence/retry-design.md`: the current local protocol table registers stream and datagram sockets but not `SOCK_SEQPACKET`. Native host applicability and `SCM_RIGHTS` behavior still require execution after review.

`custodian.py` directly `posix_spawn`s and records the runner, workload group leader, same-group anchor, holder and sentinel. It remains the sole spawner and reaper. After complete readiness, the controls are:

- `normal`: overlapping 2 MiB stream round-trip, then group closure while the anchor still pins identity.
- `cancel`: held output pipes after workload exit, followed by cooperative worker cancellation and join.
- `assert`: custodian verifies leader, anchor, holder and sentinel are live, injects a deliberate runner assertion while all I/O workers are active, then reads back cleanup.
- `timeout`: a live stalled fixture forces the copied runner's own 8-second timeout; the runner reports status 124 and three joined workers before cleanup.
- `kill`: custodian sends SIGKILL to the runner while live resources exist and verifies its exact wait status before cleanup.

The accepted caps are a 30-second case/session, a 5-second exact-child reap window, a 10-second outer cleanup allowance (45 seconds total), no more than 10 directly owned children, no more than 6 I/O workers, and 15 minutes total custody time including cleanup. Cleanup sends one SIGKILL to the managed group only while its unreaped leader is owned and the same-group anchor is observed live; it does not TERM the anchor before a later group signal. Assertion and runner-timeout controls first ask the custodian to close the scope while workers remain alive, then join workers and return their distinct expected statuses. The custodian attempts exact-child cleanup and receipt readback after each control. The outer controller removes a runtime only after receipt, evidence, and runtime identity readbacks. If the outer bound expires without a complete quiescence record, it writes an incomplete-cleanup record, retains the runtime, and leaves the live custodian as resource owner. Custodian-failure recovery is not claimed.

This source remains unexecuted. The coordinator source gate must approve the complete adapter before a native build or fixture launch. Native macOS `waitid`/`SCM_RIGHTS` behavior, interruption ordering, worker joins, and cleanup receipts still require the bounded live proof. Rust 1.77.2/MSRV and non-macOS behavior remain unverified.
