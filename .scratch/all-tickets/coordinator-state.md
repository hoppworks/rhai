# All tickets campaign — current state

## Goal and done condition
Implement every approved local stdlib ticket with strict public Engine + real OS + independent readback and wrong-assertion controls. Required scope includes process/TCP APIs, core MSRV1.66, optional sys/net1.77.2, required features and native macOS/Linux/Windows. Goal incomplete. Local Markdown tickets only; Linear is legacy and unauthorized.

## Authorization and constraints
German chat; English repository artifacts. Maximum quality; effort is secondary, but approved finite calibration/repair limits remain binding. Strict verification and automatic local integration. Owner explicitly permits this Session's pushes and verified main integration ONLY to origin https://github.com/hoppworks/rhai.git. Public original repository must receive no writes or PRs. Preserve published history and foreign local main/branches/worktrees. Author and committer exactly hoppworks <daniel@hoppworks.de>, command-local override; no coauthors or branding.

Owner approved three earlier extensions with "ok go", then separately approved both further Linux/combined verifier packages. Those answers resolve the old pending questions; do not reopen them or reset cause history. Windows has no new authorization beyond its exhausted source package.

## Current step
- Linux sys-only native feature slice accepted: frozen driver3386a82f, proof0bb13df1, integratedc699b9e3 and root acceptanceac96b6ac. One invocation18:48:55–18:49:50UTC:24targets/500passes, wrongabc101/restored1. Root57PID/start identities absent (unknown0), bothgroups/runtime/stage absent;71 manifest hashes match retained canonical export. Review linux-sys-followup-proof-review.md; proof ../linux-sys-release-features/proof.md. Full acceptance finished within new18:37:48–19:07:48UTC package. No new production changes. Clean owned checkout retired normally after verified fork push; all proof including ignored lock preserved outside it.
- Combined further package ACCEPTED: proof2315be0c, root reviewc31dd690 and integration6189486676a0bfeb680dc1ef1483f9218a14015c. Immutable source1be277f2; one invocation19:09:11–19:09:34UTC/exit0, f32 eight-target96passes. Root finalizer0:49 distinct original PID/start identities absent, unknown0, launcher/runner absent, group91223 empty, runtime absent. All22 new and35 prior manifest entries match canonical merged exports; sole production/test merge effect is tests/combined_sys_net.rs. Sampled313856KiB/7descendants, lock4aa2e322 unchanged. Prior seven non-f32 rows/control reused; previous custody limitation retained. Accepted before19:23:29UTC; fork refs independently read back b74e48d1984e3097f015947cd70d41662b1f0676, then exact clean owned checkout retired normally. All canonical proof retained in root checkout.
- Native Rust process prerequisite STOPPED after explicit owner "Freigabe": further bounded correction dispatched2026-09-30 19:39:50UTC; hardfinish20:39:50UTC including rootreview, executioncutoff20:29:50UTC. Reuse owned /Users/hoppworks/projects/rhai-process-rust-io at080e61e6/candidate988502da. Fix concrete cap receipt/order contradictions and complete bounded orchestration launcher; immutable root gate required before any runtime. One invocation<=600s/build<=300s,13 fixed serial cases<=45s each/full export reserve, jobs2,1GiB,8process resources,3workers,32RustFD,2MiB streams; zero unexpected-failure allowance, no reruns/post-gate edits/secondExpert. Existing Expert04 design and all prior exhausted source-package history preserved. Previous package had zero builds/measurements, static only. Review process-native-followup-stop-review.md defines approved scope; no production or Windows authorization inferred.
- Native Windows custody prerequisite remains unchanged and open after exhausted11:17–11:47UTC source package and sole Expert02. No repeated audit or new native execution without changed prerequisite. Production process Engine/API, remaining native/feature/MSRV release requirements remain open.

## Accepted requirements and retained evidence
Reuse unchanged accepted evidence; do not rebuild solely because a Session changed.

| Slice | Accepted source / integration | Review and proof paths |
| --- | --- | --- |
| Filesystem/environment foundation |625263/5f87d3|history-through-f9fe174b.md; ../environment-fixtures/|
| File open/shared cursor/lifecycle |62f27ac3/260ac238|file-handle-open-review.md; ../file-handles/|
| File reads |7131f253/8d646051|file-handle-reads-review.md; ../file-reads/|
| File docs |b9225862|file-handle-docs-review.md; ../file-handle-docs/|
| TCP connect |a89cb9b3/1a6660ac|tcp-connect-review.md; ../tcp-connect/|
| TCP listener |eda030a1/06d54b2d|tcp-listener-review.md; ../tcp-listener/|
| TCP reads |525737fd/e0dd28ec|tcp-stream-reads-review.md; ../tcp-stream-reads/|
| TCP writes/half-close |44275bf8/c1971d48|tcp-stream-writes-review.md; ../tcp-stream-writes/|
| Process custody Python-parent prototype |60d99b58/9bf32|process-source-gate-review.md; ../process-prototype/|
| Process private design only |073b0af8|../process-io-design/design.md|
| Core MSRV1.66 compatible resolution |20452cab/e0423fe4|core-msrv-compatible-resolution-review.md; ../core-msrv-compatible-resolution/|
| macOS net features |9005d769/3fae1808|net-feature-proof-review.md; ../net-feature-proof/|
| TCP examples/metadata |fa8904e5/4f344897|tcp-docs-example-review.md; ../tcp-docs-example/|
| Linux TCP |71446daf/57d54653|linux-tcp-review.md; ../linux-tcp-proof/|
| Unsupported WASM/compiler gates |7f60ece6/e1db9baa|unsupported-feature-review.md; ../unsupported-feature-proof/|
| Linux net features |957fc6a7/ad6e9720|linux-net-release-features-review.md; ../linux-net-release-features/|
| macOS optional MSRV1.77.2 |8f3d53a2/66ed5c7a|optional-msrv-proof-review.md; ../optional-msrv-proof/|
| Linux optional MSRV1.77.2 |61f247f7/b26276c0|linux-optional-msrv-proof-review.md; ../linux-optional-msrv-proof/|
| macOS sys-only features |488349d8/90f2349d|macos-sys-release-proof-review.md; ../macos-sys-release-evidence/|
| Linux sys-only features |0bb13df1/ac96b6ac|linux-sys-followup-proof-review.md; ../linux-sys-release-features/|
| Combined sys/net coexistence and f32 full row |2315be0c/61894866|combined-followup-proof-review.md; ../combined-package-proof/|

Accepted custody prototype has Python parent I/O and Rust child fixtures; it does not prove Rust parent cancellation or production process behavior. Unsupported compiler checks do not establish native execution. Reported resource samples do not establish continuous or true peaks. Specific evidence limitations remain in each review (including macOS MSRV wrapper/PID omissions).

## Prior attempts, escalation and budgets
Complete older history by reference: history-through-f9fe174b.md, responsible slice states/proofs and named review files. Root state before this rewrite is preserved in commitac96b6ac at this same path; no cause total is reset.
- TCP reads launch9 no_index failure,10 parse only,12 peer O_NONBLOCK discovery;13/14 accepted and15 affected cancellation. Writes retained bounded saturation correction/control and sole Expert03 history. See TCP reviews.
- Process original prototype30min12:06:47–12:36:47 then explicit60min13:18:05–14:18:05 completed14:09:42 under sole Expert01. Accepted six controls; no further prototype launch needed. Distinct Rust source package14:41:34–15:11:34 stopped15:08 with zero builds; Expert04 completed15:13:37, sole currently authorized followup above. No second chain/time reset.
- Linux sys original16:22–16:52 failed setup because archive omittedcodegen, zero tests; fd69 evidence. Extension17:40:14–18:10:14 ran17:52:41 and stopped1 after correct wrongassertion101 because literal panic matcher missed Rust threadID, zero restored/matrix; a09 attempt2 evidence,17identities/runtime/stage absent. Further explicit package above accepted attempt3. Failures are separate verifier infrastructure causes, not production corrections.
- Combined original15:36–16:06 source679e7 collected seven rows then storage2,675,624KiB exceeded2GiB. Source-only fragmentation fix14ace/c2 not yet accepted production/test integration. Extension17:54:18–18:24:18 ran18:16:06–18:17:36: wrong101/restored1 plus six other coexistence rows passed, f32 compile stopped89 on disappearing Cargo object. Finalizer1 because81 original PID start times unavailable;35 known identities gone,81 numeric PIDs absent, runtime/group empty. Evidence52363 exported evidence-only to ../combined-package-followup-evidence/; combined-followup-proof-review.md. Further explicitly approved package above does not erase this custody/measurement history.
- Windows original source allowance11:17–11:47 exhausted; source/bootstrap8f75 only, no native custody acceptance. Sole Expert02 retained. No new execution allowance.

## Resources and next action
Root owns /Users/hoppworks/projects/rhai-all-tickets on task/all-tickets. Origin main and task/all-tickets independently read back67a316e6490f9be5970efad92c51dc9750f884af after the explicit further process authorization. Primary foreign /Users/hoppworks/projects/rhai remains local maina6241621. Current root has no owned runtime processes; combined owned checkout is retired; process source correction is stopped in the clean retained owned checkoutd45f8cca; no delegated scoped invocation, build or native runtime launched. Preserve all foreign/unclassified resources.

Build/test only with configured agent-skills tools/run_scoped.py, complete private source/CARGO_HOME/target/tmp, inherited Cargo group, exact identified cleanup, and export before removal. Do not restart/reseed shared resources or change Agent homes. Retire clean owned completed worktrees only after proof retention and verified merge/push.

Next: owner explicitly authorized the interpreter-only correction with "Freigabe". Dispatch 2026-09-30 20:35:17 UTC; hard finish 20:55:17 UTC, execution cutoff 20:45:17 UTC. Unchanged gated source d45f8cca, exactly one first actual scoped invocation <=600s and 13 fixed cases; independent root review <=10min. Preserve all prior history and the shell126 stop. No source changes, reruns or second Expert; zero further unexpected failures, unchanged resource caps. Responsible process context runs the exact reviewed command and exports raw proof before cleanup. Windows still waits for a changed native custody prerequisite; full goal is incomplete.
