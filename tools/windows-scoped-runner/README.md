# Candidate Windows monitor/client custody source

This checkout contains intermediate Windows source only. It is **not accepted or
ready to run**. None of the C# sources or fixtures in this substep has been
compiled or executed, and no package build, guest run, compiler bootstrap,
installation, or staging backend operation was performed.

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

The wire value is now accepted by the monitor through the bounded transport
intake described below. Intake does not connect the specification to workload
creation; public workload launch and exact-job proof remain disabled.

The monitor accepts setup lease challenges/responses and bounded specification
intake, then remains in protocol-only setup mode and stops on deadline or
disconnect because workload custody is unavailable.
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
allocation owner for its remaining lifetime. Staging is not wired to the
monitor; ACL behavior, collision behavior, byte copying, and journal durability
remain unverified. An incomplete/torn journal record is detectable; no recovery
or cleanup decision is made from a path alone.

The source rescan is a consistency check for an operational input tree, not an
atomic or hostile-tree snapshot. It detects additions, removals, identity,
metadata, and content changes observed between the copy manifest and final
rescan. It does not rule out adversarial same-user mutation in the interval
after that rescan and before the receipt. No hostile source-tree isolation or
launch readiness is claimed.

The create/resume states in the protocol fixture are modeled transitions only;
the second challenge and actual suspended/resume operations are not wired to a
backend. Every `--source`/`--exe` workload request is refused by the public
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
The public workload path remains disabled, and production removal
fails closed because the monitor does not yet issue an exact-job closure proof.
The typed fixture authorization exercises filesystem transitions only; it does
not stand in for process/job custody. These disposition fixtures are source
only and uncompiled/unexecuted. Native disposition, receipt readback, exact-job
proof production, and end-to-end acceptance remain unverified. Its source-tree staging fixtures cover successful
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

The previous source substep's job-list creation fixture remains in
`fixtures/RunProcessCreationFixtures.ps1` and `fixtures/PayloadFixture.cs`; it
covers the older candidate path only and is not wired to the current public
entrypoint. It has not been run.

## Remaining custody and proof boundaries

Executable-relative syntax checks and staged-file identity checks are present
in source, but executable launch validation remains unverified. Monitor-to-custody
integration, local evidence
finalization/export, exact job ownership and
cleanup, the real create-time payload integration, pre-resume host challenge
integration, termination and finalization budgets remain unimplemented. Runtime
disposition is present in source, but no monitor path can create the
unforgeable exact-job closure proof, so production removal remains fail-closed.
The fixture authorization tests filesystem-only transitions, not job closure.
Handle-disposition semantics, compilation, independent native readback, and
the effect of unrelated external handles remain unverified. The lease protocol
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
Completion retains the immutable specification in monitor memory only. It does
not renew the lease, authorize create/resume, reset deadlines, or allocate a
runtime. Setup `RESPONSE` frames are checked against the exact outstanding
phase-bound challenge and may renew the short lease; this intake path uses
maintenance responses that cannot authorize create or resume. A fresh
post-staging challenge remains required before any future creation step.
Allocation, source staging, workload entry, process creation/resume, and exact
job proof remain disconnected and disabled. No pipe/native acceptance is
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
