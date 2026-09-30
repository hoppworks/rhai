# TCP stream writes implementation state

## Goal and constraints

Implement the bounded write and half-close slice in
`/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/briefs/tcp-stream-writes.md`.
Owned worktree `/Users/hoppworks/projects/rhai-tcp-stream-writes`, branch
`task/tcp-stream-writes`, base `e0dd28ec7844d2b5b88910387fca13447424d7d0`.
Actual start: 2026-09-30 14:05:27 UTC. Inclusive deadline/review: 15:05:27 UTC.
Per invocation <=900s, private storage <=2 GiB, Cargo jobs=2, <=16 sockets/handles
per serial fixture. No remote write, push or merge. Any commit must use command-local
`git -c user.name=hoppworks` and the configured email `daniel@hoppworks.de`.

## Current snapshot (2026-09-30 14:48 UTC)

Implementation is complete and immutable review is requested. Local commit
`44275bf83dc1cb7f4a9ba707ed73a6c27209d0fc` is on `task/tcp-stream-writes`; author and
committer both verify as `hoppworks <daniel@hoppworks.de>`. Source worktree status is
clean apart from the untracked evidence folder. No push or merge was performed. Design was sent before
code: one-shot string/blob writes return the accepted prefix count; write-all loops and
returns full count or `NetError.partial_bytes`; host default deadline 5 seconds, script
may shorten, host cap <=1 MiB, checked Engine cap further lowers input; shared directional
idempotent shutdown leaves the other direction open. A short shutdown mutex protects only
the syscall/state transition; polling I/O holds no lifecycle lock.

Source changes: `src/packages/net/{config,listener,mod,stream}.rs` and
`tests/net_writes.rs`. Public docs describe deadline, caps, one-shot/write-all counts,
partial errors and half-close. Accepted-stream write/readback is covered.

Meaningful Engine RED: `.scratch/tcp-stream-writes/evidence/diagnostics/.scratch-tcp-red-engine2.log`
shows missing `write_string` before registration. Main `net` matrix: 10/10 passed in
`evidence/final-matrix/net.log`; `no_index`, `unchecked`, `metadata`: 10/10, 9/9, 10/10
in same directory. Corrected host-byte-vector no-index missing-overload test passed 1/1
from private source in `evidence/final-private/no-index.log`.

The accepted sync cancellation proof is `evidence/sync-saturation/sync.log`: both changed
sync fixture tests passed serially (2/2). The writer performs repeated 64 KiB calls up
to a 64 MiB aggregate limit and test-only notification proves a real socket `WouldBlock`;
close then unblocks it and the peer's bounded readback equals complete counts plus final
partial count. The original one-call saturation assumption did not always cause
`WouldBlock`; failure diagnostics remain at `evidence/final-private-serial/sync.log`.

Deliberately wrong blob expectation failed with expected `[0, 254, 65]` versus actual
`[0, 255, 65]`, exit 101; corrected assertion passed. See `evidence/post-matrix/` and
`evidence/final-matrix/wrong-control.log`. The initial exact-filter sync run selected
zero tests and is not proof. Detailed full-stack proof and cleanup readback:
`evidence/proof.md`, `evidence/cleanup-readback.txt`.

All accepted builds used private scoped source/cache/target and completed runner paths
were checked absent. One failed diagnostic command accidentally compiled from the owned
checkout, creating ignored `Cargo.lock` and `target/` at 14:42 UTC; exact deletion was
rejected by the shell safety hook with `rm -f style commands are not permitted. Use a
safer approach`; the rejected command was `rm -rf -- target Cargo.lock`. Those artifacts
remain at 32 KiB (`Cargo.lock`, 30,522 bytes) and 457 MiB (`target/`). Do not bypass that
hook; parent should classify them or request approval. They contain no source changes.
Root-level diagnostic logs
were moved under `evidence/diagnostics/`.

Environment for accepted feature matrix: macOS arm64, Darwin Kernel 27.0.0,
`rustc 1.93.0 (254b59607 2026-01-19)`. Peak disk usage not measured; private storage
limit 2 GiB per invocation, max Cargo jobs 2. Native Linux/Windows, project MSRV and
broader release matrix remain release gates.

## Cause and launch history

- Early REDs and fixture/compiler corrections are detailed in preserved `.scratch/tcp-stream-writes/evidence/diagnostics/` logs. The Engine RED is the meaningful expected failure.
- Main matrix's reported bundle exit 1 came from a summary grep formatting mismatch, not test failures; each feature status was separately inspected. Main matrix's sync filter selected zero tests and is excluded from proof.
- A later source-copy sync test passed one cancellation test. The no-index corrected exact-overload test passed separately.
- Combined sync run exposed one-call non-deterministic backpressure: first 1 MiB write may fit in OS buffering. A subsequent serial rerun reproduced that fixture issue. Changed the bounded fixture to repeated host-bounded 64 KiB writes (max 64 MiB); final serial run passed both sync tests, including actual `WouldBlock`.
- One diagnostic wrapper omitted private source/Cargo path setup; it compiled the owned checkout, generated ignored `Cargo.lock` and `target/`, and then this Session's exact cleanup request was rejected by the tool safety hook. Kept logs and files; no workaround. This resource issue is disclosed and local only.
- Scoped-run invocation and resource evidence: `evidence/cleanup-readback.txt`. No current scoped process remains.

## Completed handoff

Final `rustfmt --edition 2021` and `git diff --check` passed before source commit
`44275bf83dc1cb7f4a9ba707ed73a6c27209d0fc`; exact sync and no-index logs show 2/2 and
1/1. Evidence/current state is retained here and will be committed as a separate
documentation-only commit. Source author and committer were verified as
`hoppworks <daniel@hoppworks.de>`. The exact cleanup rejection, command and measured
artifact sizes are retained in `evidence/cleanup-readback.txt`; ignored `target/` and
`Cargo.lock` remain in the owned checkout for parent classification. No remote push or
merge occurred. Handoff complete within the original 15:05:27 UTC inclusive deadline.
