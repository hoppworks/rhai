# Test harness correction record

The first 1.77.2 API test build exposed `i32` report getters as Rhai `i32` custom values, which did not compare with script integers. Changed both getters to `Dynamic::from_int` and added typed Engine coverage.

The next build compiled and ran 7 tests: 5 passed, including report snapshot mutation and absent/signal Engine reads; 2 error catch tests failed because the test incorrectly attempted to use `try` as an expression, first returning unit and then producing a parse error after a harness-only rewrite. Corrected those scripts to initialize a variable, assign it inside `catch`, then return it. These are test harness failures, not accepted implementation regressions; the corrected source remains to be proven.
