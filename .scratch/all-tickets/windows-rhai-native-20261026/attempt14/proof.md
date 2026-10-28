# Native Windows direct-child and timeout-boundary acceptance

Attempt14 used 439 source files (manifest SHA-256
`9fca341276f27e2f742d02744e6856d33870f20a4ec4f614eaf09733044e7d35`,
archive `0025ad72c48a869a5c0e7fb3c328ab17ed336f0a5677bebccb271ce21e85d9a2`),
candidate lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`,
and the fresh public BuildOnly manifest `8c625daf866e4bb5e30259b9fb3d27cafcb4e8e5ee813a5b07b6a5e4160ee0d1`.
Current selected source bytes match the archived manifest. The same archive passed
Rust 1.77.2 Windows-target `cargo check --locked --tests` in an owned POSIX
scope; `cross-check-unit.log` records that check. Independent pre-execution
source review found no actionable issue.

One native Driver on the RhaiTest VM exited 0 in 159.266 seconds. The original
COM1 segment is 360,752 bytes (SHA-256
`c58a38aa6b7278691d32845b39217e6e28062ec1b4636aaf311441fcf162cf0b`),
with 214 ordered frames and 15 hash-verified original files. The observer has
exact exit, drained pipes, disposed handle, no pending custody or observer kill,
and stopped owned executables. All eight journal lengths and CRC32s validate,
ending in `REMOVED`; Driver output reports the exact runtime removed.

The wrong-exit assertion produced its intended RED. The focused Windows deadline
overflow test produced its intended wrong-expectation RED and restored GREEN.
The integrated native test command then passed seven `sys_process_report` and
four `sys_process_windows` tests. The public Engine/host/OS test observed exact
raw output, child-written records and independently opened Windows child handles
with exit codes 0 and 7. The out-of-`Duration` timeout was denied before spawn:
`timeout_range_child_record=None`. Commands, feature flags, toolchain, original
logs, host preflight, binding and the full file inventory are preserved here.

Combined independent review: [combined-review.md](combined-review.md). The
accepted scope is direct-child `run_raw` normal success/nonzero/raw capture,
normal reaping, public out-of-range denial and the checked deadline overflow
branch. Managed Jobs, `run`, `spawn`, stdin, real short-timeout cancellation,
output overflow, exceptional cleanup, broader Windows process paths and the
release matrix remain open. The VM's sdc was restored to its original medium;
the three exact host staging directories and media were retired after hash
readback and all-domain reference checks (`host-cleanup-readback.json`). Guest
originals remain pending exact owned retirement.
