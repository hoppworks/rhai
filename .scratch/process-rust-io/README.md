# Native Rust process-I/O acceptance prototype

Standalone prerequisite, not the production Rhai process API. Source copied byte-for-byte from reviewed `cc4af0e8734d244311b1418518cb3715a6cd2342`; raw evidence frozen at `cddc1c38229b14428585b3941d526ea2f17d6e0e` and retained once at `../process-rust-io-followup-evidence/msrv1772-20261001-055900UTC/`.

Native macOS arm64 with direct private Rust/Cargo/rustdoc 1.77.2 passed all thirteen fixed cases in one scoped invocation, wrapper exit 0: normal exact 2 MiB I/O, held-output/backpressured cancellation, missing-wake control, TERM/KILL custody, and stdout/stderr N/N+1 boundaries at caps 4096 and 0. TERM/KILL receipts establish process custody, not worker joins. The pipe holder is externally custodian-spawned; workload-spawned escape topology remains open.

Root independently verified exact payload hashes/prefixes, 34 raw log/lock/receipt/finalizer hashes, all 78 exported original PID/start identities absent, 48 source-owned or observed groups empty (28 actually sampled), private runtime absent, and all 101 sampler children terminal 0. Three short version commands use direct Popen terminal ownership; no start identity was queried. Sampled maximum 540,731,532 private bytes and 8 process resources; these are not continuous peaks.

The driver uses unique evidence paths and refuses reuse; do not rerun accepted proof merely to rename a Session. See `../all-tickets/process-native-followup-stop-review.md` for fixed limits, review and complete cause/allocation history. Linux/Windows adapters, production Engine/API, precedence, setup rollback, and broader topology require separate proof. Existing fixture source at `../process-prototype/` is byte-identical to the proof source.
