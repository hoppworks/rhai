# Darwin unchecked output-cap attempt 01

The scoped runner stopped while compiling the integration test, before the host-cap assertion or fixture ran. The new Darwin stdin test was still enabled by its cfg under `unchecked`, where `Engine::set_max_string_size` does not exist. Cargo exited 101; the wrapper returned 1 before GREEN. This is a test-matrix compile/setup failure, not product RED, product failure, or acceptance. Raw compiler output and statuses are retained in the `attempt-01.*` files; the exact owned session scope was retired empty.

Correction: gate the Darwin stdin-specific test and its private helpers with `not(feature = "unchecked")`, then compile the unchecked host-cap selector on the corrected current test source.
