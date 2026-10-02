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
- Remote branch cleanup CLOSED. On 2026-10-02 exact ls-remote readback shows ONLY
  main at 6e3c6a5a0c2ee8f3f8a93b7b9e4c77c5d34ff64b. Nine remote task refs removed
  in the final consolidation, one earlier; every exact tip was ancestor of pushed
  main before deletion. Histories preserved. Local active/foreign/dirty worktrees
  remain; remote cleanup does not authorize discarding them.

## Current step and next action
1. Windows owner continues the authorized source-fixture package. Frozen source
   7b9fd871c3d036ff9f57e9e4e35e01b10f0c0c32 is on fork main; RunSourceFixtures.ps1
   SHA25679be8688152ae600b4126f6c03571dd6dd66d669f4dfe2a1b720b775bfe82b4d.
   Root source review accepted positive UInt32 constants, custody from first handle,
   guarded disposal, shared30s setup-failure accounting and CRLF marker matching.
   Latest owner receipt: unlocked VM console; process-local Bypass read back.
   Fresh archive curl command used lowercase-l instead of uppercase-L and saved
   an empty redirect response. Original empty archive preserved; owner diagnosed
   the exact key/input error and prepares fresh absent-path redirect-follow fetch.
   NO fixture/compiler/job handle yet; hash/parser/17-pin gate not yet verified. Continue fresh immutable
   archive/runroot, native PS5.1 parser and input gate before fixture invocation.
   Preserve failed roots and exact cleanup. Do not call this a verified live wait.
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
   no native failure or new Expert chain. Keep planned120calls/zero warmups/no retries.
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
4. Complete final current-source native OS/features/MSRV matrix, documentation,
   overhead and release gates. Reuse existing evidence only for unchanged relevant
   source/check logic/environment; final strict coverage remains required.

## Resources, counts and cause history
Unix actual native invocation count81 consumed; next unique invocation82 allocated
only at launch. No live Unix test handle is currently recorded. Linux outer598s
plus kill2s=600s, scoped585s, driver580s, aggregate Cargo540s, jobs2, descendants16,
2GiB policy and sampled stop1572864KiB. macOS scoped600s/Cargo540s/jobs2 with same
policy/sample limits. Sampling is not continuous peak or enforced byte accounting.
Use /Users/hoppworks/projects/agent-skills/tools/run_scoped.py and project flags;
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
The preceding user status turn restated authoritative state and verified only-main
remote; it did not close implementation acceptance (no implementation progress).
This continuation independently reviewed frozen Linux launcher dd95669e and found
concrete missing storage/RSS monitoring, changing next action to source correction
before native82. Linux responsible context continues that repair. Root created an
exact owned managed worktree and delegated the parallel bounded Mac safeguard
repair. Windows continues its existing owner context; no live fixture handle is
claimed from agent status or intent. No history, budget or native counter reset.
