# Shared Child fixture cleanup repair

## Changed files

- `tests/fixtures/sys_process_shared_child_contract.rs`: catch scenario panics
  inside the controller; release only the fixture's synchronization files while
  the production cleanup worker retains its exact OS `Child`; require observed
  `ESRCH` before recording closure; release before outer watchdog termination;
  retain fixture records when controller-side production reap is unproved. The
  external watchdog is 24 seconds, beyond the fixture's existing 18-second
  bound. Added a real Engine/self-reexec regression for panic cleanup.
- `.scratch/process-unix-run/shared-child-contract-activation.md`: recorded the
  repair, evidence limits, source recheck, and remaining sync wait-entry limit.
- `shared-child-cleanup-repair.md`: this result.

## Checks

- Confirmed `HEAD` is `0184e20a4e49c57f3fec7289ec3d94ec6bffb548`.
- Reviewed production `CleanupService` ownership/reap behavior and the affected
  fixture paths before static checks. Rechecked both existing corrections:
  successful controller output remains emitted, and
  `DIRECT_DROP_CHALLENGE_ENV` uses the same `unix && !no_index` gate as its
  `process_fixture` use.
- `git diff --check`: passed. Targeted source inspection confirms the shared
  child fixture no longer logs PID absence as cleanup success.
- `rustfmt --edition 2021 --check tests/fixtures/sys_process_shared_child_contract.rs`:
  is not clean; it reports formatting differences across the file, including
  existing untouched code. No whole-file formatting was applied to avoid
  unrelated edits.
- No Cargo, Rust compiler, native, or process fixture run was performed. The new
  regression and compiler compatibility are unverified.

## Unresolved requirements

- If the controller is forcibly terminated before its production worker reaps,
  or the scoped runner's hard watchdog interrupts the process group, fixture
  closure remains unverified and its records are retained. Retaining a directory
  alone is not process custody. The runner's broader bounded process-group
  custody prerequisite remains open; do not treat this repair as closing it.
- The sync start channel still does not prove entry into blocking `wait`.
- Existing native Rust 1.77.2 and release OS/feature matrix acceptance remains
  open. The two `0184e20a` corrections have source review only.

## Exact next native acceptance

After the scoped runner's process-group custody prerequisite is satisfied, use
private Rust 1.77.2 output/cache isolation and serial execution. First run the
focused cached-exit-code wrong-control for
`shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable`,
confirm failure at the intended code assertion, restore the assertion, and
confirm pass, using:

```sh
cargo test --features testing-environ,sys,sync --test sys_process \
  shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable \
  -- --exact --test-threads=1
```

Then run the registered module and panic-cleanup regression with each feature
set:

```sh
cargo test --features testing-environ,sys,sync --test sys_process shared_child_contract -- --test-threads=1
cargo test --features testing-environ,sys,sync,no_float --test sys_process shared_child_contract -- --test-threads=1
```

Capture controller output and independently read fixture records; require exact
controller and fixture reap evidence, clean owned roots, and preserve failed
records on incomplete closure. Run on each required native OS for the release
matrix. No native run or invocation85 was allocated here.
