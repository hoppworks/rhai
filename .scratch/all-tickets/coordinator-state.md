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

Windows candidate is now 0999a552 on task/windows-scoped-runner, including
74138c71 monitor/client launch and bounded lease protocol source. All five source,
fixture and documentation files were reviewed; related findings corrected in
the responsible context. See windows-monitor-lease-review.md. Only whitespace
checking ran; compiler, fixtures, native/guest behavior remain unverified.
Unsafe workload entry is disabled and candidate remains separate. Next independent
source requirement is handle-based runtime/staging and durable journal, delegated
to the responsible context under briefs/windows-runtime-backend.md from 0999a552.
Immutable specification and actual payload integration with two host responses
follow that source substep. Review also identified that IssueChallenge currently
excludes Running, so future running workloads cannot renew the lease; correction
was requested in the responsible context with meaningful fixture source.

Step 1 corrected unrestricted resolution is integrated at 5f87d339 and accepted
on native macOS: env7/fs24/policy26 pass, exact runtime absent. Red/green
unlinked-cwd contract and immediate child/marker ownership guards reviewed.
Affected Linux proof fecbfdd1 accepted on 98f66aca: fs25/policy24 pass, including
deleted-cwd and NotUtf8. Command/log/applicability reviewed and exact remote
runtime absence independently confirmed. Previous env/control proof remains valid.
Windows static candidate 2e65cb45 corrects reviewed ABI and bounded-wait defects,
but compile/native/independent monitor gates remain unverified, not integrated.
Step 2 owner TCP question remains pending; release/API proposal is unaccepted.
POSIX process prototype 35a8cf52 proof is not accepted. Correction disposition
501fa184c97f records that safe supervision was not established; no fixture was
executed. The owner explicitly authorized one further bounded attempt after consultation.
Design 2a3996cd was independently rejected: whole-runner interruption, setup,
wait and worker bounds incomplete. Review answer is at
briefs/process-retry-design-review.answer.md. Amendment 937da3c1 supplies direct
custodian ownership, polling and separate runtime, but explicitly leaves actual
shared-runner death cleanup unproven. Owner was asked once about a project-local
runner copy versus deferring the process branch. Stop dependent work until reply.
No fixture or implementation ran; no global runner/home changes.

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

Windows custody Expert answer 02-windows-runtime-custody.answer.md is retained.
It recommends a separate sole-owner monitor, creation-time job-list assignment,
host round-trip lease, bounded state machine and handle-based runtime custody.
One bounded local source implementation is delegated under
briefs/windows-monitor-implementation.md. No guest execution or package build
is authorized until source review, private bootstrap, launch survival and native
cleanup gates pass. This is the single Windows custody escalation; no completed
correction has failed for this cause. Current guest access remains unverified.

Core MSRV evidence integrated as 87099fcc and c5fecde1. The one Cargo 1.66
invocation used baseline a6241621 instead of requested b031ce8d. It failed while
parsing resolved thin-vec 0.2.20 (edition 2024), before library compilation.
Unchanged thin-vec declaration supports only the narrow dependency warning.
Neither baseline nor integrated compilation is proven. Exact scoped runtime
absence was independently confirmed. See ../core-msrv-check/proof.md and log.
No retry, dependency pin or release-policy change was made.

The latest reply repeats authorization for one further bounded process attempt.
It does not answer the separate project-local runner-copy requirement. Preserve
that authorization and stop only the dependent process execution until that
existing question is answered; no additional process attempt has been consumed.

Process amendment collected and its remaining boundary recorded; await owner
answer before dependent implementation. Corrected
macOS combined proof is accepted at 5f87d339; do not rerun unchanged source.
Keep Windows static candidate separate until independent guest cleanup is solved.
Collect and independently review the process supervision design before the single
newly authorized implementation attempt. Preserve all prior cause history.
TCP authority question remains pending; release/API proposals remain unaccepted.
Linear is legacy and excluded, with no writes performed there.

## Open owner decisions

| Question | Affected requirement | Resume condition |
| --- | --- | --- |
| Connect only or connect plus separately authorized listeners? | TCP tickets 04/05 implementation | Owner answers the existing scope question, then concrete lifecycle contract is reviewed. |
| Accept proposed platform/MSRV, additive process report, negative-read rejection and unchecked resource limits? | Ticket 06 and dependent public process/file-handle APIs | Owner answers the existing release/API question. |
| Authorize project-local scoped-runner copy with explicit supervision/runtime custody, or defer process prototype? | Actual whole-runner interruption proof under the prescribed runner workflow | Owner answers the existing runner-copy question; then implementation/source gates may proceed. |

Dependent implementation is stopped. Continue only independent authorized
requirements with new evidence; do not repeat decision/status/verification rounds.

## Goal turn classification

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
