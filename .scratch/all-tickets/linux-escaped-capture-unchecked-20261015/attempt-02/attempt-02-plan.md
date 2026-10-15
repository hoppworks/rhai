# Attempt 02

The first Cargo invocation did not reach either selected test. It failed because two stdin integration tests called `Engine::set_max_string_size`, intentionally absent when `unchecked` is enabled. They now call that API only under `not(feature = "unchecked")`; the large stdin fixtures remain available in unchecked mode. The source copy overlays the exact current modified integration test file after archiving HEAD, saves that corrected source baseline, mutates only the two named acceptance assertions, and restores that baseline before GREEN.

This one bounded invocation will run both assertion REDs and both restored GREENs for X38/post-reap at Linux x86_64, Rust/Cargo 1.77.2, `testing-environ,sys,unchecked`. Attempt 01 remains preserved as a pre-assertion compile failure.
