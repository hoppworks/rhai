# Current Rhai implementation state

## Mode, decisions and next action

Autonomous implementation remains active. A–F, Ticket03 and release are open. Windows direct-child raw, text, timeout and stdin slices pass at attempts14/17/19/21/22. Windows `spawn`/shared `Child` has an initial implementation and native spawn/clone/wait RED/GREEN at attempts23/24 with combined review PASS. **Next:** publish this reviewed WIP to fork main, then verify cancellation, drop and fault paths. Do not infer full process acceptance. The owner prefers Terra 6.1 for most delegated tasks and sparing Luna use.

## Owner boundaries and rules

Push/merge only to `https://github.com/hoppworks/rhai.git` main, never public upstream; exact author and committer name `hoppworks`, configured email, no coauthors/signatures or remote task branches. Preserve foreign/dirty work, active processes, VM originals and human limits. No Linear. Central rules HEAD `d6024420` with applicable local edits and project `AGENTS.md` govern this work. One combined independent review per coherent package with targeted risk rechecks; reuse unaffected proof. Choose heavy concurrency from actual capacity. Human authorizations persist; old PENDING labels do not revoke them.

## Accepted proof and applicability

Fork main `797395b83` contains accepted Windows sys policy/env/fs, six net targets, raw/text process, the named timeout and 1MiB stdin slices; earlier Linux, Darwin, WASM/core and MSRV evidence remains scoped by `docs/sys-package-plan.md`. The Windows backend prerequisites are not product closure.

Attempt14 native raw process and timeout-boundary proof is in `.scratch/all-tickets/windows-rhai-native-20261026/attempt14/`; attempt11 normal proof remains accepted. Rust1.77.2 Windows-target check is compilation only; native MSRV remains open.

Attempt17 native four-argument text `run`, lossy output, limits and exact child exit is accepted under Rust1.93 `testing-environ,sys,metadata`; `.scratch/all-tickets/windows-rhai-native-20261028/attempt17/`. Other overloads and native `no_index` remain unverified.

Attempt19 native direct-child `run_raw` timeout, retained prefix and exact child exit is accepted with RED/GREEN, Driver0 and combined review; `.scratch/all-tickets/windows-rhai-native-20261028/attempt19/`. Same-step overflow evidence is helper-level only; attempt18 original cleanup cause remains unknown.

Attempt21: 440 files, manifest `318bbbe8`, native Driver0 116.255s; original 222-frame/16-file serial export SHA `1a74dd7c` reconstructed across rotation; eight journal CRCs valid, runtime removed. Wrong round-trip, unread-input timeout and overlap RED; 9 units and 7+11 integration GREEN. Public real-child 128KiB Blob/64KiB-per-stream round-trip and unread-input timeout pass; pending cancellation is helper-level only. Combined review PASS, `.scratch/all-tickets/windows-rhai-native-20261028/attempt21/`. Windows1.77.2 standard/no_index/unchecked checks are compile-only; input Vec remains uncapped by a separate host input limit.

Attempt22: 440 files, manifest `c86e8816`, native Driver0 86.931s; 223-frame/16-file export SHA `004373ff`, eight journal CRCs valid, runtime removed. Four wrong-expectation REDs and 7+12 GREEN support the direct-child 1MiB Blob/256KiB-per-stream, 41-byte UTF-8 string and empty/unit EOF cases; exact handles and child-file assertions, combined review PASS. `.scratch/all-tickets/windows-rhai-native-20261028/attempt22/`. Attempt21 helper units remain applicable; other native features/MSRV and lifecycle remain open.

Attempt23: native public `spawn` contract RED at missing Windows registration, Cargo exit 101; Driver0 89.693s, 195 ordered frames/12 hash-verified files and eight journal CRCs through REMOVED. This proves the baseline only; GREEN and Child acceptance remain open. `.scratch/all-tickets/windows-rhai-native-20261028/attempt23/proof.md`.

Attempt24: native wrong-exit RED and restored 7+13 GREEN for public spawn, cloned handles, non-cancelling zero wait, exact child exit and lossy output; Driver0 88.137s, 206 ordered frames/13 hash-verified files and eight journal CRCs through REMOVED. Combined review PASS. `.scratch/all-tickets/windows-rhai-native-20261028/attempt24/proof.md`. Cancellation/drop/fault/managed lifecycle remains open.

## Open product and release work

Windows `run` overloads and stdin feature/profile rows beyond accepted slices, public pending-write cancellation and early close, `spawn`/Child, other timeout paths, output overflow/overlap, exceptional/descendant cleanup, managed Jobs, policy/quoting and feature profiles remain open. Ticket03 and strict native Linux/macOS/Windows feature/MSRV release matrix remain open. Preserve P/E/F/X/R and six-ticket requirements; use real script→Engine→host→OS and independent readback.

## Resources, cause history and consumed work

Workhorse VM UUID `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19` is running; sdb untouched and sdc restored. Guest public BuildOnly `public-refresh-e2047d40...` expires 2026-10-30 12:00 UTC. Attempt13–22 host stages/ISOs retired after export and exact checks; guest scopes01–22 await evidence-first retirement, while successful inner runtimes are removed. Retire only proven own inactive resources; rejected earlier cleanup draft deleted nothing.

Attempts11–14 consumed four native Drivers (117.434, 123.141, 79.550, 159.266 seconds) and one public build; older history and all approvals remain in prior state journal and `coordinator-history-20261015.md`. Attempts12/13 used an incorrect overflow premise; attempt14 passed.

Attempts15–17 used three Drivers (82.193, 81.646, 108.851 seconds); 15 failed before assertion on test array limit, 16 passed product checks but had a stale helper root, 17 passed.

Attempts18–19 used two Drivers (91.093, 109.507 seconds); 18 observed false timeout after child exit without recording its exact cleanup cause, 19 corrected independent pipe defects and passed. Preserve original evidence and cumulative history; no budget resets.

Attempts20/21 used two Drivers (113.324, 116.255 seconds). Attempt20 real missing-stdin failure was preserved, but its wrapper expected a hidden Debug message and did not complete; attempt21 passed. Keep original exports and cause history.

Attempt22 used one Driver (86.931 seconds) and one export; it passed the expanded Blob and scalar tests without rebuilding the unchanged unit proof. Keep all original evidence and cumulative history.

Attempt23 used one Driver (89.693 seconds) and one export. Its host ISO and stage were retired after readback, and sdc restored; guest outer scope remains. The original native test file and RED evidence are preserved as uncommitted work until the implementation package is verified.

Attempt24 used one Driver (88.137 seconds) and one export. Its host ISO and stage were retired after readback, sdc restored and guest outer scope retained. The reviewed candidate is a narrow WIP; outstanding risk checks remain.
