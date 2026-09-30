# Windows exclusive runtime allocation source substep

## Task

Continue related custody correction in the owned candidate checkout
/Users/hoppworks/projects/rhai-windows-scoped-runner, task/windows-scoped-runner,
from 967500f3. Read its AGENTS.md and the full existing Expert answer:
/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md.
Also read windows-runtime-backend-review.md in the same effort directory.

Implement exclusive runtime allocation and ordered journal custody in the
backend. This is intermediate source work, not native acceptance. Keep public
workload entry disabled; do not wire unsafe legacy staging or deletion.

## Required invariants

- Pin the fixed existing authorized parent and separate existing evidence root
  outside payload runtime. Never create or alter foreign roots/ACLs. Generate
  the exact runtime name internally; no caller-selected cleanup path.
- Before directory creation, flush bounded allocation intent with exact generated
  runtime/evidence identities. On failed intent write/flush, do not allocate.
- Exclusively create the directory with an explicit protected user/SYSTEM DACL;
  reject collisions without adopting existing data. Verify ACL and plain directory
  attributes through its opened handle, retain lifetime pin and capture identity.
- Flush identity after successful creation. Failures between intent and identity
  remain uncertain and retain the exact path and journal; never synthesize safe
  deletion or success. Once creation succeeds, failure closing/verification/
  journal flushing does not lose ownership diagnostics.
- Define a sole-owner state object with explicit intent/created/verified/recorded/
  failed/retained states or equivalent invariants. Journal and pinned evidence
  lifetime cannot accidentally end before owned runtime custody transfers.
- Native handle/DACL lifetimes and partial setup cleanup must be exception safe.
  No recursive/path-only runtime deletion. Cleanup and staging remain separate
  later requirements; losing all supervisors must leave recoverable uncertainty.
- No synchronous filesystem call on the watchdog path. Keep this backend
  unconnected until its worker/deadline integration is safe; do not claim Win32
  filesystem operations have bounded cancellation by themselves.

## Fixtures and checks

Write meaningful source fixture cases first for intent before creation,
exclusive collision refusal/foreign marker preservation, recorded identity,
protected ACL and partial failure uncertainty. No text tests as behavioral proof.
No compiler or native execution is currently authorized; clearly report fixtures
unexecuted and no RED/GREEN. Test-only seams must be narrow and disabled in normal
builds, and must not allow production paths/ownership bypass. Safe fixture cleanup
must track exact ownership; retain rather than delete uncertain data.

Commit atomically as configured human author. Report ref, files, actual checks,
remaining full contract, and source limitations. Coordinator reviews independently.
Do not expand into staging, payload launch or broad recovery logic this substep.

## Boundaries and cause history

No guest input/command, compiler/bootstrap, install, credentials/admin changes,
remote Git write, global/home configuration changes or process fixtures. No new
Expert chain. Existing escalation 02's full-custody correction remains incomplete;
no completed failed full-custody correction or infrastructure recovery has run.
Compiler unavailability alone does not block this authorized source substep.
Production recovery parsing must eventually use bounded handle reads; the current
fixture parser is for closed owned journal data only. Running lease renewal remains
a required related correction before actual payload integration.
