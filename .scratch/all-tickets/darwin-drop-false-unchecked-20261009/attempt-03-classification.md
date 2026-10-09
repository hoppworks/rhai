# X28 attempt 03 result classification

The Cargo test itself passed: `green.status` is 0 and the raw log ends with
`test result: ok. 1 passed; 0 failed`. The real public-Engine child remained
alive after both public handles were dropped, acknowledged the independent
challenge, wrote a completion record for exactly 524288 stdout and 524288
stderr bytes, and its exact PID later returned ESRCH. The fixture cleanup also
records ESRCH.

The scoped runner returned 1 only after Cargo passed. The wrapper searched for a
single-line `test <name> ... ok` marker, but `--nocapture` interleaved the
test's diagnostics on that line; Cargo printed the authoritative success summary
separately. This is a post-assertion output-classifier failure, not a test or
product failure. No rerun is needed: the saved RED and GREEN are bound to the
same base revision, source bytes, lock, features, toolchain and native host, and
the exact owned runtime/scope were removed.
