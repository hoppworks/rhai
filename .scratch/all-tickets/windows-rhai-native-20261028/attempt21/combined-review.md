# Combined independent review: Windows stdin

**PASS** for the named native Windows direct-child Blob round-trip with
concurrent output and timeout with unread stdin under Rust/Cargo 1.93.0,
`testing-environ,sys,metadata`. The reviewer checked the implementation's
buffer/OVERLAPPED ownership, chunked writes, termination and retained-owner
paths by inspection; reviewed the test fixture and packet before execution;
and checked the current 440 source hashes, original 16-file export, intended
RED controls, 9 unit and 7 + 11 integration GREEN, exact child-handle
observations and Driver custody. The test reads and asserts the child's input
file; its contents are not an exported artifact.

The coordinator independently checked the eight journal record lengths,
CRC32s and state order, reconstructed the original serial bytes across the
recorded rotation, restored the original sdc and retired the exact owned host
stage/ISO. The reviewer did not independently repeat those coordinator checks.
The public unread-input test does not establish a pending write; the pending
write/cancel assertion is limited to the real-pipe helper test. Input aggregate
memory bounds under `unchecked`, public early-close and pending-write
cancellation, partial/fault paths, other features/toolchains, managed scope,
Ticket03 and release remain open.
