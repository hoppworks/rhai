# Linux managed OutputLimit preparation

This is a source-only preparation record for one bounded native Linux Rust 1.77.2 proof. No stage, SSH transfer, build, or native run has occurred. OutputLimit acceptance remains unproven pending the reviewed recipe run and independent collection.

## Frozen inputs

- Source revision: `53b01fa5df3f3a23bb55d4659c6207e5da86dc79`
- Source archive SHA-256: `e4f024d2a1147cba5466e6421691f4087e1e96447da137b63e46c295efbdb83e`
- `tests/sys_process.rs`: `024e774b76e21d46326d007249ca5db92eab161f88af3328bdd4c3b591a2ab03`
- Contract: `0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68`
- `Cargo.lock`: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`
- Base helper: `59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06`
- Accepted success helper: `83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0`
- Archive helper: `a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b`

## Proof scope and limits

The exact test is `managed_run_output_limit_reaps_group_under_fixture_reaper`. The six positive invocations are four feature rows (`testing-environ,sys`; plus `sync,metadata`; plus `f32_float`; plus `unchecked`) and the existing prompt-success and held-zombie base regressions. One post-cleanup wrong-outcome control must reach its named assertion only after exact fixture cleanup. Three toolchain setup commands make ten helper commands total.

The proof requires a typed OutputLimit result with a 4096-byte exact prefix, `timed_out=false`, honest incomplete stdout and stderr captures, exact live host/reaper/sentinel identities at the API boundary, exact leader/worker/leaf PIDFD start/parent/group bindings, normal prompt reaping, exact descendant wait receipts, and group absence. The collector also requires all seven original case-closure files before read-only validation. Collection compares canonical original closure bytes without writing or repairing them, then requires independent export hashes, fresh PID/start/group custody, and exact stage cleanup/readback.

The reviewed source changes preserve the output cap and typed result. They keep both capture-complete flags false, allow normal prompt reaping during OutputLimit handling, and wait for exact reaper receipts before the group-absence observation. The earlier temporary-string guard correction is included in this frozen source. Native behavior and foreign-reaper interaction remain unverified until the bounded run.

Prospective stage: `/root/rhai-linux-managed-output-limit-20261003-0a6dbb5d-106`.
Prospective private scope: `/root/.local/share/agent-builds/rhai/linux-managed-output-limit-20261003-0a6dbb5d-106`.
Both paths are unallocated and uncreated.

## Bounded command and resource contract

- Seven exact test invocations: one negative control, four OutputLimit feature rows, and two base regressions.
- Three private toolchain setup commands; ten helper commands total.
- Outer limit 600 seconds; scoped runner 585 seconds; helper deadline 540 seconds with 30 seconds reserved for export.
- Two Cargo jobs; at most 16 descendants; storage preemptive stop 1,572,864 KiB; storage and RSS hard caps 2,097,152 KiB.
- Rust toolchain `1.77.2-x86_64-unknown-linux-gnu`.

## Prepared recipe hashes

- `linux-managed-output-limit-proof.py`: `c938bbdd80d24664adf72dfc768ee480996387278e6c26b03aeb5e45e491e47c`
- `linux-managed-output-limit-stage.sh`: `dc72b1eca58e74d2cc21a918f5e486b23944db4e7b373ae56b07804af5855505`
- `linux-managed-output-limit-launch.sh`: `1e4e6fb326315583503be6e43ed4320800eabbd6b3cb1ace09e50baae19daac7`
- `collect-linux-managed-output-limit.py`: `c527f21a0ab6dcca56bc7f3055c7bf5b731cd4755e304c3a00bb2c183a792765`
