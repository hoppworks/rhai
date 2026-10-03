# Linux managed run OutputLimit proof

Native 106 completed successfully at immutable source
53b01fa5df3f3a23bb55d4659c6207e5da86dc79 and recipes
c785a91364294b44c42c7c82acfb19a99f5c0c61. Independent combined acceptance review
accepted this narrow criterion; broader process and release tickets remain open.
Test SHA-256: 024e774b76e21d46326d007249ca5db92eab161f88af3328bdd4c3b591a2ab03.
Source archive: e4f024d2a1147cba5466e6421691f4087e1e96447da137b63e46c295efbdb83e.
Workhorse ran native Linux 7.2.7 x86_64 with private Rust/Cargo 1.77.2 and the
accepted Cargo.lock starting 2ba4b3a0.

## Observed behavior

The exact integration test
`managed_run_output_limit_reaps_group_under_fixture_reaper` drives a real Rhai
script through the public Engine and host package. Its assertions require typed
OutputLimit, a retained 4096-byte stdout prefix, both captures honestly incomplete,
no timeout, and termination/reaping of the managed group. Exact PID/start/PIDFD
and group observations plus reaper wait receipts distinguish API cleanup from
exceptional fixture watchdog cleanup. The host, reaper and unrelated sentinel
are live at the API boundary.

The wrong typed-outcome assertion fails with status 101 after complete fixture
cleanup. Exact source restoration precedes four positive feature rows:
`testing-environ,sys`, plus `sync,metadata`, plus `f32_float`, plus `unchecked`.
Prompt-success and held-zombie regressions also pass. Three toolchain setup
commands pass; ten commands total, one intended RED and six GREEN tests.

## Original evidence and retirement

[Original evidence](linux-managed-output-limit106-evidence/) retains actual
stdout/stderr/status, source restoration, seven original closure files and custody
records. Root independently verified all 68 original file hashes and five
subdirectories against the remote inventory. Independent read-back records 142
helper/command PID/start pairs and two launcher pairs absent, with owned groups
1352036 and 1352108 empty. Exact hash-gated retirement removed only those 68
files/five directories; fresh stage, scope and group absence is saved in
remote-cleanup.json. No retained build remains.

The original outer log includes an optional /proc/1352105/stat exit-race warning;
subsequent complete exact read-back and cleanup passed. Outer, scoped runner,
runtime, PID read-back and scope cleanup statuses are all zero. The 65 samples have maxima 962156 KiB RSS, 968804 KiB storage and 10 descendants;
these are sampled maxima, not exhaustive resource peaks. Bounds remain 600/585/540 seconds
including 30 seconds for export, two Cargo jobs, 16 descendants, 1.5 GiB storage
preemption and 2 GiB hard RSS/storage limits. The measured two-heavy-run exception
expired at terminal completion without touching the foreign Tauron run.

## Scope and history

This proof covers only the named Linux managed overflow criterion and identified
regressions at this immutable revision. The failed borrow-length source correction
count remains one; the accepted deadline105 proof and prior cause/budget history
are preserved. Escaped pipes, post-spawn faults, remaining lifecycle/performance,
additional feature/platform rows and final release acceptance remain open.

Combined independent acceptance: [review](linux-managed-output-limit-review.md).
