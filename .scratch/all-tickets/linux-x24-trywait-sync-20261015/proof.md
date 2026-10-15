# Linux X24 try_wait sync-feature proof (2026-10-15)

## Scope

This adds checked and unchecked sync-feature rows for the existing public Engine selector direct_spawn_try_wait_returns_unit_until_child_exits on lllm Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, integrated revision 731c7c61e884ca7e59849f25ec6e8fee81f12f75. Profiles: testing-environ,sys,sync and testing-environ,sys,sync,unchecked. Exact bindings: attempt-01/revision-binding.md.

The accepted Linux base-profile evidence is reused; no base rerun occurred. This does not extend acceptance to other OS/MSRV rows or close X24/Ticket03 as a whole.

## Results

One scoped one-job invocation ran an intended wrong-expectation RED and restored GREEN in each profile. The RED changed the expected terminal natural exit code from 0 to 1 and exited Cargo 101 at the targeted assertion. Both restored tests passed 1/1. GREEN output proves the real child is held alive while pending try_wait returns unit, observes terminal try_wait before wait, returns cached wait with code 0, and confirms exact child ESRCH. Timings: checked sync RED/GREEN 40.509/1.816s; unchecked sync 18.599/1.779s. Outer scoped runner status 0.

The runner's private runtime and exact owned session scope were removed after exporting the logs and hashes. Full environment, command receipts, capacity, source hashes and outputs are retained in attempt-01/.

## Review

Combined independent review passes the two named sync rows only; see attempt-01/combined-review.md. The named rows do not close other feature, platform, MSRV or Ticket03 requirements.
