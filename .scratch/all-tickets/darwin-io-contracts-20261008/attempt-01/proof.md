# Ticket 03 X14/X16/X17 — Darwin partial acceptance

## Scope

This evidence covers only the X14, X16, and X17 macOS row at source revision
`471cf2698dce1571c6e875c093c2cd2c9ffd6093`, arm64, macOS 27.0.1 (kernel
27.0.0), Rust/Cargo 1.93.0, with `testing-environ,sys`. It does not close any
other operating-system, feature, or MSRV row, or any other ticket.

The tests call Rhai scripts through the public `Engine` and process package,
launch real operating-system children, and independently read child-written
records and output. The three test functions and `assert_child_record` helper
are byte-identical to the accepted Linux source snapshot at
`.scratch/all-tickets/process-io-contract-evidence/attempt-01/sys_process-green.rs`:

| Source function | SHA-256 |
|---|---|
| `run_io_contract_empty_output` | `5cdb1ccf9cbf5990772b57541feb8d9e42833a899b2bda352657ebfee01256c6` |
| `run_io_contract_string_stdin_round_trip` | `5290819423147cff23186b47136d489a2c55eb7c33533292320322ccbba4d2a4` |
| `run_io_contract_blob_stdin_round_trip_with_concurrent_output` | `3c93624cffb11eb64e8e4ae5f96f36cb4390e997429fed16896aba15f8306167` |
| `assert_child_record` | `9dd703886a860756e0af649a499364167cef02f58d9754ff8bc0c52f23bc4693` |

The complete test source SHA-256 is `7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017`.
The accepted lock SHA-256 is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

## Real run and independent observations

The canonical command ran from an isolated archive of the identified revision:

```text
cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process run_io_contract_ -- --nocapture --test-threads=1
```

`final-green.exit` is `0`; the log reports 3 passed, 0 failed, 45 filtered out.
The test cases independently observed:

| Case | Observed result |
|---|---|
| X14 | Empty stdout/stderr; child exit 0; direct child reaped. |
| X16 | Exact 51-byte string stdin round-trip; child exit 0; direct child reaped. |
| X17 | Exact 1 MiB varied Blob stdin/readback, exact 1,310,736-byte stdout and 262,144-byte stderr during concurrent output; child record validated all input; direct child reaped. |

The child PIDs and records are in `final-green.log`. Each test checks that its
direct child is absent with `kill(pid, 0) == -1` and `ESRCH`. X17 separately
reads the child's received-input file and compares every byte with the sent
Blob. These are OS-backed observations, not mocked process results.

## Assertion sensitivity

The three per-case wrong-expectation controls from the accepted Linux proof are
reused: `process-io-contract-evidence/attempt-01/remote-output/out/x14-wrong-expectation.*`,
`x16-wrong-expectation.*`, and `x17-wrong-expectation.*` all exited 101 after
their intended assertion failed. Reuse is limited to sensitivity: the exact
test functions and helper are byte-identical, and the false expectations test
ordinary Rust assertions rather than an OS-specific behavior. The macOS run
itself freshly exercised all three real cases and readbacks. The combined
review confirmed that the controls remain applicable to the changed OS.

## Build and resource record

The run used one bounded `tools/run_scoped.py` invocation with two Cargo jobs.
`TMPDIR` was the owned scope
`/Users/hoppworks/.local/share/agent-builds/rhai/darwin-io-contracts-20261008-b7c57b02-c751-468e-8c8f-ba44a6dd4b61/`;
Cargo target and Cargo home were both under the runner's `AGENT_RUNTIME_DIR`.
The lock was copied from the accepted Linux proof and hash-checked before the
command. Cargo setup/build/test took 25.35 seconds; test execution took 0.27
seconds; the complete scoped invocation took 28.31 seconds. Actual peak memory
and storage were not sampled. Before launch, available disk was 96,307,252 KiB,
memory pressure reported 53% free on 32 GiB RAM, and system load was
12.47/11.28/10.21 on 10 cores; one unrelated E2E process remained untouched.

The runner removed its private runtime. After exporting evidence, the exact
session scope was removed; the three test-owned temporary roots were cleaned by
their guards, and the tests verified child reaping. A later host-side readback
at `cleanup-readback.txt` independently confirms the exact session scope and
private runtime paths are absent and none of the three logged child PIDs is
present. The evidence directory is retained for review. `evidence.sha256`
verifies every exported run and cleanup-readback file.

## Evidence and review state

- `run-metadata.txt` — source, OS, toolchain, lock, command, and private output paths.
- `final-green.log` / `final-green.exit` — complete test output and exit status.
- `run.sh` — scoped invocation recipe used for this run.
- `cleanup-readback.txt` — exact host-side scope, runtime, and child-PID cleanup readback.
- `evidence.sha256` — verified hashes for the exported files above.

Review status: the combined independent review returned READY after a focused
recheck of the durable cleanup receipt. It confirmed that the three Linux
wrong-expectation controls remain applicable because the test functions and
helper are byte-identical and the controls exercise ordinary Rust assertions.
The cleanup receipt confirms the exact session scope and private runtime are
absent and none of the three logged child PIDs is live; all five exported
run/cleanup hashes verify. No further run is needed for these rows. Other
platforms, features, MSRVs, and all uncovered Ticket 03 criteria remain open.
