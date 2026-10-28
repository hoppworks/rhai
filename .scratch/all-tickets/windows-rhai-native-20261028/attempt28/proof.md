# Native Windows child result snapshot isolation

After a real child wrote its PID, an independently opened exact Windows handle confirmed exit 7. In a Rhai script, `child.wait()` returned a map whose `code` and `stdout` were mutated. A subsequent `sibling.wait()` returned the original exit and independently specified lossy stdout. A deliberately wrong cached-exit expectation failed with Cargo 101 after exact-handle readback; restored `sys_process_report` and `sys_process_windows` passed 7 + 17. This is limited to the named fields and does not prove all possible map mutations.

The 441-file source manifest `d31ea18921d23311160816afec6d2ee280d1f66acec86f58c3d1e8ad3e032a98` binds commit `173b49e447ecb1e61b7c0e6670eff9e530e64a30` plus the test change, lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802` and `testing-environ,sys,metadata`; native Windows Rust/Cargo was 1.93.0. The Windows-target Rust 1.77.2 check preceded the final test-only assertion and script-scope correction; it is compile-only.

Driver0 completed in 119.985s. Original export SHA-256 `1ec31b60f7171916f374ce48ae95523029025aee2471d4a6de9abb3c525e6388` contains 207 ordered frames and 13 hash-verified files. Eight journal lengths and CRC32s verify through `REMOVED`; exact inner runtime removed. The original sdc medium was restored, and exact owned host stage and ISO retired after hash, all-domain reference and fuser checks. Guest outer scope remains for evidence-first retirement.

Combined independent review passed for this narrow slice; see `combined-review.md`. Pending-write cancellation, drop retirement, other fault paths, managed Jobs and native feature/MSRV matrix remain open.
