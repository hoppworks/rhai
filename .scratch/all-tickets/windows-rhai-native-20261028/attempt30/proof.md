# Native Windows production spawn integration after probe addition

The integration tests compile the library without `cfg(test)`, so they execute the ordinary production `spawn` wrapper and `spawn_inner` on exactly the same source manifest as attempt29. The cached-snapshot wrong-exit control failed at its named assertion with Cargo 101 after exact OS-handle readback. Restored `sys_process_report` and `sys_process_windows` passed 7 + 17 tests, including spawn/clone/wait, direct drop and kill with buffered unread input. This validates the exercised production integration cases, not the test-build-only pending probe or remaining lifecycle requirements.

The shared 441-file manifest `9b25196001a371c010018d5f0277614c4d6c613d6bf4627a15a072145755470d` binds commit `3ae3c4dbb74c2060c9fb2322d8c08fbe95c1376c` plus the test-probe source changes, lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`, and `testing-environ,sys,metadata`; native Windows Rust/Cargo was 1.93.0. Rust 1.77.2 Windows-target check is compile-only.

Driver0 completed in 103.716s. Original export SHA-256 `d82e129d035e58dd4a3e0ed6a2e78c84e5514312bb93acdc7c4c97e45e57a312` contains 207 ordered frames and 13 hash-verified files. Eight journal lengths and CRC32s verify through `REMOVED`; exact inner runtime removed. Original sdc medium was restored; exact owned host stage and ISO retired after hash, all-domain reference and fuser checks. Guest outer scope remains for evidence-first retirement.

Combined independent review of attempts29/30 passed for this narrow package; see `combined-review.md`. Registry removal, uninstrumented public pending-I/O, other fault and drop paths, managed Jobs and native feature/MSRV matrix remain open.
