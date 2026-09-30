# Retry design for bounded native process proof

Status: design only; no source implementation or fixture execution in this attempt. This design is for independent review before the one newly authorized implementation attempt. The earlier failed cause and disposition remain in `correction-attempt.md`; they are not erased or reclassified.

## Process ownership topology

Use three roles in the prototype binary: an orchestrator (the command run by `run_scoped.py`), a harness child, and a scope guardian child owned directly by the orchestrator. The harness and guardian communicate over an inherited Unix socket pair with line-framed commands and records. The orchestrator retains both `Child` handles immediately after each successful spawn, before pipes, threads, assertions, or parsing. The guardian is spawned with `CommandExt::process_group(0)` before its first instruction. It arms a finite lease as its first operation, before waiting on the socket or starting workload. The harness cannot release the guardian's start gate until both ownership records are installed and all fixture resources are registered.

The guardian is outside the workload process group and is its direct parent. It starts the workload with `process_group(0)`, immediately stores the unreaped `Child`, and only then completes readiness/setup. A same-group anchor fixture is also its direct child and joins the workload PGID during spawn. The guardian retains both `Child` handles. A separately owned pipe-holder is another guardian-owned child in its own process group; it receives duplicated stdout/stderr write ends and does not join the workload group. The orchestrator owns the unrelated sentinel. No process handle is forgotten, and no descendant is allowed to spawn further descendants.

The guardian's OS alarm is the independent lifetime fallback for harness death. Its async-signal-safe handler uses only `kill` and a `sig_atomic_t` expiry flag: it sends `SIGKILL` to the published negative workload PID when one is present, then marks expiry. The guardian publishes the PID only after the direct workload Child is stored and clears it while `SIGALRM` is blocked, before reaping that Child. Thus every handler signal occurs while the unreaped direct workload Child pins that PID/PGID against reuse. The guardian event loop uses nonblocking socket I/O and `waitpid(..., WNOHANG)`/polling, so alarm delivery cannot strand it in an unbounded wait; after expiry it kills/reaps the pipe-holder by its retained Child handle, waits/reaps the workload and anchor children, writes a durable cleanup receipt, and exits. Signal masking around publish/clear/reap and alarm disarm is a mandatory review point. If the alarm fires before workload creation, the guardian records expiry and refuses to start the workload.

This signal-handler design is a proposal, not yet validated. Before any workload fixture runs, the implementation review must verify macOS async-signal-safe operations, `sig_atomic_t` access and signal masking around PID publication/reaping, alarm delivery during the guardian's event loop, and receipt durability. If that cannot be done safely, stop without fixture execution. Do not rely on Rust `Drop` as the fallback.

## Safe group identity and normal exit

Only the guardian signals the workload PGID. It may signal while the direct workload `Child` is unreaped; no `kill(-pid, ...)` is allowed after `wait`/successful reaping. On normal workload completion, use `waitid(P_PID, pid, ..., WEXITED | WNOWAIT)` to observe exit without reaping. Keep the direct child unreaped, verify the same-group anchor is still live, signal the group while the zombie leader still pins its numeric PID, then reap the workload and anchor with their retained handles. This tests normal-exit scope closure, not only I/O-reader cancellation. `waitid(WNOWAIT)` and macOS process-group behavior must be verified on the native runner before accepting this path. A liveness probe is never used as a signal-identity guarantee.

For active cancellation, the guardian sends the group signal while the direct workload Child is still live and unreaped, then reaps both group members. For post-exit pipe cancellation, the normal-exit group closure above occurs first; the harness separately stops and joins I/O workers even while the independent holder keeps the output pipes open. These are distinct assertions and log records.

## I/O overlap and bounded work

The stream fixture consumes fixed-size input chunks, echoes distinct deterministic transforms to stdout and stderr for each chunk, flushes both, and emits a complete line-framed checkpoint after the first chunk. The harness starts nonblocking input and output workers, sends only the first segment, and waits for the complete checkpoint before sending the final segment and EOF. The total payload exceeds pipe capacity. It checks exact transformed byte counts and checksums on each output, full input transfer, and successful direct-child exit. This parent/child gate proves overlap without relying on elapsed-time scheduling.

Every wait, socket operation, worker shutdown, pipe drain, and join has one monotonic case deadline. I/O workers share stop tokens and use nonblocking descriptors. On timeout the orchestrator requests guardian cleanup, waits for its bounded receipt and child status, stops and joins every worker, kills/reaps its own sentinel, and reports every cleanup result before asserting the case failure. The guardian alarm remains armed as the independent backstop if the harness child dies or stops responding. No unbounded `wait`, `join`, or `read_to_end` is permitted.

## Failure and watchdog controls

1. **Live-resource assertion failure:** after guardian readiness, workload and holder readiness, and active I/O workers, the harness child deliberately fails an expected record. The orchestrator catches its nonzero status, requests cleanup, then independently reads the guardian receipt and waits/reaps the guardian. It verifies the workload and anchor were reaped, the holder was killed/reaped, the I/O workers finished, and the sentinel remained alive until exact orchestrator-owned cleanup. The control passes only if the intended diagnostic is present and every cleanup assertion succeeds.
2. **Harness-death lease control:** after all the same resources are live, the harness child terminates itself with `SIGKILL` without sending a cleanup command. The orchestrator remains alive, waits for the guardian's own finite lease, reads its durable receipt, reaps the guardian, and checks every guardian-owned child status. This is the required exact cleanup/readback after harness death; it does not simulate killing the orchestrator or scoped runner.
3. **Intentional stall control:** a harness child stalls beyond its case deadline while workload, holder, and workers are owned. The orchestrator watchdog must send a guardian cleanup request, collect exact cleanup/readback, stop/join workers, and return the intended timeout failure within a larger wrapper deadline. Separately, a no-private-group `run_scoped.py --timeout` control verifies the runner's timeout exit and shell status propagation. This wrapper control must not create escaped processes.
4. **Exit-status control:** run binaries redirected to scoped log files, capture `$?` immediately, then print/export logs. Passing-case nonzero status fails the script. Each expected-failure control checks its specific diagnostic and cleanup receipt rather than accepting arbitrary nonzero exit.

The runner timeout exceeds all guardian leases and case deadlines with cleanup margin. The private lease is shorter than the wrapper timeout. This ordering lets the harness-death/stall tests collect cleanup before the scoped runtime exits. No private process group may be created in the separate wrapper-timeout control. If the orchestrator itself disappears, `run_scoped.py` cannot read back a guardian in a separate group before deleting its runtime; that is outside this design's claim and must remain an explicit limit unless a different runner-level guardian is reviewed.

## Pre-execution safety review gates

Before any fixture is run, review must confirm from the implementation that:

- each guardian/workload/anchor/holder/sentinel successful spawn is immediately transferred to an owner before fallible setup;
- the guardian's lease is armed before blocking and is independent of harness lifetime;
- only the guardian signals a private group, and it does so only while retaining the unreaped direct workload Child;
- normal-exit observation uses non-reaping wait and group closure happens before reaping the leader;
- exact guardian-owned children and every worker have bounded cleanup paths;
- the guardian's signal handler and control loop cannot race a cleared/reused PGID;
- wrapper status propagation and all deadlines are explicit;
- process fixtures contain no unowned descendants.

If any item cannot be established in source review, do not run fixtures. Once approved, one scoped native macOS run exports the command, toolchain/OS, overlap log, live-assertion log, harness-death receipt, stall/timeout diagnostics, exact child/worker cleanup readback, and sentinel survival before private runtime cleanup. Preserve historical logs unchanged. Claims remain native macOS only; Rust 1.77.2 compile, Windows/Linux behavior, production Rhai API, and release matrix remain open.
