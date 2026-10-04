# Process overflow/deadline overlap acceptance

Role: Standard. Source-only preparation; do not build, SSH, signal or clean remote resources.

Read current ~/.agents/AGENTS.md, own AGENTS.md, applicable Standard role template,
tdd (including tests/mocking references), campaign and relevant e2e-proof. Confirm
loaded revision6830c49 before action. Preserve all existing proof and stopped causes.

## Requirement and agreed seam
Ticket03 Input/output contract: when readable overflow and expired run deadline are
observed in the same supervision step, OutputLimit wins. Public seam already owner
approved in project AGENTS.md: real Rhai Engine, registered SysPackage, actual OS
child and independent child-written acknowledgment/reaping. Existing source drains
readable bytes before timeout cleanup, but this exact overlap lacks accepted proof.
No new public API or production semantic change is requested.

## Workspace and sources
Own /Users/hoppworks/projects/rhai/.worktrees/process-overlap-acceptance,
branch task/process-overlap-acceptance, baseline8c0ee4634355aee4e841b455461a7dd5aac2aa18.
Read only necessary src/packages/sys/process/unix.rs (ExecutionFaults, run driver
around2465 and output branches2690–2855, existing real-OS public tests), ticket03,
project AGENTS.md. CONTEXT.md/ADRs if present. No other writer history or dirty work.
Performance accepted preparation/evidence is independent and adds no production delta.

## Package
One narrow public real-OS overlap regression first, private per-execution cfg(test)
scheduling adapter only if required to establish the same step deterministically.
Use readiness/acknowledgment and bounded watchdog, never fixed sleeps as readiness
or probabilistic elapsed-only proof. A one-shot host barrier before the driver reads
expired state may let actual child output and actual deadline become observable;
this is an option, not a prescribed public design. Keep child cleanup/reaping and
retained-owner retirement independently observable on all failure paths. Direct
and Managed may share the same workload/parameterized contract when feasible.
Do not claim first-committed-cause or other platform acceptance from this overlap.
Existing stdin/API21/Darwin09/12/Windows02/13 exhausted paths remain stopped.

Prepare a narrow native verification recipe reusing accepted pipe scoped helper,
source archive, private Rust1.77.2, locked dependencies and exact custody/export
mechanics; no general framework. Test/expected wrong cause or specific production
ordering mutant must fail for intended assertion, restore and pass. No native
acceptance claim in this source-only phase. Record which failing control remains
unexecuted. Build source must eventually be frozen root integration plus selected
intended change, never unaccepted writer stdin history.

## Bounds and return
30minute source active-work planning checkpoint, not hard cap; actual active use
unknown unless measured. Native planning one invocation later; hard outer600,
runner585, helper540 incl30export;2jobs,16descendants,1572864KiB storagepreempt and
2097152KiB RSS/storage. Root owns independent review/admission/native execution.
Two completed failed corrections or infra recoveries per cause trigger fresh Expert
under preserved campaign history; initial source review rejection isn't a retry.
No push/merge. Commit only intended files exact hoppworks <daniel@hoppworks.de>
author and committer using explicit command-local identity; no branding/coauthors.
Return immutable commit/files, meaningful design/controls, unresolved nativeproof,
and source diagnostic evidence. Do not change root tree or agent homes.
