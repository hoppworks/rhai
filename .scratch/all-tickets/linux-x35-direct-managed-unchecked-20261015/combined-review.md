# Combined independent review - Linux X35 unchecked

## Standards

PASS. The two selectors use the public Rhai Engine and real Linux processes. Their PIDFD observer binds exact PID/start-time identities before the public call returns; the DirectChild control observes leader exit while worker and leaf remain live, and Managed observes all three exact PIDFDs exited before return. Both paths independently record exact fixture cleanup. The bounded tests use the established sys_process layout and meaningful assertion control.

## Spec and acceptance

ACCEPT only the named Linux X35 row under `testing-environ,sys,unchecked`: `direct_run_returns_with_pipe_closed_worker_live_control` as the DirectChild distinction/sensitivity control, paired with `managed_run_closes_pipe_closed_worker_before_return` as the Managed behavior.

Attempt 01 stopped before Cargo because it collected source hashes before changing into the owned source copy; no selector ran. Attempt 02 records HEAD `ec46e23d9a25902723cbd27b8ac651a536c34b7b`, Linux lllm x86_64/Bazzite 44, Rust/Cargo 1.77.2, features `testing-environ,sys,unchecked`, default profile, and matching source identities: test `ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf`, Unix product `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`, lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The red mutant changes only the DirectChild PIDFD expectation, has its own test-source hash, and fails with Cargo 101 at the intended live-at-return assertion after exact PIDFD acquisition and cleanup. Restored DirectChild and Managed each pass 1/1; their logs show three exact PIDFD acquisitions and worker/leaf/leader ESRCH cleanup. Cargo statuses are 101, 0, and 0; outer runner status is 0 and the owned session scope is absent.

This is not broad X35 or Ticket03 closure. It covers no other feature, OS, or toolchain, and does not certify no-float behavior. The separate no-float attempt history correctly makes no acceptance claim: the relevant escaped-capture selectors were cfg-excluded/zero-selected and no RED or GREEN occurred. No proof.md was present at review time; this file records the combined review and exact scope.

## Binding rules

Agent-skills HEAD `d6024420e9a829e97e1857ae3a853d832348c83f`; agent-skills AGENTS SHA-256 `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`; project AGENTS SHA-256 `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`.
