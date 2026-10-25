# Linux X36 complete setup-path sync slice (2026-10-15)

## Scope

Four exact selectors in `src/packages/sys/process/unix.rs`:

- `managed_scope_setup_failure_never_executes_unmanaged_child`
- `managed_scope_partial_setup_failure_cleans_created_group`
- `managed_scope_fchdir_failure_cleans_created_group`
- `managed_scope_kernel_setpgid_denial_cleans_created_group`

Platform: lllm Linux x86_64/Bazzite 44. Toolchain: Rust/Cargo 1.77.2. Profiles: checked `testing-environ,sys,sync` and unchecked `testing-environ,sys,sync,unchecked`. Source revision `2cb6b67a9b13c2b5f363e2d2767ac6ec40898038`; Cargo.toml SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`; canonical Cargo.lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; Unix source SHA-256 `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`.

## Results

All eight targeted GREEN invocations passed (four selectors in each profile), with the scoped runner returning 0. The tests exercised the public Rhai `run` and `spawn` paths against real Linux child processes for failure before `setpgid`, after successful `setpgid`, at real `fchdir` `EBADF`, and at real kernel `setpgid` `EPERM`. Each GREEN reports the intended failure point, no marker execution, retired reservation, and PID/group ESRCH. A separate post-run readback confirms all 16 exact run/spawn PID and process-group identities are absent. The exact private runtime/session scope was removed; hashes verify.

Expected RED controls are reused only from applicable reviewed sources: pre-`setpgid` and post-`setpgid` controls in `x36-managed-scope-setup-20261008` attempts 02/03, `fchdir` control in attempt 04/05, and kernel-denial controls in attempts 09/12 and the checked-sync pair in `linux-x36-sync-20261015`. The independent reviewer confirms the test bodies and assertions are byte-identical for these transfers. The three non-kernel controls were not freshly mutated under the sync profiles; they are source-bound assertion-sensitivity reuse, not new sync-specific RED runs.

Combined independent review: `attempt-01/combined-review.md` (PASS). This accepts only the four named Linux setup selectors in these two sync profiles. X36 overall, other OS/toolchains/features, and Ticket03 remain open.
