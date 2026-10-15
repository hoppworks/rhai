# Independent combined review - current-source X34 Linux base profile

Freshly loaded lllm rules:
- agent-skills HEAD: `d6024420e9a829e97e1857ae3a853d832348c83f`
- central `AGENTS.md` SHA-256: `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`
- central common rules SHA-256: `989dcc707a9e561c5f3fab7a8a973bef3fd39a452a06476f928cf32885fe8c77`
- project `AGENTS.md` SHA-256: `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`
- `mattpocock-code-review/SKILL.md` SHA-256: `a9b6618b3c16759ddedf3e36b774cd0d76ee3fd122bbf3978c2166acad9df645`
- `build-efficiently/SKILL.md` SHA-256: `58f676b48691ea2ed476f67f13ef68aedcdb73cd4cabf13925db1927c9ccaf04`

## Standards

PASS for the two named current-source Linux cases. Evidence binds to fork-main revision `eeb2d65184762361e3c50e4a19c454471415e49b`, Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default profile with `testing-environ,sys`. Cargo.toml, preserved Cargo.lock, Unix process source, and test-source hashes match the recorded input readback. The preserved lock hash is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

One scoped invocation ran both mutation controls and restored selectors with one Cargo job, an isolated source/Cargo home/target, and a 900-second bound. Two preflight snapshots ten seconds apart recorded no Cargo/rustc process, about 95 GiB available memory, and 628 GiB free disk. The runner exited 0, and its receipt records the runtime and exact owned empty session scope removed.

The post-run process snapshot at 11:39:35 recorded a foreign cargo-chef install and rustc, which were left untouched. A separate resource snapshot at 11:39:42 records load 5.59/5.66/5.32, 95 GiB available memory, 376 KiB free swap, and 625 GiB available disk. The foreign build may have overlapped the latter part of the Rhai invocation. This is a material capacity caveat, but all requested phases have their own expected Cargo results and logs, isolated outputs, and completed cleanup; it does not warrant relabeling the successful scoped invocation. Check current shared capacity before another heavy run.

## Spec / acceptance

PASS only for:
- `managed_run_deadline_reaps_group_under_fixture_reaper`
- `managed_run_output_limit_reaps_group_under_fixture_reaper`

For each selector, its private mutation inverts only the expected public result assertion. The RED logs reach the named `RED_CONTROL` after reporting boundary and cleanup observations; each Cargo result is 0 passed / 1 failed with exit 101. The nested fixture libtest success lines are not mistaken for the outer selected test result. Each restored GREEN exits 0 with 1 passed.

Deadline records timeout-report semantics, preserved stdout/stderr markers, incomplete captures, PIDFD exit for the exact leader/worker/leaf, group ESRCH, and host/reaper/sentinel alive at the API boundary, followed by exact fixture-reaper waits and sentinel reaping. Output-limit records typed OutputLimit, exact 4096-byte stdout prefix, honest incomplete captures, PIDFD/group closure, host/reaper/sentinel alive at the boundary, and exact worker/leaf/reaper cleanup. Both receipts show no watchdog cleanup through the boundary.

The plan and coordinator edits keep this as a partial X34 row under `testing-environ,sys`, and separately preserve the previously reviewed `testing-environ,sys,sync,unchecked` pair. Other X34 selectors, feature/profile combinations, platforms, Windows Job behavior, and broader A-F/Ticket03 requirements remain open.
