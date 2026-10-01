# Production process cleanup ownership

## Decision

Replace borrowed-child `fail()` with an owned execution record that exists before any post-spawn fallible operation. Reserve its retention slot and start its package-local cleanup driver before OS spawn. Register the returned child immediately; the caller never becomes the last owner. Keep the existing Unix nonblocking, bounded-work pump as a reusable `step()` implementation. Synchronous `run` may drive that pump in the caller; on exceptional cleanup it transfers the driver token, not the child, to the already-running cleanup service. Future `spawn` uses that same owner and service from launch onward.

This is the smallest coherent correction that preserves the accepted architecture and current run proof. A background closure containing only a numeric PID, a thread started after cleanup fails, a blocking `wait()` after `kill()`, or a retained `ProcessReport` is not sufficient. Rust does not supply cleanup on Child drop. [Rust Child documentation](https://doc.rust-lang.org/std/process/struct.Child.html).

This answer is static design review. It authorizes no runtime launch and closes no native lifecycle acceptance requirement. The root may implement one coherent follow-up under the existing task authorization and resource limits; there is no additional routine implementation-approval gate.

## Reviewed scope and defect

Read the project AGENTS.md; ticket03; the process API compatibility decision; Unix run review; private process-I/O design; and custody Expert04. Read frozen commit `a338127c221303c093dacc75627fd598fdc43c4b` process/unix.rs, process.rs, mod.rs, config.rs and tests/sys_process.rs. The frozen adapter supports direct-child run only and deliberately denies Managed. It has no spawn/shared-child lifecycle yet.

In that source, run_map creates a local Child, supervise borrows it, and fail records most kill failures before calling unconditional blocking wait. If termination failed while the child remains alive, that wait may never return. If wait fails, the function returns a snapshot and subsequently drops the only Child. Ignoring every InvalidInput kill error is also unsafe: Rust does not promise its kill error-kind mapping. Treat a known cached completion as idempotent; otherwise record the actual failure. [Rust Child::kill](https://doc.rust-lang.org/std/process/struct.Child.html#method.kill).

The unchanged success/deadline/cwd/no_index evidence remains useful for those paths. It does not establish exceptional custody, managed scope or Windows. Expert04 concerns standalone parent/broker custody and must not be relabeled as production owner proof.

## Concrete private boundaries

Use these private roles; names are implementation choices, not new public API.

| Boundary | Owns and does | Must not do |
| --- | --- | --- |
| LaunchReservation | Fallibly reserves a registry entry, wake endpoint and live cleanup-driver availability before spawn; retains held cwd and owned launch options through spawn | Start a child and then discover that retention or a cleanup thread cannot be allocated |
| ExecutionRecord / ProcessOwner | Child/native process handle; managed identity pin/job; pipe endpoints; bounded input/output state; committed cause; cleanup state; cached observation | Live in a report, depend on Engine/module/script-handle lifetime, or discard custody on an error |
| DriverToken | Exactly one active caller or service driver per record; OS calls and pump steps happen through it | Permit a caller and service to reap/signal concurrently |
| ControlCell | Bounded/coalesced cancellation flags, wake writer and cached immutable observation, protected briefly by std synchronization | Hold its mutex through poll, a process wait, joins, or script callbacks |
| ClientLease | Counts script handles only; final lease sends drop cancellation when configured | Count supervisor references as script handles; cause false final-drop detection |
| CleanupService | Package-local retained registry and one nonblocking supervisor thread; drives relinquished/run-failed and spawned owners; survives last package/client drop while custody remains | Install a global SIGCHLD handler, reap foreign children, rediscover processes, or detach blocked pipe readers/writers |
| ProcessReport | Copy of bytes, EOF flags, available status, timeout certification and diagnostics | Carry the OS owner or change after it has been published |

Use std::sync::Arc/Mutex/Condvar for the thread-facing private state even when Rhai's Shared is Rc without `sync`. Pass owned String/Vec/config scalars and held OS capabilities to the service, not Rc<SysState>, Engine, Dynamic or a borrowed NativeCallContext. Convert snapshots to script values on the calling thread. Preserve all current no_index getter/collection gates, metadata and core/sys MSRVs; this architecture needs no new platform dependency beyond the approved optional boundary.

Creation order is: validate authority/options; open cwd capability; ensure service and reserve owner; start deadline immediately before OS spawn; spawn through reserved ownership; store Child before pipe configuration; then configure nonblocking endpoints. Any configuration failure now operates on the stored owner. If spawn itself fails, release the unused reservation. Do not use a closure/message transfer whose failed send drops a Child. The reservation guard must retain an unexpectedly created child until it is registered or cleaned.

The registry is the ownership root, not an ordinary SysState field whose last drop destroys children. Give the running service its own strong reference to its registry. Closing the last package launch lease stops admissions but keeps the registry/service alive while active, cleanup-pending or quarantined entries exist. Do not implement package Drop by joining indefinitely. Retain the service JoinHandle and completion state in its private lifecycle record; join only after independently observed driver completion, never as the mechanism for releasing a failed run. With no I/O threads on Unix, the live cleanup driver is a continuing supervisor, not a permanently blocked pipe worker. A later worker-based adapter must separately retain and join each actually started worker.

Keep mutable owner storage inside retained records, rather than solely on the driver thread's stack. A caller-unwind guard relinquishes its token and wakes the service. Expected I/O paths must not panic. Catch unexpected unwinds at the pump boundary and retain the record with an internal secondary diagnostic; do not let unwinding drop Child. Poison recovery must preserve ownership and fence unsafe operations. Process abort/host death is outside an in-process cleanup guarantee; do not claim the library reproduces the external scoped-runner custodian's survival after SIGKILL.

## Owner state and response publication

Track lifecycle and published observation separately.

| State | Allowed next action / release condition |
| --- | --- |
| Reserved / Launching | No release while a created OS child has not been adopted |
| Running | Concurrent bounded stdin/stdout/stderr progress and nonblocking exact-child observation |
| Cancelling | Commit primary cause once; close stdin; request direct/managed termination; cancel pipe operations |
| CleanupPending | Retain child/scope and unfinished operation state; retry only safe nonblocking operations at bounded rate |
| Cleaned | Direct child reaped, required scope-close obligations verified, endpoints closed and actual workers stopped; owner can retire |
| IdentityLost / Quarantined | Retain unresolved record, fence all numeric-PID/PGID signaling and target discovery; report incomplete cleanup |

A published terminal error may coexist with CleanupPending. This is intentional: run can return a catchable incomplete-cleanup error without abandoning the child. Cache that first published error for equivalent subsequent waits. Later cleanup progress does not mutate that snapshot or change a repeated wait to success. Maintain separate private cleanup progress for retirement/tests. Limit/deduplicate retained diagnostics by operation and state transition rather than append an unbounded error on every retry.

For normal completion publish only after required output and lifecycle completion. A finite Child.wait observation deadline returns unit when no cached terminal observation is ready, including when the child has exited but pipes have not completed. The observing caller waits on the ControlCell condition variable with its lock released. try_wait reads ready snapshots and never waits for EOF. Another handle can always queue cancellation and wake the driver.

On final ClientLease drop, kill_on_drop true queues termination/cancellation once; false relinquishes clients while the retained service continues ordinary input/output, output bounds, exit collection and scope-close policy. Module/package drop does not cancel kill_on_drop false executions. Zero clients does not imply zero owners. Use a bounded/coalesced control mailbox, not unbounded repeated kill messages.

## Exceptional cleanup algorithm

1. Select the primary cause at the supervision step. Observe bounded readable output before choosing deadline so OutputLimit wins when both occur in that step; otherwise keep the first committed cause. Preserve the existing per-stream byte prefixes and EOF facts.
2. Stop input and prevent new operations. Cancel the Unix pump by wake plus endpoint closure under its sole driver. With caller-thread pumping there are no reader/writer threads to join. Future poll/wake workers must acknowledge cancellation and be joined; Windows pending overlapped structures remain owned until cancellation completion is observed.
3. Request termination once through validated identity. Save the actual failure as a secondary diagnostic. Successful submission is not proof of child exit. A failed submission must not trigger blocking wait.
4. Observe/reap with nonblocking exact-child operations, with EINTR retries bounded by the current step/time budget. Use a short private foreground cleanup budget, initially one second total, without extending the execution deadline. This is a responsiveness choice, not a claim of hard OS completion. Poll/wake in short bounded intervals and yield fairly across retained owners; never busy-spin.
5. On termination/reap failure, or expiration of that foreground budget, freeze an incomplete-cleanup error snapshot, retain the owner, relinquish the caller driver token and notify the service. Add a diagnostic explaining unfinished reaping/scope/worker obligations even if no syscall returned an error. Return without joining an unfinished cleanup driver. The service continues natural-exit observation and safe cleanup; it does not wait forever in a blocking syscall.
6. If cleanup succeeds within the foreground budget, an ordinary run deadline may publish the existing timed_out true result map. Other primary causes remain errors. If any cleanup diagnostic prevents certification, return the error snapshot even if later cleanup completes. Use an explicit Cleaned predicate to certify timeout; `diagnostics.is_empty() && exit.is_some()` alone is insufficient.

For the initial follow-up, make at most one automatic termination submission per cancellation cause; a failed request leaves natural-exit observation active. Repeated polling is not repeated kill. This avoids an undocumented retry storm. Transient EINTR retries stay bounded; another explicit authorized cancellation request may be serviced only while identity remains valid. Recovery from a persistent OS refusal is not guaranteed by this contract.

## Unix identity and wait failures

A retained Rust Child is necessary but on Unix it is not an unconditional kernel identity pin. Never equate Child.id with a durable process handle. While this owner is the sole exact-child reaper and auto-reaping is disabled, an unreaped child pins its PID. After successful direct-child try_wait, cache status and disable all further PID signals immediately. No future kill reaches the OS after completion.

Managed Unix must use the approved non-reaping leader-exit observation (waitid WEXITED|WNOHANG|WNOWAIT through the reviewed adapter). Preserve its unreaped leader until the final group signal obligation completes. If that signal fails, retain the leader unreaped; do not release the PGID pin and plan another signal later. Only reap after all identity-dependent group signaling has ended. WNOWAIT preserves waitability; ordinary wait reaps. [Linux wait documentation](https://man7.org/linux/man-pages/man2/waitpid.2.html).

Handle failures by exact errno/adapter classification, not guessed ErrorKind semantics:

- EINTR: retry/yield without declaring identity lost or changing primary cause.
- A known non-consuming operational failure: retain the owner; retry nonblocking observation at a bounded cadence. Before any further termination submission, require valid custody. Never replace an unavailable exit status with a guessed status.
- ECHILD, auto-reaping, or any evidence that another reaper consumed the child: fence numeric signaling permanently for this execution. Keep the Child/record quarantined as evidence of unresolved custody; retaining it does not restore PID identity. No kill(pid,0), name scan, proc-table discovery or later signal can establish the original identity. Missing wait status is not verified package reaping.
- If a raw platform wait helper ever consumes status, commit it atomically to the owner's cache and fence signals; do not then call Child::kill or expect Child's private status cache to know about that reap. Prefer non-consuming raw observation plus the one owned Child reaping boundary.

Use exact positive-child wait targets only. Do not change host signal dispositions or consume unrelated child statuses. Nonblocking retries after identity loss must not match a newly created child with the reused PID either; quarantine prevents both wait and kill target reuse.

There is one precise host-interoperability boundary: portable Unix Child/process-group ownership cannot promise safe repeated numeric signaling and complete status recovery if host code concurrently reaps these same children or enables SIGCHLD auto-reaping. A pre-spawn disposition check can fail closed for already incompatible auto-reaping settings, but cannot prevent a host changing them afterward or calling waitpid(-1). The implementation must document this boundary and report custody loss, not acquire foreign SIGCHLD ownership. If the accepted contract is interpreted to require recovery even under such interference, that specific requirement remains technically unresolved on the portable macOS/Linux mechanism; an arbitrary extra retry cannot solve it. This does not block the ordinary retained-owner correction or justify weakening its tests.

Keep scope termination submission, direct-child reaping and scope completion as distinct facts. A successful group kill does not supply exit status for every descendant. Reuse the approved final-signal-before-leader-reap ordering, but do not certify broader managed quiescence solely from kill returning zero. The managed adapter must define and natively prove its scope-close evidence, preserving the accepted membership/escape boundary; this answer adds no unchecked descendant enumeration or new claim of managed proof.

## Windows boundary

Reuse the approved retained process/thread/job handles and suspended-launch assignment boundary. Start/reserve custody before CreateProcess; keep setup rollback in the owner; fail closed on job assignment failure. Retained native process handles supply identity without PID rediscovery. Keep job close/termination, process completion, and overlapped-I/O completion separately tracked. Termination/cancellation request success is not completion. Never release OVERLAPPED storage/event or thread/process handles while the corresponding operation/setup obligation is unresolved. The service may publish incomplete cleanup while retaining these handles and operations. Native Windows custody, setup races, existing host jobs and cancellation completion remain unproven; Unix source or compilation cannot close them.

## Follow-up implementation and evidence

Implement the retained direct-child run path first; factor owner/control/service boundaries so spawn will reuse them. Do not implement a second fail path just for spawn, or quietly register unsupported managed/Windows behavior. Retain the existing cwd capability and map/error representations. The current large-I/O verification runs independently and must not be restarted or edited by this package.

Before execution, record the actual scoped package start/checkpoint, cumulative launch/cause history, fixed test measurements, per-run limits, allowed adjustments and stop criteria in the existing coordinator state. Existing resource caps remain binding. Use one shared scoped build per applicable source/feature package; keep expected TDD REDs distinct from failed corrections. A proposed minimal acceptance set follows; record exact fixture bounds before launch, use readiness/acknowledgements and watchdogs, and preserve accepted evidence by reference.

| Test | Evidence needed |
| --- | --- |
| Real normal exit and deadline through Engine | Existing byte/map/EOF/read-back cases remain green; recorded reap and owner retirement, no live owner after successful return |
| Real pipe-setup failure after spawn | Fault only the actual setup boundary; real ready child, primary configure Io preserved, termination/reap and slot retirement observed independently |
| Failed termination with live child, then natural exit | Inject one termination refusal without executing kill; real fixture remains alive after catchable run return; registry still owns it; release fixture by a separately owned control channel; observe eventual exact-child reap and retirement |
| Reap failure after actual termination | Inject one non-consuming wait failure; caller returns incomplete primary error; stored Child survives; subsequent real wait reaps it; frozen report stays unchanged |
| Cancellation with externally held pipes | Real retained pipe holder remains alive through pump cancellation; incomplete EOF facts, endpoint closure and driver handoff; outer fixture separately owns holder cleanup |
| Package/Engine dropped after failed run | Error and package values dropped while real child remains; service still owns it and eventually reaps after release; no Drop joins forever |
| Future spawn final-drop true/false and sync wait/kill | Real child continues after nonfinal clone drop; true final drop terminates; false final drop and package drop preserve eventual reap; waiter cannot block another cancellation; repeated snapshots resist mutation |
| Future managed/Windows acceptance | Approved native scope/setup/cancellation suites, independent member records and unrelated sentinel; not acceptance from mocked adapters |

Supplement with deterministic adapter-level tests for kill refusal, EINTR, repeated non-consuming reap failure, timeout/overflow precedence, reserve/service-start failure before spawn, caller unwind/handoff, and ECHILD quarantine. A reused-PID fake must fail loudly if ANY later signal or wait is attempted; do not churn the OS PID space to manufacture reuse. Verify bounded diagnostics and fair service progress with two retained owners, one stalled. These fault tests establish exceptional state transitions while real-child tests establish actual OS custody; neither substitutes for the other.

Avoid another permanent-error native fixture that cannot be cleaned under the package's resource scope. Inject at reviewed boundaries while the external scoped custodian retains exact fixture ownership for assertion failure/interruption. Kernel ECHILD cannot be reliably manufactured by timing alone; test identity fencing deterministically and, if a competing-reaper native control is later used, isolate it in its own fixture process and forbid post-loss numeric actions.

The one bounded follow-up should close direct-child failed-kill bounded response, failed-reap retention, eventual real reaping, report immutability and package-drop survival. Shared spawn, managed lifecycle, native Linux/Windows and release matrix remain explicitly open until their own accepted checks run. No second Expert chain is needed for ordinary implementation details within this design. A contradictory native result or the precise competing-reaper guarantee above must be reported against the existing ticket, preserving cause history and limits.
