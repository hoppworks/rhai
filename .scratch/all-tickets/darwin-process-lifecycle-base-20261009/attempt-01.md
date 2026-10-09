# Darwin X28/X29 base-feature package

**Accepted scope:** Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2,
`testing-environ,sys`, at source revision
`62a238ce6527d6efb838611dfab4b92ec9dc2bbf`. Both exact-filtered integration
tests ran sequentially in one bounded scoped invocation and reused one compiled
`sys_process` target and pinned lock. `run-info.txt` identifies commands and
sources; SHA-256 values for all exported results are in `SHA256SUMS`.

**X28:** `direct_spawn_kill_on_drop_false_preserves_child_and_capture` passed
1/1. After the last public child handle and Engine were dropped, the child
remained alive and acknowledged a challenge. Its independent completion record
reported 524288 stdout and 524288 stderr bytes; exact-PID ESRCH followed natural
completion. The expected assertion RED and identity-checked exceptional
SIGKILL/ESRCH cleanup are reused from attempt06 in
`../darwin-drop-false-unchecked-20261009/attempt-06.md`. Combined review verified
the source, assertion and cleanup guard are byte-identical and not gated by
`unchecked`, so this transfer is valid for the base feature set.

**X29:** `shared_child_contract::script_throw_drops_and_reaps_a_live_child`
passed 1/1. The public Engine threw with a live child; a fresh challenge was
acknowledged, `try_wait()` still reported a running child before the throw, the
wrong-message control was rejected, and independent controller/fixture ESRCH
plus the watchdog closure receipt were observed.

Both Cargo statuses and the runner status are 0. The exact owned scope was
retired and no cache remains. Combined independent Standards/Spec review passed
for both named Darwin rows only. Other feature, platform and toolchain rows,
remaining Ticket 03 requirements and release closure remain open.
