# Windows public process contract — source-only step

## Goal and constraints

Prepare the first minimal native-Windows public `Engine` contract for ticket 03.
The Windows monitor/job owner alone controls the guest and performs all native
fixtures/builds. This step must not add production behavior before the prototype
gate. Preserve existing Unix contracts. No dependency, install, configuration,
admin, credentials, agent-home, remote branch, or merge changes.

## Current step and acceptance

Added `tests/sys_process_windows.rs`, gated to Windows with `sys` and indexed
collections enabled. The test re-executes its own test binary and calls public
`run_raw` through `SysPackage`/`Engine` for exit codes 0 and 7. It checks exact
binary stdout/stderr, complete capture, nonzero status as returned data, and
independently reads the child's PID/exit record after `run_raw` returns. The
fixture writes that record itself before exiting. `TempDir` owns and removes
the record directory. This is a contract preparation only: the test was not
compiled or run, so no native RED or pass is claimed.

Smallest private production seam needed: in `src/packages/sys/process.rs`,
declare a private `#[cfg(windows)] mod windows;` and dispatch to
`windows::register(module, state)` from `register`; two source lines. Keep the
adapter private and let the Windows prototype determine its internals. Public
`Child` export/state cleanup registration are outside this first `run_raw`
slice.

## Validation and limits

- Source formatting: `rustfmt --check tests/sys_process_windows.rs` passed.
- Whitespace check: `git diff --check` passed for tracked changes; the new
  untracked test has also passed `rustfmt --check`.
- No Cargo, compiler, fixture, or native Windows command was launched.
- Native Windows compilation, meaningful missing-registration RED, byte/output
  assertions, OS-level handle cleanup/reaping, and repeatability remain
  unverified and belong to the Windows owner after the custody/prototype gate.
- Active-work estimate/checkpoint: 30 minutes. Work in this step stayed within
  that estimate. Native launches: zero; source-only package count: one.
- No dependencies, shared services, guest resources, or temporary processes
  were created.

## Next action

After Windows monitor/job-owner custody and prototype acceptance, have that owner
run this focused contract unchanged first and capture the expected absent-run
registration failure. Then implement only the reviewed production slice and
prove the restored test natively, including independent child record and cleanup
ownership. Continue broader ticket 03 lifecycle coverage afterward.
