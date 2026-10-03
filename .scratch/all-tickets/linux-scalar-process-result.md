# Linux scalar process acceptance preparation

Date: 2026-10-03. Source preparation only; no native launch or acceptance claim.

## Prepared recipe

- Frozen source: `2a8fdc49a37b780c63e5c30b141c345321a876d0`.
- Compatible retained lock: `.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock`, SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- The adapter imports reviewed process identity, sampling, command, deadline, and archive/restoration primitives from `check-linux-current-msrv-examples.py`, pinned at SHA-256 `59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06`.
- It targets the exact existing test `scalar_run_with_cwd_works_without_collections` in rows `testing-environ,sys,no_index` and `testing-environ,sys,net,no_index,sync,metadata`, using private Rust/Cargo 1.77.2 and the real Engine/OS child.
- For each row, only the private archive copy of the CWD assertion is overlaid. The intentional wrong stdout expectation must fail with the actual/expected assertion values; a `finally` restores original test bytes before the positive run. The positive run requires the exact test success line, one passed test, child PID receipt and `ESRCH` reap receipt. The public worktree test remains unchanged.
- Source manifests and the compatible lock are captured before Cargo and checked after each row. Runtime, resource, deadline, process identity and bounded command handling reuse the pinned helper. Stage/launch scripts have absent-only target checks and target the exact central scope.
- Adapter-owned finalization exports command logs, source restoration details, process identities, controls, and periodic resource samples from the disposable runtime to the stage even when the run fails. It uses the pinned helper's signal handler so interruption stops/reaps the active command and reaches restoration/export.

## Source-only verification

- `PYTHONDONTWRITEBYTECODE=1 python3 .scratch/all-tickets/linux-scalar-process-source-tests.py` — 5 tests passed.
- `bash -n .scratch/all-tickets/linux-scalar-process-stage.sh .scratch/all-tickets/linux-scalar-process-launch.sh` — passed.
- Python AST parse of `linux-scalar-process-proof.py` — passed.
- Recomputed accepted base-helper and lock SHA-256 values match their pins.
- `git rev-parse HEAD` is the required frozen revision. No test or production source was edited.

## Not verified

The stage and launch scripts were not run. No SSH, Cargo, Rustup install, build, test, native process, or host readback was performed. The recipe has not yet been independently reviewed, and no native row is accepted. Full run-time readback, cleanup, exact PID/start identity closure, source restoration receipt, OS/toolchain output, and failure evidence remain required before acceptance.

Work stayed within the brief's source-only allowance and remained under its 30-minute planning checkpoint. Native cumulative process count remains 84; no new launch allocation was consumed.

## Subsequent integrated acceptance

The initial source preparation findings were corrected and independently rechecked. Nine source-flow checks now pass. One native integrated package accepted both narrow feature criteria; exact proof and limitations are in linux-scalar-process-proof.md. Preserve this original preparation account as source-only historical status.
