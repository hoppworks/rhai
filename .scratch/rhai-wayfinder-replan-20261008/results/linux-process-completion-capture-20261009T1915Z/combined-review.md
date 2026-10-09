# Combined review — Workhorse Linux process lifecycle

**Decision: ACCEPT, limited to the twelve named selectors in these four proof packets.**

Reviewed packets:

- `../linux-managed-spawn-lifecycle-20261009T1850Z/`
- this packet, `linux-process-completion-capture-20261009T1915Z/`
- `../linux-zombie-false-drop-20261009T1940Z/`
- `../linux-x34-reaper-20261009T1830Z/`

All four bind to revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`, source
archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644`,
`tests/sys_process.rs` SHA-256
`86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`, lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, Workhorse
Linux x86_64, Rust/Cargo 1.77.2, and `testing-environ,sys` with defaults. Each
packet manifest verified. The current integrated checkout has the same process
test source.

Each of the twelve exact selectors has an intentional wrong-expectation RED
(exit 101 at its named assertion) and a restored-source GREEN (exit 0, one exact
selector). The REDs are assertion controls, not product or runner failures.
Original output supports the claimed real-process observations: leader/worker/
leaf and process-group lifecycle, PIDFD exit and exact reaping, retained custody
for held zombies, unrelated sentinel survival, and bounded pipe cancellation
with `EPIPE` observations for escaped writers. The zombie return is the accepted
incomplete-cleanup error under retained ownership, not a false success. Each
owned session scope was read back with the same identity, empty after export,
and retired; panic-path cleanup is also recorded.

No material finding applies to the twelve named Linux selectors. This review
does not close other process selectors, features, Darwin/Windows, interruption
custody, or packages A–F as a whole.

Reviewer: `/root/linux_e2e_review`, after reloading project rules, memory
entrypoints, and current relevant skills. This review was read-only and ran no
builds or tests.
