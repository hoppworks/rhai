# Linux X37 managed drop and unrelated sentinel proof: base profile (2026-10-15)

## Accepted scope

Combined independent review accepts this named X37 Linux base-profile slice only: lllm Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default profile, features `testing-environ,sys`. Review: `attempt-01/combined-review.md`. This adds one profile row alongside the previously accepted Linux `unchecked` row; it does not close other X37 platforms/features or Ticket03.

## Contract and bound inputs

Public integration test: `managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not`. It creates a managed leader/worker/leaf process group and an unrelated sentinel in its own process group. Dropping a nonfinal Child clone leaves the managed processes alive. Dropping the final clone stops all managed members while the sentinel remains alive; fixture teardown then kills/reaps the exact sentinel.

Revision: `d304d1ad325275873b04b096cb9f519634125e00`. Features: `testing-environ,sys`. Cargo used `--locked --test sys_process <test> -- --exact --nocapture --test-threads=1`; one scoped invocation ran RED and restored GREEN with Cargo jobs 1 and 300-second per-phase bounds. Rust/Cargo 1.77.2 on Linux x86_64/Bazzite 44.

Cargo.toml SHA-256: `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`; pinned lock SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; Unix source SHA-256: `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`; restored test SHA-256: `ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf`. The lock is preserved at `.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock`; its hash matches the run manifest and independent readback.

## Results and limitation

RED exited 101 at the deliberately inverted final sentinel-live assertion after the log recorded all managed PIDs absent and the sentinel alive. Restored GREEN exited 0: 1 passed. The log records nonfinal-drop liveness, final-drop ESRCH for leader/worker/leaf, sentinel liveness at the boundary, and explicit sentinel cleanup.

The original run-scoped runner and script both exited 1 because their post-run parser expected `sentinel_cleanup pid=... esrch=true` with no intervening field. The actual log includes `status=...` between PID and ESRCH. The saved corrected replay passed and independently confirmed exact leader, worker, leaf, managed PGID, sentinel PID and sentinel PGID absence. The runner status remains 1 and is not claimed as successful. No test or build was repeated for this parser defect.

Evidence, commands, environment, logs, source hashes, result replay and cleanup are under `attempt-01/`. The exact private runtime was absent; the owned empty session scope was removed after evidence export. Other X37 platform/profile rows and broader Ticket03 requirements remain open.
