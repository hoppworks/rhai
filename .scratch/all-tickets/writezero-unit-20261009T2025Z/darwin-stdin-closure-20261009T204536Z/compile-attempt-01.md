# Darwin stdin compile attempt 01

The scoped Cargo invocation stopped while compiling the new integration-test helper, before the test executable or fixture ran. Rust reported E0596 at `factors.try_fold`: the iterator binding needed to be mutable. This is a source compile failure, not expected RED, product RED, or acceptance. Runner exit was 1; the exact private scope was empty and retired. The full compiler output and statuses are retained in `compile-attempt-01.log`, `compile-attempt-01.status`, `compile-runner.status`, and `compile-scope-cleanup.txt`.

Correction: make only the local `split('*')` iterator binding mutable. No assertion, product code, lock, feature or run limit changed. A fresh scoped build is required because the prior private target was removed on runner exit.
