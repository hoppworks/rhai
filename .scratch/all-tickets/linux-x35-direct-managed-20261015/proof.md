# Linux X35 DirectChild versus Managed proof (2026-10-15)

## Accepted scope

Combined independent review accepts this named Linux X35 row only: lllm Linux
x86_64, Rust/Cargo 1.77.2, features `testing-environ,sys`, source revision
`b489b05e01824f419398f23eaea805546a09736e`. It closes no other X35 path,
feature profile, toolchain, platform, or Ticket03 requirement. The independent
decision is recorded in `combined-review.md`.

## Contract and bound inputs

The public Rhai `run` API is exercised with real Linux children and a pipe-closed
worker fixture. `direct_run_returns_with_pipe_closed_worker_live_control` proves
DirectChild returns while its worker remains live. Its paired Managed case,
`managed_run_closes_pipe_closed_worker_before_return`, proves the managed scope
closes before returning. Both tests acquire PIDFDs for the exact leader, worker,
and leaf so liveness is observed independently of timing or PID reuse.

Restored test-source SHA-256: `ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf`.
Unix product source SHA-256: `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`.
Pinned `Cargo.lock` SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

## Results and limits

Attempt 01 stopped before Cargo because this library checkout has no root
`Cargo.lock`; no test ran. Attempt 02 reused the already accepted hash-pinned
Linux lock and used one scoped build, Cargo jobs 1, and explicit Rustup PATH.
The wrong-expectation DirectChild control exited 101 at the named assertion
that the managed member remained live at API return. The restored DirectChild
test passed 1/1 and recorded the leader exited while worker and leaf remained
live at API return; teardown recorded exact worker, leaf, and leader ESRCH.
The Managed test passed 1/1 and observed all three PIDFDs exited before return,
then recorded exact fixture cleanup. Cargo statuses were RED 101, DirectChild
GREEN 0, and Managed GREEN 0. Exact logs, status files, script, source snapshot,
capacity sample, and cleanup receipts remain in `attempt-02/`.

The outer `run_scoped.py` invocation returned 1 after the Cargo commands because
a post-test Python checker incorrectly required literal `live`/`exited` words
in logs. Its result is a checker-format failure; the separate Cargo results
and test assertions/readbacks are the accepted evidence. The runner is not
claimed successful. The checker stopped before environment export, so no
`environment.txt` was produced; the invocation pinned Cargo/Rustup to 1.77.2,
and the bounded host scope is lllm Linux x86_64. The owned runtime and exact
session scope were confirmed absent; no compiled build remains.
