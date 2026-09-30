# Filesystem contract repairs

## Goal
Implement the four accepted filesystem contract repairs from `.scratch/stdlib-wayfinder/issues/02-filesystem-contract.md` on `task/filesystem-contract` and commit verified local work.

## Done
- Read project `AGENTS.md`, coordinator state, canonical contract, and review repro/logs.
- Created isolated worktree `/Users/hoppworks/projects/rhai-filesystem-contract` from `task/all-tickets`.
- Added configured-root symlink/parent regression. It failed against old code (selected lexical sentinel) then passed after preserving the OS-resolved root path. Logs: `.scratch-config-root-red.log`, `.scratch-config-root-green.log`.
- Added unrestricted host path dispatch through std filesystem operations, plus symlink read/write/copy/remove public API regression. Targeted test passed once after initial compile corrections; rerun after final edits required.

## Current
Finish focused acceptance regressions and correction of non-UTF8 proof claim. The non-UTF8 test was rerun with `--nocapture`; this macOS filesystem returns EILSEQ (92), so fixture creation is skipped and `NotUtf8` remains unverified here. The guard now skips only EILSEQ raw codes 84 or 92; unrelated I/O errors panic. New unrestricted symlink/parent and nested-root equivalent-alias regressions pass in the scoped build.

## Constraints
Use `tools/run_scoped.py`, private source copy inside runtime, scoped `CARGO_TARGET_DIR` and `CARGO_HOME`. Do not touch other worktrees or remote state. Preserve test/support layout. No Windows or broader release matrix claims.

## Next
Add/run final proof and capture environment, observed independent host state, fixture capability, false-green result, and cleanup evidence in `.scratch/filesystem-contract/`.

## Completed evidence
- Final source formatted in the three touched Rust files; `git diff --check` clean.
- Strict scoped suite after final routing change: `testing-environ,sys,metadata`, sys_env 6/6, sys_fs 22/22, sys_policy 25/25. Current native environment: macOS 27.0 arm64, rustc 1.93.0.
- False-green control: configured-root payload changed to `wrong expected value` failed with code 101; restored correct expectation passed with code 0.
- Non-UTF8 fixture is rejected by this host filesystem with EILSEQ (92). `nonutf8-nocapture.log` explicitly shows the skip; public `NotUtf8` behavior is unverified on this host.
- `unrestricted-symlink-parent.log` and `nested-root-alias.log` show focused tests passing, with host-side sentinel/readback assertions.
- Detailed proof record: `.scratch/filesystem-contract/proof.md`; all run logs are alongside it.

## Current state
All four repair areas are implemented. Focused macOS tests prove OS path selection, unrestricted symlink semantics and equivalent nested-root aliases. The filesystem rejected the non-UTF8 fixture, so that public API behavior is not proven on this host. Windows/other OS and release matrix remain unverified. Next: review status and commit the proof correction/regressions atomically; no push or merge.
- `rustfmt --edition 2021 --config skip_children=true` succeeded for the three changed Rust files; `git diff --check` is clean. Repository-wide `cargo fmt --all -- --check` remains red only for pre-existing formatting in untouched `src/eval/mod.rs` (details in `format-check.log`).
