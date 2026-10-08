# Candidate Windows monitor/client custody source

## Native bootstrap and separate custody acceptance route

`MonitorAcceptanceDriver` is a separate route prepared for Windows guest
custody acceptance. On 2026-10-08, the narrow native BuildOnly bootstrap passed
as non-admin RhaiTest: three compiled binaries, real exit-status and setup-cleanup
controls, owner-only job disposition/watchdog drain, and a complete hash-verified
24-file host export. The combined review accepts only that compiler prerequisite.
See [the original proof](../../.scratch/rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/bootstrap-proof.md). `fixtures/RunSourceFixtures.ps1 -BuildOnly` compiles it without
launching it inside the compiler job. Native acceptance remains unproven until
the actual driver and its OS readbacks pass. It launches the public `ScopedRunner.exe
--lease-client`, transfers the canonical immutable `RHAI-LAUNCH/1`
specification, and answers fresh monitor challenges. `success` requires a
single-deadline bounded journal readback, canonical CRC32 frames, the exact
ordered completion grammar, linked allocation/evidence identities,
independently hashed evidence files, matching expected payload and client exit
codes, confirmed cleanup, and an absent runtime directory.
`--expected-payload-exit HEX` is mandatory and must be the exact expected
eight-digit payload exit value. EOF or disconnect does not count as successful
protocol coverage.

The native route uses a separate controller job with fixed active-process,
per-process-memory, and job-memory limits. The controller job grants breakaway
capability to eligible children; this launch path uses it for the detached
monitor while retaining the real `--lease-client` process until completion or
the driver's 180-second whole-driver monotonic deadline. That deadline covers
protocol I/O, client exit, journal inventory/readback, evidence hashing, and
job disposition. An exact-current-process watchdog stays armed for that entire
interval, including bounded reader joins and cleanup; on expiry it terminates
the retained driver process handle, leaving the main thread as the sole
controller-job handle owner. The escaped monitor has its own
production 30-minute absolute deadline, 30-second termination deadline, and
30-second finalization deadline; it watches the client's real process handle
and owns payload cleanup. The payload job does not grant breakaway; it uses its
own kill-on-close containment. The driver refuses to start inside an ambient job because the
existing source-fixture harness deliberately uses a no-breakaway containment
job. The driver is a separate bounded guest launch route, never a child of that
source-fixture harness. `disconnect-alive`, `client-death`, and `replay` are finite negative
controls. Their observed journals and exact exit/cleanup diagnostics are
controls, never successful protocol coverage. They act only after four fresh
post-transfer challenges, spanning setup, create, resume, and a Running lease
renewal in the current monitor protocol. Each negative control requires
its explicit driver action, exact `MonitorStopped` outcome, client exit
(`client-death` is 1; the other modes are 78), payload exit `0000007D` from
the monitor's `TerminateJobObject(..., 125)` action, cleanup receipt, and
removal readback. This negative-control contract assumes the payload was
created before the host action; missing or contradictory payload termination
evidence fails closed. Journal inventory ambiguity,
malformed/torn records, CRC mismatch, or an unbounded journal fail closed. The
job flag allows eligible children to break away; source does not prove the
detached monitor is the only child that could do so. Cleanup clears
kill-on-close only after the exact client has exited and job accounting reports
exactly the driver process. If that check or a cleanup API fails, the job
remains kill-on-close and final status fails.

### Compile and launch custody route

Use the existing bootstrap's narrow `-BuildOnly` selection for this project's
custody prerequisite. Launch the script in a new 64-bit PowerShell child, with
`-SourceRoot <immutable-input>` and an absent
`-RunRoot %USERPROFILE%\.local\share\agent-builds\rhai\<session>\run\monitor-source-<GUID>`.
Create only that owned session's `run` parent first. `BuildOnly` retains the
setup-failure and real exit-0/17/mismatch controls, verifies the nine production
pins plus the driver/payload pins, and compiles only `ScopedRunner.exe`,
`MonitorAcceptanceDriver.exe`, and `PayloadFixture.exe`. The missing-source
compiler control must fail with CS2001. No synthetic suite or native driver runs
inside this compiler job. Its wall deadline is 15 minutes, each compiler has
180 seconds, output files are capped at 4 MiB, and the existing no-breakaway
job retains its 1 GiB per-process / 2 GiB aggregate / 16-process limits.
`build-manifest.txt` and `run-result.txt` are written after owner-only accounting,
job disposition and watchdog drain. Preserve their exact compiler/source/binary
hashes and original logs. `BUILD_ONLY_PASS` proves only this bootstrap slice;
it does not prove public lease-client custody or native product behavior.

Only after this compiler child has exited, invoke the driver from the independent
uncontained console. The driver and runner must stay in the same retained build
directory. Do not invoke the driver from the bootstrap or one of its descendants.

The existing `RunSourceFixtures.ps1` output is reusable only when its retained
`build/ScopedRunner.exe` was produced from the exact nine production-source
hashes pinned by that harness and the accepted monitor-source checkpoint. Keep
that fixture run directory intact. Copy that exact runner into a fresh direct
child of the current user's private `<session>\run` directory named
`monitor-driver-<32 lowercase hex>` and
record/read back its SHA-256. Copy the nine pinned production sources,
`MonitorAcceptanceDriver.cs`, and
`fixtures/MonitorAcceptanceDriverFixture.cs` into that run's private `input`
tree; verify every frozen source hash before invoking the existing compiler at
`C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe`. Compile both outputs
into the run's `build` directory with bounded stdout/stderr files and the
existing 180-second per-compiler ceiling:

The dependency freeze for this route is the nine-file source manifest in
`RunSourceFixtures.ps1` (checkpoint `c8c6b18caaa855d2f66e0fc1f84e594d4f1e5e6b`),
plus the driver
from checkpoint `5583d7b3de50bb0f8c2706b837d2d4ba64ff9368` with the native-proven
missing `TerminateJobObject` declaration repair, and its unchanged pure fixture.
Their current SHA-256 values are
`MonitorAcceptanceDriver.cs`:
`80235547abbf1ccdaed6bac7aae816a236676ef38f3055366fb206255e95a550`, and
`fixtures/MonitorAcceptanceDriverFixture.cs`:
`33581ea00e1dc536bf4afdd8842c0a9cc3fdd028514e228c8b1ca776d40e1db0`. Retain
the unique run root, copied sources, runner and driver binaries, fixture result,
compiler logs, and hashes for inspection; do not reuse or delete it after a
failed run.

```text
csc.exe /target:exe /main:MonitorAcceptanceDriver /out:<run>\build\MonitorAcceptanceDriver.exe <nine production sources> MonitorAcceptanceDriver.cs
csc.exe /target:exe /define:SCOPED_RUNNER_TESTING /main:MonitorAcceptanceDriverFixture /out:<run>\build\MonitorAcceptanceDriverFixture.exe <nine production sources> MonitorAcceptanceDriver.cs MonitorAcceptanceDriverFixture.cs
```

`fixtures/CompileMonitorAcceptanceDriver.ps1` is the separate compile-only
wrapper candidate. Its inputs are the source checkout, the retained
`monitor-source-<GUID>\build\ScopedRunner.exe`, the independently accepted
build's lowercase SHA-256 as `ExpectedRunnerSha256`, and a fresh
`%USERPROFILE%\.local\share\agent-builds\rhai\<session>\run\monitor-driver-<GUID>` root. It verifies the retained
runner against that supplied accepted-build hash before and after copy,
verifies the retained source tree against the nine production pins, copies and hashes those files
plus the driver and pure fixture, compiles the driver and fixture, checks a
deliberate compiler failure, and runs only the fixture. It retains the runner,
inputs, outputs, manifest, result and capped compiler/fixture logs. The wrapper
uses a 4 MiB per-log polling cap, 180-second compiler and fixture waits, and a
one-hour exact-owner watchdog. Its controller job is no-breakaway, kill-on-close,
and limited to 1 GiB per process, 2 GiB aggregate and 16 active processes. It
must query exactly one remaining process before clearing kill-on-close and
closing the job. Any query, flag-change, or close failure terminates the exact
controller fail-closed before the watchdog or retained process owner is
released; if close fails after the flag was cleared, it explicitly terminates
the exactly-accounted job first. This wrapper source has not been compiled or executed on
Windows; source-presence tests are scaffolding, not custody proof. The accepted
source-fixture harness compiles the driver only under `BuildOnly` and cannot launch it from its
no-breakaway job.

Only after that compiler owner has exited, launch the driver directly from a
separately verified uncontained interactive console process. Do not run it
from `RunSourceFixtures.ps1`, one of its descendants, or another job-contained
launcher: driver `Main` checks `IsProcessInJob(self, NULL)` and refuses ambient
job membership. It creates its own controller job, assigns itself before
creating the `ScopedRunner.exe --lease-client` child, requires that client to
remain in the controller job, and permits eligible children to break away so
the detached monitor can refuse ambient membership. The payload job remains
kill-on-close without breakaway. The escaped monitor retains its independent
Expert02 absolute and cleanup deadlines; the driver watchdog retains the exact
driver process handle and its single 180-second monotonic deadline through
protocol, client wait, journal inventory/readback, evidence hashing, pipe
joins, and job disposition. The controller job's flag allows any eligible
child to break away; source does not establish that only the monitor can do so.

The implemented driver modes are `success`, `disconnect-alive`,
`client-death`, and `replay`. Each sends the immutable specification and exact
transfer ACKs. Disconnect closes the driver's input after four fresh
post-transfer challenges; client-death kills the exact client after that
point; replay re-sends a previously answered challenge after a bounded delay.
The success validator requires the caller's exact expected payload exit,
`PayloadExited`, client exit 78, confirmed cleanup/removal, and independent
evidence hashes. Negative validators require the exact driver action,
`MonitorStopped`, payload exit `0000007D`, client exit 1 for client-death and
78 otherwise, confirmed cleanup/removal, and evidence hashes. These are source
contracts only: no native protocol, process, journal, or evidence behavior has
been exercised.

The driver's workload path is the public `--lease-client` entrypoint, which
receives the immutable source/executable specification over the protocol; it
does not call the refused legacy direct `ScopedRunner.Main --source/--exe`
path. Subject to compilation and native execution, the driver is intended to
exercise one ordinary successful payload run plus connection loss while the
client remains alive, exact client death, and a replayed challenge. The
negative controls need a created payload to establish the expected
`TerminateJobObject(..., 125)` result; absent or contradictory termination
evidence must fail closed. None of these four native cases has been run yet.

The full Expert02 native set remains required under its one-hour outer bound,
2 GiB job memory cap,
16-process cap, 2 GiB free-space preflight, and unique retained run root:
ordinary success with residual-child cleanup, payload failure, lease expiry,
connection loss while client remains alive, client death, expired/replayed
challenge, suspended-create/resume failure, nested-job refusal, output cap,
evidence/readback failure, and cleanup timeout. Every monitor retains the
fixed 2-second challenge interval, 15-second lease, 120-second setup deadline,
nonrenewable 30-minute absolute lifetime, 30-second termination/emptiness/
handle-closure deadline, and shared 30-second evidence-finalization/removal
deadline. The maximum-lifetime case consumes the full 30 minutes. Record
elapsed time and storage use separately. Preserve every runtime, evidence
directory, and journal on failure; diagnose and have root read back preserved
state before retrying. Host export is not implemented and remains open for all
four modes; the driver verifies locally retained evidence and reports
`HOST_EXPORTED=0`.

The public custody route is **not accepted**. The native BuildOnly compiler
prerequisite above is accepted; no public lease-client or Rhai product run follows
from it. The separate driver parser/control fixture remains source-only
scaffolding. Python source-presence checks do not prove native custody. No SDK
installation or staging backend operation was performed by the bootstrap.

The parser/control fixture has its own executable `Main`. Its isolated compile
route explicitly selects `/main:MonitorAcceptanceDriverFixture` and uses the
full production source set already declared in `RunSourceFixtures.ps1`:
`LaunchSpecification.cs`, `LeaseMonitor.cs`, `MonitorPayloadJob.cs`,
`MonitorSpecificationIntake.cs`, `MonitorStagingHandoff.cs`,
`MonitorTransport.cs`, `ScopedRunner.cs`, `SpecificationTransfer.cs`, and
`WindowsCustodyBackend.cs`, plus `MonitorAcceptanceDriver.cs` and
`fixtures/MonitorAcceptanceDriverFixture.cs`. Compile with
`/define:SCOPED_RUNNER_TESTING` and place output under the scoped private
runtime directory. The fixture is not included in `RunSourceFixtures.ps1`;
its compile and execution remain open; BuildOnly compiles the production driver
and finite PayloadFixture, not this parser/control fixture.

`ScopedRunner.exe --lease-client` is the only public source entrypoint. It starts
a detached monitor with an explicit inherited-handle list containing two pipe
ends and a real restricted handle to the client process. It requests breakaway
when the client is in a job, clears handle inheritance in the monitor, and the
monitor refuses ambient job membership before allocation. The client forwards
host input and monitor output on separate workers; the monitor's watchdog loop
uses finite polling and does not join those workers or wait on a pipe. The lease
protocol uses bounded input frames/output queue, a fresh nonce and increasing
sequence for each outstanding challenge, phase-bound one-use authorization,
fresh Running-state lease renewals that cannot authorize create/resume, a
nonrenewable absolute deadline, monotonic `GetTickCount64` deadlines, and an
irreversible stopping state.

`LeaseProtocolFixture.cs` is protocol-only behavior source. It covers stale
nonce/sequence and future responses, one-use and phase-bound create/resume
authorization, setup and absolute expiry with timely Running renewals, response
replay/phase/nonce/sequence rejection, exact lease expiry, a live blackholed
client, EOF and client death, pre-resume expiry, and bounded output backpressure.
These cases exercise the protocol state model only. They do not launch a monitor process,
create payloads, inspect exact process/job handles, or prove transport survival.
The fixture is deliberately unexecuted.

`LaunchSpecification.cs` adds a pure managed, immutable version-1 specification
codec, not a launch integration. Its canonical UTF-8 representation is newline
delimited `RHAI-LAUNCH/1`, followed by base64 UTF-8 `source`, `executable`, an
`argument-count`, and contiguous indexed `argument-N` records. The full encoded
input is limited to 8,192 bytes; source/executable/argument fields to 1,024
decoded UTF-8 bytes each; arguments to 32; and the conservatively bounded,
Windows-quoted command line to 4,096 characters. Source and relative executable
paths receive syntax-only validation. The parser does no filesystem I/O and
proves no source identity, existence, authority, staging, or executable
validity. Its unconnected command-line formatter also checks the eventual
staged executable path as a bounded absolute local Windows path, without
checking that the path exists. Unknown fields reject cleanup paths and policy
overrides; policy continues to come from the fixed monitor policy.

The wire value is accepted by the monitor through the bounded transport intake
described below. Accepted staging now requests fresh create and suspended-resume
host challenges through the dispatcher, then retains the payload job and staged
allocation on the same owner worker. This source path is uncompiled and does not
establish native launch or exact-job closure proof.

The monitor accepts bounded specification intake and phase-tagged lease
challenges/responses. Once a complete immutable specification is accepted, it
starts the monitor-owned staging worker. After staging acceptance, that worker
requests a fresh create challenge, creates the payload suspended in its private
job, requests a fresh suspended-phase challenge, resumes, and retains ownership
until stop or deadline. The watchdog continues polling, dispatching frames, and
signaling only; it does not create or clean up the payload.
The `WindowsCustodyBackend.cs` source slice pins the fixed local
`C:\RhaiQuality\runs` root and each ancestor through non-reparse directory
handles that omit delete sharing, and captures volume/file identity. Its
bounded journal creates a unique external file with a protected current-user
and SYSTEM DACL, verifies that ACL through the opened handle, and flushes each
bounded framed record. A source-only allocation owner now flushes an intent
before exclusive `CreateDirectoryW`, supplies a protected user/SYSTEM DACL at
creation, refuses an existing name, verifies the opened directory handle's
DACL and file identity, and flushes identity before marking it recorded. It
also contains a source-only staging operation: it accepts only an
identity-recorded allocation, bounds the tree to 2,048 entries, depth 32, 64
MiB per file, and 512 MiB total, creates destination entries exclusively with
protected user/SYSTEM DACLs, hashes each copied file, rescans the source and
destination manifests, and writes a durable `STAGED` receipt only after those
checks. Source file and directory pins stay held through the consistency scan
and receipt. The staged executable and each parent directory are pinned on the
allocation owner for its remaining lifetime. The monitor worker invokes
allocation and staging after immutable intake; ACL behavior, collision behavior,
byte copying, and journal durability remain unverified. An incomplete/torn
journal record is detectable; no recovery
or cleanup decision is made from a path alone.

The source rescan is a consistency check for an operational input tree, not an
atomic or hostile-tree snapshot. It detects additions, removals, identity,
metadata, and content changes observed between the copy manifest and final
rescan. It does not rule out adversarial same-user mutation in the interval
after that rescan and before the receipt. No hostile source-tree isolation or
launch readiness is claimed.

The monitor source now routes fresh create/resume challenges and suspended
process transitions through its owner worker. Native backend behavior remains
unverified. Every `--source`/`--exe` workload request is refused by the public
entrypoint. The older payload staging implementation remains as unreachable
source history and must not be used.

`fixtures/CustodyBackendFixture.cs` is source-only behavioral coverage for
directory pin identity, rename exclusion, bounded journal writes, external
placement, independent journal readback, and rejection of truncated frames or
missing final newlines. It also describes allocation transitions, including
intent-before-create, collision refusal, ACL and identity verification, ordered
identity journaling, and retained post-create uncertainty. The fixture has not
been compiled or run. It deliberately retains every allocation fixture runtime
and its associated journal, including the uncertain post-create case, and
prints each exact runtime/journal path pair. The source now includes a bounded,
bottom-up handle-disposition path using the retained runtime DELETE pin,
no-follow child opens, protected-ACL and full 128-bit identity checks, durable
removal intent, and independent pinned-parent absence readback before the
removal receipt. It uses `FileIdExtdDirectoryInfo`/`RestartInfo`; an unsupported
class or a filesystem that does not return a usable 128-bit ID fails closed.
The public workload path remains disabled. The monitor source now wires exact
job closure to bounded stdout/stderr capture, a complete runtime snapshot,
independent evidence readback, outcome recording, and the identity-bound
removal gate. These steps are source paths only: the disposition fixture seam
does not stand in for native process/job custody, and no runtime removal was
executed. The source fixtures are uncompiled and unexecuted; native
disposition, receipt readback, exact-job proof production, and end-to-end
acceptance remain unverified. Its source-tree staging fixtures cover successful
nested copies, fail-closed source changes and sharing, source/destination
reparse points, collisions, partial-copy retention, inventory, per-file, total
byte and depth bounds, cancellation, and receipt readback after handles close.
Failure-boundary cases assert their specific diagnostic, the retained runtime
and identity record, and absence of a `STAGED` receipt after disposal. The
aggregate-byte case may require up to 576 MiB of logical source input and 512
MiB of destination capacity; run it only under a separately bounded native disk
budget. These fixtures are uncompiled and unexecuted; fixture dependencies and
symlink privileges remain native gates.
No compiler, runtime, Windows build command, guest command, or fixture process
was invoked for this change. Disposition fixtures intentionally retain and
print every exact runtime/journal path pair, including partial and uncertain
states; they do not claim cleanup of those fixture resources.

`MonitorPayloadJob.cs` adds a monitor-owned, noninheritable unnamed job owner.
It applies kill-on-last-close without breakaway flags, associates the staged
payload during `CreateProcessW` through `PROC_THREAD_ATTRIBUTE_JOB_LIST`, keeps
the exact process/thread/job handles, checks job membership while suspended,
and requires a second protocol authorization before `ResumeThread`. Setup
failure stops the protocol, terminates through the exact job when a process was
created, waits on its exact process handle, releases every initialized
attribute allocation, and attempts to close exact process/thread/job owners.
Those owners use `SafeHandle`: failed explicit close retains the exact handle
for retry or finalization; an abandoned job owner requests exact-job
termination before its bounded close retry. Setup and cleanup failures are
retained together. If the kernel continues rejecting close or termination,
eventual process-exit cleanup is the only remaining OS guarantee; that outcome
is unknown and is reported as incomplete custody.

`fixtures/MonitorPayloadJobFixture.cs` is source-only coverage for missing and
phase-stale transition authority, callback failure/exception stop behavior,
deadlines before and after the callback, atomic stop/resume serialization, and
injected exact-handle close failures with SafeHandle fallback.
The fallback case invokes `SafeHandle.Dispose` directly; GC finalization is not
tested. Its stop/resume race case samples noncompletion for 100 ms after the
stop-attempt signal; that bounded observation is not a deterministic scheduler
proof. The fixture has not been compiled or executed and cannot establish
Windows job, process, finalizer, or native close behavior.

The owner worker is now wired into `MonitorTransport` for the accepted staging
transition and retains the payload until protocol stop/deadline. This source
connection has not been compiled or run. The existing
`fixtures/RunProcessCreationFixtures.ps1` still covers only the older
`ScopedRunner.cs` reference path. The new fixture exercises the protocol and
injected handle seam only; it does not create a native job or payload. No
fixture has been compiled or run. The monitor source contains a launch path, but
successful Windows process/job behavior remains unverified.

## Remaining custody and proof boundaries

Executable-relative syntax checks and staged-file identity checks are present
in source, but executable launch validation remains unverified. Monitor-owned
allocation/staging handoff, exact-job closure, and bounded outcome-metadata
journaling are present as source. The record distinguishes payload exit,
supervision outcome, confirmed cleanup, saved metadata, payload evidence,
host export false, and runtime removal. The payload uses explicit NUL stdin and
restricted inherited stdout/stderr named-pipe writers; one owner worker drains
overlapped reads into bounded external logs. After exact-job closure, the same
worker inventories and copies the complete runtime tree, checks the independent
snapshot and manifest readback, and binds an evidence receipt to allocation,
identity, closure proof, exit status, supervision outcome, and one absolute
deadline. Runtime disposition is source-wired behind that receipt. An
incomplete copy, log, readback, diagnostic, or deadline check withholds the
receipt and retains the runtime. The monitor watchdog polls worker completion
only through that worker's already established cleanup deadline; unresolved
overlapped storage remains strongly held until process teardown. Host export
has no protocol response contract and remains explicitly unimplemented.
Source fixtures now cover successful snapshot/readback/removal ordering and
pending-I/O release-state decisions, but remain uncompiled and unexecuted. The
monitor process, Win32 I/O, ACL, job, filesystem-removal, and end-to-end
behavior remain unverified. The lease protocol
model supports fresh Running-state renewal challenges while keeping the absolute
lifetime fixed; real workload and native transport integration remain
unproven. Client/monitor pipe behavior, breakaway compatibility, ambient
job refusal, process and job readback, failure cleanup, host-disconnect survival,
sleep/resume deadline behavior, and all other native Windows behavior remain
unverified.

Do not use this source to launch package builds until the full custody backend
is implemented and the authorized native acceptance gates pass. No compiler,
fixture, runtime, Windows build command, or guest command was invoked for this
source change.

## Immutable launch-specification transfer model

`MonitorTransport.RunMonitor` now uses `MonitorSpecificationIntake.Dispatcher`
and `SpecificationTransfer.Receiver` to accept one immutable
`LaunchSpecification` over the monitor pipe. The reader preserves original
bytes, including the final LF, and applies the 512-byte bound to the complete
frame. Partial EOF, CRLF/noncanonical control framing, malformed transfer
frames, fixed setup-deadline expiry, reader/writer failure, and bounded queue
admission failure stop intake. The dispatcher checks fresh monotonic time for
each frame and again before acknowledging a transfer frame. It queues ACKs
without waiting and keeps the 32-frame/8192-byte limits.

The monitor creates and advertises one random 32-lowercase-hex transfer token.
Completion retains the immutable specification in monitor memory and starts
one staging worker. It does not reset deadlines. `RESPONSE` frames are checked
against the exact outstanding phase-bound challenge and may renew the short
lease. Only challenges explicitly requested by the owner worker after staging
or suspended creation can authorize create or resume; ordinary setup and Running
responses only renew the lease. The fixed setup deadline applies until Running;
the lease and absolute deadline continue afterward.
Source allocation and staging now run on a dedicated monitor worker after
intake. The watchdog uses a one-slot atomic ownership handoff and only signals
cancellation; a separate signal thread updates the backend token. In-flight
filesystem calls may finish after stop. Failed or rejected allocations are
disposed by the worker, retaining their runtime and journal. A successful
accepted allocation remains pinned on the owner worker while it waits for fresh
create/resume responses and retains the resumed payload. Stop or deadline
returns payload and allocation cleanup to that worker. The monitor polls worker
completion through the same absolute cleanup deadline without joining it; then
it exits with failure and process teardown releases unresolved kernel I/O. Setup
unwind uses the setup deadline, while successful setup binds its first cleanup
request to the lifecycle cleanup deadline; later cleanup calls can only shorten
that deadline. A stalled worker or pending I/O never becomes a cleanup receipt.
Exact-job proof, evidence, outcome, and runtime-removal gates are wired in
source, but no native execution or runtime deletion was performed. Their
successful Windows behavior remains unverified; no pipe/native acceptance is
claimed.

`SpecificationTransfer` implements `SPEC-XFER/1` `BEGIN`, `DATA`, and `END`
frames, each terminated by one LF byte. The receiver token is supplied by its
monitor owner; the transfer receipt does not authorize process creation or
renew a lease. The fixed chunk size is 324 input bytes, encoded as at most 432
base64 bytes.

The largest DATA frame is 486 bytes including token, fields, and LF; the largest
DATA acknowledgement is 57 bytes. An 8192-byte specification uses 26 DATA
frames plus BEGIN and END, for 28 frames in each direction. The sender retains
one outstanding frame and advances only after the corresponding token/kind/
index acknowledgement. The immutable input limit, 512-byte transport frame
limit, and 32-frame/8192-byte queue are unchanged.

The source fixture covers framing, dispatcher/lease interleaving, maximum-size
transfer, replay and wrong-token failure, queue pressure, and deadline
boundaries. It has not been compiled or executed. Source fixtures prove neither
pipe connectivity nor process, job, or native custody. Native Windows API
behavior, monitor/client process behavior, compiler compatibility, and all
full-custody acceptance gates remain unverified.
