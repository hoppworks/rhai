# Unsupported feature release proof

## Requirement
Close the approved release negative compilation gates: sys/no_std, net/no_std, sys/no_object, and sys/net WASM separately and combined. Unsupported combinations must emit the intentional package diagnostics, not be counted as accepted merely because compilation failed. Existing source guards may suffice; do not change API behavior or relax contracts. No production process, combined runtime, native Windows, or toolchain install scope.

## Context
Read AGENTS.md and .scratch/all-tickets/release-proposal.md in this checkout. Base79eca3c0. Relevant sources src/packages/sys/mod.rs, src/packages/net/mod.rs, src/packages/mod.rs and Cargo.toml. Read campaign and e2e-proof as needed. Compilation gates are compiler contract proof, not Engine OS behavior proof.

## Budget and stop conditions
Original fixed package 2026-09-30 16:01:15–16:31:15 UTC inclusive coordinator review. Private scoped invocation <=600s, jobs2, debug0/incremental0, whole runtime storage <=2GiB with1s sampling and preemptive stop at1.5GiB. Stop on cap/deadline/unsupported setup requiring install; no budget reset. Reserve at least5min root review. Local routine setup fixes only within budget, preserve actual cause counts. All diagnostic results exported as completed. No global changes or installs. Use existing installed WASM target if available; otherwise report WASM gate unverified without incidental-error acceptance.

## Execution and deliverable
Own task/unsupported-feature-proof checkout /Users/hoppworks/projects/rhai-unsupported-feature-proof. Use python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py, private copied source/CARGO_HOME/CARGO_TARGET_DIR. One related build invocation reused across checks; check logs contain exact intended diagnostics. Control: temporarily remove a specific guard in private source and show diagnostic matcher rejects missing intended diagnostic, restore and confirm detection. This is compiler assertion proof only; no runtime acceptance claim. Native host compiler needed; native WASM compiler target diagnostic evidence only, not WASM runtime.
Record exact Cargo commands, exit statuses, expected diagnostic occurrences, rust/target/lock details, source correction if any, sampled resources and cleanup. Preserve existing package proof; no duplicate full runtime matrix. Commit only slice/proof as author AND committer hoppworks with configured email, command-local override, no coauthor. Do not push or merge. Return commit SHA, evidence paths, changed file list, accepted/unverified requirements, exact owned cleanup paths. Coordinator independently reviews then integrates accepted proof and pushes; leave checkout intact for review.
