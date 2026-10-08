# X31 Darwin wait-entry combined review

## Verdict

READY for the named native Darwin blocking-entry rows only. No material findings. The review does not close X31 as a whole.

## Reviewed binding and evidence

- The exact test, `Cargo.toml`, `process.rs`, restored `unix.rs`, accepted `Cargo.lock`, feature sets, staged working directory, native arm64 Darwin environment, and Rust/Cargo 1.93.0 are bound in `proof.md` and the run manifest.
- Attempt 01 is correctly classified as a compile/setup failure: it did not execute the test assertion and is not product RED.
- For both `testing-environ,sys,sync` and `testing-environ,sys,sync,no_float`, attempt 02 records RED with Cargo status 101, exact test ID, failed summary, intended assertion marker, positive nonterminal wait-entry checkpoint, and exact-child `ESRCH` cleanup.
- Restored GREEN records Cargo status 0, 1/1 passed, public wait entry before cancellation, waiter wakeup, exact-child `ESRCH`, and the restored source hash for both feature rows.
- Evidence hashes recompute, the scoped runner succeeded, and the exact session scope was removed after evidence export.

## Acceptance boundary

Accept only the native Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0 blocking-entry rows for the two recorded feature sets at source `05320c2c9bf3d4396956632e0cc1706e96c94b15`. Existing accepted Linux evidence remains separate. Other operating systems, non-sync blocking-entry, MSRV and feature rows remain open.

## Rule revision context

The review loaded the installed global and project rules. The installed global instructions and linked campaign, e2e-proof, and ocr-delegate skills resolve to central Agent-Skills checkout HEAD `0e846bfc577a51bd1a98a5606966aecda40320c2`; this differs from the previously advertised `35ba734135a64100b891f422d4ced9d76795ab57`, and the global file content hash is not equal to that advertised revision. No synchronization was performed. This records the reviewer's observed local state only and makes no claim about other Sessions or machines.
