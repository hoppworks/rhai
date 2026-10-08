# X36: managed scope setup failure

Status: partial. This accepts only named Workhorse Linux x86_64 rows with
features `testing-environ,sys`: the earlier before/after-`setpgid` proof at
Rust/Cargo 1.96.0, and the later `fchdir` and kernel-generated `setpgid`
denial proofs at Rust/Cargo 1.97.1. Attempt 08 adds a successful six-test
recheck at Rust/Cargo 1.77.2. Attempt 09 independently demonstrates the
kernel-denial assertion's sensitivity and restored GREEN on Rust/Cargo 1.77.2;
independent combined review accepted this named 1.77.2 row. Other platforms, feature combinations
and MSRV rows remain open.

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
child and group absence, and reservation retirement.

The added `managed_scope_kernel_setpgid_denial_cleans_created_group` test
reaches a real Linux kernel `setpgid(0, 0)` denial. Its test-only child hook
calls `setsid()`, records PID/PGRP/SID, and then lets normal setup call
`setpgid`; because the child is now a session leader, Linux returns `EPERM`.
Public `run` and `spawn` assert the exact `PermissionDenied`/`EPERM` error,
PID=PGRP=SID, no marker execution, exact child and process-group absence, and
reservation retirement. A mutation disabling the hook made the public test
fail because the command ran, so the assertions detect the intended path.
This establishes only the named Workhorse Linux row; other platforms,
features and MSRVs remain open.

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

## Kernel denial and affected setup recheck

- Attempt 06 (`attempt-06/`) covered the kernel-generated denial on Workhorse Linux x86_64, Rust/Cargo 1.97.1, features `testing-environ,sys`. Its source archive is based on `397761661b87e8ab452bb752af16fdc7ca155c85`, replacing only `unix.rs`; archive SHA-256 is `ad869e2f338e432a246fec6ce13d102c6b49a5a8c2d062306e98e1eb88601215`, source SHA-256 `55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713`, and runner SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`. Its one bounded 600-second invocation (two Cargo jobs) first disabled the test-only denial hook: the public test failed as expected (exit 101) because the shell ran. Restored-source GREEN passed; exact run/spawn PIDs 176035/176037 and groups were independently absent. `inputs.json`, source archive, mutation/restored hashes, logs, environment, statuses and readback are retained. The private runtime and exact session scope were removed after export; no compiled output is reusable.
- Attempt 07 (`attempt-07/`) rechecked the six tests affected by the shared setup-failure helper/tuple change using the identical source archive and dependency hashes from attempt 06. The runner script SHA-256 is `9bc8991ae547c7c0b2b6d5e6ea321bebb9c5ed8975da335e3a890d46860cc0ba`; its 600-second scoped invocation used two Cargo jobs and finished in 17 seconds. `cargo test --locked --features testing-environ,sys --lib managed_scope_ -- --nocapture --test-threads=1` passed all 6 tests (24 filtered). Independent readback verified all eight exact run/spawn IDs across BeforeSetpgid, AfterSetpgid, Fchdir and KernelSetpgidDenial absent as both PID and process group. It reuses `../attempt-06/source-input.tar.gz` (SHA-256 `ad869e2f338e432a246fec6ce13d102c6b49a5a8c2d062306e98e1eb88601215`); each of six exported raw evidence files matched its remote SHA-256. The runtime and owned scope were absent after export, and no Cargo/Rust process remained. The remote hash transcript, extracted raw evidence, transport logs and cleanup readback are retained; byte-identical transport archives were removed. No compiled output is reusable.

- Attempt 08 (`attempt-08/`) adds the Linux x86_64 Rust/Cargo 1.77.2 row using the exact six `managed_scope_` tests, features `testing-environ,sys`, and the same immutable source archive as attempt 06/07. `Cargo.toml`, `Cargo.lock` and `unix.rs` hashes match `inputs.json`; the archive SHA-256 is `ad869e2f338e432a246fec6ce13d102c6b49a5a8c2d062306e98e1eb88601215`, tested source SHA-256 `55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713`, runner SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`, and invocation script SHA-256 `3e0e8e26006a350e8d2aacef8161341c49334bf32d8d2c4f8e2473ae145b660e`. The command `cargo +1.77.2 test --locked --features testing-environ,sys --lib managed_scope_ -- --nocapture --test-threads=1` passed all six tests (24 filtered) in a 20-second bounded invocation; existing build output contained nine warnings. The 12 exported evidence entries match the remote SHA-256 manifest. Independent Workhorse readback confirmed exact run/spawn PIDs 181901/181903 (Fchdir), 181906/181908 (KernelSetpgidDenial), 181912/181914 (AfterSetpgid), and 181917/181919 (BeforeSetpgid) absent as both PID and group; reservations retired and markers remained absent. The exact session scope `/var/roothome/.local/share/agent-builds/rhai/x36-msrv1772-20261008-d791ec24` and private runtime were removed after export; no Cargo/Rust process remained. An initial attempt to create the absent nested scope stopped before Cargo because its parent directory was missing; after staging, the canonical scope and ownership were verified before launch. The prior mutation RED from attempt 06 is reused only if review confirms its test and assertion sensitivity remain applicable across the changed compiler version. No build artifact is reusable.
- Attempt 09 (`attempt-09/`) closes that mutation-sensitivity question for the named Workhorse Linux x86_64, Rust/Cargo 1.77.2, `testing-environ,sys` row. It reuses attempt 06's immutable source archive (SHA-256 `ad869e2f338e432a246fec6ce13d102c6b49a5a8c2d062306e98e1eb88601215`); `Cargo.toml`, `Cargo.lock`, and `unix.rs` hashes match its manifest, with tested `unix.rs` SHA-256 `55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713`. In one 600-second scoped invocation with two Cargo jobs, the exact `managed_scope_kernel_setpgid_denial_cleans_created_group` test first ran with only the test-only kernel-denial seam disabled and reached the intended public assertion failure (expected RED, exit 101: the shell ran); after byte-identical source restoration, the same test passed (GREEN, exit 0). Cargo/rustc were 1.77.2. Invocation script SHA-256 is `9b4d429ed3acc316b6444bb15b0cbd3ae47bbac557e0743556ffbe1e9827e9d7`; input manifest SHA-256 is `1c87de405180e7440341a9f88c4aee4c96e9976181ad05144ffa047b2dc34f53`; canonical `run_scoped.py` SHA-256 remains `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`. Raw red/green logs and 13 execution-evidence files were exported before cleanup; each exported evidence hash matches the Workhorse copy. The local post-cleanup readback was then added, and the final 14-file manifest `attempt-09/evidence-export.sha256` covers all local evidence. The test reported run PID 184402 and spawn PID 184404, with no marker execution and retired reservations; in-run and independent Workhorse readback confirmed both exact PIDs and process groups absent. The exact scope was `/var/roothome/.local/share/agent-builds/rhai/x36-msrv1772-redgreen-20261008-7870fc0b49bf46868f759045676c0df0`; the invocation returned exit 0, the scoped private runtime was absent, and the session scope was removed after export. The combined independent review returned READY for this named 1.77.2 row; X36 overall remains partial. No compiled output is reusable. The expected RED is a successful mutation control, not a product failure.
