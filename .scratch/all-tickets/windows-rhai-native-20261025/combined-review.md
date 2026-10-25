# Combined independent review: native Rhai attempts 01–03

Verdict: **PASS for the saved partial evidence and OPEN classification**, 2026-10-25. This is not a whole-Windows or A–F acceptance verdict.

The reviewer recomputed attempt01's 95-frame/nine-file original export and 143,956-byte raw serial hash, and attempt02's 101-frame/nine-file original export and 158,429-byte raw serial hash. File hashes and lengths matched both readback records. Attempt01's Cargo stderr places the path-length failure before test execution. Attempt02's original stdout contains the real independent host-file readback, intended `assert_eq` RED and failed summary, followed by restored GREEN and one-pass summary. Its four-record journal, Driver exit 2 and missing removal receipt keep lifecycle acceptance open. Attempt03's host pre-entry hashes and screenshot show the PowerShell pin mismatch rejected before Driver/Cargo; no product result was inferred.

Review limitation: the earlier SOURCE READY review of attempt03 did not spot the transcribed external PowerShell hash. The guest's executable identity guard stopped the run safely. A future attempt must compare the full machine-readable hash before binding the new medium.
