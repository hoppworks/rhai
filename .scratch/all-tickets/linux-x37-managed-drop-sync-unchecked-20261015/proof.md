# Linux X37 final-drop proof: `sync,unchecked` (2026-10-15)

## Bound execution

- Revision: `c94a7a5f830e9589bb79297cebb1756c3a57e39f` on fork `main`.
- Host: lllm, Linux x86_64, Bazzite 44; Rust/Cargo 1.77.2.
- Features: `testing-environ,sys,sync,unchecked`; profile: default.
- Test: `managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not` in `tests/sys_process.rs`.
- Cargo used `--locked --test sys_process <test> -- --exact --nocapture --test-threads=1`, one job, 300-second per-phase limits. The exact accepted lock was copied from the earlier X35 proof; its SHA-256 is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. Cargo.toml, Unix source, and test hashes match the previously accepted X37 source. Full inputs and commands are recorded in `attempt-01/inputs.json` and `attempt-01/run-x37-linux-sync-unchecked.sh`.

## Results

RED exited 101 at the deliberately inverted sentinel-live assertion after logging all managed leader/worker/leaf identities absent and the unrelated sentinel alive. Restored GREEN exited 0: 1 passed. The test records a nonfinal clone drop preserving all managed members, final clone drop stopping them, and sentinel survival until explicit cleanup. The corrected post-run replay independently verified exact leader, worker, leaf, managed process group, sentinel PID, and sentinel process group absence. Both the output and the exact helper (`attempt-01/postrun-readback-replay.py`, SHA-256 in `attempt-01/evidence/readback-helper.sha256`) are included.

The outer scoped command exited 1 after GREEN because its copied post-run parser required cleanup fields to be adjacent, while the real log includes an intervening status field. That parser was corrected for readback only; the Cargo test was not repeated. The status remains 1 and is not reported as a successful wrapper. The exact runtime and owned session scope are absent. See `attempt-01/evidence/runner-classification.txt`.

The pre-run snapshot recorded a concurrent unrelated Tauron Cargo build. This is preserved as a capacity deviation in the evidence; the Rhai invocation used one job and isolated source, Cargo home, and target. No subsequent heavy Rhai run should start until lllm is confirmed idle.

This proof is one X37 Linux `sync,unchecked` profile row only. It does not close X37, Ticket03, other platforms, or the release matrix. Independent combined review is recorded in `attempt-01/combined-review.md`.
