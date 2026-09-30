# All tickets campaign — current state

## Goal and done condition
Implement all approved local stdlib tickets with strict Engine + real OS + independent readback proof and deliberate failing controls. Full acceptance includes process/TCP APIs, core MSRV 1.66.0, optional sys/net MSRV 1.77.2, and native Linux/macOS/Windows release gates. Goal active, incomplete.

## Accepted requirements
- Filesystem/environment foundation: 625263/5f87d3, native macOS and affected Linux proof; references in historical state.
- File open/cursor/shared lifecycle: 62f27ac3 integrated at260ac238; file-handle review and retained owned proof.
- File reads:7131f253 integrated8d646051; proof ../file-reads/, file-handle-reads-review.md; owned checkout retired.
- File docs/example:b9225862; proof ../file-handle-docs/, file-handle-docs-review.md; owned checkout retired.
- TCP connect:a89cb9b3 integrated1a6660ac; tcp-connect-review.md, ../tcp-connect/.
- TCP listen/accept:eda030a1 integrated06d54b2d; tcp-listener-review.md, ../tcp-listener/; sole Expert03 bounded followup accepted, checkout retired.
- Core compatible-resolution MSRV:20452cab integratede0423fe4; core-msrv-compatible-resolution-review.md and ../core-msrv-compatible-resolution/. Optional/native release gates remain open.
Existing unchanged accepted evidence remains valid. Unmeasured resource peaks are explicitly unverified in reviews.

## Current step and remaining gates
TCP reads525737fd accepted after full seven-file review and affected cancellation proof15; unchanged launch13/14 reused. Proof ../tcp-stream-reads/, review tcp-stream-reads-review.md. Integrated and exact remotee0dd28ec verified; clean owned receive checkout retired, proof retained. Writes/half-close newly dispatched, native release still open.
Process9bf32e45 source gate independently approved after full65483bf + conditional-hold delta. First scoped normal vertical case passed at14:05; proof pending independent assessment, live controls active before original14:18:05. Only explicit reviewed --fixture modes; historical bare Rust main forbidden.
Windows8f75da53 source/bootstrap gate closed; no new native execution. Unchanged external prerequisite is recorded once, no repeated audit. Process production and TCP writes/half-close remain open after current slices.

## Decisions and authorization
German chat; repository English. Local Markdown tickets only; Linear legacy.
Strict verification, automatic local integration. Owner explicitly authorizes this Session to push integrated task/all-tickets to origin https://github.com/hoppworks/rhai.git; preserve published history. No remote merge. Every future author/committer exactly hoppworks, configured email unchanged, command-local override, no coauthor.
Owner accepted recommended API/release decisions and recommended process extension; do not reopen answered questions.
Updated global instructions and campaign snapshot/export rules applied. Retain elapsed time and cause history; no duplicate builds/evidence or default launch cutoff.

TCP write/half-close responsible fresh task at /Users/hoppworks/projects/rhai-tcp-stream-writes, task/tcp-stream-writes basee0dd28ec; brief briefs/tcp-stream-writes.md. Record original60min start/deadline before work.

## Budgets and cause history
- TCP original13:17:48–14:17:48UTC inclusive review,900s/invocation,2GiB private storage, jobs2,16 sockets/handles, serial tests. Launches1–14 retained in owned .scratch/tcp-stream-reads/; setup diagnostics classified separately from completed corrections. Launch9 no_index failed; tuple parse only10; launch12 confirmed peer inherited O_NONBLOCK;13 repaired fixture passed. Notifier refinement is source-only test review finding.
- Process original stopped30min12:06:47–12:36:47, explicit60min extension13:18:05–14:18:05UTC inclusive review. Sole Expert01 validated contradictory historical proof; no second chain or time reset. Caps/build and controls in briefs/process-prototype-continuation.md and owned evidence/correction-attempt.md. Source findings unexecuted; zero completed corrective native implementation checks in extension.
- Windows prior source allowance exhausted11:17–11:47; native custody/bootstrap still unproven. Sole Expert02 and original history remain binding.
- Docs bounded13:21:01–13:51:01 complete. No active resources.

## Evidence and resources
Root own /Users/hoppworks/projects/rhai-all-tickets task/all-tickets atf9fe174b (pushed; exact latest remote readback next). Active owned process/TCP worktrees by brief; preserve foreign primary/planning and all unaccepted work. run_scoped.py via python3; private source/CARGO_HOME/CARGO_TARGET_DIR, export each result before cleanup. No broad process/deletion/config changes.

## History references
Complete prior state, accepted details, retired resources, failed checks, escalation and decision history: history-through-f9fe174b.md (preserved without duplication). Cause details: escalations/01-process-prototype-proof.answer.md; tcp-stream-reads-review.md; responsible task state/logs. Historical snapshots are history, this file is authoritative current state.

## Next action
Review corrected process source and authorize only safe bounded native vertical proof before original stop. Review TCP affected unit proof/final source, merge accepted slice with lowercase identity, preserve proof, push/read back exact fork ref. Continue remaining local ticket acceptance; goal stays active.
