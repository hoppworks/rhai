# TCP listener slice state

## Goal
Implement optional, exact-grant TCP listen and bounded accept in `NetPackage`, preserving outgoing connect. Prove with the strict real-Engine/real-socket acceptance slice and report uncovered contracts.

## Start and limits
- Start recorded: 2026-09-30 12:34 UTC (14:34 CEST); 60 active minutes including coordinator review, stop by 13:34 UTC.
- Branch/worktree: `task/tcp-listener`, `/Users/hoppworks/projects/rhai-tcp-listener`, based on `6ce0a58d2c6752f66659736441fcb22a3bcc637b`.
- Per scoped invocation: `--timeout 900`; private build storage <=2 GiB; `CARGO_BUILD_JOBS=2`; <=12 owned live fixture sockets.
- Scoped runner: `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py`; source copy, `CARGO_HOME` and `CARGO_TARGET_DIR` must be under `AGENT_RUNTIME_DIR`. Export logs before cleanup. Do not run native guest work.
- No push or merge. Commit as configured human Git author. No child agents without coordinator authorization.

## Launch and diagnosis log
1. 12:34 UTC: `git worktree add -b task/tcp-listener ... HEAD` succeeded at authorized integrated commit. Earlier abbreviated `coordinator6ce0a58d` ref failed to resolve; exact full commit from `HEAD` used. No resources beyond owned worktree.

## Closed steps and evidence
- Read project `AGENTS.md`, `CONTEXT.md`, TCP/release proposals, and required TDD/E2E skill references. Strict verification selected; E2E method is Cargo integration test via real Rhai Engine and OS sockets.
- Source review: `NetPackage` currently supports connect only; `NetConfig` has connect grants, connect timeout and shared atomic handle ceiling; `NetStream` clone close is idempotent and its mutex is not held during socket I/O. Existing integration contracts are in `tests/net_connect.rs`.

## Current step
Write a public-script listener acceptance test first, then run its scoped RED against a copied source tree. Send RED and draft source early for coordinator review.

## Decisions and open gates
- Script API shape follows approved contract. Plan `listen(address, port)` and `listener.accept(timeout_ms)` where timeout is a positive integer duration in milliseconds capped by host `accept_timeout`; expose actual `local_addr` and listener `close`/`closed`.
- Exact IP/port authorization and explicit grant of port 0; validation and authorization precede socket bind. Listener and accepted stream consume same package quota; clones share close state; accepted streams inherit quota.
- Must preserve outgoing connect.
- Full-package/release gates (bytes, reads/writes, shutdown/partial transfers, platform/MSRV/feature matrix, native Windows custody, no_std/wasm diagnostics) remain outside this slice and will be documented unverified.

## Stop conditions
Stop at 60 active minutes, scoped invocation >900s, private storage >2 GiB, more than 12 live fixture sockets, or after two consecutive launches without diagnosis or closed check. No Expert escalation without coordinator consultation.
2. Timestamp correction: the subagent clock returned 12:34 UTC; the 12:38 UTC timestamp below is an inaccurate estimate. Authored `tests/net_listen.rs` first at public Rhai script/real-socket seam. Acceptance asserts OS-selected nonzero port, a separate `TcpStream` connection, script accept, and peer address independently matching the client socket. `RHAI_NET_WRONG_PEER_EXPECTATION` provides the later false-green control. Next launch is scoped RED compilation.
3. Timestamp correction: 12:39 UTC below is an inaccurate estimate. Scoped `cargo test --features net --test net_listen ... --no-run` passed compilation (14.17s Cargo compile; private runtime storage measurement exported to `logs/red-storage-kib.txt`). Rhai dynamic lookup means this is diagnostic compile only, not the intended RED; no socket fixture created. Next launch runs the test to observe the missing script registration.
4. Timestamp correction: 12:40 UTC below is an inaccurate estimate. Scoped targeted `cargo test --features net --test net_listen authorized_listener_accepts_an_independent_peer -- --nocapture` failed as expected at the public Rhai script call: `ErrorFunctionNotFound("listen ...")`; no socket was created because evaluation stopped before binding. Runtime source+Cargo private tree measured by scoped wrapper; exported value is `logs/red-runtime-storage-kib.txt` (KiB, end-of-launch size only; not a peak measurement). RED established.

Clock audit: coordinator observed 12:37:32 UTC on receipt of review; prior 12:38–12:40 estimates were in the future and are explicitly marked inaccurate.

## Clock and test-review correction
- Coordinator clock reported 12:37:32 UTC while subagent clock was 12:34 UTC. Earlier `12:38`, `12:39`, `12:40` launch labels were future estimates and are inaccurate; they have been marked as such above. Current observed subagent clock is 12:45:35 UTC.
- Coordinator's independent review findings applied: exact ephemeral grant in primary test; shared accept RAII reservation before OS accept; blocking mode normalized; deadline checked every loop; max handle docs cover listeners.
- Added contract tests for mismatched and zero-port denials, numeric/port validation, bind-failure quota release, timeout quota release, listener clone close, final-drop bind release, accepted-stream quota across engines, and sync clone close while an accept reservation is observed through quota pressure.

## Next launch
5. 12:45 UTC (observed): one scoped command compiles/runs `net_listen` and existing `net_connect` with `net,sync`, serial test execution to keep owned socket peak below 12, then runs the wrong-independent-peer assertion control and requires that control to fail. Log and end-of-launch private tree size exported before cleanup. No prior changes have been compiled.

### Launch 5 diagnosis
The combined scoped run failed during compilation, before any integration test executed. `#[export_module]` wrapped three `Result<_, Box<EvalAltResult>>` functions instead of returning the Rhai error directly. The current fix marks the listener's `local_addr` and `accept` and stream's `peer_addr` exports `#[rhai_fn(return_raw)]`. This was an implementation compile diagnosis, not a failed assertion. Next launch is the bounded combined test and wrong-peer control.
6. The previous scoped build exited 101 before tests: the Rhai attribute proc macro rejects two `rhai_fn` attributes on one export. Consolidated each function's export option and `return_raw` into one attribute. No behavior assertion ran; runtime storage end measurement was 215552 KiB. Next launch repeats the same combined test/control invocation.
7. Scoped build completed. Existing net_connect passed (4/4); listener tests were 6/7, with the clone-close contract script failing to parse because `shared` is a Rhai reserved word. Renamed it `same_state`; no product defect indicated. Compiled code also surfaced a `private_interfaces` warning on the handle-reservation helper, so narrowed it to module visibility. End runtime storage was 513304 KiB. Next launch repeats combined suite and the wrong-peer control.
8. At observed 12:50 UTC, scoped combined suite passed: `net_connect` 4/4 and `net_listen` 7/7; wrong-peer control failed as intended with actual peer `127.0.0.1:61346` versus deliberately false `127.0.0.1:1`. End private tree storage was 513148 KiB (not peak). Recorded OS/rustc, commands and bounded proof in `.scratch/tcp-listener/proof.md`. `git diff --check` clean. Next: send review-ready source/evidence to coordinator; await review within original 60-minute window. No push/merge.

### Coordinator review corrections
Coordinator's full source review found acceptance-fixture gaps (no production-source findings): timeout test's default quota 64 did not expose two leaked reservations; sync worker error/panic path could detach the join handle; requested explicit zero host deadline and negative script accept validation. Updated timeout test to `max_handles(2)`, added negative accept and zero accept_timeout validation, and restructured sync test to capture fallible probes/close/readiness then always close and join before assertions. Next launch: format and rerun combined tests plus wrong-peer control. Original stop time remains 13:34 UTC.
9. Post-review run with quota release tightened failed sync test's readiness condition: listener-bind probes could continually win the available second quota slot before waiting accept. Changed readiness probe to call accept on an owned listener clone with a 1ms bound; it distinguishes its timeout from `ResourceLimit` caused by the actual waiting accept reservation and allocates no temporary listener/socket. Per coordinator, final run will execute both `net` and `net,sync` suites plus wrong-peer control in one scoped invocation. This was an informative flaky fixture observation, not source failure.

### Sync readiness cause and fix
A sync readiness probe calling `accept(1)` temporarily consumes the second quota slot itself. The worker's first accept can then see `ResourceLimit` and exit, so no later probe can observe its wait reservation. Coordinator diagnosed this deterministic race. Worker now retries only `ResourceLimit` until a later accept can wait; all other errors terminate, while the main test closes the clone within its 2s bounded probe, then receives and joins before asserting. Next bounded launch tests this cause.
10. 12:57 UTC scoped targeted sync readiness test passed. Worker retries only temporary ResourceLimit, so the quota-pressure accept-clone probe sees the waiting worker; close and join complete promptly.
11. 12:58 UTC final one-invocation feature matrix passed: `net` connect 4/4/listener 6/6; `net,sync` connect 4/4/listener 7/7. Wrong-peer control failed as expected (actual peer `127.0.0.1:57329`, expected intentionally wrong `127.0.0.1:1`); private runtime end storage 861980 KiB, not peak. Full proof updated at `.scratch/tcp-listener/proof.md`, final outputs under `logs/accept-*`. No diff-check errors. Ready to commit as configured human author and report exact ref to coordinator.
