# Native Windows Managed parent-CWD regression: attempt58

## Binding and outcome

- Fork-main base: `c62a0a99113beb51601ee9ea39656367fe7b51c5`; candidate source manifest SHA-256 `d65351e9855e5f4ac8f56626aa058abda34629c8a7c0eb8378e10ae0192d9abf`; lock SHA-256 `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
- Native Windows VM `rhai-win11-quality`, Rust/Cargo 1.93.0, `testing-environ,sys,metadata`; private source and Cargo target in owned `n-0cea30ae` scope. The original `source-manifest.json`, `build-manifest.txt`, command, logs and observer are in `original-export/` and `media-input/`.
- Public Rhai `run_raw` in Managed scope found `rhai-managed-cwd-probe.exe` only in the controller's current directory, with cleared child environment. An independent child-written record identified the copied executable and child PID. The controller's parent current directory was unchanged.
- The deliberately wrong executable-path assertion exited 101 at `deliberately wrong Managed cwd executable expectation`. The restored targeted test exited 0. The full `sys_process_windows` target passed 31 tests, 0 failures. Exact logs: `original-export/run/.scoped-evidence-a65c18b059f04a79814d5ddc9caa96d5/runtime/{wrong,green,suite}.log`.
- The native observer reported `accepted=true`, `driver_exit=0`, `product_test_run=true`, owned executables stopped, no pending custody and no observer kill. This is a narrow test outcome; `product_acceptance=false` remains the campaign-level flag. Eight length/CRC journal transitions end at `REMOVED`. The serial export decoded 202 frames, 14 hash-checked files and 169626 bytes.
- The owned host ISO and stage were removed after original sdc restoration, domain reference and fuser checks. The foreign sdb was untouched; see `host-cleanup-readback.txt`. Guest outer evidence scope `n-0cea30ae` remains for exact evidence-first retirement.

## Diagnostic RED and review

Attempt57 ran the pre-fix public test and failed at the intended missing-program assertion. Its Driver stopped before strict acceptance because its parser sought a controller panic in the outer test log. Preserve attempt57 as diagnostic TDD RED, not accepted E2E. The independent combined reviewer checked source/lock/features, the wrong assertion, independent child readback, full target, custody and cleanup, and found no further concrete blocker for this bounded fork-main package. Wider Windows search ordering, real OS fault injection, permanent Job refusal, short-lived membership races, other feature/toolchain profiles and release acceptance remain open.
