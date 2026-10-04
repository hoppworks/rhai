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


## Accepted Linux simultaneous IO and active deadline subset — 2026-10-03

Frozen9e56d5f2, native Rust/Cargo1.77.2, sys/sys+sync/sys+metadata+serde/
sys+net+sync+metadata+serde/sys+f32_float: public Engine simultaneous128KiB
stdin and256KiB per-stream output reaches exact cap with complete flags and
independent completed-input record/reap. Blocked512KiB stdin with active
stdout/stderr reaches configured deadline, returns bounded partial output and
incomplete flags through both raw/text APIs, with independent readiness/reap.
Two meaningful controls per row fail101 after explicit record-derived ESRCH,
then original tests pass. No per-call latency upper bound is asserted.

Invocation89 has50 original exact GREENs covering ten selected cases, but only
the two controlled cases above have newly established assertion sensitivity.
Other eight cases are positive regression evidence awaiting applicable controls
before strict individual closure. Root independently checks425PID/start
identities/tencontrolPIDs absent, group/runtime/scope closed and221ownedstage
files removed after exported hash verification. Proof/review/original logs:
.scratch/all-tickets/linux-process-io-proof.md and linux-process-io-review.md.
All remaining platform/feature/managed/fault/latency/performance and release
criteria remain open. Existing partial evidence/cause/budget history unchanged.

## Remaining Linux process-options branch acceptance — 2026-10-03

Frozen469998 with privateRust1.77.2 and compatible lock2ba4: invocation90
passes40 exact original tests and80 intended sensitivity controls for eight
remaining process cases across five checked feature rows. Capture raw/text
under exit0/7, stdout/stderr cap+1, zero-cap silent/first-byte branches, raw/text
deadlines, unit timeout/stdin, capability-held cwd/escape denial and lossy UTF-8
limit expansion have targeted branch proof. Combined review accepts this narrow
coverage; it is not proof of every assertion or complete process-ticket closure.
Original logs, control overlays/restoration, independent729PID/start and95printed
fixturePID readback, and exact401file/sixdir staging cleanup are in
../../all-tickets/linux-process-options-proof.md and its referenced artifacts.
No no_float/unchecked/managed/performance/other-native-platform/finalrelease
claim. Existing record-reuse, cwd PID and deadline-latency limits remain explicit.
Invocation89's two controlled cases retain their accepted applicability.

## Linux integer-only and unchecked process subset — 2026-10-03

Native invocation 93 uses frozen `6c451c5c` plus the exact reviewed test patch
`5cf5d453`; production is unchanged. Private Rust/Cargo 1.77.2, compatible lock
`2ba4`, and three rows (`sys`, `sys+only_i32+no_float`, `sys+unchecked`, each with
`testing-environ`) pass 32 original exact tests and 33 intended assertion controls.
Independent combined review accepts the targeted feature compatibility and host
output-cap criteria. Scripts requesting 8192 bytes cannot raise the host's
4096-byte cap for either stream; real child records and reaping precede exact
prefix/error checks. The helper's INT-width and unchecked Engine API compiler
regressions are reproduced separately and repaired in tests.

Fractional deadlines under `no_float` are host defaults; fractional per-call
script values are not proven. The unchecked Engine expansion criterion is
excluded, not passed. Existing normal-row sensitivity from invocations 89/90 is
reused; new feature controls cover selected branches, not every prior assertion.
Original evidence, combined review, all source/overlay identities and independent
445 PID/start plus 42 fixture-PID closure receipts are referenced in
`../../all-tickets/linux-process-feature-proof.md`. All 251 owned stage files and
five subdirectories were retired after export verification. Failed preparation
invocations 91/92 and their causes remain preserved without product acceptance.

This partially closes the Linux process feature requirements only. Managed
groups, remaining fault/lifecycle criteria, performance, other native platforms
and final release acceptance remain open.

## Linux managed final-clone drop — native102, 2026-10-03

The exact public-Engine final-clone-drop case is accepted on Rust 1.77.2 in four
selected Linux feature rows by the combined review in
`../../all-tickets/linux-managed-final-drop-review.md`. Nonfinal clone drop preserved the live managed
group; final drop was recorded independently, followed by bounded PIDFD
closure observation while the host, reaper, and sentinel remained live. Exact
leader/worker/leaf identities and groups, successful fixture reaping, a
post-cleanup wrong-control, affected base-row regressions, original export,
restoration, and fresh cleanup readback are documented in
`../../all-tickets/linux-managed-final-drop-proof.md`. The native originals are
retained under `../../all-tickets/linux-managed-final-drop102-evidence/` in the
acceptance worktree.

This covers only final-clone drop for the selected Linux rows. It does not close
the process contract: managed deadline/overflow, remaining lifecycle/fault
cases, other platform rows, and final release acceptance remain open.

## Current Linux MSRV held-zombie boundary — 2026-10-03

Native invocation 95 at frozen `257edf69`, private Rust/Cargo 1.77.2 and
`testing-environ,sys` passes the exact held-zombie integration test after two
meaningful wrong-expectation controls fail at their intended assertions. Real
Engine/OS observations bind live host, reaped direct leader, exact held worker/
leaf zombies, typed closure TimedOut, direct exit 0, complete captures and final
fixture reaping. Source restoration, original receipts and independent combined
acceptance are recorded in `../../all-tickets/linux-managed-zombie-proof.md`.
Fresh readback confirms 99 exact PID/start identities absent, four groups empty,
and all owned stage/runtime/scope resources removed. Invocation 94 remains an
infrastructure output-parser failure; its originals and consumption are retained.

This closes only the current Linux MSRV held-zombie criterion. Ordinary managed
success, remaining managed/fault/lifecycle paths, other feature/native-platform
rows, performance and final release acceptance remain open. Prior valid proof
and stopped cause/budget histories retain their recorded applicability.

## Linux managed prompt-success and held boundary — 2026-10-03

Native invocation 96 at frozen `003da064`, private Rust/Cargo 1.77.2 and compatible
lock `2ba4` proves the public managed run prompt-success and held-zombie boundary
in four rows: `testing-environ,sys`, plus `sync,metadata`, plus `f32_float`, and
plus `unchecked`. All eight exact original tests pass after the three intended
held-mode/wrong-exit/wrong-sentinel controls fail at their named assertions.
The prompt fixture independently reaps its adopted worker/leaf while the host
stays live; exact PID/start/group relations, code 0, complete capture, foreign
reaping, sentinel survival at return and later fixture cleanup are observed.
The held fixture retains the accepted typed incomplete-cleanup boundary.

Combined independent acceptance, exact source restoration, all 72 original
exported files, eleven closure records and fresh identity/group readback are in
`../../all-tickets/linux-managed-success-proof.md` and its referenced originals.
All 210 recorded identity rows are absent and 13 groups empty; these row counts
are not a claim of unique PIDs. Owned stage/runtime/scope were retired exactly.
Integration at `92146c60` preserves the frozen non-scratch source tree; subsequent
evidence commits change no production/test inputs. The two receipt/custody
correction failures and single Expert/follow-up history remain preserved.

This closes ordinary prompt-reaped managed success and adds these held-boundary
feature rows on Linux. Managed deadline/overflow/explicit-kill/final-drop/escape/
setup/drop-false criteria, performance, macOS/Windows and final current-source
release gates remain open. No full ticket closure is claimed.

## Accepted Linux managed Child.kill subset — 2026-10-03

Native101 source61f7bc66, recipes5f78341a, privateRust1.77.2: public Engine spawn/kill/wait closes the managed group, returns a killed unsuccessful report with complete captures, preserves the unrelated sentinel, and independently verifies exact leader/worker/leaf identities and reaping plus successful reaper exit. Four feature rows pass; two post-cleanup opposite controls fail101; affected prompt/held base regressions pass. Same combined review accepted original74 files/eight case closures and fresh exact cleanup. Proof/review/originals: .scratch/all-tickets/linux-managed-kill-proof.md, linux-managed-kill-review.md, linux-managed-kill101-evidence/. This is a partial criterion closure; broader lifecycle/native-platform/current release gates remain open.

## Accepted Linux managed run deadline — native105, 2026-10-03

At immutable source31a61e752d0ffb747be827475278e3fc5d9dbe30, real Engine run
proves managed timeout, honest partial stdout/stderr, exact member/group closure
and independent reaping while host/reaper/sentinel remain live. Four private
Rust1.77.2 Linux feature rows and four affected base regressions pass; one named
post-fullcleanup wrong-timeout control fails101 and source is restored. Combined
review accepts78 originals/nine closure artifacts and fresh exact owned cleanup.
See ../../all-tickets/linux-managed-deadline-proof.md, linux-managed-deadline-review.md
and linux-managed-deadline105-evidence/. This is partial criterion closure only;
OutputLimit, remaining lifecycle/fault/performance, other native platforms and
final current-source release acceptance remain open.

## Accepted Linux managed run OutputLimit — native106, 2026-10-03

Immutable source53b01fa5 with frozen recipesc785a913 passes public Engine managed
run overflow at cap4096 on native Linux/private Rust1.77.2. Exact retained stdout,
typed OutputLimit, timed_out=false, honest incomplete captures, managed group
termination/reaping and live host/reaper/sentinel boundary are independently
proven. Four feature GREEN rows and prompt/held regressions pass; the wrong typed
outcome fails101 after full fixture cleanup, followed by exact source restoration.
All68 original files/five directories match exported hashes; seven original
closures,142 helper/command and two launcher identities are absent, owned groups
empty and exact stage/scope retirement complete. See
../../all-tickets/linux-managed-output-limit-proof.md, the combined review and
linux-managed-output-limit106-evidence/. This closes only the named Linux overflow
criterion and affected regressions. Escaped pipes, post-spawn faults, remaining
lifecycle/performance, other native platforms and final release acceptance remain
open. Earlier borrow correction count1 and other cause/budget history are retained.

## Accepted Linux deadline with escaped capture pipes — native109, 2026-10-03

Immutable source523608648dcae99bc0f6b46eaf2bb91fa4ecc752, reviewed recipes19764c1f,
private Rust1.77.2: public Engine managed run returns typed timeout with retained
markers and honest incomplete captures despite a live escaped holder. Exact
leader/group closure at API return, live host/reaper/sentinel/holder, independent
post-return EPIPE on both writers, then exact fixture release/reaping are proven.
Four feature GREENs and three affected base regressions pass; named opposite
control fails101 after full cleanup and source restoration passes. Same combined
review ACCEPTED all71 immutable originals/seven closure artifacts, fresh custody
and exact stage/scope retirement. See ../../all-tickets/linux-managed-escaped-pipe-proof.md,
linux-managed-escaped-pipe-review.md and linux-managed-escaped-pipe109-evidence/.
This closes only this Linux escaped-reader/deadline criterion. No no_float/no_index,
macOS/Windows, stdin/postspawn faults, remaining lifecycle/performance or full
current-source release acceptance is claimed. Native107 prefix and108 polarity
infrastructure history, successful bounded recoveries and cumulativeUnix109 remain.


## Accepted Linux runnable examples — native example3, 2026-10-04

Source20d25ad8/private Rust1.77.2/lock2ba4: one same-build public Engine
sys/net/sys_process package passes three restored runs after three meaningful
wrong-expectation controls101. Independent host file, TCP peer and child record
readbacks cover effects; process pending wait/release/eight cached fields agree.
Combined review plus separate102 identity/two-group/four-path cleanup accept
this scoped criterion. See ../../all-tickets/linux-process-example3-proof.md.
Only three proven Cargo/example/docs files integrated, no unaccepted stdin
changes. Other lifecycle/platform/feature/performance/release criteria stay open.


## Accepted Linux final handle drop with kill_on_drop(false) — 2026-10-04

Baseline523/private Rust1.77.2, testing-environ,sys, default float/index: real
public Engine direct and managed final-drop cases pass after named wrong-survival
controls101. Independent request-bound observers prove held child/group survival
and eventual closure. Combined review accepts69 immutable originals/seven
directories, fresh131-identity/six-group custody and independent exact retirement
readback. A post-retirement receipt-harness failure and missing deletion stdout
remain explicitly recorded; independent fresh absence confirms closure, and the
reviewed consumer fix requires early receipt persistence for future runs. See
../../all-tickets/linux-drop-false-native2-proof.md and the combined infrastructure
review. No production delta was required; relevant source matches integrated63d948b1.
Only this Linux criterion closes. Remaining pipe-setup fault controls, stdin,
other platforms/features, performance and final release acceptance remain open.
No stopped retry/cause chain is renewed by this partial acceptance.


## Accepted Linux post-spawn pipe configuration failure — 2026-10-04

Baseline523608648dcae99bc0f6b46eaf2bb91fa4ecc752/currentba3 unchanged
production/test source, private native Linux Rust/Cargo1.77.2, testing-environ,sys:
a real Rhai Engine/SysPackage run and real shell child preserve the typed
configure-pipe I/O cause, report honest incomplete captures, reap the child and
retire the owner. Wrong-cause and wrong-completion controls each fail101 after
inner/outer ESRCH readbacks; restored source passes0. Combined review accepts
53 immutable originals/five directories,104 identity/two-group/four-path fresh
closure and exact retirement. See ../../all-tickets/linux-post-spawn-pipe-setup-proof.md
and the combined report. Native1 pre-extraction-cwd failure and native2 consumer
cwd correction remain recorded; valid native proof was reused without another
build or original export. Only this named Linux fault criterion closes. Stdin,
other lifecycle/fault paths, other platforms/features, performance, API metadata
and full release acceptance remain open; stopped retry histories are unchanged.

## Accepted Linux Direct/Managed measurement subset — 2026-10-04

Frozen production baseline8c0ee4634355aee4e841b455461a7dd5aac2aa18, reviewed
measurement overlaya7cef566, private native Linux x86_64 Rust/Cargo1.77.2,
`testing-environ,sys`, locked dependencies and2jobs. Public Engine/SysPackage
and real children produced5start and3complete1MiB captured-run samples per mode,
plus one held/closed resource observation per mode. Start-readiness medians were
1.356ms Direct/1.537ms Managed; whole captured-run medians100.860ms/201.227ms.
The rate includes startup/collection, not transfer-only throughput or causal overhead.
Both modes returned the observed host thread/descriptor counts to their baselines.

Three corruption/census controls passed. One native allocation finished0; the first
custody consumer encountered exited sampler empty cmdline observations, then one
reviewed collector repair recovered using the same unchanged sole originals archive.
93original files/8directories, actual source/tool/lock/rows binding, fresh custody,
exact retirement and separate84PID/start identity/8group/6path closure readback
were independently accepted. No retained build or stage remains. Detailed ranges,
commands, control limits and archive identity are in
[the accepted measurement proof](../../all-tickets/linux-process-performance-proof.md)
and [combined review](../../all-tickets/linux-process-performance-review.md).

This closes only the Linux measurement criterion at the stated revision/workload.
Remaining lifecycle/first-cause, stdin, native macOS/Windows, API metadata/docs,
full current feature/MSRV and release acceptance stay open; stopped causes are
not renewed. Prior unaffected proof is reused, not rerun.

## Accepted Linux same-step overflow/deadline precedence — 2026-10-04

Reviewed source9dc92b16 (production baseline8c0ee463), native Linuxx86_64 private
Rust/Cargo1.77.2, testing-environ,sys. Both DirectChild and Managed public script
runs observe actual child-written readiness, expired deadline and readable stdout
in the same supervision step; OutputLimit wins, with retained prefix, timed_out=false
and honest incomplete captures. Two actual timeout-first controls each select one
test and fail101 for the intended cause assertion after cleanup; pristine source
restoration yields0/0. Sole62originalfiles/5directories/archivee5f0bf6c are preserved.
Live custody and separate fresh closure prove99PID/start identities/fourgroups/six
path entries closed; exact owned stage/runtime/scope retired. No foreign work changed.
The installer observed argv was unavailable; the independently accepted collection-
only recovery binds exact original identity, reviewed spawn, raw setup/private
versions and ancestry, rejecting populated mismatches/other empty command rows.
See ../../all-tickets/linux-process-overlap-proof.md and process-overlap-review.md.
Only this Linux requirement closes. First committed cause, stdin, other lifecycle/
fault criteria, native macOS/Windows, API/docs, full current feature/MSRV matrix and
release acceptance remain open. Existing stopped histories are preserved.
