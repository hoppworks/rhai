# Linux production process proof readiness

Status: source-only package is prepared for independent review. No remote stage was created and no native build/test ran. Launch remains gated on root review of the frozen source package.

## Pinned inputs and applicability

- Candidate: `/Users/hoppworks/projects/rhai-process-unix-run`, immutable commit `ccaa5ab66771e6dc14b9b193612ef3716e429f78`; complete `git archive --format=tar` SHA256 `030bc9630b1348ff1dd540985e3032d2840c4dfb3a462499254758a8d6c8ad91`.
- Accepted baseline lock SHA256 `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa`; private edge-only lock SHA256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Existing accepted inputs include `.scratch/linux-optional-msrv-proof/{run-proof.py,remote-launch.sh}` and `.scratch/process-unix-run/direct-drop-false.py` from evidence commit `4a8d4e5cfa4e76ae62ebfcd1c4a77e3ee6207dd2`. Prior macOS evidence does not establish Linux behavior.
- Read-only host inspection found direct Rust/Cargo/rustdoc 1.93.0 binaries and Linux Python pidfd support. No toolchain install or shared-home changes are part of this package. This proves first Linux development behavior only, not MSRV, feature matrix, performance or ticket 03 completion.

## Frozen execution sequence

The stage helper is absent-only and verifies candidate archive, baseline lock, all staged tool files, and remote SHA256 readback. The launcher runs the driver through the accepted `run_scoped.py` at a 585-second runner timeout, leaving time within the 600-second package cap for remote custody/readback. The driver reserves the first 580 seconds for active work and cleanup, with 540 seconds aggregate Cargo time; Cargo concurrency is 2. Source, Cargo/Rustup homes, target and temporary files are under the private scoped runtime. The lock transformation adds only the direct `rhai -> libc` edge and checks the accepted derived lock hash.

The finite package sequence is: (1) mutate exactly the final-client `kill_on_drop` branch from `if !state.terminal && state.kill_on_drop {` to `if !state.terminal {`, run the exact public direct false-policy test, require exit 101 at its child-survival assertion and validate its exact fixture cleanup; (2) restore and SHA-verify production bytes; (3) run the Unix owner filter serially and require 13 passing tests plus the exact owner/worker/reap/output receipt; (4) run the full public `sys_process` integration suite serially, require 29 passing tests, and validate fresh direct and managed challenge, capture, reaping, group-closure and fixture cleanup receipts. Source hashes are recorded after restore and each restored suite. Nested summaries are excluded by selecting the final matching outer libtest summary.

## Custody and failure controls

- Driver samples `/proc` with the final `)` parse for PID/start ticks/PPID/PGID and bounded `du -sk` storage each second; storage reports are sampled maxima, not continuous peaks. More than 16 owned descendants or sampled storage at 1,572,864 KiB stops the run under the 2 GiB policy.
- The independent monitor pins the `run_scoped` root with pidfd and checks its start tick against the launcher ledger before traversal. It publishes ready/heartbeat files only after that check; the driver refuses to start Cargo without readiness and aborts an active command if the heartbeat stops. Monitor observations are retained outside the private runtime.
- Cleanup anchors exact PID/start-tick identities with pidfds before signaling. Successful proof fails if any sampled child remains at cleanup. Failed/interrupted launches use only identities retained in external ledgers; remote readback checks exact identities and detached owned process groups. The inherited SSH process group is excluded from group-absence checks because it intentionally contains the live launcher; exact member identities in that group are still checked individually.
- The outer readback rejects missing/malformed ledgers, surviving identities, surviving detached owned groups, monitor failure, and a retained private runtime. Inputs, logs, status files, resource samples, identity ledgers and lock output remain in the exact evidence stage outside runtime cleanup.

## Source-only checks completed

Python and shell syntax checks, diff whitespace validation, positive classifier fixtures and negative classifier mutations have passed. These do not substitute for root source review or native execution. No remote stage, Cargo command, fixture, or Linux test has run.
