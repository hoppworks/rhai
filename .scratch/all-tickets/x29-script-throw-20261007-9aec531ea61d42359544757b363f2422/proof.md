# X29: Rhai throw while a public child is live

Status: partial, accepted for the named Workhorse Linux row only.

## Scope and result

The test runs Rhai through the public `Engine` and registered `sys` package. The script starts the real test executable through public `spawn`, waits for an OS fixture to report readiness, and then throws while the child remains live. The outer test harness confirms the exact fixture PID is present before opening the throw gate. The returned Rhai error must contain the intended throw message, and an in-process wrong-message control is rejected by the same assertion. After evaluation unwinds and drops the script-owned `Child`, the outer harness independently observes `kill(pid, 0)` returning `ESRCH` for that PID.

This is a backend/OS integration test; no UI layer applies. It does not close X29 for macOS, Windows, other feature combinations, or other MSRV rows.

## Run

- Machine: Workhorse, Linux 7.2.8, x86_64.
- Toolchain: Rust/Cargo 1.93.0.
- Features: `testing-environ,sys`.
- Command: `cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process shared_child_contract::script_throw_drops_and_reaps_a_live_child -- --exact --nocapture --test-threads=1`.
- Result: exit status 0; the exact test passed (1 passed, 0 failed; 59 filtered out).
- Preflight passed with no active heavy process groups, 88,186,324 KiB available memory and 671,314,255,872 bytes free. The admission reserves were 16 GiB each for memory and disk; the conservative additional storage estimate was 2 GiB.
- After local copies were verified against Workhorse SHA-256 readback, the exact owned Workhorse session scope was removed. The scoped runner had already cleaned its private runtime.

## Evidence and input identity

- `out/attempt-02/preflight.json` records machine, toolchain, capacity and input hashes.
- `out/attempt-02/cargo.combined` contains the exact test result, readiness/liveness gate, wrong-message rejection and ESRCH receipts.
- `out/attempt-02/cargo.status` is `0`; `out/attempt-02/command.txt` and version files record the command and toolchain.
- Source revision: `acbffcc84763b160576337ee6602e6a839c880fe`; the source archive overlays only the X29 fixture and reuses the accepted X30 `Cargo.lock`.
- Source archive SHA-256: `a49ea6ef5cde41db9dc2eee17debf1d5aecc3338a306660e1b44fe834316f5fc`.
- X29 fixture SHA-256: `2925f184b84ae830bed5478be0cec0b4dd93b6eb6824ce87062883c53d08a579`.
- Combined test output SHA-256: `c9f831623cf4726fc3c0ea85e3d3481653d601891f42d83bf6ce8d63fce89bfa`.
- Preflight output SHA-256: `404e2a16e51b7b324ee441e24f7b3b35e66fd38e1bec0b2c25294df39d09a1a3`.

## Setup history

Two pre-assertion setup issues were corrected and retained in the attempt logs: the first admission found the owned scope root at mode 0755 instead of 0700; the first runner attempt then invoked Cargo from the wrong working directory and stopped before compiling or running the test. The runner now changes to the frozen source directory. Neither setup stop exercised or failed an X29 product assertion. The next bounded test run passed; no product correction or acceptance retry was needed.
