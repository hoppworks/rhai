# Close process lifecycle and resource-limit ambiguities

Type: grilling
Label: wayfinder:grilling
Status: resolved
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: none

## Question

What observable outcomes must run/spawn guarantee when waits, stdin, output limits,
timeouts, shared handles and cleanup interact?

## Context

The sys plan already accepts options maps, nonzero exit as data, captured output,
timeouts, kill-on-drop and sync-compatible handles. Do not reopen those choices without
new evidence. Allow-listed programs run with host OS authority; neither filesystem
roots nor program names sandbox the child's subsequent actions.

## Resolution requirements

Clarify run timeout versus Child.wait timeout, repeated wait/kill, final-clone drop,
large simultaneous stdin/stdout/stderr, output-limit precedence, and cleanup/reaping.
Determine the policy for inherited pipe handles or descendants that can outlive the
direct child; distinguish guarantees from documented limits. Address command-name
versus absolute executable identity and inherited environment in the reviewed-script
trust model. Specify fixture-observable cases and platform differences.

Reference: ../../../docs/sys-package-plan.md sections 3.3, 4.4 and 5.

## Lifecycle contract and API candidates

The owner clarified that effort is secondary to maximum quality. This does not add
an automatic-retry or durable-recovery requirement. Preserve the accepted API and
make its lifecycle observable before selecting implementation mechanisms.

### Completion and cancellation

- `run` owns the execution until its output and direct-child exit are collected.
  A run deadline starts immediately before OS spawn and covers input transfer,
  execution and output collection, not merely the polling loop. OS spawn itself
  may not be interruptible; document that limitation rather than promise a hard
  wall-clock bound. On deadline, stop input, request termination, collect bounded
  output and reap the child. Return `timed_out: true` only when cleanup succeeds.
- `Child.wait(seconds)` is an observation deadline: `()` means no final result is
  available yet. It leaves execution running and allows another wait or kill.
  `try_wait` must not block waiting for pipe EOF. A final result includes collected
  output; a process exit alone need not mean output collection has completed.
- Cache final results or terminal errors. Repeated waits and waits through cloned
  handles return equivalent snapshots; script mutation of one result cannot alter
  future results. `kill` is idempotent after completion and uses the owned OS child
  handle, never an unvalidated PID. A blocking wait must not monopolize the lock
  needed for another handle to request cancellation.
- The final script handle triggers termination when `kill_on_drop` is true. Dropping
  an earlier clone does not. The package retains cleanup ownership until reaping
  and worker shutdown finish; it must not silently abandon a child or detach a
  permanently blocked I/O worker. Drop must not wait forever on inherited pipes.
  With `kill_on_drop: false`, execution continues deliberately; the package still
  owns eventual output collection and reaping. Validate this lifetime explicitly.

### Input, output and errors

- Drain stdout and stderr while transferring stdin. Close stdin after supplied
  bytes, or immediately for `()`. `spawn` must not synchronously finish a large input
  write before returning a cancellable handle. Bound internal queues as well as
  retained output; do not buffer an unbounded stream before applying its limit.
- Validate durations and limits before spawning: reject negative, non-finite,
  overflowing or nonrepresentable values. A zero output limit allows empty output
  and fails on the first byte. The existing limit remains bytes per stream.
- At output overflow, retain at most the configured prefix for each stream, request
  termination and return catchable `SysError::OutputLimit`. A nonzero normal exit
  remains result data. Byte capture is authoritative; text remains lossy UTF-8.
- Preserve a primary terminal cause chosen by the supervisor. If deadline and
  overflow are observed in the same supervision step, prefer `OutputLimit`;
  otherwise preserve the first committed cause. No ordering between independent
  stdout/stderr events is promised. Cleanup failures are secondary diagnostics,
  never a replacement that hides the primary cause.
- Propose an additive `SysError.process` getter: `()` for unrelated errors, otherwise
  a report containing retained stdout/stderr, capture-complete flags, available exit
  status, timeout state and cleanup diagnostics. Raw bytes remain available in the
  report even when text decoding is lossy; respect feature gates. The current error
  enum does not contain this report: its Rust compatibility and representation need
  review under ticket 06 before implementation. This is proposed behavior, not an
  assertion about existing code.
- Failures after child creation must take the same owned cleanup path, including
  worker-start failure and input/output errors. Never report successful cleanup if
  termination, reaping or worker shutdown is unverified. Exceptional OS failures
  must retain ownership and expose incomplete cleanup; no absolute completion-time
  guarantee is claimed for an OS that cannot complete the requested operation.

### Descendants and executable authority

The initial release includes both direct-child supervision and an explicitly
selected managed process group/job. Host configuration selects the supervision
scope; scripts cannot downgrade a host-required managed scope. Preserve direct-child
semantics when managed scope is not selected. Exact configuration spelling is an
API-review detail, not an existing method.

In managed scope, run deadline, output overflow, explicit kill and final-handle drop
with `kill_on_drop` terminate the owned group/job as well as the direct child. A
normal direct-child exit also closes its managed scope before a successful final
result is published: managed mode is for a bounded task, not a launcher for
persistent services. On 2026-10-02 the owner explicitly approved a clear
incomplete-cleanup error when scope members have stopped but remain zombies under
foreign parents. This revises the former requirement for normal completion
independent of foreign reaping. The error preserves available direct-child exit
and bounded capture data, reports unresolved cleanup, and retains cleanup custody.
Termination submission alone does not certify closure. A permission error or
unverified membership must not be converted into success or described as proof
that every member stopped. Direct-child reaping and local I/O shutdown remain
required; this exception does not authorize reaping foreign children or changing
host signal/subreaper policy.
With `kill_on_drop: false`, the retained owner continues supervision until ordinary
completion, then closes the scope. Use direct-child mode for intentional independent
background services.

Management means the processes associated with the owned OS group/job, not every
possible descendant. Windows job objects and Unix process groups have different
membership and escape rules. Arbitrary escaped descendants remain outside this
contract; this is not an OS sandbox. Never discover cleanup targets by executable
name or by an unchecked recursive PID snapshot.

Create and establish the owned scope before the program can start unmanaged work.
If managed supervision cannot be established, fail the launch and clean up any
already-created child; never silently fall back to direct-child mode. Native proof
must cover setup races, existing host job/group contexts and partial setup failures.
The mechanism and dependency choice remain gated on a bounded platform prototype.

A descendant holding a pipe must not hang `run` with a finite deadline or block
`wait(seconds)` beyond its observation deadline. After cancellation, partial output
is marked incomplete if EOF was not obtained. With no deadline, waiting for output
may continue indefinitely by explicit configuration. Before implementation, prove
that the selected MSRV-compatible I/O design can cancel both readers and writers
on each supported native platform; kill-then-join alone is not an acceptable design.

Keep verbatim program allow-list matching. Recommend host-configured absolute
executables for stable identity; a name intentionally uses host PATH resolution and
is not binary identity pinning. Child environment inheritance remains explicit and
separate from the script environment-read policy; use `env_clear` when the host
requires a controlled child environment. No shell interpolation is introduced.

### Test-first acceptance cases

Extend the existing self-reexec integration fixture with explicit readiness and
independent child-written records. Each case calls the public Rhai API through
Engine. Parent-side observations must verify effects and cleanup independently.

| Case | Required observation |
| --- | --- |
| Success, nonzero exit, raw/text output | Exact fixture bytes and independent exit record; nonzero is data |
| Large stdin with simultaneous stdout/stderr | Completes without deadlock; byte prefixes and exit independently checked |
| Input EOF and early child exit | EOF observed; input error retained; no orphaned writer or unreaped child |
| Run deadline during input and output | Child termination/reaping observed, partial output and timeout reported |
| Timed wait followed by later wait | First returns `()`; child remains alive; later result is stable |
| Clone/drop and repeated wait/kill | Only final drop terminates; cached results cannot be mutated via a prior map |
| Wait on one shared handle, kill on another | Cancellation progresses under `sync`; no wait-held lock deadlock |
| Each stream at N and N+1 bytes; zero cap | Exact boundary behavior, bounded capture, overflow cause and cleanup |
| Overflow and deadline together | Stable specified precedence without assuming stream event ordering |
| Descendant retains pipe after direct child exit | Finite deadline returns with incomplete capture; workers end; fixture owns descendant cleanup |
| Invalid options and denied program | No fixture start record and no process created |
| Failure after OS spawn | Controlled fault at worker setup/I/O boundary proves cleanup ownership; supplementary injected fault is not a substitute for real-OS acceptance |
| `kill_on_drop: false` | Child continues after handle drop and is eventually reaped by its retained owner |
| Native platform differences | Unix signal data and Windows exit data; native cleanup evidence, no Wine-only acceptance |

Fixtures get an external watchdog that fails with diagnostics rather than hanging
CI, exact resource ownership, and cleanup for every assertion failure. Run lifecycle
cases repeatedly with varied payload sizes/scheduling; repetition supplements the
contract assertions and does not establish correctness by itself. Avoid fixed
sleep-based readiness and timing assertions tighter than scheduler guarantees.

### Implementation gates

1. The owner selected managed group/job support for the initial release. Preserve
   both explicit supervision modes and their documented boundaries.
2. Prove cancellation and reaping mechanics in a bounded platform prototype before
   promising completion semantics. If the prototype contradicts the contract,
   escalate the concrete contradiction; do not weaken assertions to get green tests.
3. Implement one failing integration contract at a time; keep OS-specific code behind
   a small private boundary. Select dependencies only after the prototype exposes a
   concrete need and after MSRV, maintenance and feature compatibility review.
4. Execute strict proof with independent read-back on each supported native OS;
   release feature/MSRV combinations are resolved in ticket 06.

### Primary-source basis

- [Rust Child](https://doc.rust-lang.org/std/process/struct.Child.html): ordinary Child
  drop does not terminate or reap; repeated waits preserve exit status. The package
  must supply its own supervision rather than inherit a cleanup guarantee from std.
- [Microsoft job objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects):
  job lifetime/termination and child association have platform-specific rules;
  these are not equivalent to killing a single Child.

## Answer

On 2026-09-30 the owner explicitly selected managed process group/tree support:
“soll dabei sein”, referring to the comparison's managed group/tree option. The
preceding recommendation placed it in the first version as an explicit choice,
with native tests and no sandbox claim. It is therefore part of initial scope,
alongside the direct-child foundation; it is not deferred to a later release.

The contract above supplies the implementation requirements for that choice.
The exact host-config API and the proposed `SysError.process` representation are
API candidates for ticket 06, not separately owner-approved spellings. No production
implementation or native Rust I/O cancellation proof is complete. The Darwin
controller/custodian prerequisite is accepted at `60d99b58`, with Python parent-side
I/O and Rust child fixtures; it does not close the production cancellation gate.
The reviewed private adapter design is recorded in
`.scratch/process-io-design/design.md`; its native
Rust, dependency/MSRV and Windows gates remain open.

Additional managed-scope acceptance cases:

| Case | Required observation |
| --- | --- |
| Fixture starts child and grandchild workers | Explicit readiness and independent worker records establish scope membership |
| Deadline, overflow, kill, final-clone drop | Every associated fixture worker stops; owned handles/workers are cleaned up |
| Main process exits while workers remain | Managed mode closes the task scope; direct mode preserves its distinct behavior |
| Scope setup failure or unavailable mechanism | Launch fails without unmanaged work or silent fallback |
| Host already belongs to a group/job | Fixture-owned cleanup cannot terminate host or unrelated sentinel process |
| Escaped descendant and retained pipe | Documented membership boundary holds; bounded capture cancellation still completes; fixture cleans up escapee |
| Managed scope with kill-on-drop disabled | Retained supervisor preserves task lifetime, then performs normal scope cleanup |

Record start latency, capture throughput and retained resource counts for each mode
with identical fixture workloads and platform/toolchain details. Benchmarks describe
observed overhead; no performance numbers are promised before measurement.

## Accepted Linux shared Child subset — 2026-10-03

Source4bb0848f, native Linux Rust/Cargo1.77.2, normal/sync/sync+no_float: public
spawn returns with8MiB input still blocked, finite wait returns unit, later
wait/try_wait snapshots remain stable after caller mutation and repeated
post-completion kill; nonfinal clone drop remains operational; final-drop true
reaps and false remains operational then eventually reaps after fixture release.
Intended panic production-reap is verified and success/unrelated-panic controls
rejected. All three wrong exit-status expectations fail101, restored GREEN0.
Original evidence, root independent process closure and combined independent
review: .scratch/all-tickets/linux-shared-child-proof.md and referenced originals.

At invocation87 sync concurrent cancel/wait passed, while actual blocking condvar
entry remained unproven; invocation88 below closes that specific missing criterion. Managed groups, externally
forced controller custody, remaining options/I/O boundaries and platform/release
requirements remain open. Ticket is not complete. Initial invocation86 compiler
failure and one-borrow recovery87 retain consumed history and closure evidence.


## Accepted Linux actual wait-entry subset — 2026-10-03

Source08507d68, native Linux7.2.7 x86_64, private Rust/Cargo1.77.2, sync and
sync+no_float: public Engine wait enters the Condvar path while a real FIFO-held
child remains nonterminal; another public handle kills it, the waiter completes
within3s, joins, and the independently recorded child PID is reaped. Test-only
counter plus reacquired snapshot mutex establishes actual entry before cancel;
spurious wakes remain permitted, so continuous sleep at kill is not claimed.
Both intentionally wrong entry assertions fail101 at their intended checkpoint,
restore exactly and pass0. Original child records are freshly checked by the host,
four fixture PIDs and107recorded PID/start identities independently absent,
groups/private runtime/scope closed. No production change required.
Proof and combined independent review: .scratch/all-tickets/linux-wait-entry-proof.md
and linux-wait-entry-review.md, original native88 logs and root closure receipts.
This closes only the untimed wait cancellation-lock criterion in these Linux rows.
Timed waits, other features/platforms, managed-group/forced-custody/performance and
full release requirements remain open; ticket implementation is not complete.
