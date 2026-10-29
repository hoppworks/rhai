# Independent combined review: Windows package-alone profiles

Verdict: **PASS for the recorded Windows Rust/Cargo 1.77.2 `testing-environ,sys` and `testing-environ,net` cases only**. The reviewer found no remaining actionable issue after final cleanup readback.

The reviewer checked the source/lock/VM binding, original COM1 export, exact Sys and Net RED101 assertions, restored 55 Sys and 30 Net passing tests, original payload markers, eight-state Runner journal, Driver exit/custody, and separate guest/host cleanup receipts. The original observer's `accepted:false` is preserved. It required literal `wrong expectation` in the Sys RED log; the actual assertion printed those words as byte values. `corrected-parser-replay.json` decodes the expected bytes and checks the original results without rerunning native tests.

The guest screenshots show removal of only the owned scope and a separate absence/process readback. Host cleanup and fresh readback show the owned stage and ISO absent, original `sdc` restored, and foreign `sdb` unchanged. The review does not accept the complete release matrix, all process cases, or a false-green control for every assertion.
