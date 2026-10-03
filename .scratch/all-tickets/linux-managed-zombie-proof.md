# Linux managed held-zombie MSRV proof

## Accepted criterion

Native invocation 95 is accepted for `managed_run_reports_while_fixture_reaper_holds_stopped_zombies` on Linux 7.2.7 x86_64, private Rust/Cargo 1.77.2, features `testing-environ,sys`, frozen revision `257edf695f953271adf17b12dcc70c4287ae76b5`. No permanent production or test change was required.

A real Rhai Engine host runs the managed process fixture. Independent PIDFD/start/parent/group observations establish a live host, a reaped direct leader and stopped worker/leaf zombies held by the fixture reaper. The API reports `observe_process_group_closure` / `TimedOut`, preserves direct exit `Some(0)` and complete output, and supplies honest incomplete-cleanup diagnostics. The fixture subsequently releases and reaps both zombies.

## Commands and sensitivity

Original commands are in [commands.json](linux-managed-zombie95-evidence/proof-evidence/commands.json). Private toolchain setup and both version checks exit 0. The exact Cargo command is:

```text
cargo test --locked --features testing-environ,sys --test sys_process managed_run_reports_while_fixture_reaper_holds_stopped_zombies -- --exact --nocapture --test-threads=1
```

Two temporary after-cleanup wrong expectations require a success report and direct exit 7. Both exit 101 at their exact named assertion, with the real boundary and cleanup receipts retained. Byte restoration to test SHA `8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b` precedes the final original GREEN: 1 passed, 0 failed, exit 0. The controls test assertion sensitivity; they do not simulate different production outcomes.

## Original evidence and independent acceptance

[Original evidence](linux-managed-zombie95-evidence/export-manifest.json), [source restoration](linux-managed-zombie95-evidence/proof-evidence/source-restoration.json), [independent readback](linux-managed-zombie95-evidence/independent-readback.json), and the [combined review](linux-managed-zombie-review.md) bind all 52 exported file hashes, executed recipes, source archive SHA `ea085b4d28ee5ce3c7b998044242a50c755d9e9252638dbcf28c036b3df7c922` and accepted lock SHA `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The helper intentionally records `acceptance_claim=false`; external acceptance is recorded here and in the review.

[Fresh final cleanup readback](linux-managed-zombie95-evidence/independent-owned-cleanup.json) confirms 99 exact PID/start identities absent, four exact groups empty, stage and central scope absent after hash-gated removal of 52 owned files and five directories. The collector did not save its cleanup stdout; this receipt is a subsequent independent absence check. No private build is retained.

Bounds remain outer 600 seconds, runner 585, helper 540 including 30 seconds reserved for export; jobs 2, descendants 16, storage/RSS hard limit 2 GiB. Observed one-second sample maxima are RSS 874592 KiB, storage 801064 KiB and seven descendants, not continuous peaks or API latency guarantees. Export started at 28.515 seconds. The preserved disappearing `/proc` census warning is an exit race; subsequent terminal identity/runtime checks all succeed.

Invocation 94 is a preserved infrastructure failure: the first intended control reached its assertion, but nested libtest output defeated a contiguous outer-result parser. Its 44 original files and cleanup are in [failed94 evidence](linux-managed-zombie-failed94-evidence/failed-export-readback.json). The reviewed repair separates the outer prefix, final summary, failure list and named panic; strict boundary checks remain unchanged. Invocation 95 closes that harness cause without resetting history. Cumulative Unix invocations: 95.

## Applicability and open coverage

This partially closes tickets 03 and 06 for the current Linux MSRV held-zombie boundary. Earlier native74 proof remains valid narrowly. Ordinary managed success with foreign reaping, other managed fault/lifecycle branches, feature/platform matrix, performance and final release acceptance remain open. Stopped Darwin/Windows paths and all existing cause/budget history are unchanged.
