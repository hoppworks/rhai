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
briefs/process-retry-design-review.answer.md. Responsible context is amending
the design using a project-local custodian/runtime-ownership adapter; no fixture
execution or implementation before gate review. No global runner/home changes.

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

Collect amended process supervision design and review its gates. Corrected
macOS combined proof is accepted at 5f87d339; do not rerun unchanged source.
Keep Windows static candidate separate until independent guest cleanup is solved.
Collect and independently review the process supervision design before the single
newly authorized implementation attempt. Preserve all prior cause history.
TCP authority question remains pending; release/API proposals remain unaccepted.
Linear is legacy and excluded, with no writes performed there.

## Goal turn classification

Current turn made progress: corrected unrestricted paths and guarded regression
integrated at 5f87d339; full native macOS proof accepted and affected Linux checks
accepted (fs25/policy24). Windows static review defects corrected but native gates open.
Owner-authorized process retry design reviewed and rejected before execution;
responsible context is applying the reviewed custodian amendment.
