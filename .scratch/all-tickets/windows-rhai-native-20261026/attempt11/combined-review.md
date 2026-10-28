# Combined independent review: Windows direct-child `run_raw`

Result: **PASS for the named native normal-completion slice** at the exact
attempt11 source and lock. This does not close Windows process, Ticket03 or
release acceptance.

The reviewer checked the 439-member source archive against its manifest and the
current worktree, the pinned `Cargo.lock`, the accepted fresh public BuildOnly
receipt and exact Runner/Driver binaries. The original serial export has 204
ordered frames and 13 hash-verified files. The wrong-exit assertion produced the
intended RED (Cargo exit 101); restored GREEN ran 7 `sys_process_report` tests
and 2 `sys_process_windows` tests. The public Rhai Engine test separately opened
real Windows child process handles and observed exit 0 and 7, exact raw stream
bytes and child-written records. Driver exit 0, drained pipes, eight valid
journal transitions, runtime removal and no pending custody were confirmed.

**P2 open finding:** `src/packages/sys/process/windows/mod.rs` forms an optional
deadline with `timeout.and_then(|d| started.checked_add(d))`. An otherwise valid
duration beyond the platform `Instant` range becomes `None` and silently disables
the timeout. The normal-completion result is unaffected; timeout acceptance stays
open pending a public regression and correction.

Acceptance boundary: direct-child `run_raw` success/nonzero exit, raw capture and
normal reaping only. Managed Job scope, stdin, `spawn`, timeout/cancellation,
output overflow, inherited descendant pipes, exceptional cleanup, native Windows
Rust 1.77.2 and remaining process cases are unverified here.
