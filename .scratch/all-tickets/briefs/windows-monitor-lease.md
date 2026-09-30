# Windows monitor and lease implementation substep

## Task

Continue the existing custody correction at b596feba on task/windows-scoped-runner.
Implement the independent monitor/client launch and bounded end-to-end host lease
portion of the already reviewed design. This is a source substep toward the full
contract; it is not acceptance and does not authorize native execution.

Read the complete Expert answer:
/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md
and the source review:
/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/windows-job-creation-review.md.
Use the existing clean owned candidate checkout
/Users/hoppworks/projects/rhai-windows-scoped-runner and its AGENTS.md.

## Required source invariants

- Monitor is the sole future payload job/runtime owner; client only forwards host
  traffic. No duplicated payload job ownership and no client-generated renewal.
- Launch has DETACHED_PROCESS, explicit inherited pipe ends and real restricted
  client-process handle, permitted breakaway where needed; monitor refuses any
  ambient job before allocation. Extra/inheritable handle cleanup is explicit.
- Bounded frames/queues and immutable source/exe/args/fixed limits; bounded setup,
  lease, absolute deadline and cleanup phases. No pipe flush, I/O thread join or
  connected-peer dependency may stall watchdog termination.
- Challenge nonce/sequence outstanding-response checks reject stale/prebuffered
  renewal. Host handshake is required before creation and again before resume.
  Stopping is irreversible; no late commit/renewal/launch.
- Dedicated test source first covers stale nonce/sequence, blackholed live client,
  EOF/client death, setup/absolute expiry, pre-resume expiry and output backpressure.
  Source fixtures may remain unexecuted when no safe C# runtime exists; do not
  substitute static text assertions for behavior or claim RED/GREEN.
- Keep source entry points unable to launch workloads before the remaining safe
  staging/runtime/journal contract is integrated. Existing unsafe copy/staging is
  not a suitable monitor backend; do not silently call it as if custody were done.
  Clearly distinguish implemented protocol/launch portions and missing backend.

## Boundaries

Reuse related context. No guest execution/input, compiler bootstrap, installation,
credentials, administrative work, remote Git writes or agent-home changes. No
new Expert chain. Use only prescribed scoped runner if executable checks are
possible with existing tooling. No running process fixtures on the host.

Create an atomic intermediate source commit with meaningful fixture source and
clear protocol documentation. Report exact commit, files, actual checks, missing
invariants and remaining integration boundaries. Do not stop solely because the
native compiler is unavailable; source implementation is authorized. Do not
report the full contract complete or merge to the coordinator. Preserve cause
history: this remains the same correction; no native correction has failed.
