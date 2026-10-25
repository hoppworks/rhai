# Linux X36 base-unchecked setup-failure rows

Status: combined independent integration review PASS.

## Scope and source applicability

This packet covers three previously uncovered Linux x86_64/Bazzite44,
Rust/Cargo1.77.2 rows under `testing-environ,sys,unchecked`:

- `managed_scope_setup_failure_never_executes_unmanaged_child`
- `managed_scope_partial_setup_failure_cleans_created_group`
- `managed_scope_fchdir_failure_cleans_created_group`

The scoped source archive was revision `2cb6b67a9b13c2b5f363e2d2767ac6ec40898038`.
The coordinator's integrated candidate `c22011d4453c48fca4a4e327df0bdf3755613bf5`
has identical Unix library/test source (SHA-256
`2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`) and Cargo.toml
(`cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`). The
intervening commit changes only unrelated integration-test fixture cleanup and
proof documents. The canonical lock is unchanged:
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, also retained
in the tracked `../core-current-msrv-evidence-04/Cargo.lock`.

## Real behavior, assertion sensitivity and readback

Each selector registers the real SysPackage in a public Rhai Engine and invokes
both `run` and `spawn`. The before/after-setpgid seams deliberately inject EPERM;
the fchdir seam closes the child's inherited cwd fd and reaches real fchdir EBADF.
Each public call reports the expected Io setup error, leaves its marker absent,
retires its pending reservation, and observes the exact failed-launch PID/group
absent. These tests do not claim every syscall failure is kernel-generated.

The three Cargo selectors and scoped runner each exited 0; their logs each show
one passed test, zero failures and two public-operation cleanup records. A separate
post-run Python observer checked all six recorded PIDs and groups using signal
zero, accepting absence only for ESRCH. The readback is exported with the logs. Its observer implementation was executed
as an SSH heredoc and was not separately exported; the six exact per-identity
results are retained. The reviewer recorded this limitation and accepted the rows.

No assertion code changed. Reuse the previously reviewed pre-setpgid/post-setpgid
RED controls in `../x36-managed-scope-setup-20261008/` attempts02/03 and fchdir
control in attempts04/05, as already bound to the identical selector/helper source
by the PASS review in `../linux-x36-setup-sync-20261015/attempt-01/combined-review.md`.
This is assertion-sensitivity reuse; no fresh base-unchecked RED is claimed. The
accepted unchecked kernel-denial row in attempt12 is unaffected and was not rerun.

## Commands, resources and export

The existing scoped command pattern was reused with one Cargo job and three exact
`cargo test --locked --features testing-environ,sys,unchecked --lib <selector>
-- --exact --nocapture --test-threads=1` invocations. `attempt-01/run.sh` records
all expanded paths and commands; `attempt-01/invocation.md` records finite limits
and preflight. The outer runner timeout was 600s; per-selector timeout 300s. One
compile took 35.37s; the three test executions each took 0.01s. Subsequent Cargo
preparations took 0.03s each and reused the same target and private dependency cache.

Source copy, target, Cargo home and test fixtures remained below the unique owned
runner runtime. Evidence was exported before it exited. The runner removed the
runtime; the separate observer confirmed the exact session scope empty and retired
it with rmdir. No build/cache is retained. Original remote evidence and dirty
remote documents were preserved. No product/test code, shared service, toolchain,
SSH trust or foreign process was modified.

This closes only these three profile rows; X36 overall, other native
platform/profile/MSRV rows, Ticket03 and packages B/C/D/F remain open.
