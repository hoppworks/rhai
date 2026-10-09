# X25 Darwin `testing-environ,sys,unchecked` — Rust/Cargo 1.77.2

**Review pending.** The focused public-Engine contract
`managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel` ran on
Darwin arm64/macOS 27.0.1 (kernel 27.0.0), Rust/Cargo 1.77.2.

RED inverted only the `members_gone` expectation. The test observed leader,
worker and leaf `ESRCH`, the unrelated sentinel still live, and successful
bounded wait before the named assertion failed; fixture cleanup then reaped
the exact sentinel. Cargo status 101. RED log SHA-256:
`9bdaf483d77fdfd323e41b19da3a7a88160acf4365c9e2130e0e998a7f887393`.

Restored GREEN passed 1/1. It observed all three managed processes absent,
sentinel live at return, a non-unit bounded wait result, and sentinel status
plus exact `ESRCH` after cleanup. Cargo status 0; GREEN log SHA-256:
`4b3ed75d20306a3c97386648df3e112502248ddbdb61cc7657c93c172efe2a72`.

Both runs bind lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` and Unix
product source SHA-256
`7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`. RED
test-source SHA is the isolated one-assertion mutant; restored GREEN matches
current source SHA `a8fdc21e73b56bf12c82603c941b7c22b01c942a56d5f649ff2ec98b494c935c`.
Environment versions, raw logs, statuses and hashes are in this attempt
directory. Runner status 0; `scope-cleanup.txt` records exact owned-scope
retirement after private runtime removal.

This row covers only X25 on this Darwin profile. Other feature, OS/MSRV rows and
the rest of Ticket 03/A–F remain open.
