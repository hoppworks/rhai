# Linux Child.wait decoded-expansion proof

Status: accepted for this selector on the recorded native Linux 1.77.2 configuration after combined independent review; see `combined-review.md`.

## Bound inputs and command

- Source: fork main revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`; accepted source archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644`. The prior X35 archive-to-Git-tree readback binds all 9,199 files to this revision.
- `tests/sys_process.rs` baseline/restored SHA-256: `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`.
- Lock SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Features `testing-environ,sys`; Linux x86_64; Rust/Cargo 1.77.2. The exact selector was listed from both built executables before execution.
- Attempt01 used one `run_scoped.py` invocation, timeout 600 seconds, `CARGO_BUILD_JOBS=2`, `CARGO_HOME` and `CARGO_TARGET_DIR` under `AGENT_RUNTIME_DIR`. Its restored-source GREEN is valid. Its first RED, an unconditional inserted panic, is invalid as a behavioral control; see `attempt01/post-review-assessment.md`.
- Attempt02 used one scoped invocation to build and run a corrected RED. It flipped only the expected first raw byte in the no-primary case. The test failed at the actual `wait must retain exact raw bytes` assertion with status 101; then the exact baseline test source was restored and hash-checked. The valid attempt01 GREEN is reused because its source, lock, features, toolchain, target and environment are unchanged. This avoided an unnecessary repeat build/test.

Commands, feature arguments, test selector, tool versions, resource inputs, and results are retained in each attempt's payload, command, JSON build output, list and test logs.

## Corrected RED and restored GREEN

Attempt02's deliberate wrong expected-byte control caused the named public test to fail with status 101 at `wait must retain exact raw bytes`; it was not a forced panic or product RED. It restored the baseline test SHA `86f1142f…` before scope cleanup.

Attempt01's restored-source GREEN ran exactly one test: `1 passed; 0 failed`. Both cases used the public Rhai Engine, registered `sys` package, real test-executable child and Linux process API. The no-primary case had 134 raw bytes—below the Engine string limit—whose lossy UTF-8 decoding exceeded that limit. It preserved typed `Process/OutputLimit`, exact bytes, exit code 0, complete stdout/stderr, no signal, no timeout, cloned/repeated stable wait snapshots, the independently read child-written record and host-confirmed ESRCH. The already-committed-primary case retained its stdout OutputLimit cause instead of replacing it with decoded-expansion failure; it also preserved the exact 237-byte raw prefix, empty stderr, no timeout, stable cloned/repeated snapshots, host record and ESRCH.

The false-panic RED is preserved but excluded. Attempt02 is the acceptance RED; attempt01 is the unchanged-source GREEN. This is one criterion using compatible frozen inputs, not a complete Unix or A–F package.

## Custody and limits

Attempt01 scope `/root/.local/share/agent-builds/rhai/child-wait-expansion-20261009T1644Z`, identity `(device 58, inode 119660934, uid 0, gid 0, mode 0700)`, was empty and retired with exact `rmdir`. Attempt02 scope `/root/.local/share/agent-builds/rhai/child-wait-expansion-red-20261009T1648Z`, identity and cleanup receipt are in `attempt02/`; the scope was empty and retired. Both runners exited 0. Each source copy, target and Cargo home was inside its private runtime; no foreign process or resource was signaled, restarted, or cleaned. Workhorse X35 evidence remains separate and was not rerun.

Preflight capacity and compiler-process samples are in each attempt's `preflight.txt`. The run-specific cap was 600 seconds per runner and two Cargo build jobs; these are this invocation's limits, not standing machine policy.

This result closes this selector only for the recorded Linux 1.77.2 checked/default configuration. Darwin's corresponding behavior, remaining Unix process-closure cases, Windows, TCP, integration, release and all A–F criteria remain open.
