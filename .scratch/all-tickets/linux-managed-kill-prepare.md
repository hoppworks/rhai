# Linux managed `Child.kill()` acceptance package

This is a pre-execution source and recipe record for the bounded Linux 1.77.2 proof. The immutable source revision is `d70e2c409c82b09ab205e2fc12b08a7c6b94acec`; stage input is generated from that revision, while local scratch-only recipe commits may follow it. The test source SHA-256 is `9c6ca59e753ebae483a3f2bed6cf5ffd076e80a7c6ef1be76dc87e49c5ea00da`, source archive SHA-256 is `4510841b868ad57cbff61129b2f6244c21b3915588d36caf760a54d653e9e43d`, lock SHA-256 is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, and contract source SHA-256 is `1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41`.

The exact new test is `managed_child_kill_reports_group_closed_under_fixture_reaper`, selected in four feature rows: `testing-environ,sys`; `testing-environ,sys,sync,metadata`; `testing-environ,sys,f32_float`; and `testing-environ,sys,unchecked`. The two sensitivity overlays are `require-success-control` and `require-sentinel-absent-control`; each inverts one post-cleanup assertion and must exit 101 at its exact named assertion after fixture cleanup. The same base-feature build also runs the accepted native96 `managed_run_succeeds_after_fixture_reaper_reaps_descendants` and `managed_run_reports_while_fixture_reaper_holds_stopped_zombies` cases. Total: eight exact test invocations (six positive, two controls) plus three toolchain setup commands.

The new receipt parser binds early live PID/start/group identities, exactly three acquired PIDFDs and parent/group relationships, the API's successful call outcome separately from the returned unsuccessful child report, complete captured streams, host/reaper liveness at return, exact descendant wait receipts without requiring exit status zero, the live unrelated sentinel, and exact host/reaper/sentinel/group cleanup. The collector additionally requires each case-specific closure artifact and independently reads back exact process identities and groups before export; cleanup is permitted only after local exported file hashes match a fresh remote inventory.

The prospective stage is `/root/rhai-linux-managed-kill-20261003-a17f40a7-97`; the private build scope is `/root/.local/share/agent-builds/rhai/linux-managed-kill-20261003-a17f40a7-97`. Native97 is unallocated. Planned bounds are 600 seconds outer, 585 seconds scoped runner, 540 seconds helper with a 30 second export reserve, two Cargo jobs, 16 descendants, 1.5 GiB storage preemptive stop, and 2 GiB RSS/storage hard stops.

Recipe hashes:

- `linux-managed-kill-proof.py`: `929e0509ba74c41fc294f03d99e6a8e157cc5a63a8fbcfc00b45d43b7f74f13b`
- `linux-managed-kill-stage.sh`: `6fe4319a1bd3b57c1e47a23cc97b837843566da6a867a40e88582ba7d2a52554`
- `linux-managed-kill-launch.sh`: `d7f90e31bb593171a5b7739463495f104497ecad65b17388c8bf4c06c5731be5`
- `collect-linux-managed-kill.py`: `4941c6757d82d42b4b950387d563773940ca83179c556df2953a311ac81bed8c`

The source-only checks are Python AST parsing under Python 3.12, Bash syntax validation, and synthetic exact-format receipt and negative-mutation checks. No Rust build, Cargo test, SSH staging, native run, wrong-control execution, or restored-green run has occurred. This package does not establish native acceptance; the named controls still need to prove sensitivity in the integrated run, followed by independent collector readback. `no_float` and `no_index` compatibility is not claimed because the managed test and its helpers are gated off for those configurations.
