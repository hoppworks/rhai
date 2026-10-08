# X36: managed scope setup failure

Status: partial. This accepts only the named Workhorse Linux x86_64 row with
Rust/Cargo 1.96.0 and features `testing-environ,sys`. Other setup stages,
partial OS membership cleanup, platforms, feature combinations and MSRV rows
remain open.

## Acceptance covered

The open X36 criterion requires a managed-scope setup failure to avoid silently
running an unmanaged child and to clean up the failed launch. The exact test
`packages::sys::process::unix::tests::managed_scope_setup_failure_never_executes_unmanaged_child`
registers the real `SysPackage` in a public Rhai `Engine`, then calls public
`run` and `spawn` with a real `/bin/sh` child. A test-only child-side fault
reports its exact PID and returns `EPERM` from the `pre_exec` setup hook. The
test asserts a permission error, no marker file, exact child and process-group
absence, and retirement of the pending reservation for both public operations.
This is a backend/OS integration path; a UI layer does not apply.

The injected error is not a kernel-generated `setpgid` denial. It occurs before
the real `setpgid` call, so this proof does not claim that a partially created
OS process group is cleaned up. It proves the pre-exec failure path and no-fallback
behavior for this named Linux row.

## Run and result

- Command: `cargo test --locked --features testing-environ,sys --lib managed_scope_setup_failure_never_executes_unmanaged_child -- --nocapture --test-threads=1`.
- Baseline: exit 0; the exact test passed (1 passed, 0 failed).
- Sensitivity control: the test-copy mutation ignored the managed-scope setup error; the exact assertion failed because the real shell completed, exit 101.
- Restored source: exit 0; the exact test passed (1 passed, 0 failed).
- GREEN output records `run` child PID 139026 and `spawn` child PID 139028, with no marker, `pid=ESRCH`, `group=ESRCH`, and `reservation=retired`. A separate host-side readback confirmed both exact PIDs and groups absent.
- Inputs: source snapshot SHA-256 `cf938e6317639f126a4d2723a9c4282fe1f1b77ef757de6e576dfeb63d0ab95d`; `Cargo.toml` SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`; accepted `Cargo.lock` SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; tested Unix source SHA-256 `02e392792ea524ade719e44cc9e2b50761c4fdbb60c06e3f1fe76ccd1cd0a3d6`.
- Canonical Workhorse runner SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`; the frozen run script passed `bash -n` and has SHA-256 `8781589745a106a222c8cb7fdd249f7a711a3731da13d36d6b5b2db14123b426`.
- Raw baseline, mutation and restored logs, machine/tool versions, input manifest, statuses, result, and independent readback are retained in `attempt-02/evidence/`. Every exported file's SHA-256 matched Workhorse readback before its exact owned scope was retired. `attempt-02/cleanup-readback.txt` (SHA-256 `b740b51b6930a7a81c29440531d9db0c9f659a5c5a5ce96057f4ca8ff755d559`) confirms both exact owned scopes absent and the similarly named pre-existing scope preserved. The scoped runner removed its private Cargo runtime; no compiled build remains reusable.

Attempt 01 stopped before assertions because a nested test helper lacked a
`RawFd` import. That harness-only failure and its output remain in
`attempt-01/`; it was corrected before attempt 02 and does not count as product
RED or acceptance.
