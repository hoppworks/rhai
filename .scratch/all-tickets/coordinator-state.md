# Current Rhai implementation state

## Mode
Implementation is active. The accepted A–F, Ticket03, and release work remains open; a partial profile does not close its parent ticket or release matrix.

## Decisions and boundaries
- Rhai product/library implementation stays Rust. Use real-OS behavior, public Engine/script paths, independent readback, assertion sensitivity, bounded cleanup, source/feature/toolchain binding, and one combined review per coherent package.
- Push and integrate only on `https://github.com/hoppworks/rhai.git` `main`; never write to the public upstream. Preserve remote main consolidation and foreign work. Commit author and committer are exactly lowercase `hoppworks`, with the configured email and no coauthors.
- Preserve accepted decisions and limits in `docs/sys-package-plan.md`, this state, proof folders, and the invocation/history archives. Choose heavy runs using current capacity; expired per-run exceptions do not apply.

## Current progress
- X30 now has combined-review PASS for Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, `testing-environ,sys,unchecked`. It proves the intended +1-FD RED (101) and restored 200-call GREEN (0), with FDs 4→4. Details and parser history: `.scratch/all-tickets/linux-x30-unchecked-20261029/`.
- Existing named Linux/macOS/Windows sys/net/release profile slices remain accepted only at the scopes recorded in `docs/sys-package-plan.md`; full A–F and release remain open.

## Next action
Resolve the Windows current-directory object-binding race and finish the scoped-runner custody gate before any Rhai guest build. The local uncommitted candidate at `src/packages/sys/process/windows/cwd.rs` is not accepted: `FILE_SHARE_READ` does not prove that in-place `FILE_WRITE_ATTRIBUTES`/reparse mutation is blocked, and an archived probe demonstrated the mutation. Review a documented handle-bound launch design, implement the safe Rust path and real contract, then complete runner custody/source review before one bounded native run/raw/spawn package. Preserve the existing unsupported-CWD RED only as baseline; it does not prove the new design. Nested Managed membership and other matrix rows remain open.

## Completion
Close every accepted P/E/F/X/R and six-ticket requirement with applicable real-OS proof, review, source/feature/MSRV binding, cleanup, and fork-main integration. Production release approval remains separate. `docs/sys-package-plan.md` is the detailed requirement crosswalk and next-work record.

## Retained resources and history
The Windows quality VM remains foreign/shared and must not be restarted or altered without checking current ownership. Existing retained guest toolchain state, its exact current expiry, process identities, run budgets, causes, and accepted evidence are recorded in the relevant proof folders and `docs/development/history/expired-build-invocations-20261009.md`; do not infer active authorization from those historical records.

The complete pre-compaction state is preserved at `.scratch/all-tickets/coordinator-state-history-20261030-precompact.md`. Detailed attempts, reviews, consumed limits, and source/lock evidence remain in `.scratch/all-tickets/`, `docs/sys-package-plan.md`, and the history archives. No evidence or requirement is closed by this summary alone.
