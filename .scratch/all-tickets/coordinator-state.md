# Implement all sys and TCP tickets

## Goal

Complete the private sys/TCP backlog inherited from task/stdlib-net-assessment.

## Done when

All accepted sys/process/file-handle and TCP contracts are implemented, documented,
committed and proven under the strict project profile. Open owner decisions must
be resolved before their dependent implementation. No remote publication.

## Steps

1. Repair the four reviewed filesystem/fixture defects with public API regressions.
2. Resolve TCP authority, compatibility/release and byte/lifecycle decisions.
3. Implement accepted process lifecycle contracts, including managed scopes.
4. Complete streaming file handles and documentation.
5. Implement the accepted TCP package and real-peer acceptance scenarios.
6. Run the accepted native OS/feature/MSRV gates and independently assess evidence.
7. Integrate only verified changes locally; retain proof and record retrospective.

## Done steps

- Located the canonical local tickets and accepted project configuration at
  task/stdlib-net-assessment (3eb2f73b). Created isolated coordinator worktree
  /Users/hoppworks/projects/rhai-all-tickets on task/all-tickets.

- Step 1 implementation repair integrated in 62526323; strict native macOS
  combined proof: combined-sys-proof.md and combined-sys.log. Environment 7,
  filesystem 23, policy 26 all pass; invalid-name fixture explicitly unsupported.
  Public API/host readback and preserved failing controls independently reviewed.

- Native Linux sys proof accepted and locally retained from 854d05f2. Source
  f7aed036 has unchanged relevant code versus accepted macOS source. Linux env7,
  fs24, policy24 pass; invalid-UTF8 public API and wrong-variant control proven.
  Exact remote runtime absence independently confirmed; see ../linux-sys-proof/proof.md.
- File-handle compatibility facts retained from 17991878 in
  file-handle-compatibility.md. Genuine negative-length/unchecked divergences and
  release choices remain unresolved; source facts are not acceptance of bugs.

## Current step

Windows immutable launch specification 91e474d7 and related correction 73020670
are independently source-reviewed across all four files each, zero skips, in
the separate owned Windows worktree. OCR-excluded README/fixture were manually
read. Input-bound and quoting source findings are closed; see
windows-immutable-specification-review.md. No compiler, fixture execution or
native proof has occurred. Public workload entry and exact-job issuance remain
disabled. The source-reviewed predecessor is Running renewal 43d2f067, following
allocation/staging/disposition source slices referenced in their review files.

Accepted filesystem/environment production and macOS/Linux proof remain unchanged;
reuse the applicable evidence. The one further POSIX attempt is authorized and
unconsumed; the separate pending runner-copy question stops its dependent work.
TCP/release decisions also remain pending. No remote writes.

## Decisions

- Owner clarified Linear is legacy; use only the local Markdown tracker for this effort.
- Strict verification and automatic local integration are already recorded.
- Private work overrides automatic push. Never publish or modify remote state.
- Preserve all foreign worktrees, the existing planning state and Windows baseline.
- The implementation request supersedes the earlier planning-only mode for accepted
  contracts, but does not answer unresolved API/scope decisions.
- Public test seams are already owner-approved in AGENTS.md.
- Pending owner TCP choice: connect plus separately authorized listeners or connect only.
- Owner release/API question asks approval of the concrete three-OS/Rust matrix,
  additive ProcessReport failure variant, rejected negative file reads, and
  retained resource limits under unchecked. Await reply; no inferred approval.
- Missing-workflow question was asked before discovering canonical configuration;
  reuse existing selections unless owner explicitly changes them.

## Evidence and resources

- Accepted prior evidence remains referenced in ../stdlib-wayfinder/coordinator-state.md.
- Review repro and logs: /Users/hoppworks/projects/rhai-review-sys-windows/.scratch/review-sys-windows/.
- Builds must use agent-skills/tools/run_scoped.py and AGENTS.md output isolation.
- Windows requires proven guest process-tree cleanup before another native build.

Windows static candidate 97fe3f93 is not accepted or integrated. Native gates and
independent guest lease/cleanup remain unverified. Review found DWORD accounting
fields incorrectly declared UIntPtr and unbounded termination waits; corrected
in 2e65cb45 without native execution. Remaining monitor/native gates are open. Brief at
briefs/windows-scoped-runner.md. Inspect current guest state, preserve baselines,
prove adapter cleanup before any new Rust/package build. No prior adapter failures.

## Cause attempts and escalations

Outcome classification under the owner's replacement instructions (2026-09-30):
501fa184 stopped at a design/supervision boundary without implementation or
execution; it is not a completed failed implementation correction. The original
contradictory proof remains rejected. Design review 2a3996cd is also not a failed
implementation correction. No calibration package or measurement slots have
been approved. Preserve the earlier consultation and explicit further-attempt
authorization, with zero completed implementation corrections in this retry.

Prototype-proof cause: initial report conflicts with the actual fixture's I/O ordering
and exceptional-path cleanup. One Expert escalation opened at
escalations/01-process-prototype-proof.md; answer saved at
escalations/01-process-prototype-proof.answer.md. All five concerns validated.
The one allowed correction attempt closed at 501fa184c97f without implementation
or execution; safe independent scope lifetime remains unestablished. Owner was
asked whether to allow a further bounded attempt with a reviewed supervision design
or defer this branch while other tickets continue. Consultation answered on 2026-09-30: owner selected one further bounded attempt
with a pre-reviewed supervision design. Prior failures remain recorded; this is
an explicit budget override, not a reset. Draft requested at the owned prototype
worktree evidence/retry-design.md before implementation or execution.
Disposition: /Users/hoppworks/projects/rhai-process-prototype/.scratch/process-prototype/evidence/correction-attempt.md.
No owned live resources reported; historical source/logs remain unaccepted.
One further attempt is owner-authorized. Design-only 2a3996cd was rejected by
the independent review; minimal custodian direction is proposed, not approved
implementation. Amendment is active; no new fixture or implementation ran.
Original cause history and the single new implementation budget remain intact.
Do not accept concurrent-I/O/cleanup claims until independent evidence review.
Inherited VM history remains authoritative.

## Next action

Launch-spec correction review is complete. The same responsible context is
continuing the bounded transfer model under briefs/windows-specification-transfer.md.
Review its exact eventual commit including excluded fixture/README; preserve
existing frame/queue/lease limits and disabled workload launch. Native
bootstrap and guest runtime custody remain prerequisites for execution. Do not
count static corrections as executed TDD or native acceptance.

Preserve the sole Windows Expert chain and the authorized unconsumed POSIX retry.
Await existing owner answers for dependent branches; do not repeat questions.
Linear is legacy and excluded.

## Open owner decisions

| Question | Affected requirement | Resume condition |
| --- | --- | --- |
| Connect only or connect plus separately authorized listeners? | TCP tickets 04/05 implementation | Owner answers the existing scope question, then concrete lifecycle contract is reviewed. |
| Accept proposed platform/MSRV, additive process report, negative-read rejection and unchecked resource limits? | Ticket 06 and dependent public process/file-handle APIs | Owner answers the existing release/API question. |
| Authorize project-local scoped-runner copy with explicit supervision/runtime custody, or defer process prototype? | Actual whole-runner interruption proof under the prescribed runner workflow | Owner answers the existing runner-copy question; then implementation/source gates may proceed. |

Dependent implementation is stopped. Continue only independent authorized
requirements with new evidence; do not repeat decision/status/verification rounds.

## Goal turn classification

2026-09-30 launch-spec commit continuation: progress. Source changed to 91e474d7;
independent four-file review identified pre-allocation/pre-scan bounds and exact
quoting fixture gaps. Related correction 73020670 reviewed and findings closed in source. Bounded
transfer-model source work dispatched in the same responsible context.
No build/native operation or temporary resource. Existing custody correction is
incomplete, with no completed failed full-custody correction/recovery. Independent
source work remains; goal active and incomplete, not blocked.

2026-09-30 immutable specification continuation: progress. Previous turn
implemented and reviewed Running renewal 43d2f067. Current authoritative dirty
fixture source and pure syntax-helper extraction advance the specification;
intermediate findings change the required correction before final review.
The responsible agent is independently confirmed live, not restarted on timeout.
No compiler/native execution, resource creation or completed full-custody failure.
Goal remains active and incomplete; this is not a blocked impasse.

2026-09-30 Running renewal continuation: progress. Authoritative 43d2f067 fixes
the missing Running challenge path and replaces misleading early-expiry fixture
coverage with explicit accepted renewals and aligned boundaries. All three files
were source-reviewed; no compiler/native execution or resources. The existing
custody correction remains incomplete. Next specification work is confirmed live;
open owner decisions still stop only their dependent branches. No blocked impasse.

2026-09-30 latest disposition review continuation: progress. Previous turn
reviewed bb7060a2 and recorded findings in 702260ae. Current authoritative source
6c37071b corrects identity/pseudoentry/partial-readback gaps; all affected source
was reviewed, no skips. The next concrete requirement is Running lease renewal,
not native acceptance. No completed full-custody failure or runtime resource.
Goal remains active and incomplete; independent authorized source work remains.

2026-09-30 disposition continuation: previous turn was progress (source changes
b4c055ee/03a56347 and independent review). Current live responsible agent was
confirmed; authored disposition fixture source and intermediate findings change
the implementation/review action. No compiler/native run or created runtime.
The Windows full-custody correction remains incomplete with no completed failed
correction/recovery. Goal stays active and incomplete, not blocked.

2026-09-30 staging continuation: progress. Candidate b4c055ee implements the
bounded source slice. Three-file source review found identity-chain and fixture assertion gaps;
03a56347 corrects them and was independently reviewed across three files. This
is not another full-custody attempt. Disposition brief is prepared for the same
responsible context. No compiler/fixture/native run, runtime
resource or ticket acceptance occurred. Goal remains active and incomplete.

2026-09-30 current continuation: progress. Exclusive runtime allocation source
3d7a659b and reviewed corrections 9a68a437/08fb7cd5 advance the existing Windows
custody implementation. Three files reviewed, no skips, whitespace checks clean.
No native/fixture/compiler execution, created runtime or ticket acceptance.
No completed failed full-custody correction or infrastructure recovery occurred.
Owner authorization for the further bounded process attempt remains unconsumed;
the separate runner-copy decision still stops dependent POSIX work. Independent
source work remains, so the goal is active and incomplete, not blocked.

2026-09-30 latest continuation: progress. Backend foundation source changed in
4bf0e3a5/967500f3, all three files independently reviewed and related issues
corrected in the responsible context. Current source requirement advanced from
root/journal primitives to exclusive runtime allocation and ordered custody
journal. No ticket acceptance, compiler/native execution or temporary resource
occurred. Existing full-custody correction remains incomplete, with no completed
failed full-custody attempt or infrastructure recovery. Open owner decisions
still stop their dependent branches. Goal remains active and incomplete; safe
independent source work remains, so this is not an impasse or a blocked turn.

2026-09-30 continuation: progress, not a verified wait or no-progress turn.
Authoritative Windows source changed in 74138c71/0999a552; source review changed
the next action from monitor/lease construction to safe backend/journal and payload
integration. No full custody or ticket acceptance is claimed. No compiler,
fixture, native run or owned temporary process/resource occurred. This remains an
intermediate part of the existing correction, with no completed failed full
custody correction or infrastructure recovery; reviewed source defects and their
corrections are retained in windows-monitor-lease-review.md. Open owner decisions
continue to stop their dependent branches. Goal remains active and incomplete.

Latest continuation made source progress: Windows creation-time job assignment
candidate b596feba is committed and source-reviewed in
windows-job-creation-review.md, with related cleanup/fixture review corrections.
The full custody task was narrowed to this intermediate source substep after
the responsible session could not produce the coupled rewrite in one pass.
No actual native/compiler/fixture run occurred, no completed failed correction
or infrastructure recovery is counted, and no runtime resources were created.
Candidate remains separate and must not launch workloads. Next independent
source work is the monitor/client ownership and bounded host-lease state machine;
native launch/bootstrap/guest access and full filesystem custody remain gates.
Core MSRV baseline diagnostic was retained with corrected scope. Pending owner
decisions continue to stop only dependent work. Goal remains active, not complete.

Current turn made progress: corrected unrestricted paths and guarded regression
integrated at 5f87d339; full native macOS proof accepted and affected Linux checks
accepted (fs25/policy24). Windows static review defects corrected but native gates open.
Owner-authorized process retry design reviewed and rejected before execution;
custodian amendment 937da3c1 retains an explicit runner boundary. Open owner
decisions now stop dependent work. No owned build/fixture processes remain.
