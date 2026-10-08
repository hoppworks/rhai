# Attempt 02 post-run classification

The scoped Cargo build completed, and the intended test ran on Darwin arm64/macOS 27.0.1 with Rust/Cargo 1.93.0 and features testing-environ,sys. The deliberately changed expected bytes produced the intended assertion failure: actual stdout ended with the byte sequence for stdin-eof, while the mutant expected stdin-not-eof. The test result was 0 passed, 1 failed, exit 101.

The attempt's wrapper then misclassified this as red_control_not_confirmed because it required the libtest test-name line and FAILED marker on one line. With --nocapture, the panic output is interleaved before libtest prints its terminal FAILED marker. Independent checks of the raw log confirm the test ran and failed at the expected equality assertion. This is valid expected RED, not a product failure or infrastructure stop.

GREEN was not run in that invocation. The restored test source matches the committed source at bcb524b866103f9a684b8da41725c802a00d2458: SHA-256 7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017. The project-private runtime and exact session scope were removed. Reuse the existing RED; the next run should execute only restored GREEN from the same committed source and accepted lock.
