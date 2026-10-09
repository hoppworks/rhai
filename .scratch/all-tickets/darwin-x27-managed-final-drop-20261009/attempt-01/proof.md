# X27 Darwin managed final-clone drop — Rust/Cargo 1.77.2

**Combined review passed.** Scope is the exact public-Engine test
`managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not` on
Darwin arm64/macOS 27.0.1 (kernel 27.0.0), Rust/Cargo 1.77.2, with
`testing-environ,sys`.

RED changed only the final `all_gone` expectation to its inverse. The real test
observed all three managed members absent after final clone drop while the
unrelated sentinel remained live; the intended assertion then failed with its
named panic. Cargo status 101. Its sentinel was killed, waited, and independently
observed ESRCH; fixture leader, worker and leaf cleanup also logged ESRCH.
RED log SHA-256:
`0b23a5e6072592ac4b8d35f54004c281347f78ae879fe7da1af5da763d7db5c2`.

Restored GREEN passed 1/1. It independently observed the leader, worker and
leaf all live after dropping a nonfinal clone; all three absent after final
clone drop; the sentinel still live at that boundary; and exact sentinel reap
afterward. Cargo status 0. GREEN log SHA-256:
`3355725bde8b13bbf01990765bdb778ee9ce7480108a27db3fb11d378b003b3e`.

Both runs bind lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` and Unix
product SHA-256
`7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`. The RED
test-file SHA is the isolated assertion mutant; restored GREEN matches current
`tests/sys_process.rs` SHA
`a8fdc21e73b56bf12c82603c941b7c22b01c942a56d5f649ff2ec98b494c935c`. Runner
status 0. `scope-cleanup.txt` records retirement of the exact owned scope after
the runner removed its private runtime.

Environment and complete hashes are in this attempt directory. This is a
partial X27 Darwin base-profile row only; direct-child drop, other platforms,
feature/MSRV combinations, Ticket 03 and A–F remain separately scoped.
