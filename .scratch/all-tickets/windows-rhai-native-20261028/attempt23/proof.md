# Native Windows spawn baseline

The public Rhai script in `windows_spawn_child_can_be_polled_and_waited_through_clones` failed because Windows has no registered `spawn` function. The native Cargo test exited 101, printed `windows_spawn_contract_missing_public_spawn` and `ErrorFunctionNotFound("spawn (...` and reported one failed test. This is a RED baseline, not acceptance of the Child contract.

The test used 440 source files bound by manifest SHA-256 `f4fa142a2d74d69fe8bd821f890671f97ef3817bf04af74d03a77d461ea984e5`, baseline commit `797395b836b5ce33b79eb162e5bb8e25a2bcfe98` plus the test change, lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`, features `testing-environ,sys,metadata`, and native Windows Rust/Cargo 1.93.0. A Windows-target Rust 1.77.2 compile of the test before its final diagnostic-marker correction passed; it is compile-only evidence.

The bounded Driver exited zero after 89.693 seconds. The test's expected Cargo exit was independently checked inside the payload. Export contains 195 ordered frames and 12 hash-validated files. All eight journal record lengths and CRC32s verified through `REMOVED`; the exact inner runtime was removed. Host sdc was restored and this attempt's exact host stage and ISO were retired after hash, all-domain reference and fuser checks. The guest outer scope remains for evidence-first retirement. Existing native acceptance proofs remain scoped to their original source and cases.

A source review approved the bounded baseline packet before execution. Further implementation, a restored GREEN with independently observed real child and a combined change review are still required.
