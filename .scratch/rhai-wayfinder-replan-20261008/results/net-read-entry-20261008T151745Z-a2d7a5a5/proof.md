# Actual public read entry and clone-close cancellation

Darwin arm64 and Linux x86_64, Rust/Cargo1.77.2, accepted v3 lock
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
Source is the frozen ef423 archive plus explicit owned patch through 19c3 and the
hash-bound two-file GREEN overlay. Foreign shared child fixture is excluded.

Meaningful Darwin test-first RED101 requires `read_wait`, observes the old worker
`thread_started`, and fails the exact readiness assertion before public close.
GREEN0 on both native OSes in `sys,net,sync` and
`sys,net,no_index,sync,metadata` receives a one-shot host-only testing-environ
notification from the actual nonblocking socket read WouldBlock branch, confirms
its result channel is still empty while the independent peer is open without
sending data, then closes a script-visible clone. Read cancellation occurs before
its two-second host deadline, the reader joins, quota permits a second public
connection, its independent peer observes EOF, and the peer joins. Exact --list
binding, command cwd, compiler/executable/source hashes and original markers are
retained. Cleanup guards close and join on assertion failure; finite outer scopes
were retired after originals were exported.

This repairs the outstanding-read evidence gap identified in the combined Darwin
semantic review. The unchanged semantic rows are reused, not repeated. The hook
is Rust-host-only, doc-hidden, testing-environ gated, not a script function; it
changes neither socket behavior nor production builds without that feature.
Independent combined review is appended to the existing Darwin report before
acceptance/integration. Windows read cancellation remains open.
