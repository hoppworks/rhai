# Linux current-feature setup failure

The first compiler package exited 1 before Rustup or Cargo. The immutable staged
inputs passed their recorded SHA-256 checks, but the helper compared the canonical
stage path with a lexical `/root` path. On this host `/root` resolves to
`/var/roothome`, so the same intended directory was incorrectly rejected.

Original local invocation: `linux-current-feature-outer.log` and `.status`.
Original remote receipts are retained at the exact stage
`/root/rhai-linux-current-features-msrv-1ca21e32-20261002`; local copies are in
`linux-current-feature-setup-evidence/{proof-evidence,outer-evidence}`.
Outer elapsed 0.4396 seconds, helper export elapsed 0.001 seconds. No feature
assertion ran, and no process fixture/control/measurement invocation was consumed.

Cleanup finalization also failed closed because the helper records its runtime
and process ledger after the failing stage check. Independent root read-back in
`linux-current-feature-setup-evidence/independent-cleanup.json` confirmed the
recorded launcher 1197315, runner 1197387 and helper 1197390 absent, their observed
groups empty, and the exact runtime `agent-build-8dpbkisi` absent. Only the exact
owned, empty session scope was removed. Other processes and scopes were preserved.

The responsible source owner is correcting canonical directory identity and
early failure receipts with pure RED/GREEN tests. A fresh v2 stage will preserve
the failed original inputs/evidence. Proposed follow-up caps are outer590,
helper530, work500 and export30 seconds, retaining prior consumption and the
original cumulative600/540 bounds. Jobs2, descendants16, RSS2GiB and storage1.5GiB
remain unchanged. Independent affected-source review precedes any launch; renew
the Machine heavy-slot inventory. Linux compiler acceptance remains open.
