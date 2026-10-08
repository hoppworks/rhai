# Choose the minimum safe native Windows acceptance route

Type: task
Label: wayfinder:task
Status: resolved (route selection only; native custody remains unverified)
Assignee: current planning agent
Parent: [Complete the remaining Rhai host-library acceptance](../map.md)
Blocked by: none

## Question

Can the already authorized `rhai-win11-quality` guest and its existing console
path satisfy the approved Windows execution-ownership and interruption evidence
without the previous proposed C# runner/monitor stack? If not, what is the smallest
different route that preserves exactly the same ownership and readback guarantees?

## Context

Ticket 06 requires the Windows scoped run to prove owned-resource isolation and
interruption cleanup before native package builds. This is a safety outcome, not a
requirement to implement the old candidate architecture. The saved VM README records
an installed Windows 11 Pro baseline, an MSVC toolchain and one controlled filesystem
test. It does not prove current live guest readiness, Windows process/TCP behavior,
or the package-minimum feature matrix.

`.scratch/windows-scoped-runner/acceptance.md` records a static suspended-process/job
candidate, no native execution, and no independent monitor. The old gate describes
an independent lease/monitor and fixed runner design, while the October 8 request
explicitly rejects forced harness layers as product requirements. A separate saved
black-console screenshot and later clean-boot history are historical observations;
neither establishes the current guest state. Previous harness attempts and their
actual consumption remain history. The current user instruction suspends old
harness/fixed-budget directions; they do not become new routine approval gates.

## Original resolution requirements (historical)

- First read the exact authorized VM state and current console/guest readiness. Do
  not send guest input until the read-only observation confirms the intended domain.
- Compare only routes capable of proving: bounded owned work; exact job membership;
  an observer outside the tested job; termination/reaping after supervisor or
  controlling-connection loss; truthful status and evidence export; independent
  runtime/resource cleanup; and preservation of an unrelated sentinel.
- Reuse current installed images and toolchains only after exact live readback.
  Do not reset/reseed the VM, install tools, touch another domain/session, handle
  credentials, or perform a product build while resolving this planning ticket.
- Recommend the route with the fewest layers that still proves every accepted
  outcome. Keep the old monitor/candidate as evidence, not mandatory architecture.
  If the current guest cannot demonstrate a safe route, record the exact missing
  prerequisite and leave Windows acceptance open.

## Original acceptance wording (historical)

An evidence-backed route decision records the live guest baseline, existing entry
path, independent owner/observer boundaries, interruption/readback contract, exact
resource scope and why the selected method is the least layered valid option. This
ticket does not pass Windows package acceptance and does not authorize executing the
route. It remains unassigned until later implementation work is explicitly resumed.

## Comments

2026-10-08, follow-up planning request: the owner requested a fully autonomously
executable implementation plan. The planning scope still forbids guest execution.
The question is therefore narrowed to selecting an existing, source-inspected
route and defining its native admission test; live readiness is an execution
prerequisite, not a fact this planning ticket can establish. The original live
acceptance wording above is retained as history and is superseded only for this
route decision. No product or custody criterion is weakened. This ticket was
claimed by the current planning agent before recording its resolution.

## Answer

Select the existing `ScopedRunner.exe --lease-client` public entry and
`tools/windows-scoped-runner/MonitorAcceptanceDriver.cs`, with the monitor owning
the payload Job outside the driver/controller Job. The scoped compiler bootstrap
already exists in `fixtures/RunSourceFixtures.ps1` and establishes native ownership
through Reflection.Emit before compiling a child. A narrow build-only selection
can produce these binaries without making the full historical synthetic harness
a product gate. The native driver must start after that bootstrap owner exits,
from an independently verified uncontained guest console.

This is the smallest *currently source-supported* route to reuse all required
owner/observer, interruption and export observations; it is not a proof that no
simpler design could ever work. The direct legacy `--source/--exe` entry is
explicitly refused. Bare PowerShell/Cargo does not establish independent custody,
connection-loss closure or an export receipt. Starting a new generic supervisor
would duplicate mechanisms already present. The source audit establishes the
entry, refusal, ambient-job restriction and owner boundaries; it proves no native
behavior.

Before Cargo, implement and prove the specific missing composition: runtime-local
payload environment, a bounded project command payload, a product-duration driver
deadline, exact scope roots and bounded host export/readback. Run a finite native
fixture for success, payload failure, connection loss with client alive, client
death and monitor death, residual-child cleanup, nested/assignment refusal and
failed export/cleanup. Retain exact handles/identities and unrelated sentinel
readback. No success on missing journal, lost evidence or unproved cleanup.

The live domain UUID, console, guest token/toolchains/capacity and native gate
remain prerequisites in [the canonical implementation plan](../implementation-plan.md#windows-custody-prerequisite).
If unavailable, record the concrete prerequisite and continue independent packages;
do not reset the VM, grant admin rights or claim Windows accepted. Ordinary code/
fixture repairs later need no new routine human preference decision. This answer
closes route selection only. Its native assumptions remain explicitly untested.
