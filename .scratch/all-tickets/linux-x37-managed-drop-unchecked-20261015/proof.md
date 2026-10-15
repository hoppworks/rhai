# Linux X37 managed drop and unrelated sentinel proof: unchecked (2026-10-15)

## Accepted scope

Combined independent review accepts this named X37 row only: lllm Linux x86_64,
Bazzite 44, Rust/Cargo 1.77.2, features
`testing-environ,sys,unchecked`, source revision
`68a6a83af3cced6a0215fa815efc7a79b348873b`. Standards and Spec/acceptance are
recorded in `combined-review.md`. This does not close other X37 feature,
platform, toolchain, or Ticket03 rows.

## Contract and bound inputs

The public Engine test
`managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not` creates
a managed leader/worker/leaf group and a separate sentinel process group. It
checks `sentinel_pgid == sentinel_pid` and that the managed group differs.
Dropping one nonfinal Rhai Child clone leaves all three managed members live;
a bounded wait remains pending. Dropping the final clone must stop the managed
group. The test independently checks exact leader/worker/leaf absence while
the sentinel remains live, then explicitly kills/reaps the sentinel and checks
its exact PID is absent.

Restored test-source SHA-256: `ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf`.
Unix product source SHA-256: `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`.
Pinned `Cargo.lock` SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

## Results and cleanup

Attempt 01 used one scoped build, Cargo jobs 1, the hash-pinned lock, and the
exact feature profile. The intentional wrong-expectation control inverted only
the sentinel-live assertion and exited 101 at that assertion after the log
showed all managed PIDs absent and the unrelated sentinel live. Panic cleanup
reaped the exact sentinel. Restored GREEN passed 1/1: nonfinal drop preserved
the group, final drop yielded exact ESRCH for leader/worker/leaf, the sentinel
remained live at that boundary, then its explicit cleanup reaped it. Cargo
statuses were RED 101 and GREEN 0; the outer runner exited 0. Environment,
commands, logs, source hashes, capacity sample, and cleanup are in `attempt-01/`.

The exact session scope and private runtime are absent; no compiled build
remains. No claim extends beyond this named Linux unchecked row.
