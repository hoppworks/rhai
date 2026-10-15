# Linux X35 DirectChild versus Managed proof: unchecked (2026-10-15)

## Accepted scope

Combined independent review accepts this named X35 feature row only: lllm Linux
x86_64, Bazzite 44, Rust/Cargo 1.77.2, features
`testing-environ,sys,unchecked`, source revision
`ec46e23d9a25902723cbd27b8ac651a536c34b7b`. Standards and Spec/acceptance
are recorded in `combined-review.md`. This adds the unchecked feature profile
to the separately accepted base-profile row; it closes no other feature,
toolchain, platform, or Ticket03 requirement.

## Contract and bound inputs

The tests exercise the public Rhai `run` API with real Linux children and a
pipe-closed worker fixture.
`direct_run_returns_with_pipe_closed_worker_live_control` proves DirectChild
returns while the exact worker and leaf remain live. Its paired Managed test,
`managed_run_closes_pipe_closed_worker_before_return`, proves the managed scope
closes before return. Both acquire PIDFDs for the exact leader, worker, and leaf.

HEAD: `ec46e23d9a25902723cbd27b8ac651a536c34b7b`. Restored test-source
SHA-256: `ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf`.
Unix product source SHA-256: `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`.
Pinned `Cargo.lock` SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

## Results and cleanup

Attempt 01 stopped before Cargo because environment hash collection ran before
changing to the owned source copy. No selector ran. Attempt 02 used one scoped
build, Cargo jobs 1, the hash-pinned lock and exact feature set. The intentional
wrong-expectation control exited 101 at the expected live-at-return assertion.
Restored DirectChild passed 1/1 and Managed passed 1/1. Both emitted three exact
PIDFD acquisitions and exact worker/leaf/leader ESRCH cleanup readbacks. Cargo
statuses were 101, 0, and 0; outer runner status was 0. Full command, environment,
logs, source hashes, capacity sample, classifications, and cleanup record are
in `attempt-01/` and `attempt-02/`.

The scoped runtime and exact session scope are absent; no compiled build remains.
No claim extends to other feature profiles, platforms, MSRVs, or Ticket03 rows.
