# X31 Darwin public wait-entry proof

## Criterion and scope

X31 requires `Child` to be shareable across threads under `sync` and to work through the public API. This proof closes only the native Darwin blocking-wait-entry slice for `testing-environ,sys,sync` and `testing-environ,sys,sync,no_float`. The full X31 matrix remains partial: Linux rows are accepted separately; other OS, non-sync blocking-entry, MSRV and feature rows remain open.

## Bound inputs

- Source revision: `05320c2c9bf3d4396956632e0cc1706e96c94b15`.
- `Cargo.toml` SHA-256: `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`.
- `src/packages/sys/process.rs` SHA-256: `090094476662417aa94e2ff519cb8038c1d3721e02be6ec166762502bfbff2e2`.
- `src/packages/sys/process/unix.rs` SHA-256 after restoration: `55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713`.
- Compatible `Cargo.lock` SHA-256: `4ff0a7de6f504510af64092d446d411b86d95228b23a188b396bd188da367627`; `cargo metadata --locked` returned 0. The exact accepted input is retained as `Cargo.lock.accepted`; its digest matches the source path recorded in `command.txt` and `source-preflight.txt`. The original run manifest remains unchanged and covers the files present when execution completed.
- Native arm64 Darwin, macOS 27.0.1 / Darwin 27.0.0, Rust/Cargo 1.93.0.
- Exact test: `packages::sys::process::unix::tests::public_wait_is_cancelled_after_entering_condvar`.
- Staged source working directory was explicitly recorded under the private runtime. Cargo used one job and a shared private target/cache for both feature rows in one `run_scoped.py` invocation.

## Results

Attempt 01 did not reach the test. Its mutation added an invalid extra `assert!` message argument and the compiler reported `argument never used`; this is preserved as a setup failure and does not count as RED.

Attempt 02 deliberately inverted only the wait-entry assertion. RED met all expected-failure conditions for both rows: Cargo status 101, the exact test ID, `test result: FAILED. 0 passed; 1 failed`, the intended `X31 RED` assertion, and a positive `wait-entry checkpoint` with `nonterminal=true`. The unwinding cleanup independently reported `reap=ESRCH` for exact child PIDs 40792 (`sync`) and 40887 (`sync,no_float`).

After restoring the original source hash, GREEN passed 1/1 for both rows with Cargo status 0. It recorded a positive wait-entry/nonterminal checkpoint, successful public cancellation and waiter wakeup, and `reap=ESRCH` for exact child PIDs 40813 (`sync`) and 40910 (`sync,no_float`). The original Unix source SHA-256 matched before each GREEN. The RED and GREEN outputs are separate per-row logs; classification uses exit status, test ID, assertion/receipt strings and result summary independently, without requiring test name and outcome on one line.

## Resource and evidence custody

The package ran once in a fresh session scope under `~/.local/share/agent-builds/rhai/`, with a 600-second runner timeout and one Cargo job. Recorded command durations were RED/GREEN 23s/3s for `sync` and 9s/1s for `sync,no_float`. Before private-runtime cleanup, the target was 823844 KiB and Cargo home 80052 KiB; peak RSS is unknown. The runner removed its private runtime and the exact empty session scope; readback says `session_scope_removed=true`. Logs, hashes, metadata, command, environment, mutation diff, restoration hash and cleanup evidence are retained beside this record. `evidence.sha256` covers the files present when the run completed; this proof record is written afterward.

## Acceptance status

The combined independent review is READY, and the named native Darwin blocking-entry rows are accepted in the X31 crosswalk in `docs/sys-package-plan.md`. X31 remains partial because other OS, non-sync blocking-entry, MSRV and feature rows remain open. No product source change was made.
