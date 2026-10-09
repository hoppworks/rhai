# X34 native Linux managed-run reaper acceptance

**Package:** `managed_run_deadline_reaps_group_under_fixture_reaper` and `managed_run_output_limit_reaps_group_under_fixture_reaper`.

**Result:** Both selectors have meaningful assertion REDs against deliberate wrong expectations and restored-source GREENs on native Workhorse Linux x86_64. This evidence covers only these two selectors under Rust/Cargo 1.77.2, `testing-environ,sys` plus default features, the checked test profile. It does not close other X34 selectors, Darwin/Windows variants, interruption/custody work, or the full A–F plan.

## Bound inputs and execution

The run used source archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644`, already matched to Git tree `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`; accepted lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; baseline `tests/sys_process.rs` SHA-256 `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`; native Linux x86_64; Rust 1.77.2 / Cargo 1.77.2; features `testing-environ,sys` with defaults; and the default checked development/test profile. The archive and lock were rehashed before extraction. The exact baseline source was restored and rehashed before GREEN.

One `run_scoped.py` invocation covered RED build, both RED controls, source restoration, GREEN build and both GREEN selectors. Boundary: 600 seconds, Cargo jobs 2. Build source copy, Cargo home, target and transient runtime were inside `AGENT_RUNTIME_DIR`; test outputs and diagnostics were exported to the attempt directory outside that runtime. The exact owned session scope `/root/.local/share/agent-builds/rhai/x34-reaper-20261009T1830Z-01` had the same device/inode/owner/mode before and after, was empty, and was retired. Runner status 0; elapsed 25 seconds. No Cargo or rustc process remained in the preflight; the contemporaneous capacity sample is in `attempt01/preflight.txt`.

## Assertion controls and independent observations

- Deadline RED flips only the expected timeout-report boolean. It exits 101 at `RED control: deadline report unexpectedly present` after fixture cleanup. Restored GREEN exits 0 with exactly one test passed. The host reports a timeout report map, preserves both partial marker streams and marks both captures incomplete. Independent PIDFD polling, PID/start-time checks, negative process-group probe with `ESRCH`, exact fixture-reaper waits for worker and leaf, live host/reaper/unrelated sentinel boundary, post-boundary sentinel reap, and absence of watchdog cleanup are recorded in `green-deadline.log`.
- OutputLimit RED flips only the expected OutputLimit boolean. It exits 101 at `RED control: OutputLimit unexpectedly present` after fixture cleanup. Restored GREEN exits 0 with exactly one test passed. The host reports typed OutputLimit, preserves exactly the 4096-byte stdout prefix, marks both open captures incomplete and does not report timeout. Independent PIDFD/PID identity checks, process-group `ESRCH`, exact worker/leaf reaper waits, live host/reaper/sentinel boundary, sentinel reap and no watchdog cleanup are recorded in `green-output-limit.log`.

The resulting fixture logs independently show exact member cleanup and retained custody at API return. Original sources and accepted proof inputs remain unchanged. This package has not yet received the required combined independent review; retain it as pending review until that review accepts the binding and observations.
