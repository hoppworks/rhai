# X36: managed scope setup failure

Status: partial. This accepts only named Workhorse Linux x86_64 rows with
features `testing-environ,sys`: the earlier before/after-`setpgid` proof at
Rust/Cargo 1.96.0 and the later `fchdir` proof at Rust/Cargo 1.97.1. Kernel-
generated `setpgid` denial, other platforms, feature combinations and MSRV rows
remain open.

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
claim a kernel-generated `setpgid` denial. The added
`managed_scope_fchdir_failure_cleans_created_group` test performs real
`setpgid(0, 0)`, records PID/PGRP, closes only the child's inherited cwd fd,
then reaches the real `fchdir` call and receives `EBADF`. Through public Rhai
`run` and `spawn`, it asserts that exact OS error, no marker execution, exact
child and group absence, and reservation retirement. It tests one later setup
stage without claiming the remaining stages or kernel-generated denial.

## Run and result

- Attempt 02 ran `cargo test --locked --features testing-environ,sys --lib managed_scope_setup_failure_never_executes_unmanaged_child -- --nocapture --test-threads=1`. Baseline and restored source passed; the ignored-error mutation failed because the real shell completed. Exact PIDs 139026/139028 and their groups were independently absent. Inputs and raw evidence remain in `attempt-02/`.
- Attempt 03 ran that existing pre-`setpgid` test and `cargo test --locked --features testing-environ,sys --lib managed_scope_partial_setup_failure_cleans_created_group -- --nocapture --test-threads=1`. Baseline passed; a test-copy mutation disabling `setpgid` failed the expected `pgrp == pid` assertion (exit 101); restored partial-setup and existing pre-setup tests both passed.
- Restored GREEN records `run` PID 152783 and `spawn` PID 152785 with `after_setpgid=true`, `pid=ESRCH`, `group=ESRCH`, `reservation=retired`, and `marker=absent`. An independent Workhorse readback confirmed both exact PIDs and groups absent.
- Attempt 03 source base: `eb0aae40c994cba46cf5dbe367dd155e486fa764` with only `unix.rs` overlaid. Archive SHA-256 `63f603ee51d1adf3d71d6e9dad09628c27ecd46855573abf0baecb707dc18fe7`; `Cargo.toml` SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`; accepted `Cargo.lock` SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; tested Unix source SHA-256 `6066728c6033c794b249017c40b0280166b90b65f9f20fd79d2d118e97519f62`. Historical `.scratch` files and the foreign dirty fixture were excluded from the source archive.
- Canonical Workhorse runner SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`; attempt-03 script SHA-256 `98f0193764bba08b6be3115f7c23294bc561471770c7024e9a7b17236be2aba1` passed `bash -n`. Exported evidence archive SHA-256 `2f8bf07c745099fa9a08e7cd1fc5e1e7d37848426043b50bdeaa696e3f2e921f`.
- Attempt-03 manifest and raw logs/readback are in `attempt-03/`. The 600-second scoped invocation used two Cargo jobs and took 19.2 seconds end-to-end. Its private Cargo runtime and exact session scope were absent after evidence export; no Cargo/Rust process remained (`attempt-03/cleanup-readback.txt`). No compiled artifact remains reusable.
- Attempt 04 (`attempt-04/`) used base `397761661b87e8ab452bb752af16fdc7ca155c85`, Rust/Cargo 1.97.1, the same manifest/lock hashes above, source SHA-256 `a87b364155c2792945c881eff755aec47b73933503bff75e7973c35652349131`, archive SHA-256 `bbe873bae22edbc33c73472a99b16d6e63e5c8bffa2f13d46a55e03404ff9d65`, and the canonical runner. One 600-second scoped invocation (two Cargo jobs) passed baseline, the expected-red control (exit 101 because disabling the child fd close allowed marker execution), restored fchdir, and both existing before/after-`setpgid` tests. Exact PIDs 162808/162810, 162827/162829, and 162846/162848 and their groups were independently absent; each reservation retired and marker remained absent on restored runs. The compile took 15.02 seconds; test bodies reported 0 seconds.
- Attempt 05 (`attempt-05/`) rechecked the fchdir test after removing two redundant `unsafe` wrappers around `libc::close`; no behavior or assertion changed. At the same base, with source SHA-256 `6e777d774f0fc9a7d493abe192dbbf1a703db057f3b996df0fa9a011ca93da92` and archive SHA-256 `5b00d21a5994533983e43315915340948ce4143c5fd402f1dc991ae02b8f268c`, the targeted test passed on Rust/Cargo 1.97.1. Reuse attempt-04's mutation evidence because the changed lines only removed redundant safety syntax and the mutation/test assertion were unchanged. Exact PIDs 167113/167115 and groups were independently absent. Compile took 14.76 seconds; test body reported 0 seconds. The build log has nine remaining warnings from existing code.
- The only later source edit corrects a test-helper comment from “identity pipe” to “identity record file”; it changes no executable code, assertions or test inputs, so attempt-05 remains applicable.
- Both newer attempts used `Cargo.toml` SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`, accepted lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, and runner SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`. Both exported evidence before cleanup; the attempt logs record private runtime absence and no remaining Cargo/Rust process. A fresh exact-path Workhorse readback on 2026-10-08 returned `exists=False, symlink=False` for session scopes `/home/workhorse/.local/share/agent-builds/rhai/x36-fchdir-20261008-4ef8a19b` and `/home/workhorse/.local/share/agent-builds/rhai/x36-fchdir-check-20261008-8a9f32d1`. No compiled artifact is reusable.
- Preparation history for attempt 04: an archive-prep helper first failed before build due to an unsupported `Popen(check=False)` argument; the initial source archive omitted the repository's untracked lockfile, which was recovered from accepted attempt-03 inputs and hash-checked; direct runner execution was denied by its file mode, so the same canonical runner was invoked with `python3`. None reached a product assertion or launched a build. Attempt 05 was the narrow source-affected recheck, not another full batch.

Attempt 01 stopped before assertions because a nested test helper lacked a
`RawFd` import. That harness-only failure and its output remain in
`attempt-01/`; it was corrected before attempt 02 and does not count as product
RED or acceptance.
