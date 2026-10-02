# All tickets campaign — current state

## Goal and done condition
Implement every approved local stdlib ticket with strict public Engine, real OS,
independent readback and meaningful failing controls. Scope includes filesystem,
environment, shared file handles, TCP connect/listen/accept/streams, process
run/spawn/shared Child, managed Unix groups and Windows jobs, core Rust 1.66,
optional sys/net Rust 1.77.2, required features and native Linux/macOS/Windows.
Done only when every local ticket and final release gate is proven. Decision
resolution, source review and repository consolidation are not implementation
acceptance. Local Markdown tickets only; no Linear. Goal active and incomplete.

## Authorization and ownership
Only https://github.com/hoppworks/rhai.git may receive writes; never public
upstream. Root owns /Users/hoppworks/projects/rhai-all-tickets on task/all-tickets.
The foreign primary checkout and foreign/dirty worktrees remain untouched.
Author and committer exactly hoppworks <daniel@hoppworks.de>, command-local Git
configuration, no coauthors/branding. Strict verification, automatic fork pushes
and coordinator merges are authorized. The owner explicitly requested all fork
histories consolidated into main with main the only remote branch; development
integration does not claim release acceptance. Do not recreate remote task refs.
No installs, admin, credentials, agent-home/config or shared-service changes.
Windows guest control belongs solely to windows_monitor_job_owner.

## Done steps and accepted evidence
- Foundation filesystem/environment/file handles/TCP slices are integrated with
  earlier accepted proofs. Detailed slice applicability is preserved in the
  historical state and original evidence; final current-source matrix is open.
- Revised Unix completion contract accepted by the owner's “beides ja”: stopped
  foreign-parent zombies may produce an honest incomplete-cleanup error. Native74
  proves this boundary with live host, direct child reaped, complete captures,
  stopped held zombies, closure TimedOut and immutable diagnostics. Original
  launch-74-evidence at 94e5373f and native74-review.md retain exact receipts.
- Provisional Unix EPERM recovery now has native Linux80 and macOS81 acceptance.
  Shared absolute one-second window; persistent errors retain typed failure and
  diagnostics; no post-reap nonzero group signals; exact ESRCH plus direct reap
  and complete local I/O is required. Source e5b55460ff8f94dba5d35564ced640e6ac8ea3ee,
  archive 70b7404b1dd40c6371d5638d1e5492fe8ff6b73c03ddfd86ba7bfc68af65793c.
  Six native paths match this source after integration. Linux production is
  unchanged from 1241a5f8; e5 only selects /usr/bin/true on Darwin in the test.
- Linux80 original launch-80-evidence at 430a3da184e524b4782bbcb30946f525f1871f5c:
  both known-broken controls meaningful status101, restored owner21/public32
  (raw33 with nested test), outer/scoped/monitor0. Root accepted original logs,
  matching manifests, 99 exact PID/start pairs absent, owned groups empty and
  runtime /tmp/agent-build-1ftfwo9g absent. Cargo result is development proof,
  not final MSRV/all-features proof. Sample maximum303500KiB is not continuous peak.
- macOS81 original macos-process-refresh.pvRbIs and three Cargo logs in
  .scratch/all-tickets/macos-process-refresh-evidence: terminal0, EPERM control
  meaningful101, prior native75 exit0→42 control reused with unchanged relevant
  source, owner21/public29 passed. native81-root-cleanup-readback.json confirms
  34 emitted PIDs/10 groups and exact runtime absent, three manifests matching.
  Cargo53.432s, sampled276896KiB; no continuous peak claim.
- Remote branch cleanup CLOSED. Latest independent ls-remote readback shows ONLY
  main at 1167770c7a94c9687724afcd819195e73422e89d (2026-10-02 integration readback). Nine remote task refs removed
  in the final consolidation, one earlier; every exact tip was ancestor of pushed
  main before deletion. Histories preserved. Local active/foreign/dirty worktrees
  remain; remote cleanup does not authorize discarding them.

## Current step and next action
1. Windows owner launched the single reviewed source-fixture harness at exact
   C:\RhaiQuality\runs\monitor-source-c58407e0123145698ab1d70e70473f7e after
   guest archive7d44819d/script79be8688 integrity and native PS5.1 parser gates.
   Original PowerShell console disappeared; owner reopened read-only inspection,
   with no relaunch. Actual retained logs show setup-control PASS marker,17-file
   input/copy gate reached and compile-production-runner started. Compilation
   failed with CS0103 at WindowsCustodyBackend.cs1543/1626/1750/1931/1936:
   EnsureFinalizationBudgetIfSet is defined in nested RuntimeAllocation, while
   callers are in outer WindowsCustodyBackend. Root rg independently confirmed
   the one definition at724 and five callers. No fixture executable ran; native
   job/fixture acceptance remains open. Owner preserves original setup-failure-
   6244.txt and compiler logs, checks exact process/job cleanup, then source-first
   fixes helper visibility without weakening shared finalization deadlines.
   Frozen correction and originals require root review before another native
   invocation. Focused c776b8e3 relocation of both unchanged guards to enclosing
   backend independently reviewed/integrated as source-only; fivecallers unchanged.
   Root viewed actual compiler screenshot (fiveCS0103). Desktop-only screenshot
   is not exactjob closure proof. Owner checks exact6244/compiler/setupchild IDs
   and updates changed backend's immutable17input hash before nextfresharchive.
   Source pin aa38e83a integrated as26277055: root independently computed all17
   declared input hashes from frozen Git blobs; all match,16 unchanged. Harness
   SHA b1ce7161c87d8aead4d46953f87719dba1f3203a166973ff6bdee655e8c2e372.
   Owner live read-only get-process IDs6244/5864/3972 and csc returned none;
   original run root/logs retained. This is known-process absence, not direct
   closed-job handle readback or native fixture acceptance. Owner records exact
   receipts, then fresh canonical archive/parser/hash staging for focused fix.
   Existing hard caps and nonrenewable real-client allocation remain.
   This is a concrete compilation cause, not a verified live wait. Original
   detailed setup history is retained by reference to root state at f8b65ad6.
2. Linux overhead invocation83 is terminal. Frozen measurement source00bed4a0,
   archive5414ea19,120 alternating calls/zero warmups/no retries. Cargo/scoped/
   monitor0; originalouter1 because49 descriptive cmdlines were empty in89
   otherwise numeric-valid identity rows. Preserve original false SystemExit:0
   diagnostic and failed finalization, not a workload failure. Root independently
   re-parsed all120 Cargo records, compared CSV/recomputed summary and six frozen
   manifests, then SSH-read89 distinct PID/start pairs absent,23 groups empty,
   exact runtime/session scope absent, no signals. Receipt:
   linux83-measurement-root-readback.json. Narrow descriptive Linux data accepted;
   retained worker/handle/descriptor census and final release coverage remain open.
   Median true direct0.699ms/managed101.177ms;16MiB capture direct111.474ms,
   managed211.284ms. Sample maxima RSS911638528bytes/storage300040KiB;
   sampling is not continuous peak. Original83 evidence/staging integrated with
   corrected verifier as278d4924, consuming19048043 patch without importing
   misattributed57e68c6f ancestry. Root byte-compared originalCSV/summary/outer/
   readback with190 blobs; four hashes match. All89 ledger rows and malformed
   identity/quiet-success/real-error controls pass, embedded Python AST/bash syntax
   pass. Empty descriptive cmdline now allowed; numeric identity fields remain
   mandatory. Driver sys.exit is outside Exception logging. No native84 allocated
   or measurement repetition needed. Owner's corrected-finalizer replay is
   supplemental; original failed finalization retained. Next source-only task in
   same responsible Linux context: concrete retained worker/handle/descriptor
   census and meaningful controls for ticket03, reuse accepted timing data.
   No new build/native invocation before root source review. Prior launcher,
   resource/preflight review and invocation82 missing dependency failure remain
   by reference to root state4d095f86 and original82 receipts; no history reset.
   macOS overhead remains SOURCE-ONLY and NOT ready to launch. Expert09 answer
   escalations/09-macos-overhead-custody.answer.md requires sole spawner/reaper,
   owned process-group anchor and command release gate, direct Cargo with frozen
   parser, complete conservative Darwin leaf census and audited actual build
   script/toolchain confinement. Existing f7dab scaffolding is incomplete.
   Launch guard e4971b03 integrated as4d095f86; root verified first main action
   checks CUSTODY_IMPLEMENTATION_FROZEN=False before setup/runtime/children.
   Prerequisite document explicitly incomplete; guard does not prove custody.
   Source audit found46 of131 locked registry sources missing from cache. Root
   authorized ordinary exact locked archive acquisition into a new owned source-
   audit path outside disposable runtimes, verifying Cargo.lock checksums; no
   install/toolchain/config/credentials/agent-home change. Same responsible Mac
   context implements Expert09 architecture and pure controls before native gate.
   No new Expert chain or native slot. Historical Mac prerequisite count82 is
   pre83 snapshot; authoritative actual Unix count83 below. Thirty-minute repair
   checkpoint is an estimate, reviewed with concrete progress; caps unchanged.
3. Windows public-contract source preparation is integrated at43e9ef8c (parent
   056c0b53). OCR selected1 Rust file, reviewed1/skipped0; excluded Markdown state
   was read separately. Initial review corrected INT typing and no_float timeout,
   and distinguished pre-exit intent record from actual process termination proof.
   tests/sys_process_windows.rs adds focused Engine run_raw success/nonzero/raw-byte
   contract, exact streams and child-written record. Static rustfmt/whitespace checks
   pass; no compiler/native test launched, missing-registration RED is unobserved.
   Native owner must prove retained process-handle/PID termination separately;
   pre-exit record and report alone do not prove that. Managed source worktree
   /Users/hoppworks/.codex/worktrees/windows-public-contract/rhai and local
   task/windows-public-contract are clean/owned, retained until native gate review.
   After actual Windows prerequisite acceptance, implement and prove the Windows
   production adapter/lifecycle against ticket03/design. Current process.rs registers
   only cfg(unix); runner scaffolding is not the Windows production implementation.
4. Root added docs/sys-process.md and README link, describing only the current
   Unix registration: host scope/program/output policy, run/raw/shared Child,
   no_index/no_float differences, wait versus execution deadlines, immutable
   failure reports and honest foreign-zombie cleanup boundary. Source descriptions
   checked against config.rs/process.rs/unix.rs/error.rs; all local README/doc
   links resolve and whitespace check passes. Documentation-only change, no
   runtime behavior or native/example acceptance claim. Executed examples and
   final Windows documentation still remain required.
   Complete final current-source native OS/features/MSRV matrix, documentation,
   overhead and release gates. Reuse existing evidence only for unchanged relevant
   source/check logic/environment; final strict coverage remains required.

## Instruction reconciliation
Root reread /Users/hoppworks/.agents/AGENTS.md and project AGENTS.md after the
owner's056b17c update. Commit056b changes global instructions/tooling contract,
not skill files; no unaffected skill reread. Prior approvals cover ordinary
reversible repairs, exact locked source acquisition and fork push/coordinator
integration. Stored PENDING labels do not override human authorization. Explicit
limits, safety caps, histories and acceptance requirements remain. New builds
use owned unique ~/.local/share/agent-builds/rhai/session scope, absolute TMPDIR,
existing run_scoped and project private output/cache/source flags. No existing
build/process was moved, removed or restarted because of the instruction update.

## Resources, counts and cause history
Unix actual native invocation count83 consumed.82 failed before runtime;
83 measurementCargo0 but originalouter1 due optional cmdline receipt validation.
83 is terminal; no liveUnix testhandle. No84allocated. Preserve originalfailures
and root independently accepted narrow descriptive data/cleanup readback. Linux outer598s
plus kill2s=600s, scoped585s, driver580s, aggregate Cargo540s, jobs2, descendants16,
2GiB policy and sampled stop1572864KiB. macOS scoped600s/Cargo540s/jobs2 with same
policy/sample limits. Sampling is not continuous peak or enforced byte accounting.
New global resource-path instructions applied prospectively and recorded in
project AGENTS: own unique ~/.local/share/agent-builds/rhai/<session-id> scope,
absolute TMPDIR before runner, private child runtimes, exact empty-only retirement.
Do not migrate or remove prior failed stages/runtimes. Use
/Users/hoppworks/projects/agent-skills/tools/run_scoped.py and project flags;
private source/lock/home/target/tmp, exported originals outside before cleanup.
Baseline lock8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa;
private libc edge lock2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.
Windows source-fixture outer package1h; Expert02 real-client lifetime30min is
nonrenewable, setup120s, closure30s and shared finalization30s. Job2GiB,
per-process1GiB, processes16, free-storage preflight2GiB. No budget reset.

Preserve all consumed work, original classifications and Expert01–08 histories
by immutable prior state at commit6e3c6a5a (same path), including references to
older a876b2d2 and history-through-f9fe174b.md. Do not execute superseded next-action
paragraphs from those snapshots. Specific recent outcomes:
- Mac75 test E0433 before assertion: namespace setup defect, repaired c6e820d4.
- Linux76 alive monitor age1.187s exceeded agent-chosen1s: infrastructure cause;
  reviewed3s grace repairs only age threshold, exact identity/fail-closed preserved.
- Mac77 opaque runtime initially classified behavior failure; Mac79 typed diagnosis
  proves /bin/true spawn NotFound before closure. Retain both observed failed runs
  and historical classification; test-only Darwin path fix is concretely justified.
- Linux78 expected broken EPERM RED had opaque diagnostic classifier failure,
  not a second corrected-source behavior failure. Typed diagnostic added1241a5f8.
- Mac79 cleanup verified17PIDs/two groups/runtime absent; Cargo50.008s,
  sampled195884KiB; Mac81 closes corrected native requirement.
- Windows737 kernel32 PSObject extraction setup defect, repair2580f04d; b6 long-path
  extraction failure preserved; fresh short path then revealed PS5.1 signed hex
  conversion at line193 after job assignment before17 pins/compile/fixtures.
  Lost old job scope was a real setup custody hole. Sole owner stopped exact
  interactive PID8600; no compiler/fixture child had started. Source7b repairs this
  path and adds real nested setup-failure control; native outcome still open.
Existing Expert08 Unix chain and Expert02 Windows limits are not restarted.
Agent-selected estimates are checkpoints; actual safety/user caps remain binding.
After two failed corrections or recoveries for the same underlying cause follow
one existing/new applicable Expert escalation; no second chain or blind retry.

## Remaining acceptance
Ticket03 full run/spawn/shared Child/options/fault/setup/lifecycle/sync behavior,
Windows job custody plus real client plus production implementation and native
public Engine proof; final Linux/macOS/Windows source matrix, core1.66 and optional
1.77.2 compatibility, sys/net alone/combined and required feature/negative gates,
measured overhead, docs/examples and release integration. Reference local issues
in .scratch/stdlib-wayfinder/issues and release-proposal.md. Preserve original
scope; no release or goal-complete claim. Retire only exact owned clean worktrees
after verified integration, retaining necessary original proof outside them.

## Current turn classification
PROGRESS: reread current global/project rules; independently verified Windows17
pins and integrated focused hash correction; integrated Mac fail-closed launch
guard while responsible implementation continues; reviewed/retested corrected
Linux83 verifier and preserved all originals without repeating measurements.
Full goal active/incomplete. Root integration published to fork main1167770c; exact ls-remote confirms only
refs/heads/main and the matching head. Every new author/committer is lowercase
hoppworks. Root worktree clean. This state update follows that verified readback.
