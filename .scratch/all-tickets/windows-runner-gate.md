# Native Windows scoped execution gate

Status: native compiler bootstrap and named public custody rows accepted; the
complete gate before Windows project Cargo/Rust acceptance remains open.

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
within recorded ownership/purpose/expiry. Old10-10 guest builds are historical
references. Never reset the VM, touch backups/baselines/foreign work, or treat SSH
loss as guest supervision. No new routine approval gate or fixed heavy-run slot.

## Required outcomes and current proof

| Outcome | Accepted scope | Still open |
|---|---|---|
| Payload and grandchild actual Job membership before useful work | Existing root ownership and historical descendant stop/identity proofs retained | A current direct both-member pre-work observation; do not infer it from counts alone |
| Success, failure, deadline stop members and retire runtime | Normal success/private env; generic failure narrow actual cause; parent-exit residual child; real large ordinary-abort retirement2107entries/613419011bytes; current empty-work lease stops | Deliberate deadline with descendant/runtime closure; bounded real project-command composition/product duration |
| Supervisor death, independent observer, unrelated sentinel | Original monitor-death run and later readback: six identities stopped, sentinel survival/natural completion, exact target runtime observer-retired; original sharing/release failures preserved | No clean monitor/backend receipt inferred; current changed-composition and failed cleanup/export applicability remain to establish |
| Failed association/nested context; no fallback | Native nested-refusal proves public ambient/nested admission refusal before payload launch | Actual failure to establish atomic JOB_LIST association; conservative termination/wait if any child handles were returned |
| Controlling connection/lease failure | Current disconnect-alive/client-death/replay: Drivers0, payload125, client78/1/78,4/4/5challenges, each8CRC records, PID/start stopped, literal runtime absent | Nonempty product work/further failure paths are not directly claimed by the three empty-work cases |
| Assertion sensitivity and truthful export/cleanup | Wrong marker and snapshot-as-absent controls; restored positives; hash/length/CRC host readback; host-bound exact-scope retirement | Additional failed export/cleanup outcomes do not become done from a healthy export |

Evidence: [current lease cases](windows-lease-interruptions-20261025/proof.md),
[real work retirement/environment](windows-workhorse-retirement-20261025/proof.md),
and original bindings under
`../rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/`.
The preserved canonical plan is `../../docs/sys-package-plan.md`; this gate table
updates actual requirements/evidence, not the overall scope. No Windows Rust/Cargo
product acceptance, release or full A–F closure is claimed.
