# Native Windows kill with buffered unread input

A Rhai `spawn` sent 1 MiB to a real child that read exactly one byte and then stopped reading. The child independently reported at least 8191 unread bytes via `PeekNamedPipe`; this run reported 12288. Two handles requested `kill`, subsequent waits returned matching exit status, and an independently opened exact process handle signaled exit 1. A further kill after completion returned normally. An intentionally wrong exit-0 assertion failed with Cargo 101 after the exact-handle readback; restored full `sys_process_report` and `sys_process_windows` tests passed 7 + 15.

This shows cancellation with unread buffered input, not that a particular overlapped write was pending at the instant of cancellation or the actual pipe capacity. Pending-write cancellation still needs synchronized evidence. The false assertion controls exit readback, not write-cancellation sensitivity.

The tested source has 441 manifest-bound files at commit `3dcef0438129b6d31a42aa750cbe27b22a475e96` plus the test change; manifest SHA-256 `dc3974da778c1821d4f9e9c3121471c0d8e346f7bfc53af6a870cb6290a52327`, lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`, features `testing-environ,sys,metadata`, native Windows Rust/Cargo 1.93.0. Windows-target Rust 1.77.2 checked compilation before the test-only rename; no native MSRV claim.

The bounded Driver exited zero in 125.005 seconds. Original export SHA-256 `29ef85577cb9f5bf668935f9db85710255197c98aa7862eac96e449a36185067` contains 206 ordered frames and 13 hash-verified files. All eight journal lengths and CRC32s verified through `REMOVED`, and the exact inner runtime was removed. The original sdc medium was restored; the exact owned host stage and ISO were retired after hash, all-domain reference and fuser checks. The guest outer scope is retained for evidence-first retirement.

Independent combined review passed for this narrow slice; see `combined-review.md`. Inherited pipes, final-drop policies, concurrent wait/kill, explicit pending-write state, panic/handoff faults, managed Jobs, native MSRV and other feature profiles remain open.
