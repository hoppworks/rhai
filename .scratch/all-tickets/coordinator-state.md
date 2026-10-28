# Current Rhai implementation state

## Mode, decisions and next action

Autonomous implementation remains active. A–F, Ticket03 and release are open. Windows direct-child raw, text, timeout and stdin slices pass at attempts14/17/19/21/22. Spawn/clone/wait at attempts23/24, kill with unread buffered input at attempt25 and direct-child drop at attempt27 passed combined review and are on fork main. Attempt28 proves script mutation of cached code/stdout; combined review PASS. **Next:** publish this proof, then verify pending-write, drop retirement and fault paths. Do not infer full process acceptance. The owner prefers Terra 6.1 for most delegated tasks and sparing Luna use.

## Owner boundaries and rules

Push/merge only to `https://github.com/hoppworks/rhai.git` main, never public upstream; exact author and committer name `hoppworks`, configured email, no coauthors/signatures or remote task branches. Preserve foreign/dirty work, active processes, VM originals and human limits. No Linear. Central rules HEAD `d6024420` with applicable local edits and project `AGENTS.md` govern this work. One combined independent review per coherent package with targeted risk rechecks; reuse unaffected proof. Choose heavy concurrency from actual capacity. Human authorizations persist; old PENDING labels do not revoke them.

## Accepted proof and applicability

Fork main `173b49e44` contains accepted Windows sys policy/env/fs, six net targets, raw/text process, the named timeout, 1MiB stdin, narrow spawn/clone/wait, kill with unread buffered input and direct-child drop observations; earlier Linux, Darwin, WASM/core and MSRV evidence remains scoped by `docs/sys-package-plan.md`. The Windows backend prerequisites are not product closure.

Attempt14 native raw process and timeout-boundary proof is in `.scratch/all-tickets/windows-rhai-native-20261026/attempt14/`; attempt11 normal proof remains accepted. Rust1.77.2 Windows-target check is compilation only; native MSRV remains open.

Attempt17 native four-argument text `run`, lossy output, limits and exact child exit is accepted under Rust1.93 `testing-environ,sys,metadata`; `.scratch/all-tickets/windows-rhai-native-20261028/attempt17/`. Other overloads and native `no_index` remain unverified.

Attempt19 native direct-child `run_raw` timeout, retained prefix and exact child exit is accepted with RED/GREEN, Driver0 and combined review; `.scratch/all-tickets/windows-rhai-native-20261028/attempt19/`. Same-step overflow evidence is helper-level only; attempt18 original cleanup cause remains unknown.

Attempt21: 440 files, manifest `318bbbe8`, native Driver0 116.255s; original 222-frame/16-file serial export SHA `1a74dd7c` reconstructed across rotation; eight journal CRCs valid, runtime removed. Wrong round-trip, unread-input timeout and overlap RED; 9 units and 7+11 integration GREEN. Public real-child 128KiB Blob/64KiB-per-stream round-trip and unread-input timeout pass; pending cancellation is helper-level only. Combined review PASS, `.scratch/all-tickets/windows-rhai-native-20261028/attempt21/`. Windows1.77.2 standard/no_index/unchecked checks are compile-only; input Vec remains uncapped by a separate host input limit.

Attempt22: 440 files, manifest `c86e8816`, native Driver0 86.931s; 223-frame/16-file export SHA `004373ff`, eight journal CRCs valid, runtime removed. Four wrong-expectation REDs and 7+12 GREEN support the direct-child 1MiB Blob/256KiB-per-stream, 41-byte UTF-8 string and empty/unit EOF cases; exact handles and child-file assertions, combined review PASS. `.scratch/all-tickets/windows-rhai-native-20261028/attempt22/`. Attempt21 helper units remain applicable; other native features/MSRV and lifecycle remain open.

Attempt23: native public `spawn` contract RED at missing Windows registration, Cargo exit 101; Driver0 89.693s, 195 ordered frames/12 hash-verified files and eight journal CRCs through REMOVED. This proves the baseline only; GREEN and Child acceptance remain open. `.scratch/all-tickets/windows-rhai-native-20261028/attempt23/proof.md`.

Attempt24: native wrong-exit RED and restored 7+13 GREEN for public spawn, cloned handles, non-cancelling zero wait, exact child exit and lossy output; Driver0 88.137s, 206 ordered frames/13 hash-verified files and eight journal CRCs through REMOVED. Combined review PASS. `.scratch/all-tickets/windows-rhai-native-20261028/attempt24/proof.md`. Cancellation/drop/fault/managed lifecycle remains open.

Attempt25: native wrong-exit RED and restored 7+15 GREEN for public kill with 1 MiB stdin and 12,288 unread buffered bytes, exact child exit and repeated kill; Driver0 125.005s, 206 frames/13 hash-verified files and eight journal CRCs through REMOVED. `.scratch/all-tickets/windows-rhai-native-20261028/attempt25/proof.md`. This does not establish a pending overlapped write. Combined review PASS.

Attempt26: Driver124 after 180.226s; recovered exact `compile.log` ends during compilation without Cargo completion, before the RED/GREEN commands. Four journal CRCs validate through LIFECYCLE; guest runtime and outer scope retained. `.scratch/all-tickets/windows-rhai-native-20261028/attempt26/failure.md`. No Drop product result or proven cause of slow compilation.

Attempt27: two survival REDs and restored 7+17 GREEN for nonfinal/final drop policies with challenge acknowledgements and exact child exits. Driver0 98.788s; 213 frames/14 hash-verified files, eight journal CRCs through REMOVED. Combined review PASS; proof `.scratch/all-tickets/windows-rhai-native-20261028/attempt27/proof.md`. Supervisor/permit retirement remains open.

Attempt28: wrong cached-exit RED and restored 7+17 GREEN after Rhai script mutates `code`/`stdout` then rereads a cloned Child result. Driver0 119.985s; 207 frames/13 hash-verified files, eight journal CRCs through REMOVED. `.scratch/all-tickets/windows-rhai-native-20261028/attempt28/proof.md`; combined review PASS. Only named fields covered.

## Open product and release work

Windows `run` overloads and stdin feature/profile rows beyond accepted slices, public pending-write cancellation and early close, `spawn`/Child, other timeout paths, output overflow/overlap, exceptional/descendant cleanup, managed Jobs, policy/quoting and feature profiles remain open. Ticket03 and strict native Linux/macOS/Windows feature/MSRV release matrix remain open. Preserve P/E/F/X/R and six-ticket requirements; use real script→Engine→host→OS and independent readback.

## Resources, cause history and consumed work

Workhorse VM UUID `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19` is running; sdb untouched and sdc restored. Guest public BuildOnly `public-refresh-e2047d40...` expires 2026-10-30 12:00 UTC. Attempt13–22 host stages/ISOs retired after export and exact checks; guest scopes01–22 await evidence-first retirement, while successful inner runtimes are removed. Retire only proven own inactive resources; rejected earlier cleanup draft deleted nothing.

Attempts11–25 consumed 15 native Drivers; timings, accepted proofs, earlier approvals and causes remain in their proof directories, prior state journal and `coordinator-history-20261015.md`. Attempt18 had an undiagnosed false timeout; attempt20's real stdin failure was followed by a wrapper-marker failure. No budgets reset.

Attempt26 used one Driver (180.226s), one export and read-only compile-log recovery; its unfinished guest runtime and outer scope remain. Attempt27 used one Driver (98.788s), one export and two Cargo jobs following live capacity checks. Its host ISO/stage were retired, sdc restored and guest outer scope retained.

Attempt28 used one Driver (119.985s) and one export. Host ISO/stage retired, sdc restored; guest outer scope retained. For real pending-write proof, use a private per-child `cfg(test)` probe at `ERROR_IO_PENDING`, observe an unsignaled event, gate the worker boundedly until public `kill`, then verify real cancellation and owner retirement; avoid global state or new production API.
