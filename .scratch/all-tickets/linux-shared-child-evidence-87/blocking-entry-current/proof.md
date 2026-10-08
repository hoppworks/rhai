# Linux X31 blocking-entry addendum — 2026-10-08

Status: native test passed; combined independent review READY 2026-10-08. A pre-run host-preflight scope ending `6cb71f4b` is distinct from the successful runner scope ending `6cb71f4c`; see `preflight-stop.txt`, `preflight-host-metadata.txt`, and `preflight-cleanup-readback.txt`. This adds only the blocking-entry observation missing from the accepted Linux shared-Child proof in `../linux-shared-child-proof.md`. It does not repeat the existing shared-handle, cancellation, `no_float`, or assertion-sensitivity rows.

## Inputs and command

- Workhorse source revision: `c644085ccf65160bd3d39f5353e8b933310ffe03`, archived into the runner's private runtime.
- Native host: Linux x86_64; `rustc 1.97.1 (8bab26f4f 2026-07-14)`, Cargo 1.97.1.
- Features: `testing-environ,sys,sync`.
- The library checkout has no root `Cargo.lock`. Reused the retained X31-compatible lock, SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The current manifest differs from its earlier X31 source only by an example declaration (`sys_process`, requiring `sys`); no dependency declarations changed. Full `cargo metadata --locked` succeeded against the current manifest and lock before compilation.
- Current source hashes: `Cargo.toml` `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`; `src/packages/sys/process/unix.rs` `55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713`; `tests/sys_process_report.rs` `b081e8de1174433bd8ef5668945bfdda7b81fdcdeb6ef1b1d92a2c04d6f5c53f`.
- Test: `cargo test --locked --manifest-path source/Cargo.toml --lib --features testing-environ,sys,sync public_wait_is_cancelled_after_entering_condvar -- --nocapture --test-threads=1`.

## Result

The existing unit test builds a real public Rhai `Engine`, evaluates Rhai `spawn`/`wait`/`kill`, and holds a real `/bin/sh` child on a FIFO. The waiter thread evaluates public `child.wait()`. The test observes the internal wait-entry counter and reacquires the child snapshot mutex while the child is independently confirmed nonterminal, proving the waiter reached `Condvar::wait` before cancellation. Public `child.kill()` wakes that waiter; the test independently checks the exact recorded PID is reaped (`ESRCH`).

The native output records `wait-entry checkpoint pid=192939 count=1 nonterminal=true` and `shared-child entered-wait pid=192939 wait_entries=2 nonterminal_at_cancel=true waiter_woke=true reap=ESRCH`. Cargo reports exactly one matching test passed, 30 filtered, zero failures. Both Cargo metadata and test ran with `--locked`; the test source was unmodified.

This closes the Linux x86_64, Rust/Cargo 1.97.1, `testing-environ,sys,sync` blocking-entry row only. Existing proof still covers the named Linux Rust/Cargo 1.77.2 normal, sync, and sync+`no_float` shared-child rows. Other platforms, MSRVs and feature combinations remain open. No product change or test re-run is indicated.

## Resource and cleanup record

The canonical Workhorse `tools/run_scoped.py` ran with a unique session scope under `/root/.local/share/agent-builds/rhai/` and `TMPDIR` set to that absolute scope. `CARGO_TARGET_DIR`, `CARGO_HOME`, extracted source, and Cargo metadata were inside `AGENT_RUNTIME_DIR`. GNU `time` reports Cargo wall time 7.87 seconds and maximum RSS 948,644 KiB; immediately before cleanup, target output was 564,396 KiB and private Cargo cache 161,508 KiB. These are reported measurements, not continuous peak samples. The runner removed its runtime; exact readback confirmed runtime and session scope absent. Proof files were exported before cleanup, hash-matched against the Workhorse copy, then the owned remote evidence copy was removed. The earlier missing-lock host preflight (session `…6cb71f4b`) stopped before the runner; its host metadata and exact scope-removal readback are separate from successful runner attempt 01 (session `…6cb71f4c`).

Raw command output, statuses, hashes, runtime path, lock input, and cleanup readback are retained in `attempt-01/` and the parent directory.
