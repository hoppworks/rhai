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
  file-handle-compatibility.md. Negative-length rejection and resource bounds under unchecked are now approved;
  implementation and strict proof remain open. Source facts do not accept bugs.

## Current step

Actual monitor intake `dd8c07dc` and related stopped-state fixture `24c3a19f`
are independently source-reviewed (six files plus one correction, zero skips).
Findings are closed in source; see windows-monitor-specification-intake-review.md.
Original framing, real bounded dispatch and maintenance/transition separation
are implemented. Nothing has compiled or run. Candidate stays isolated.

Monitor-owned allocation/staging source slice is completed in candidate
8f75da53, independently reviewed across six files with zero skips; see
windows-monitor-staging-ownership-review.md. It connects actual intake to a
single worker and atomic completion/stop handoff. No compilation or execution;
no integration or full custody acceptance. Fixed source allowance was recorded
before work in
briefs/windows-monitor-staging-ownership.md: 11:17–11:47 UTC on 2026-09-30,
30 active minutes including review, zero execution/build/native launches,
two consecutive source revisions without requirement progress stop the slice.
This continues the sole Expert/cause correction; previous effort/history is not
reset. Payload/proof authority and native execution prerequisites stay closed.

Immutable specification `91e474d7`/`73020670` and Running renewal `43d2f067`
source reviews remain applicable. Accepted filesystem/environment production and
macOS/Linux proof remain unchanged. The further POSIX attempt is authorized and
unconsumed; the runner-copy, TCP and release recommendations were accepted by the owner
on 2026-09-30; dependent work may resume. No remote writes.

## Decisions

- Owner clarified Linear is legacy; use only the local Markdown tracker for this effort.
- Strict verification and automatic local integration are already recorded.
- Private work overrides automatic push. Never publish or modify remote state.
- Preserve all foreign worktrees, the existing planning state and Windows baseline.
- The implementation request supersedes the earlier planning-only mode for accepted
  contracts, but does not answer unresolved API/scope decisions.
- Public test seams are already owner-approved in AGENTS.md.
- Owner accepted the recommended open choices on 2026-09-30, prioritizing maximum
  quality regardless of effort: connect plus separately authorized listeners;
  the complete tcp-proposal.md contract; the release-proposal.md matrix and additive
  process error/report; reject negative file reads and retain resource limits under
  unchecked; permit a project-local runner copy with explicit custody.
- Acceptance of decisions is not implementation or native proof. Existing Windows
  bootstrap constraints, privacy and all explicit package limits still apply.
- Replacement global instructions remove default-only launch cutoffs for ordinary
  repairs within remaining original time/resources. Preserve every launch and cause
  history; stop after two consecutive launches without diagnosis or a closed check.
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

Resume the unconsumed POSIX retry in its responsible context: amend the actual
project-local runner custody design and source, submit it for independent review
before any interruption fixture launches. In parallel, implement the first TCP
vertical slice against the accepted contract in a fresh owned worktree.
Existing Windows source slice remains closed; no native/bootstrap launch is allowed.

## Owner decisions resolved on 2026-09-30

Tickets 04/05/06 now have approved specifications linked to tcp-proposal.md and
release-proposal.md. The owner also authorized the proposed project-local scoped
runner copy. Preserve the historical blocked observations below; the owner's answer
is the changed resume condition. The goal is active and remains incomplete.

## Active bounded work

- POSIX: the same one further owner-authorized attempt, sole Expert 01 history
  retained. Source/design amendment and correction: 30 active minutes from actual
  resumption, no build/fixture launch until coordinator source gate. Use the original
  remaining limits if stricter; do not reset elapsed time. No default launch-count
  cutoff, no new escalation chain, stop on hard caps or contradictory evidence.
  Source-only preparation creates no process workload or runtime. Record exact
  custody roles, resource/time caps and interruption controls before execution.
- TCP first slice: numeric endpoint parsing, deny-by-default exact connect grants,
  catchable structured errors and independent-peer connection/close proof. Fresh
  feature work, not another process repair. Up to 60 active minutes including review;
  runtime <=15 minutes per scoped invocation, <=2 GiB private build storage, <=8
  owned socket resources in fixtures, bounded joins and no shared services. Record
  every launch and stop after two consecutive launches without diagnosis or closed
  checks, contradictory evidence or uncovered decisions. Remaining TCP requirements
  stay open; no package-wide/native-three-OS acceptance claim from this slice.

## Goal turn classification

2026-09-30 post-staging frontier audit: no progress, blocked observations 1–3
on consecutive goal turns. Third minimal check found unchanged canonical
ticket states, candidate 8f75da53, the same prototype boundary and no executing
delegated task. The blocked threshold is met; goal controller is being marked
blocked. Resume only after an outstanding decision or external prerequisite
changes. All prior work and the full objective remain preserved.
Canonical tickets 04 and 06 remain unresolved; 05 explicitly depends on both.
Production process/file-handle contract decisions remain pending. Prototype
937da3c1 still explicitly stops implementation at the unanswered runner-copy
boundary. Agent inventory confirms the Windows and MSRV tasks terminal; the
prototype agent is pending_init, not an executing proof. Windows source slice
is complete in 8f75da53 and may not be silently extended or executed without
the existing native/bootstrap prerequisites and bounded correction authority.
No independent authorized next action identified; the same pending owner
decisions/external native prerequisites are the blocker. This record is not implementation
progress or a verified wait. Do not repeat broad audits or pending questions.

2026-09-30 staging completion continuation: progress. Previous goal turn was
progress through source limits and concrete fixture findings. Current candidate
8f75da53 implements actual allocation/staging integration and completion/stop
ownership. Six-file final source review closes this subrequirement; zero skips.
No executed acceptance, full custody or backlog completion. Responsible agent
is terminal; no verified-wait claim. No new independent scope is started here.
Goal remains active and incomplete; no blocked audit threshold established.

2026-09-30 staging ownership continuation: progress. Pre-work finite source
limits committed in d9fd5e5f. Existing responsible agent resumed; concrete
ownership design assessed and first real fixture source independently inspected,
changing the correction action with two lifecycle findings and one timing-test
finding. No implementation acceptance or executed test claim. Full backlog
remains incomplete; the bounded live source task is continuing, so goal active.

2026-09-30 actual intake commit continuation: progress. Authoritative source
changed to dd8c07dc/24c3a19f; independent final review closes original-frame,
real-dispatch and maintenance-separation source subrequirements. Previous turn
was progress from concrete draft findings. No compiler/native/fixture operation
or runtime resource. Full custody and backlog remain incomplete; safe bounded
source integration remains, so goal active, not blocked. Owner's replacement
repair rules govern next work; no execution budget/Expert history is reset.


2026-09-30 intake fixture continuation: progress. Previous turn was a verified
wait on the same live Windows agent. Current authoritative untracked fixture
source changes state; complete source inspection changes the correction action
with concrete clock/coverage findings. Agent confirmed running; not restarted.
No compiler/native operation or owned resource. Full backlog remains incomplete;
independent implementation continues, so goal active/incomplete, not blocked.


2026-09-30 monitor intake continuation: verified wait. Previous turn was
progress: committed transfer review and actual intake scope at 8fbe043d. The
current agent inventory independently confirms the same responsible Windows
agent running before and after two bounded 45-second waits. No new source is
present; candidate remains clean at 53140bcf. Observation timeouts are not
terminal and the agent was not restarted. No native operation or owned runtime
resource occurred. Continue waiting for this exact task and review its eventual
source; full backlog and native gates remain incomplete. Not a blocked impasse.


2026-09-30 transfer commit review: progress. Authoritative source is now committed
at 53140bcf; independent all-file review closed related findings and advanced the
next requirement to actual monitor intake. No build/fixture/native operation or
runtime resource occurred. The full custody correction remains incomplete,
without a completed failed correction/recovery. Independent source work remains;
goal active/incomplete, not blocked.


2026-09-30 transfer fixture continuation: progress. Previous turn was a verified
wait on the live Windows agent. Current authoritative untracked fixture source
changes state; full source inspection identifies additional bounded-loop and
ACK/invalid-assembly requirements before final review. Same agent confirmed
running, not restarted. No compiler/native operation or resource. Incomplete
full-custody correction has no completed failed correction/recovery; independent
source work remains, so goal active/incomplete, not blocked.

2026-09-30 transfer continuation: verified wait. Previous turn was progress:
91e474d7/73020670 source and related independent review changed authoritative
state. Current live agent inventory independently confirms the same responsible
Windows agent running; two bounded 45-second mailbox waits timed out without
terminal evidence. Candidate is still clean at 73020670, no transfer file yet.
Do not restart the job or infer failure from the observation timeout. Source
review found a stale README claim that Running renewal is absent despite
43d2f067; delivered for related correction in the active slice.

The integrated sys module currently registers env/fs only and has no process
module. The ticket's real Engine lifecycle, cancellation, managed-scope, error
report and native acceptance requirements therefore remain incomplete. Windows
source infrastructure is a prerequisite, not product completion. No compiler,
fixture/native operation, runtime resource or completed failed correction.
Await and review the exact transfer commit; goal active/incomplete, not blocked.

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
