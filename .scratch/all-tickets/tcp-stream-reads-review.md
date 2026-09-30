# TCP stream read source review

Initial mutable candidate reviewed on 2026-09-30 before integration. OCR delegate preview selected seven Rust files: config.rs, error.rs, listener.rs, mod.rs, stream.rs, tests/net_connect.rs and tests/net_reads.rs. All seven reviewed against resolved Rust rules, zero skips. Local Markdown/proof reviewed separately on final submission.

Findings delivered to responsible context; final immutable source and affected live proof still required:

- Compute lossy decoded UTF-8 length without allocating expansion before checking Engine string limit. Existing from_utf8_lossy already allocates before checking. Prove exact ResourceLimit and consumed partial count through host readback outside constrained Engine evaluation.
- Bounded EOF blob errors must identify read_to_end_blob, not read_blob.
- Close after partial EOF-loop progress must return cancellation error with actual count, rather than successfully treating local shutdown as peer EOF.
- Sync read cancellation proof must observe actual waiting operation, not a message sent before Engine evaluation. Use approved test seam or independently observable readiness, no fixed sleep.
- Bound host fixture accept/read/join paths and preserve cleanup on assertion failure.
- Add unchecked host-cap verification; checked tiny Engine test is inapplicable under unchecked.

Launch6 net, sync and no_index suites and deliberate wrong actual-peer expectation are reported green/expected-failing. Those results are preliminary until final log review and do not cover subsequent changed implementation. Prior RED and every setup/failed assertion remain in responsible state. Original deadline14:17:48 UTC includes final review. No new correction package or history reset.

## Final acceptance — 2026-09-30

Accepted source4057a537 + test followup525737fd. All seven selected Rust files reviewed, no skips. Nonallocating lossy-length scanner matches UTF-8 error segmentation; decoded expansion checked before allocation. Correct EOF operation, shared cancellation after progress, checked/unchecked/no_index bounds and inherited accepted-stream policy assessed. Launch13 actual logs verify net struct1/connect4/read7, sync unit2/connect4/listen8/read8, no_index struct1/read7. Launch14 verifies unchecked struct1/connect4/read7 and deliberate actual a�b versus wrong peer payload assertion failure101. Followup15 passes actual-WouldBlock-after-captured-byte cancellation1; notifier race fixed, unit accepted peer blocking. Product unchanged, reuse unaffected launch13/14. Independent exact absence checks: ngaey2l4,2w9ctgxb,a4847cob,cos0tyn7,1j573515. Proof moved without duplication to ../tcp-stream-reads/. Latest launches have no peak samples; resource-cap measurement remains unverified, no peak claim. Native macOS slice accepted; other OS/MSRV/release gates and writes/half-close remain open.
