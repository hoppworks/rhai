# Combined independent review: Windows no_index scalar

Standards: PASS for the scoped test and execution inputs; no actionable finding.

Spec: PASS only for the named Windows Rust 1.77.2 `testing-environ,sys,net,no_index` cases. The test hash matches the sole source overlay; the 448 unchanged archived files were compared to base `e0ec6fae0` during preparation. Four original controls reached their chosen Direct/Managed wrong hostname or denial assertions, and the final suite passed 3/0. The reviewer inspected the original logs and observer but did not independently re-hash all source files or repeat the frame/CRC verification.

The runtime comparison applies to the observed ASCII hostname and environment; it does not establish Unicode, codepage or DNS/NetBIOS equivalence generally. The test does not independently observe exact child handles or prove no spawn on denied options. `run_raw` absence has no separate wrong control. Array overloads, broader R3 and release matrix remain open. No tests were run by the reviewer.
