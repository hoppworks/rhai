# Core minimum compatible resolution

## Requirement

Close the approved existing core Rust 1.66.0 library gate, independent of sys/net.
Earlier diagnostic is retained under .scratch/core-msrv-check and coordinator
state: latest thin-vec 0.2.20 uses edition 2024, so old Cargo cannot consume it.
That diagnostic did not test the core source with an MSRV-compatible resolution.
The release proposal now approves recording exact resolved locks.

## Scope

Fresh owned worktree /Users/hoppworks/projects/rhai-core-msrv-resolution,
task/core-msrv-resolution, based on current coordinator HEAD. Read AGENTS.md,
release-proposal.md and the earlier core diagnostic. Use existing installed
1.66.0-aarch64-apple-darwin only; no installation, global config or agent-home edits.
Prepare a reproducible compatible private Cargo.lock and run actual Cargo/Rust
1.66 core library check with default features, without sys/net. Use official crate
manifests/docs as needed for compatible versions. Do not raise core rust-version,
ignore rust-version checks or substitute a newer compiler for acceptance. A newer
Cargo may prepare a compatible lock only if its role and old-Cargo lock compatibility
are explicit. Preserve the exact lock as acceptance evidence. If source itself
fails under 1.66, report the concrete affected path before changing it.

Minimum-compatible locked resolution is the acceptance contract; do not claim all
latest dependency versions or optional-package minimum gates work. Avoid broad
dependency pinning solely to work around old Cargo fetching a latest release.
Run a small real core Engine evaluation on the accepted old-compiler build with
independently asserted result if the library gate passes. Retain an intended wrong
result control if adding new runtime harness behavior. Do not rerun unrelated sys
or net proof and do not alter foreign worktrees or existing evidence.

## Limits and deliverable

60 active minutes including coordinator review from recorded start, <=900 seconds
per scoped invocation (--timeout 900), <=2 GiB private build storage, two build jobs.
Use python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py, private source
copy/CARGO_HOME/CARGO_TARGET_DIR, exported logs/lock before cleanup. Record actual
commands, versions, native OS, statuses, storage observations with units/method,
exact runtime path and cleanup. Preserve earlier boundary history; no default
launch-count cutoff. Stop after two consecutive launches without new diagnosis or
closed check, hard limits or uncovered decision. No new Expert chain without
coordinator consultation. No push/merge/remotes. Human-author commits, English files.
Return committed ref and concise truthful scope, proof path, unresolved gates.
