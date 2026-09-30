# Preserve the existing core Rust minimum

## Task
Perform one bounded native check of the existing core Rust 1.66.0 contract on the
current integrated source without sys/net. This is independent of pending package
release/API choices: Cargo.toml already declares core rust-version 1.66.0.

## References
- /Users/hoppworks/projects/rhai-all-tickets/AGENTS.md and Cargo.toml.
- /Users/hoppworks/projects/agent-skills/tools/run_scoped.py.
- Existing local toolchain 1.66.0-aarch64-apple-darwin (read-only).

## Scope and constraints
Reuse or create an owned worktree task/core-msrv-check; no source fixes, remote
writes, installs, credentials, agent-home changes or global Cargo config changes.
Freeze task/all-tickets source revision. Use private source copy/CARGO_HOME/target
and temp under the configured scoped runner. One invocation, total timeout 300s.
Run actual Cargo/Rust 1.66.0, cargo check --lib with existing default features.
Do not substitute a newer compiler/Cargo, change feature scope, pin dependencies,
invent a release lock policy or bypass rust-version checks to obtain green.
If registry/toolchain/dependency resolution blocks compilation, preserve exact
diagnostic and classify infrastructure versus unsupported dependency boundary.
No automatic second build or recovery. No calibration package is approved.

## Acceptance and deliverable
Report whether current default core library compiles at its advertised minimum.
Record source identity, toolchain/OS, exact command/status, actual failure cause,
lock/resolution used where available, and exact scoped cleanup readback. Do not
claim runtime/E2E, sys/package feature or release-matrix completion. Preserve
the accepted native sys evidence without rerunning it. Commit a concise proof/log
under .scratch/core-msrv-check in the owned branch and report HEAD/path/status.
