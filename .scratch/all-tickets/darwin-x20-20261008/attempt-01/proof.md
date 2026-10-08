# Ticket 03 X20 — Darwin partial acceptance

## Scope

This proof covers X20 (a deadline is not reached and the process API returns a normal result) for the named Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys` row at source revision `17021f5d3976501cd8e04dfe56aeb7e00967c431`. It closes no other operating system, feature, or MSRV row.

The test is `tests/sys_process.rs::run_io_contract_empty_output`, which invokes `run(...)` through the public Rhai `Engine` with a five-second deadline and a real `/bin/sh` child. It asserts `success=true`, `code=0`, `timed_out=false`, complete stdout/stderr, and empty captured output. The child writes its PID and exit status to a fixture file. The test checks `kill(pid, 0) == -1` and `errno == ESRCH` before returning.

## Native result and sensitivity

A bounded `tools/run_scoped.py` invocation used one Cargo job. The native test command was:

```text
cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process run_io_contract_empty_output -- --exact --nocapture --test-threads=1
```

The private test-source mutation inverted only the `timed_out` assertion from false to true. Its source hash was `9dcb76f4eb86d0f03c2c23f79bc2e8d0be66302909d4d8908f18170d52a96da7`; the accepted baseline test-source hash is `7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017`. The mutated run exited 101 with 0 passed/1 failed at the intended `timed_out` assertion. The original source hash was restored before the GREEN run, which exited 0 with 1 passed/0 failed. Raw logs preserve both results.

libtest interleaved the test name, `--nocapture` output, and final status across lines, so the launch wrapper's same-line matcher returned a false negative for both RED and GREEN. The raw logs and exit statuses are authoritative and prove the expected RED and restored GREEN. The classification was corrected from those outputs without rerunning either command; raw logs remain unchanged.

The GREEN output records `success=true`, `code=0`, `timed_out=false`, complete empty captures, child record `child-pid=83117 child-exit=0`, and `child_reaped=true`. The test itself independently verifies ESRCH. A later exact-PID readback also found PID 83117 absent.

## Inputs, resources, and cleanup

- Accepted lock SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- OS/architecture: macOS 27.0.1, arm64.
- Toolchain: Rust/Cargo 1.93.0.
- Features: `testing-environ,sys`; exact test filter above.
- Cargo used one job. The first build/test command took 34.38 seconds and the test 0.11 seconds; the restored incremental build took 0.66 seconds and the test 0.11 seconds. One scoped invocation covered RED and GREEN. Actual peak RSS/storage were not sampled.
- Before launch, available disk was 90,272,716 KiB, memory pressure reported 52% free on 32 GiB RAM, and load average was 12.69/12.24/12.12 on 10 CPUs. An unrelated TableTop E2E run remained active and was left untouched.
- `TMPDIR` was the owned session scope `/Users/hoppworks/.local/share/agent-builds/rhai/darwin-x20-20261008-82f295c8/`. Cargo target and home were under the runner's `AGENT_RUNTIME_DIR`. The runner removed its private runtime; host readback confirmed it absent. The now-empty exact session scope was removed with `rmdir`, then read back absent. Test-owned temporary files were cleaned by their guards.

## Evidence and limits

`run-metadata.txt`, `mutation.patch`, `red.log`, `red.status`, `green.log`, `green.status`, `outcome.txt`, `cleanup-readback.txt`, and `evidence.sha256` preserve the command, source identities, outputs, corrected classification, and cleanup. No product or test source was changed in the repository. Combined independent review is READY (2026-10-08), confirming the identities, raw RED/GREEN results, child readback, cleanup, and Darwin-only limits. Other platforms, features, MSRVs, and remaining Ticket 03 criteria remain open.
