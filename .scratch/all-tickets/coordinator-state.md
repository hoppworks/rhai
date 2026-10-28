# Current Rhai implementation state

## Mode, decisions and next action

Autonomous implementation remains active. A–F, Ticket03 and release are open. Windows direct-child raw, text, timeout and Blob-stdin slices pass at attempts14/17/19/21. **Next after fork-main readback:** implement the remaining Windows process contracts; first atomically publish this accepted package if absent. Do not infer full process acceptance. The owner prefers Terra 6.1 for most delegated tasks and sparing Luna use.

## Owner boundaries and rules

Push/merge only to `https://github.com/hoppworks/rhai.git` main, never public upstream; exact author and committer name `hoppworks`, configured email, no coauthors/signatures or remote task branches. Preserve foreign/dirty work, active processes, VM originals and human limits. No Linear. Central rules HEAD `d6024420` with applicable local edits and project `AGENTS.md` govern this work. One combined independent review per coherent package with targeted risk rechecks; reuse unaffected proof. Choose heavy concurrency from actual capacity. Human authorizations persist; old PENDING labels do not revoke them.

## Accepted proof and applicability

Fork main `ce8bcbcd1` contains accepted Windows sys policy/env/fs, six net targets, raw/text process and the named timeout slice; earlier Linux, Darwin, WASM/core and MSRV evidence remains scoped by `docs/sys-package-plan.md`. The Windows backend prerequisites are not product closure.

Attempt14 native raw process and timeout-boundary proof is in `.scratch/all-tickets/windows-rhai-native-20261026/attempt14/`; attempt11 normal proof remains accepted. Rust1.77.2 Windows-target check is compilation only; native MSRV remains open.

Attempt17 native four-argument text `run`, lossy output, limits and exact child exit is accepted under Rust1.93 `testing-environ,sys,metadata`; `.scratch/all-tickets/windows-rhai-native-20261028/attempt17/`. Other overloads and native `no_index` remain unverified.

Attempt19 native direct-child `run_raw` timeout, retained prefix and exact child exit is accepted with RED/GREEN, Driver0 and combined review; `.scratch/all-tickets/windows-rhai-native-20261028/attempt19/`. Same-step overflow evidence is helper-level only; attempt18 original cleanup cause remains unknown.

Attempt21: 440 files, manifest `318bbbe8`, native Driver0 116.255s; original 222-frame/16-file serial export SHA `1a74dd7c` reconstructed across rotation; eight journal CRCs valid, runtime removed. Wrong round-trip, unread-input timeout and overlap RED; 9 units and 7+11 integration GREEN. Public real-child 128KiB Blob/64KiB-per-stream round-trip and unread-input timeout pass; pending cancellation is helper-level only. Combined review PASS, `.scratch/all-tickets/windows-rhai-native-20261028/attempt21/`. Windows1.77.2 standard/no_index/unchecked checks are compile-only; input Vec remains uncapped by a separate host input limit.

## Open product and release work

Windows `run` overloads beyond accepted slices, string/unit stdin, public pending-write cancellation and early close, `spawn`/Child, other timeout paths, output overflow/overlap, exceptional/descendant cleanup, managed Jobs, policy/quoting and feature profiles remain open. Ticket03 and strict native Linux/macOS/Windows feature/MSRV release matrix remain open. Preserve P/E/F/X/R and six-ticket requirements; use real script→Engine→host→OS and independent readback.

## Resources, cause history and consumed work

Workhorse VM UUID `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19` is running; sdb untouched and sdc restored. Guest public BuildOnly `public-refresh-e2047d40...` expires 2026-10-30 12:00 UTC. Attempt13–21 host stages/ISOs retired after export and exact checks; guest scopes01–21 await evidence-first retirement, while successful inner runtimes are removed. Retire only proven own inactive resources; rejected earlier cleanup draft deleted nothing.

Attempts11–14 consumed four native Drivers (117.434, 123.141, 79.550, 159.266 seconds) and one public build; older history and all approvals remain in prior state journal and `coordinator-history-20261015.md`. Attempts12/13 used an incorrect overflow premise; attempt14 passed.

Attempts15–17 used three Drivers (82.193, 81.646, 108.851 seconds); 15 failed before assertion on test array limit, 16 passed product checks but had a stale helper root, 17 passed.

Attempts18–19 used two Drivers (91.093, 109.507 seconds); 18 observed false timeout after child exit without recording its exact cleanup cause, 19 corrected independent pipe defects and passed. Preserve original evidence and cumulative history; no budget resets.

Attempts20/21 used two Drivers (113.324, 116.255 seconds). Attempt20 real missing-stdin failure was preserved, but its wrapper expected a hidden Debug message and did not complete; attempt21 passed. Keep original exports and cause history.
