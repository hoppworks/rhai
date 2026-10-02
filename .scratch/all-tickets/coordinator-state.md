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
  main at 658221520e1226c39e75ddb3f922db64c2d0e95c (2026-10-02). Nine remote task refs removed
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
   invocation. Existing hard caps and nonrenewable real-client allocation remain.
   This is a concrete compilation cause, not a verified live wait. Original
   detailed setup history is retained by reference to root state at f8b65ad6.
2. POSIX overhead source00bed4a0dfeb103ff209ba4c76dac7ae797b7c56 integrated.
   OCR selected2 files, reviewed2/skipped0; excluded contract/state read separately.
   Root Python AST and parser self-test pass, including meaningful missing/reordered
   sample rejection. Rust formatting/whitespace checks passed in responsible context.
   No Cargo/native measurements yet. Thirty paired samples per API-entry-to-report
   latency and 8MiB stdout plus8MiB stderr throughput, alternating mode/workload
   order,120 executions/zero warmups. Explicit frozen revision/archive IDs, bounded
   metadata commands and early raw export address root pre-freeze findings.
   Exact capture fixture PID absence is narrow observed resource evidence, not a
   worker/handle/descriptor census; those ticket03 resource requirements stay open.
   Responsible Linux context froze launcher/preflight at local dd95669e. Root
   independently read all launcher/wrapper/contract/preflight sources: descendant
   monitoring exists, but storage sampling is missing from the new wrapper and
   memory RSS observation/stop is absent despite printed claims. Root returned
   first source-review correction: implement actual bounded storage/RSS sampling
   and export, add measurement-command identity ledger to final readback, retain
   exact identity/heartbeat/cancellation and existing bounds. No staging or native
   invocation82 is released; no measurement slot or native failure consumed.
   Owner added concrete du/storage and owned-tree RSS sampling. Root early review
   of the in-progress correction found final strict ledger/cap validation could
   raise before failed-run exact cleanup, and failed readback was not exported.
   Returned concrete correction: unconditional exact cleanup/readback from valid
   available identities first, preserve failed receipts, then fail acceptance.
   Confirmed same-start zombie/X entries without VmRSS must be terminal0, while
   missing live-process VmRSS stays fail-closed. These are source-review findings
   within the same first correction; no native cause count or budget reset.
   Corrected frozen package b6f34e20efea282f3a31cf040b9e89831a17bd6d now
   independently read and integrated into root. Root verified all four reported
   hashes, Python AST, four embedded Python blocks and bash syntax in scoped30s.
   Finalizer exports initial live identities/cleanup actions and rejects status0
   with leftovers; current snapshot receipts precede resource stop checks. Source
   gate accepted; responsible Linux context resumes fresh staging/hash/empty-
   evidence readback released ONE bounded native82. It actually launched at
   2026-10-02T05:22:31Z and returned terminal1 before private runtime/measurement:
   copied runner imports agentskills.pyguard but the stage omitted that package.
   Native82 consumed; zero benchmark calls/results. Original seven exported files
   at responsible .scratch/managed-unix-scope-close/launch-82-evidence independently
   read by root: exact ModuleNotFoundError, run-scoped/monitor/outer1, failed required
   ledger acceptance and no matching runner identity remaining. Owner additionally
   observed launcher3539356/start5515212 and runner3539364/start5515216 absent,
   PGID3539298 empty; requested original readback receipt preservation. No
   PRIVATE_RUNTIME emitted, because import failed before runtime creation.
   First infrastructure cause is incomplete copied runner dependency bundle. Root
   inspected configured run_scoped.py plus agentskills/{__init__.py,pyguard.py}:
   exactly these three files are required; pyguard uses existing Python>=3.11,
   no install/config changes. Responsible context prepares a frozen complete
   dependency manifest/contract/preflight and NEW absent stage, retaining82 stage.
   Corrected patch from local57e68c6f was applied without importing that
   misattributed commit: root verifies preflight86cb738f, launcher020dc216 and
   contract2b871c13, AST/bash syntax/whitespace and original post-exit identity/
   group receipt. Exactly3 hash-bound runner files, nativePython>=3.12/filter and
   bounded --help import gate now precede workload. Root accepted source gate
   and released fresh absent-only staging/preflight; native83 remains withheld
   until staged receipts are independently reviewed. Root then independently
   SSH-read stage /root/rhai-process-overhead-00bed4a0-b6f34e20-preflight83:
   all10 exact hashes match, evidence real/empty. Native preflight reports
   Python3.14.7, tarfile filter and copied runner --help imports pass. Original
   receipts in responsible launch-83-staging/{staged-hashes,preflight-output}.txt.
   Source/staging gate CLOSED; ONE native83 released under unchanged caps and
   exact120calls/zero warmups/no retries. Count83 consumes only at actual launch;
   no live handle or actual launch receipt yet. No performance acceptance claimed.
   Root macOS measurement adaptation is SOURCE-ONLY and NOT approved to launch:
   macos-process-overhead.py and run-macos-process-overhead.sh bind00bed/archive
   5414ea195ad00152b1eae36b3f4e10943ba5d9bf323baff6410cca0c5b4d8b98.
   Fresh Worker reviewed both files: frozen inputs, private lock/runtime, sample
   semantics/export and watchdogs present; inherited du-only sampling lacks live
   descendant<=16 and2GiB memory observation/stop. run_scoped group-only cleanup
   must not be claimed as exact managed-child closure after interrupted driver.
   No Mac launch consumed. Responsible fresh Standard macos_overhead_safeguards now owns managed worktree
   /Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai on local
   task/macos-overhead-safeguards from39617ee7. Source-only repair brief requires
   concrete live descendant/RSS monitoring, bounded cancellation/reap and exact
   identity readback without unsafe stale-PID/group signaling. No native/Cargo
   launch; root independently reviews frozen safeguards before release. First source-review finding,
   no native failure or new Expert chain. Keep planned120calls/zero warmups/no retries. Root inspected frozen io_stress
   fixture: exact2 writer threads/no process descendants, stdin EOF, write errors
   panic and failed joins unwind before process exit. This gives a concrete route
   for a later bounded pipe-closure interruption control, not native closure proof.
   Owner must retain candid unresolved escaped-PGID closure status; passive
   PID+lstart ledger never authorizes stale/nonchild numeric signaling.
   macOS safeguards frozen source31f22f960c4df69638d52007eef64afc4e8927e8
   passed responsible pure/static checks but root rejects native launch readiness.
   Root read the adapter, harness and frozen measurement driver: harness run()
   owns the measurement Python Popen, not Cargo; frozen driver subprocess.run
   has no interruption forwarding/finally. Reaping the Python starter cannot
   establish Cargo or test descendant closure. Setup git-archive Popen also
   starts outside cancellation/ledger while state still says no-process-started,
   permitting unsafe runtime removal after interruption. Final ps readback must
   fit the total adapter deadline. Returned concrete source corrections to the
   same responsible context; first source review, no native attempt consumed.
   A project-local direct Cargo invocation can reuse frozen parsing/measurement
   semantics and remove the intermediate child, but still needs accepted group
   anchor custody and benchmark-specific escaped-fixture interruption proof.
   No group/PID signaling authority is granted by passive snapshots.
   Corrected safeguards f7dab7934f7f7f42245ec23008fe8e2616606799 integrated
   as source progress only. Exact child log names corrected to measurement driver;
   setup-in-progress prevents false no-process-started cleanup, final readback
   has a remaining-time bound. Generic interrupted descendant closure still open.
   Fresh read-only Expert09 /root/macos_overhead_custody_expert is analyzing the
   uncovered benchmark-launch custody decision,15-minute planning checkpoint,
   no native/Cargo slots. Brief escalations/09-macos-overhead-custody.md; answer
   delivered at escalations/09-macos-overhead-custody.answer.md. Root reviewed
   sole-spawner/reaper anchored command gate, direct Cargo with frozen parser,
   conservative complete Darwin leaf readback and exact build-script/toolchain
   confinement prerequisite. Same responsible macos_overhead_safeguards context
   now implements one source-first bounded repair,30-minute active checkpoint.
   No native/control/measurement launch until frozen source/pure controls/ABI and
   confinement review. One cause09 chain; no count or hard-cap reset.
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

## Resources, counts and cause history
Unix actual native invocation count82 consumed; native82 failed at runner import
before runtime/measurement. Next unique invocation83 allocated only at launch after
new source/staging gate. No live Unix test handle is currently recorded. Linux outer598s
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

## Previous turn classification
The user-requested overall-status turn was NO PROGRESS (readback/status only).
This continuation makes PROGRESS: independently accepted/applied Linux dependency
bundle correction and82 original cleanup receipts, advanced absent-only staging,
reviewed Expert09 answer and resumed bounded Mac source implementation, and obtained
actual Windows compiler-failure evidence that determines the targeted correction.
No new native slot or benchmark result claimed; goal remains active/incomplete.
