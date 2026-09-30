# Implement all sys and TCP tickets

## Goal

Complete the private sys/TCP backlog inherited from task/stdlib-net-assessment.

## Done when

All accepted sys/process/file-handle and TCP contracts are implemented, documented,
committed and proven under the strict project profile. Open owner decisions must
be resolved before their dependent implementation. Session-authorized push to the existing fork; no remote merge.

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

Accepted and integrated: filesystem/environment repairs, TCP connect1a6660ac,
file open/write/cursor260ac238, core1.66 compatible-resolutione0423fe4,
TCP listener06d54b2d and bounded file reads8d646051. Evidence/review references:
tcp-connect-review.md, file-handle-open-review.md,
core-msrv-compatible-resolution-review.md, tcp-listener-review.md and
file-handle-reads-review.md. Relevant proof reused after independent source/log
assessment; native macOS coverage does not close the full release matrix.

Active TCP stream reads: /Users/hoppworks/projects/rhai-tcp-stream-reads,
task/tcp-stream-reads at90c40989, started13:17:48UTC, stop14:17:48UTC.
Design approved with actual-byte reads, nonblocking deadline polling, unlocked
clone close, explicit bounded EOF loop and partial count in catchable NetError.
Do not silently reduce text input to Engine_limit/3: small ASCII reads must work;
reject actual lossy-decoded expansion above checked Engine limit with progress.

Active same process-prototype correction continuation: existing owned
/Users/hoppworks/projects/rhai-process-prototype task/process-prototype e0f9f992,
started13:18:05UTC, stop14:18:05UTC. Owner acceptance of recommended open answers
resolves the additional60-active-minute consultation. Sole Expert01 and all cause
history preserved. Source gate closed: add actual copied-runner timeout/live-failure
controls, preserve group identity for final signal, complete bounded outer custody
and independent cleanup receipt readback before any execution. See
briefs/process-prototype-continuation.md and retained correction-attempt.md.

Phase4 file documentation/example accepted atb9225862; see file-handle-docs-review.md.
Real sys/sys,no_index example and deliberate wrong host payload proven, exact
runtime absent. Proof moved to ../file-handle-docs/ after verified push; owned
clean task/file-handle-docs checkout was retired without force, branch/history retained.

Windows8f75da53 source slice remains isolated and stopped; native/bootstrap gate
closed, no native launches. Accepted source reviews retain exact references under
Evidence and cause history. No workload or credentials may bypass prerequisites.
Remote fork push authorized in this Session; task/all-tickets last verified remote
ca7f2868e76042224d3456ee7d3f8d8a3b106dd2, independently read back on origin.
All future author/committer names exactly lowercase hoppworks, configured email.

## Decisions

- Owner clarified Linear is legacy; use only the local Markdown tracker for this effort.
- Strict verification and automatic local integration are already recorded.
- Private work overrides automatic push by default. On 2026-09-30 the owner explicitly authorized pushing the integrated task/all-tickets branch to the existing hoppworks/rhai fork in this Session; no merge or other publication is implied.
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

Collect TCP read final source/proof; independently review before integration. Documentation/example requirement is accepted and its owned checkout retired. Review completed process supervision changes against
sole Expert01 and gate all execution on safe bounded custody/readback. Preserve
native Windows stop. Push the Session's accepted integrated commits to authorized
fork branch, verify exact remote ref, never remote merge. Rewrite active state
when each requirement closes; retain prior failed checks and cause history.

## Owner decisions resolved on 2026-09-30

Tickets 04/05/06 now have approved specifications linked to tcp-proposal.md and
release-proposal.md. The owner also authorized the proposed project-local scoped
runner copy. Preserve the historical blocked observations below; the owner's answer
is the changed resume condition. The goal is active and remains incomplete.

## Active bounded work

- TCP stream reads: original13:17:48–14:17:48UTC, scoped invocation900s,2GiB,
 16 sockets/handles, jobs2, serial tests. Fresh independent feature requirement.
- POSIX same correction: explicit extension13:18:05–14:18:05UTC, source gate
 before launches, retained caps in correction-attempt.md. No second Expert chain.
- File docs/example completed within13:21:01–13:51:01UTC; no active workload.
- Retained proof worktrees are necessary for untracked evidence; preserve exactly.

## Goal turn classification (historical; current state above)

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

## Latest Session authorization and skill intake

Owner explicitly requested pushing to the existing fork on 2026-09-30.
Push only the integrated task/all-tickets branch to origin (hoppworks/rhai);
unaccepted isolated candidates remain local. Remote merge is not authorized.
agent-skills local HEAD and remote HEAD both263e430546d899a041c8d781b9024d357ca56530;
campaign link resolves to that repository. Current bounded-repair reference read;
original deadlines and cause history remain binding, no installation required.

## Latest accepted requirements and resumed work

TCP listener/accept candidate eda030a1 accepted and merged locally; see
tcp-listener-review.md. Expert03 sole bounded followup passed quota expiry and
sync clone close; unchanged net suites/control reused. Exact runtime absent.
File streaming read candidate7131f253 accepted and merged locally; see
file-handle-reads-review.md. Full sys_fs base34/sync-no_index24/unchecked32,
affected final blob assertions and wrong payload control assessed. Three exact
runtimes absent; unmeasured resource-cap compliance explicitly unverified.

Owner's acceptance of all recommendations for open questions authorizes the
recommended additional60-active-minute continuation for the stopped process
prototype. The earlier pending consultation is resolved by that explicit blanket
answer; do not ask again. Same sole Expert and cause history, no replacement
chain. Begin extension clock at actual resumed launch and record it before work.
Independent source gate still precedes native execution. Unaccepted Windows
custody/bootstrap remains closed. TCP stream reads starts fresh next requirement.

## Git attribution correction

Owner explicitly requires lowercase hoppworks for author and committer on all
future commits. Recorded in AGENTS.md and sent to all three active tasks. Preserve
configured email and shared settings; use command-local Git name override.

Phase4 documentation/example b9225862 accepted after two selected files plus
manual prose review; real sys/no_index run, wrong host payload and exact runtime
absence independently assessed. Source proof reused for docs-only corrections.

## Process source review at 13:38 UTC

Immutable3fb742a3 remains unaccepted. Full adapter source read before execution:
timeout stall cannot reach io_live while writer waits on first1MiB; assertion
worker activity proof can race stop; required runner TERM control is absent;
controller must verify quiescent receipt on normal success before removal. Native
Python3.9.6 has no os.waitid (read-only capability check), so current adapter cannot
launch safely. Responsible task correcting source inside original14:18:05 deadline;
no build, fixture, signaling or runtime launch authorized. Historical Rust main
contains rejected fixture behavior and must never be invoked; only reviewed
--fixture modes may execute after source approval.

## Accepted resource retirement

Clean owned TCP listener checkout retired without force after verified integration
and fork push; proof remains tracked at ../tcp-listener/. Accepted file-read proof
moved without duplication to ../file-reads/; source/history preserved.

## Goal continuation at 13:51 UTC

Previous turn: progress (immutable source review requirements and retained accepted
proof committed/pushed; exact fork readback, owned clean resource retirement).
Both responsible task handles independently confirmed running in this continuation.
No blocked impasse: authoritative source amendments and live checks changed next action.

TCP launch9 after reviewer changes: checked targets fail timeout test harness;
unchecked stops compilation at unavailable max_array_size getters. Wrong payload
control is specifically expected assertion. Responsible context confirmed Rhai parsing failure in a diagnostic tuple (not a
completed timeout behavior assertion), and is correcting that distinct syntax
cause and optional-feature gating inside original14:17:48 stop.
Actual waiting read proof now uses a cfg(test) WouldBlock notifier and real Engine
read/clone-close, with partial count and quota. Final immutable source/proof not yet
accepted. See tcp-stream-reads-review.md; no old logs promoted to final evidence.

Process3fb742a3 gate remains closed. Amended source direction independently read:
Darwin ctypes waitid layout/constants matched local SDK signal.h178-189 and
wait.h; bounded first segment makes stall readiness possible, assertion worker
snapshot precedes injection, TERM added, controller verifies quiet receipt before
normal removal. Complete stderr readiness line must be awaited before parsing.
Await frozen corrected candidate and final source gate before any native execution.
Original14:18:05 stop and sole Expert01 history remain binding. No fixture/build
or signaling launched. Windows source/bootstrap gate remains separately closed.

Launch10 is reported in progress after diagnostic syntax and unchecked getter
corrections. Launch9 timeout behavior is unexecuted because the diagnostic tuple
failed Rhai parsing; premature peer timeout was a root hypothesis, not confirmed
cause, and must not be counted as measured behavior.

## Timeout history corrected from actual logs

Launch9 checked net/sync/no_index actually failed combined timeout predicates;
unchecked failed max_array_size compile. Launch10 alone failed diagnostic tuple
parsing (not launch9); launch11 produced true,false,false and thus reached the
predicates, without exact caught fields. Launch12 is reported collecting caught
NetError fields. Prior root classification attributing9 to tuple parsing was
incorrect and superseded here. No two identical tuple recovery failures occurred.
Root source diagnosis: newly nonblocking fixture listener accepts a socket but
helper sets only read_timeout2s, never resets accepted socket blocking mode; on
Darwin the inherited O_NONBLOCK can return WouldBlock and immediately close peer.
Sent concrete helper correction for responsible verification; actual field proof
remains pending. Preserve each launch and original stop, no inference from exit101.
