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
upstream. Root owns /Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai on
task/all-tickets-continuation. The former owned checkout was externally removed
a second time; retained committed4ac93a44 was used to create this attached managed
checkout. Do not recreate/prune/remove the old missing worktree entry blindly.
Committed proof is intact; removed uncommitted contents are not certified.
The foreign primary checkout and foreign/dirty worktrees remain untouched.
Author and committer exactly hoppworks <daniel@hoppworks.de>, command-local Git
configuration, no coauthors/branding. Strict verification, automatic fork pushes
and coordinator merges are authorized. The owner explicitly requested all fork
histories consolidated into main with main the only remote branch; development
integration does not claim release acceptance. Do not recreate remote task refs.
No installs, admin, credentials, agent-home/config or shared-service changes.
Windows guest control belongs solely to windows_private_staging_readback; historical owner records remain preserved.

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
  main at6199fcabc755355929ced07e9b6d306a33dded2e (reviewed Linux package integration readback). Nine remote task refs removed
  in the final consolidation, one earlier; every exact tip was ancestor of pushed
  main before deletion. Histories preserved. Local active/foreign/dirty worktrees
  remain; remote cleanup does not authorize discarding them.

- macOS locked registry SOURCE INTEGRITY prerequisite CLOSED narrowly. Root
  independently verified baseline lock8bd35 against archive-manifest4b678d45,
  all131 archive checksums/declared byte sizes, and byte-compared5968 unpacked
  regular files with exact tar members; no extras/nonregular payloads. Total
  archive37,649,963bytes. Receipt macos-locked-source-root-readback.json; exact
  durable owner source-audit path recorded there. This closes source acquisition
  integrity only, not selected execution graph/toolchain/custody or native proof.

- Linux net-only feature proof source applicability checked at6d4d9e0f against
  original243404c9: net production, codegen, build.rs and all six net integration
  targets/support unchanged. Entire src diff outside sys is only token.rs spawn
  function-call allowance gated by feature sys; these net-only rows omit sys.
  Cargo changes only move optional cap-std to non-WASM and add sys-only libc;
  net feature remains std. Original957fc acceptance and raw23invocations/148tests
  retain their original Linux7.2.4/Rust1.97.1/lock4aa2 coverage; do not claim they
  ran on present Linux7.2.7/privateRust1.77.2. No relevant net check/source change
  warrants a duplicate control or build solely for current integration. Combined
  sys/net, changed platform/MSRV and final current-native release coverage open.

## Current step and next action

Current instructions/roles revision958a4538b0191c53f2ccb2cd00d96c15045fbf68.
Current authoritative history through this rewrite is Git commit
10d4a0d55400ebe8c24feff134e7161ff36bf8d5, this same state path. It retains
all earlier cause/attempt/resource/source applicability records. Read that
history for consumed work, not superseded next actions. No reset occurred.
Last independently read-back fork mainef1a8d62; only remote main, lowercase
human author/committer. Goal active and incomplete.

### Accepted current Linux non-process package

Frozen productiona2d7a8c2/archive551c03db, v3lock2ba4, privateRust1.77.2,
Linux7.2.7: nine real Engine/OS feature rows,601 tests, five meaningful wrong
controls. Seven rows430 plus combined-no-index-sync-metadata82 and f3289.
Original linux-policy-package-evidence and linux-current-sys-net-policy2-evidence,
policy2-review.md and root readbacks establish exact source/coverage/cleanup.
All10 policy2PID/start absent, groups/runtime/scope absent; sampledRSS912224KiB,
storage1000220KiB/desc10; export34.471s; unchanged proof remains applicable.
Compiler11rows and optionalexamples on Linux/Darwin remain accepted narrowly;
core1.66Darwin42/wrong43/restored42 reused under unchanged relevant inputs.
Ticket06 contains detailed applicability. None closes process/fullrelease.

### Darwin files/network preparation

Owned /Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai,
task/current-darwin-sys-net-behavior. Test/source2f795ecee8edd6ddf348f382e5397cc6e348ad37,
archive43c8b8e43a2bcd3e74dd0be3d60a0dea2eab50eb5bfe65cc736684631523d52b,
lock2ba4. Initial2d52 review and affected8b974/4c4a originals retained once in
current-darwin-sys-net-source-review/. F2 conservative cleanup source accepted;
F3 configured prefix-root source accepted, native canonicalization still open.
Two failed F4 corrections retained:8b974 split ordering,4c4a stderr diagnostic
loss invalidating derived-path F1 EILSEQ rejection. Cause11 single fresh Expert
answer escalation11-darwin-split-stream-coverage.answer.md, one source follow-up.
Follow-up frozen CLEAN322ac6be2a46191242d3982c3b4e2f2f62cd9425: separate frozen
sys_fs/F19 diagnostic mapping, unresolved/conflict failclosed partial receipts,
structural diagnostic isolation, status0 incomplete continuation and strict
SESSION_ID2f795ece naming. Owner ten pure categoriesGREEN; RED/GREEN at
current-darwin-sys-net-diagnostic-red.md/-green.stdout in owner worktree.
SAME reviewer current_darwin_sys_net_review ACCEPTED this affected source scope.
Ten original review artifacts and root readback retained once in
current-darwin-sys-net-source-review/affected-322ac6be/. Actual stderr F19 rejection,
unresolved failclosed partial rows, main-loop continuation and strict naming
independently verified source-only. Production/source/lock unchanged; Linux proof
retained. Responsible owner preparing exact staged inputs, private toolchain,
heavy-slot availability and scoped bounded command before coordinator allocation.
Stage now exists at owner .scratch/all-tickets/current-darwin-sys-net-behavior-2f795ece-20261002,
all staged pins verified; exact corresponding central scope created empty.
Darwin arm64 confirmed; helper performs private1.77.2 install/verification. Initial
/usr/bin/ps probe failed before native invocation; actual /bin/ps works.
Exact later /bin/ps confirms foreign TableTop Playwright test PID51269,
worker51296/browser51297 remain alive (second observation12s later, elapsed~38min).
Heavy Mac slot occupied by actual E2E; no signal or run launch. TaUron MCPs likely
idle services; ffmpeg exited. Use same E2E identities for later slot observation.
Prepared dispatch command requires configured modern Python for BOTH runner/helper
and PYTHONDONTWRITEBYTECODE=1, explicit outer timeout600; no system Python assumption.
Native Darwin acceptance remains pending; no native launch allocated yet.

### Mac process overhead/control preparation

Owned /Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai,
task/macos-overhead-safeguards. Expert09 solecustodian/anchors/directCargo/private
PATH/native passive escaped-leaf route remains current, no second custody chain.
All earlier confinement/ABI/header audits and exact measurement overlays/fixtures
retained by historical state references. Measurement source00bed/archive5414,
30 alternating pairs/workload120calls/zero warmups, fixture8MiB/stream unchanged.
Guardfalse, nativecount84; measurement85 allocated/unlaunched; four one-attempt
controls unallocated. Source readiness sixfields remain open before dispatch.
Findings1–3 source accepted atb1e05; finding4 failed actionrace correction retained.
Latest29cfb009 per-read bound independently source-accepted: at most one unpublished
64KiB quantum/stream, paired atomic generation, stdout8388592/stderr8388608 strict
remaining bounds. Full85/85 ownerpure and independent affected12/12 do not certify
native behavior. Same affected report/eight originals retained once at
macos-control-independent-review-20261002/affected-29cfb009/.
Two terminal defects: real observer drops validatedSSTOP status and always rejects;
fail() closes capture endpoints while old capturing receipt remains actioneligible,
including publicationfailure. Two failedfinding4 corrections retained.
Authorization reconciled with current human Autonomous workflow and standing
acceptance of recommendations: earlier root no-third-patch note was internal,
not human sourceattemptcap. Concrete boundclosure/new diagnoses justify continuing
SAME Expert09 source-first follow-up at30min planningcheckpoint; no newpackage,
chain or nativeallowance. Owner follow-up frozen5ed13c10a341250755372bf03445f0b597294848: stopped status
propagates into actual observer; aborted receipts rejected before native census;
CONTROL fail() atomically invalidates capturing receipt before endpoint teardown,
and exits before teardown if invalidation cannot be guaranteed. Focused3/full88
pure tests pass. SAME reviewer macos_finite_control_review dispatched on new freeze,
including actual error/STOP/invalidationfailure boundaries; no native acceptance.
Reviewer decisive checkpoint: original stopped observer regression passes, aborted
observer cannot KILL; STOP before invalidation retains incomplete endpoints, after
invalidation sees aborted. Terminal SAME affected report independently read back and ten exact originals
retained once at macos-control-independent-review-20261002/affected-5ed13c10/.
Both outstanding manifestations source CLOSED, no residual material finding.
Owner preparing existing four one-attempt control
commands/stage/scopes/pins/cleanup under SAME Expert09, no control allocation or
native dispatch. Darwin heavy run precedes Mac controls when foreign slot clears.
Production/measurement/fixtures and historical failures retained. Foreign tracked
prerequisite deletion/untracked assets remain untouched.

### Windows private preparation

Soleowner windows_private_staging_readback, VM rhai-win11-quality UUID
dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19,4vCPU8GiB; foreigntauron untouched.
Exact own guestroot C:\Users\RhaiTest\.local\share\agent-builds\rhai\w9e0-20261002-6f804a9c4c4a4e78.
Single9e0GET consumed terminalcurl0/13380569bytes/SHA8291e58652a7dc8494513d910460e6dae39a716f5dfca937bda40fafcfa0caa4;
one extraction consumed. Earlier nonexistentIsRooted guard emitted nonterminal
errors; no retry/overwrite. Correct failfast readonly archive/path/name audit
24expected/24actual/0differences, ancestor noReparsePoint accepted by independent
root visual readback. Follow-up whole source subtree directories/files reparse
scan count0 cleanprompt independently accepted; originals/readbacks retained once
windows-staging-9e0-root-evidence/. Script17C#pins all match, PS5.1parser0, scriptSHA19c030... verified by actual
ConsoleHost result and independent root visual readback. Exact Roslyn file
C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe59720bytes/SHAcf32... read only.
Three actual console frames plus narrow parser-compiler-root-readback.json retained
once in windows-staging-9e0-root-evidence/. Compiler execution still unperformed.
Old5fe4GET/history and Expert02 nonrenewable limits retained. Responsible soleowner
continues already authorized single bounded source-fixture invocation after fresh
exact RunRoot/path/storage/slot/pin checks. Outer1h and existing job/process timers
unchanged; no installs, real client or production-native acceptance authorized by
these source prerequisites. Keyboard43606 terminal confirmed; no restart.
Workhorse heavy slot initially occupied by foreign Tauron Cargo PID2801039 and
rustc2801043. Later exact ps and /proc paths both absent; no signal was sent.
This does not prove absence of a new heavy owner. Sole owner checks fresh slot
and exact guest RunRoot/free storage, then executes existing single authorized
source-fixture invocation; no allowance/history reset.

### Next actions and turn classification

Collect Mac5ed13 affected result; Darwin owner prepares exact native dispatch;
Windows owner proceeds to existing bounded source-fixture execution after fresh
preflight. Allocate actual Darwin native run only after exact source/helper/lock/
contract/toolchain/slot/runtime checks. Preserve all caps and no foreign disruption.
Previous turn PROGRESS: retained/readback Darwin source review and Windows
parser/pins/compiler-file prerequisites pushed as67968f30, soleforkmain checked.
Current PROGRESS: actual exact Darwin pinned stage and empty owned scope prepared;
command interpreter corrected before launch; foreign Windows heavy-build identities
subsequently observed absent. Source/native counts unchanged. No native acceptance
or completion claim. Mac same affected source review remains active.

## Resources, counts and cause history
Unix actual native invocation count84 consumed.82 failed before runtime;
83 measurementCargo0 but originalouter1 due optional cmdline receipt validation.
83 and84 are terminal; no live owned Unix process-test handle. Invocation84 was
launched and consumed; its result is recorded in the current step and prior
Linux84 evidence. Measurement85 is allocated but unlaunched; four one-attempt controls are unallocated. Preserve originalfailures
and root independently accepted narrow descriptive data/cleanup readback. Linux outer598s
plus kill2s=600s, scoped585s, driver580s, aggregate Cargo540s, jobs2, descendants16,
2GiB policy and sampled stop1572864KiB. macOS outer600s/scoped585s/work560s/closure575s/evidence580s/cleanup585s,
aggregateCargo540s/jobs2, same policy/sample limits (Expert09). Sampling is not continuous peak or enforced byte accounting.
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
