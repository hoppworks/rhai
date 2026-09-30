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
monotonic `GetTickCount64` deadlines, and an irreversible stopping state.

`LeaseProtocolFixture.cs` is protocol-only behavior source. It covers stale
nonce/sequence and future responses, one-use and phase-bound create/resume
authorization, setup and absolute expiry, a live blackholed client, EOF and
client death, pre-resume expiry, and bounded output backpressure. These cases
exercise the protocol state model only. They do not launch a monitor process,
create payloads, inspect exact process/job handles, or prove transport survival.
The fixture is deliberately unexecuted.

The monitor currently accepts a valid first host round-trip and then fails
closed. The source does not create a runtime, journal, evidence store, payload
job, or payload process. The create/resume states in the fixture are modeled
transitions only; the second challenge and actual suspended/resume operations
are not wired to a backend. Every `--source`/`--exe` workload request is refused
by the public entrypoint. The older payload staging implementation remains as
unreachable source history and must not be used.

The previous source substep's job-list creation fixture remains in
`fixtures/RunProcessCreationFixtures.ps1` and `fixtures/PayloadFixture.cs`; it
covers the older candidate path only and is not wired to the current public
entrypoint. It has not been run.

## Remaining custody and proof boundaries

Safe handle-based staging, protected runtime ACL and identity, durable journal,
local evidence finalization/export, exact job ownership and cleanup, the real
create-time payload integration, pre-resume host challenge integration,
termination/finalization budgets, and verified runtime removal remain
unimplemented. Client/monitor pipe behavior, breakaway compatibility, ambient
job refusal, process and job readback, failure cleanup, host-disconnect survival,
sleep/resume deadline behavior, and all other native Windows behavior remain
unverified.

Do not use this source to launch package builds until the full custody backend
is implemented and the authorized native acceptance gates pass. No compiler,
fixture, runtime, Windows build command, or guest command was invoked for this
source change.
