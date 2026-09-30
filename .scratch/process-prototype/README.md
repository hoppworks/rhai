# POSIX process lifecycle prototype

This is a bounded native macOS prototype, not the Rhai process implementation. It tests the process-group, pipe-I/O, interruption and cleanup seam on one native host.

## Current native proof

The coordinator approved adapter source `9bf32e45d770ce3b021ac7e8f333d0d2bbe11501` before execution. The proof ran on Darwin 27.0 arm64 with Rust/Cargo 1.93.0. Cargo built the copied prototype source inside the shared scoped runner's private runtime (`CARGO_BUILD_JOBS=2`, 0.78 seconds); the executable was exported before that runtime was cleaned and removed after the controls. The historical bare Rust entry point was not run; the custodian invoked only `--fixture stream`, `--fixture stall` and `--fixture anchor`.

All six project-local controls passed. Their durable receipts are under `evidence/`:

- `custodian-88024-normal.json`: runner and workload exited 0; three workers joined; 2,097,152 input and stdout bytes matched SHA-256 `91d3beb88a9b2f778a6c44a1c53b63d3c79931845a9aef84b3fb414610bd1938`; 2,097,152 stderr bytes matched the expected transformed stream, SHA-256 `6856d04b31b5cc305ceda6e7ec9a9e557c8eeb9e952f15ed0efa2c737b76944a`.
- `custodian-93052-cancel.json`: workload exited while an independent holder kept output pipes open; the runner canceled and joined all three workers, returned 1, and the same exact byte/hash checks passed.
- `custodian-91927-assert.json`: leader, anchor, holder and sentinel were live at injection; the snapshot recorded all three workers alive, active, held and acknowledged; the runner returned 86 and all workers joined.
- `custodian-92369-timeout.json`: the runner's own timeout returned 124 after three workers joined; all four managed resources were live before custodian cleanup.
- `custodian-92635-term.json` and `custodian-92930-kill.json`: the runner was terminated by SIGTERM and SIGKILL respectively, with exact wait statuses and all managed resources live at injection. Worker joins after abrupt runner termination are not claimed.

For every custody case, the custodian recorded exact child statuses, closed its owned descriptors, read back the quiescence record and matching receipt, and the controller removed the exact runtime. The coordinator independently recomputed the stream hashes and verified every recorded child PID and runtime absent. The normal receipt does not separately serialize the anchor's PGID; the custodian validated its complete readiness line and `anchor_pgid == workload_pid` before proceeding. The timeout receipt does not serialize the prior stream checkpoint/readiness bytes; those conditions were validated in the unchanged approved protocol before it emitted `io_live`. These are limitations of retained fields, not additional claims from the receipts.

A separate shared-runner timeout check is recorded in `evidence/shared-runner-timeout.txt`: the shared `run_scoped.py --timeout 1` returned 124 for a sleeping Python child. This checks status propagation only, not private fixture cleanup. Earlier correction attempts and their reviews remain in `evidence/correction-attempt.md`; the complete current state and commit reference are in `coordinator-state.md`.

## Limits

These observations apply only to Darwin 27.0 arm64 with Rust 1.93.0. Rust 1.77.2/MSRV, Linux and other Unix targets, Windows, production Rhai Engine process behavior, and broader release coverage remain unverified. The prototype does not establish escaped-descendant containment, custody-failure recovery, partial spawn/setup failure behavior, deadline/output-limit policy, backpressure benchmarks, or bounded retained output. Unix process groups do not contain descendants that deliberately leave the group. Production should keep direct-child and managed-group modes distinct, request group membership as part of spawn, and cancel I/O workers independently of EOF. A production OS adapter still needs platform review, dependency selection and MSRV verification.
