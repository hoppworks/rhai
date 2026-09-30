# Windows runtime disposition source contract

Continue the related custody implementation in the existing owned candidate
`/Users/hoppworks/projects/rhai-windows-scoped-runner`, task/windows-scoped-runner.
Finish pending staging review corrections first. Read its AGENTS.md and the
retained Expert answer at
`/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md`,
especially Filesystem custody and partial setup. This is the next source
requirement in the existing incomplete correction, not a new escalation or run.

Implement a handle-based disposition operation on the exact identity-recorded
RuntimeAllocation owner. Keep public workload launch disabled. Do not run a
compiler, fixture, guest command, build, install or measurement.

## Required behavior

- Production disposition must remain unavailable until independent exact-job
  emptiness and process-reference closure have been established. Do not expose
  an unchecked caller boolean as proof. Define the future monitor-facing gate
  concretely, keep it closed in the current public entry, and separate any
  test-only no-payload authorization under SCOPED_RUNNER_TESTING. Uncertainty,
  identity-not-recorded and lost ownership retain data; do not reconstruct
  ownership from old paths or PIDs.
- Preserve the held runtime, full ancestor chain, evidence parent and external
  journal. Verify recorded identity through the same owned handle. Close the
  staged executable and its parent pins independently before disposition when
  necessary for compatible sharing; any failed release stops safe removal.
- Enumerate only below the held runtime, with fixed entry/depth and cancellation
  limits. Open every component without following reparses, verify plain type,
  identity and expected private ACL, and pin directories before descent. Reject
  reparses, duplicate identities/hardlinks, unexpected substitutions, unsupported
  filesystem behavior and read-only/sharing failures. Leave foreign targets alone.
- Delete only opened verified entries by handle disposition, bottom-up. Never
  use recursive Directory.Delete, File.Delete, remove reparse metadata, clear
  read-only attributes, release ancestor pins early, or adopt another runtime.
  All handle closures on partial failure must proceed independently.
- Record bounded removal intent before irreversible work. Journal failures stop
  deletion before the next irreversible action. After closing disposition
  handles, independently inspect absence through the pinned parent and preserve
  the external journal. Only confirmed absence may produce a removal receipt.
  Distinguish partial removal, retained residual data, unknown closure/readback,
  and completed removal. Keep exact paths and bounded diagnostics for failures.
- Blocking Win32 filesystem calls stay off the watchdog path. Checks between
  bounded actions do not prove a synchronous call can be forcibly interrupted;
  preserve the requirement for future monitor termination/finalization budgets.

## Source fixtures and reporting

Author meaningful fixture source first: nested successful removal with independent
absence and journal readback; missing authorization; unrecorded identity; partial
failure retention; source/reparse target and separately owned sentinel unchanged;
sharing/read-only refusal; identity mismatch; bounds/cancellation; journal failure
before mutation; and no successful receipt on failed readback. Do not execute
them. Keep fixture-only seams narrow and explicit. Identify any case not expressible
until native monitor integration rather than simulating its acceptance.

Use primary Windows documentation for new ABI/handle semantics. Apply small
related corrections in this responsible context. If the retained design cannot
meet an invariant, report the precise boundary without claiming completion or
opening another Expert chain. Commit atomically as the configured human author;
report files, commit, actual static checks, unexecuted fixtures and remaining
native/monitor gates. No product integration, remote writes or ticket acceptance.
