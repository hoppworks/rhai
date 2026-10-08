# X36: managed scope setup failure

Status: partial. This accepts only the named Workhorse Linux x86_64 row with
Rust/Cargo 1.96.0 and features `testing-environ,sys`. It covers cleanup after
injected failure before and after successful `setpgid`. Later setup stages
(including `fchdir` failure), kernel-generated `setpgid` denial, other platforms,
feature combinations and MSRV rows remain open.

## Acceptance covered

The open X36 criterion requires a managed-scope setup failure to avoid silently
running an unmanaged child and to clean up the failed launch. Both tests register
the real `SysPackage` in a public Rhai `Engine`, then call public `run` and
`spawn` with a real `/bin/sh` child. The original
`managed_scope_setup_failure_never_executes_unmanaged_child` injects `EPERM`
before `setpgid`. The added
`managed_scope_partial_setup_failure_cleans_created_group` runs real
`setpgid(0, 0)`, records the child PID and process-group ID from inside the child,
confirms they match, then injects `EPERM`. Both cases assert the public setup
error, no marker file, exact child and process-group absence, and retirement of
the pending reservation. This is a backend/OS integration path; a UI layer does
not apply.

The post-`setpgid` case proves cleanup after process-group membership has been
created before a later setup error. Its `EPERM` is test-injected; it does not
claim a kernel-generated `setpgid` denial or exercise later `fchdir` failure.

## Run and result

- Attempt 02 ran `cargo test --locked --features testing-environ,sys --lib managed_scope_setup_failure_never_executes_unmanaged_child -- --nocapture --test-threads=1`. Baseline and restored source passed; the ignored-error mutation failed because the real shell completed. Exact PIDs 139026/139028 and their groups were independently absent. Inputs and raw evidence remain in `attempt-02/`.
- Attempt 03 ran that existing pre-`setpgid` test and `cargo test --locked --features testing-environ,sys --lib managed_scope_partial_setup_failure_cleans_created_group -- --nocapture --test-threads=1`. Baseline passed; a test-copy mutation disabling `setpgid` failed the expected `pgrp == pid` assertion (exit 101); restored partial-setup and existing pre-setup tests both passed.
- Restored GREEN records `run` PID 152783 and `spawn` PID 152785 with `after_setpgid=true`, `pid=ESRCH`, `group=ESRCH`, `reservation=retired`, and `marker=absent`. An independent Workhorse readback confirmed both exact PIDs and groups absent.
- Attempt 03 source base: `eb0aae40c994cba46cf5dbe367dd155e486fa764` with only `unix.rs` overlaid. Archive SHA-256 `63f603ee51d1adf3d71d6e9dad09628c27ecd46855573abf0baecb707dc18fe7`; `Cargo.toml` SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`; accepted `Cargo.lock` SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; tested Unix source SHA-256 `6066728c6033c794b249017c40b0280166b90b65f9f20fd79d2d118e97519f62`. Historical `.scratch` files and the foreign dirty fixture were excluded from the source archive.
- Canonical Workhorse runner SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`; attempt-03 script SHA-256 `98f0193764bba08b6be3115f7c23294bc561471770c7024e9a7b17236be2aba1` passed `bash -n`. Exported evidence archive SHA-256 `2f8bf07c745099fa9a08e7cd1fc5e1e7d37848426043b50bdeaa696e3f2e921f`.
- Attempt-03 manifest and raw logs/readback are in `attempt-03/`. The 600-second scoped invocation used two Cargo jobs and took 19.2 seconds end-to-end. Its private Cargo runtime and exact session scope were absent after evidence export; no Cargo/Rust process remained (`attempt-03/cleanup-readback.txt`). No compiled artifact remains reusable.

Attempt 01 stopped before assertions because a nested test helper lacked a
`RawFd` import. That harness-only failure and its output remain in
`attempt-01/`; it was corrected before attempt 02 and does not count as product
RED or acceptance.
