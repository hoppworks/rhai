# Darwin X26/X27 base-feature package

**Accepted scope:** Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2,
`testing-environ,sys`, base `8f333d196380def8ba902f549341e160f0ec7f05`.
Both exact integration tests ran sequentially in one bounded scoped invocation
and reused a single compiled target and pinned lock. Source/fixture/lock hashes,
commands and environment are in `run-info.txt`; raw output/status hashes are in
`SHA256SUMS`.

**X26:** `shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable`
passed 1/1. Independent fixture output records child exit code 17, stable wait
and try-wait snapshots, two post-completion kills, unchanged cached output and
exact-PID ESRCH. The accepted Darwin 1.93 expected-RED control transfers: its
recorded mutation targets this same assertion, the fixture is byte-identical,
and the completed-child kill path is unaffected by the intervening stdin-only
implementation changes.

**X27:** `shared_child_contract::nonfinal_child_clone_drop_keeps_the_real_child_available`
passed 1/1. The nonfinal clone remained operational; dropping the final client
with `kill_on_drop=true` terminated the child, and independent controller and
fixture observations plus the watchdog receipt confirmed ESRCH. Its accepted
Darwin 1.93 RED targets the same final-drop assertion with the same byte-identical
fixture and unchanged process implementation.

The combined independent Standards/Spec review passed. Both Cargo statuses and
runner status are 0. The exact scope was retired; no build/cache remains. These
are named partial rows only; other platforms, features, MSRVs, managed final-drop
scope and broader Ticket 03/release requirements remain open.
