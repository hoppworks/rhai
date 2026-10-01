# Linux production process proof preparation

Status: source-only preparation. No workhorse stage was created, no Rust toolchain was installed, and no build or native test ran.

## Frozen inputs and accepted evidence

- Production workspace candidate: `/Users/hoppworks/projects/rhai-process-unix-run`, commit `ccaa5ab66771e6dc14b9b193612ef3716e429f78` (`task/process-unix-run`). The complete `git archive --format=tar` SHA256 is `030bc9630b1348ff1dd540985e3032d2840c4dfb3a462499254758a8d6c8ad91`.
- Candidate test/source hashes and accepted macOS control evidence are retained by root at evidence-only commit `4a8d4e5cfa4e76ae62ebfcd1c4a77e3ee6207dd2`; this does not establish Linux behavior. The real public tests are `tests/sys_process.rs`, including `direct_spawn_kill_on_drop_false_preserves_child_and_capture` and `managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit`.
- Reusable Linux staging/custody patterns: `.scratch/linux-optional-msrv-proof/stage-remote.sh`, `remote-launch.sh`, and `run-proof.py`; native Linux process identity and launcher precedent: `.scratch/all-tickets/native-linux-stage-input-readback.json` and `native-linux-io-proof-review.md`. Linux stage inputs previously included configured `run_scoped.py`, `agentskills/__init__.py`, and `pyguard.py`.
- Accepted baseline lock: `.scratch/core-msrv-compatible-resolution/Cargo.lock`, SHA256 `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa`. It already contains `libc 0.2.189`; adding only `libc` to the locked `rhai` package dependency list yields private edge-only lock SHA256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The staged baseline remains unchanged by the driver.
- Root read-only host inspection found Linux x86_64 direct Rust/Cargo/rustdoc `1.93.0` at `/root/.rustup/toolchains/1.93.0-x86_64-unknown-linux-gnu/bin/`; `1.77.2` was absent in that inspection. This is a development behavior run only and does not satisfy the optional MSRV gate. The driver requires these direct binaries and performs no rustup/toolchain install or shared-home mutation.

## Prepared package and limitations

The staging script pins and hashes the complete candidate archive and accepted lock before staging and copies the driver, launcher, scoped runner and its two helper files. The launcher applies a 600-second outer timeout. The driver prepares a private lock with only the `rhai -> libc` edge, checks its exact SHA, uses direct Rust/Cargo/rustdoc 1.93 paths, two Cargo jobs, and private source/lock/CARGO_HOME/RUSTUP_HOME/target/tmp paths under `AGENT_RUNTIME_DIR`. It applies a 540-second aggregate Cargo deadline and samples `du -sk` after each completed command, stopping at 1,572,864 KiB under the 2 GiB policy.

The known-broken control mutates only `if !state.terminal && state.kill_on_drop {` to `if !state.terminal {`, runs the direct public false-policy test, requires exit 101 at its named survival assertion and direct fixture cleanup receipt, and restores/verifies the original source bytes in `finally`. This control is grounded in `.scratch/process-unix-run/direct-drop-false.py` and `tests/sys_process.rs`; no file-handle control is reused. It does not yet port the existing harness's full temporary-root validation and start-tick identity checks.

The restored package runs exact direct and managed false-policy tests, the Unix owner-unit filter `packages::sys::process::unix::tests::`, and the full `sys_process` integration suite serially with `testing-environ,sys`. It records logs/statuses outside the private runtime and checks summary strings, source restoration, and direct/managed fixture receipts. Existing fixture guards own cleanup. Critical limitation: the draft has not yet ported the established `/proc` PID/start-tick/PPID/PGID sampling and exact runner-group absence readback. Detached-group and process-identity cleanup is therefore not independently fail-closed by this draft, especially on interruption. Do not use it to launch until that custody/readback path is added and reviewed.

## Files prepared

- `prepare-linux-process-stage.sh`: stages only the pinned archive and declared inputs when explicitly run later; it requires the exact candidate ref and archive hash.
- `remote-launch.sh`: launches the staged driver under the copied scoped runner, preserves raw outer evidence, and performs exact PID/start-tick, process-group and runtime absence readback after runner cleanup.
- `linux-process-proof.py`: private-runtime driver, lock edge-only transformation, source manifest, resource sampler, process custody ledger, intended wrong-control/restored sequence, and development-toolchain direct-path checks.

Known gaps before launch: the driver does not sample storage/process identities continuously during Cargo, has no `/proc` start-tick/PPID/PGID custody ledger, no fail-closed check for detached groups or unknown identities, and its launcher records no runner identity or robust post-cleanup group readback. There is no direct 1.93 tool version assertion. The stage helper refuses existing stage paths but the transfer sequence and launcher lack full interrupted-transfer/cleanup identity handling. These files are a source inventory handoff, not a launchable proof package.

The files passed shell/Python syntax checks only. No staging, SSH, build, or native test was run. The live Linux compiler observation does not make this package an accepted proof; a fresh implementation pass must close the listed gaps before launch.
