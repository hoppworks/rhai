# Corrected proof attempt: stopped before execution

Date: 2026-09-30 (native macOS ARM64, Darwin 27 host)

## Outcome

The single correction attempt did not establish safe supervision, so no prototype executable was run. The original source and its two logs remain unchanged and are historical observations only. In particular, they do not prove simultaneous I/O, cleanup on live-resource failure, or safe timeout behavior.

## Ownership assessment

The scoped runner starts its command in a private supervisor process group. Its timeout cleanup signals that group with `SIGTERM`, waits 200 ms, then sends `SIGKILL` to that same group. The existing prototype moves fixtures into separate process groups. Therefore the runner cannot terminate those fixtures, and adding `--timeout` alone would leave them running.

A live in-group lease could provide independent cleanup: the first fixture code would arm a finite alarm before blocking, and the alarm handler would signal only its still-live own group. A parent-side owner would separately retain the direct `Child`, pipe-holder, worker stop tokens and join handles, and explicitly clean them on assertion/setup failures. The parent would signal a group only while its unreaped direct child anchors that identity. This design has not been implemented or validated here. The current source lacks the lease, immediate ownership guard, bounded worker lifecycle and held-pipe owner. Running it again would repeat known unowned-resource hazards.

The lease would also need to be validated against the actual spawn and failure ordering, including the first-instruction window, alarm delivery, normal exit, and harness termination. No assertion about managed-scope closure after normal leader exit follows from an in-group lease alone; that remains a separate identity/guardian gate.

## Evidence not produced

No corrected scoped run was performed. Consequently there are no corrected logs for overlap gating, live-resource assertion failure and cleanup readback, watchdog stall, wrapper exit propagation, exact holder cleanup, or sentinel preservation. Creating synthetic output for these checks would misrepresent execution. Existing `native-macos.log` and `wrong-assertion.log` are preserved verbatim as historical evidence.

## Remaining gate

Implement and review the lease and immediate owner as one coherent harness change, then validate ownership before execution. Only after that should the scoped run execute the overlap, live-failure and watchdog controls with reliable status capture and exact cleanup/readback. Rust 1.77.2 compilation and non-macOS platform behavior remain unverified.
