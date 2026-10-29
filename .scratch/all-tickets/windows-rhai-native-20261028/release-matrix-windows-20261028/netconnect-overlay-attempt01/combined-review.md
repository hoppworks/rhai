# Independent combined review: Net accepted-peer fixture correction

Verdict: **PASS for the corrected `tests/net_connect.rs` helper and the named native Linux, macOS and Windows Rust/Cargo 1.77.2 slices**. No actionable standards or specification finding remained.

The reviewer checked macOS attempt01's genuine `WouldBlock` at the independent IPv6 peer read, the narrow change that makes only the accepted peer blocking while retaining bounded reads and all assertions, and macOS attempt02's restored 5/8/7/10 suite with exact IPv6 bytes/EOF and deliberate peer-EOF RED101. The current helper was then checked on Linux: same overlay/lock, RED101, all five affected `net_connect` cases including IPv6 passed, and scoped export/cleanup passed. The unchanged Linux `net_listen`, `net_reads` and `net_writes` results remain applicable.

The native Windows package bound the same reviewed overlay and lock, ran separate Sys and Net profiles, rejected both deliberately wrong assertions (101), and passed 55 Sys and 30 Net tests including the current IPv6 case. Its observer reported `accepted:true` and Driver 0 after 100.847 seconds. The COM1 export was recovered across a pinned log rotation; 230 ordered frames, 19 original file hashes and an eight-state `REMOVED` journal checked. Guest own-scope absence, no named Runner/Driver and exact host ISO/stage cleanup with original `sdc` and foreign `sdb` readbacks close the custody path.

These results cover the stated package-alone and affected target slices. They do not establish sensitivity of every assertion, all feature combinations, process criteria, or the complete release matrix.
