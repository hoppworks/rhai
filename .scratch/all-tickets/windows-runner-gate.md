# Native Windows scoped execution gate

Status: native compiler bootstrap and named public custody rows accepted; the
complete gate before Windows project Cargo/Rust acceptance remains open. Current
pair-membership, Driver180s stop/closure, actual atomic-association denial and
returned-handle setup-unwind rows are accepted at their recorded scopes.

## Current route and resources

Use the existing public `ScopedRunner.exe --lease-client` and separate
`MonitorAcceptanceDriver`, after the compiler owner exits. The monitor runs outside
the tested controller Job, owns the payload Job and has its independent lease and
absolute/finalization deadlines. Payload creation uses PROC_THREAD_ATTRIBUTE_JOB_LIST
with suspended CreateProcessW and membership verification before resume. The old
proposal's separate payload AssignProcessToJobObject step is a technique, not a
requirement to reintroduce. Failure must never run unowned work or silently fall back.

Sources/caches/output belong to exact current-user private scopes under
`%USERPROFILE%\.local\share\agent-builds\rhai\<session>\run`. Cargo source,
generated files, home/target/temp stay in the owned runtime/work copy. Retire work
only after exact closure; secure originals/independent readback before deleting any
outer evidence scope. Runtime `scoped-GUID` and retained `.scoped-evidence-GUID` are
distinct. Host export does not rewrite native HOST_EXPORTED=False.

Reuse compatible tools only after source/compiler/hash/physical-path checks and
within recorded ownership/purpose/expiry. Old10-10 guest builds and the now-retired current compiler cache are historical
references. The membership/deadline package retired all8 exact own guest scopes and
all6 own media after host-bound export. A later resource-limit package now retains
one new compatible GREEN build under its exact finite record; use
`windows-job-resources-20261025/retained-green-build.json`, not historical paths. Never reset the VM, touch backups/baselines/foreign work, or treat SSH
loss as guest supervision. No new routine approval gate or fixed heavy-run slot.

## Required outcomes and current proof

| Outcome | Accepted scope | Still open |
|---|---|---|
| Payload and grandchild actual Job membership before useful work | Current native complete four-PID lists independently include both exact payload/ordinary-child PID/start identities before work; public normal Driver0/root0 and complete Job closure | No gap in this named row at its source/guest scope; no arbitrary nested-execution or product acceptance inferred |
| Success, failure, deadline stop members and retire runtime | Normal success/private env; generic failure narrow actual cause; parent-exit residual child; real large ordinary-abort retirement2107entries/613419011bytes; current empty-work lease stops; current normal membership/root-exit closure and deliberate Driver180s timeout with post-teardown actor/runtime closure | Monitor30min absolute deadline, explicit watchdog124 termination branch and bounded real project-command composition/product duration |
| Supervisor death, independent observer, unrelated sentinel | Original monitor-death run and later readback: six identities stopped, sentinel survival/natural completion, exact target runtime observer-retired; original sharing/release failures preserved | No clean monitor/backend receipt inferred; current changed-composition and failed cleanup/export applicability remain to establish |
| Failed association/nested context; no fallback | Native nested-refusal; current real CreateProcessW JOB_LIST query-handle denial/error5/no returned handles; separate real successful suspended-create abort proves returned-handle unwind and exact already-stopped termination-race correction | No false-return/nonzero-partial-handle permutation or arbitrary API interruption/nested-execution guarantee claimed; current named denial and returned-real-handle cases are accepted |
| Controlling connection/lease failure | Current disconnect-alive/client-death/replay: Drivers0, payload125, client78/1/78,4/4/5challenges, each8CRC records, PID/start stopped, literal runtime absent | Nonempty product work/further failure paths are not directly claimed by the three empty-work cases |
| Assertion sensitivity and truthful export/cleanup | Wrong marker and snapshot-as-absent controls; restored positives; hash/length/CRC host readback; host-bound exact-scope retirement | Additional backend failed export/cleanup outcomes do not become done from healthy export; Driver deadline logs retain failed orderly client/controller disposition and kill-on-close through teardown |

Evidence: [current membership/Driver deadline](windows-membership-deadline-20261025/proof.md),
[current lease cases](windows-lease-interruptions-20261025/proof.md),
[real work retirement/environment](windows-workhorse-retirement-20261025/proof.md),
and original bindings under
`../rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/`.
The preserved canonical plan is `../../docs/sys-package-plan.md`; this gate table
updates actual requirements/evidence, not the overall scope. No Windows Rust/Cargo
product acceptance, release or full A–F closure is claimed.

Driver180s acceptance is a real deadline/stop outcome: exact timeout diagnostic at180.2336s,
independent observer kill not reached, both actor identities seen live then stopped,
EXACT Job closure and runtime absent. Orderly client/controller release failed before
Driver teardown; retained kill-on-close completed that path. Keep those original
diagnostics. It does not establish the separate monitor30min or watchdog124 branch.

Actual payload resource setup is now21e59d11: kill-close/no breakaway,16active,
1GiB committed memory per process and2GiB per Job before atomic association.
Native old-source RED then current root+child resource GREEN and same-build
private-environment GREEN pass: [resource proof](windows-job-resources-20261025/proof.md).
These observe real kernel configuration/inheritance and small-workload closure;
quota-exhaustion and real project-command behavior remain open. Older deadline/
lease/membership rows keep their original-revision scope, not new-limit labels.

Native creation-failure proof now closes the actual denial and returned-real-handle
setup-unwind slice: [original RED/diagnosis/fixed GREEN](windows-creation-failure-20261025/proof.md).
The fix559fda32 accepts a failed individual termination only after the SAME retained
root handle is kernel-signaled; exact bounded root wait and Job-empty remain.
Both earlier POST failures are preserved. The denied call returned no handles;
a separate successful-create fault exercised real returned process/thread handles.
No hypothetical partial-return or full Windows/Rhai acceptance is inferred.
The creation packet subsequently retired all7own guest scopes,4own media and
76-entry host staging after independent host-bound export; original CDs are restored.
Only the previously useful baseline remains under its original finite retention,
with Driver/Payload compatibility and an older normal Runner explicitly distinguished.
