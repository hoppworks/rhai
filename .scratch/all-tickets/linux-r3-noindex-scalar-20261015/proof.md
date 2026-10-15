# Linux R3 no_index process proof history, 2026-10-15

## Current status

The Linux R3 requirements are now accepted at the integrated candidate for `testing-environ,sys,no_index`: `run(program)` succeeds without an argument list and array-taking `run` overloads are absent. See [attempt 06](attempt-06/proof.md) for current-source binding and the restored GREEN; [attempt 05](attempt-05/evidence/classification.txt) records the valid intended RED. The attempt-02 text below is historical evidence for its narrower scalar-options row; its “partial” status was accurate at that earlier point and is superseded for Linux R3 by attempt 06. This does not close R3 on other release targets or the broader A–F/Ticket03 acceptance.

## Scope

This accepts only `tests/sys_process.rs::scalar_run_with_cwd_works_without_collections` on Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default profile, features `testing-environ,sys,no_index,sync,unchecked`, at integrated fork-main revision `9b01104639c4032c892f142a4e049f66ea65fba2`. Exact source/lock/feature binding and retry cause are in `revision-binding.md` and the attempt receipts.

The test drives the public Rhai Engine `run` API with a scalar program and options. A real `/bin/sh` child writes its PID into a unique fixture file and prints its working directory. The test independently reads that record, confirms the child is absent (`ESRCH`), checks exact cwd stdout, complete stdout/stderr, successful exit and code 0, then confirms `run_raw` is not registered. This exercises a real process and filesystem, without mocks.

## Assertion control and restored result

Attempt 01 reached the intended deliberately inverted `run_raw`-absence assertion. Cargo exited 101; libtest reported 0 passed / 1 failed, and the test had already printed the child PID with ESRCH readback. Its harness then falsely rejected the valid child marker because it searched `child-pid=` while the test prints `child_pid=`. It stopped before GREEN and returned runner status 1. The exact cause and cleanup are retained; no product failure is indicated and this runner status is not called success.

Attempt 02 is the targeted restored-source GREEN only: Cargo exited 0 and the exact selector passed 1/1. It records `child_pid=… reap=ESRCH`; the test assertions also passed for cwd, full captures, successful status/code and absent raw API. RED was not repeated.

## Resource custody and limits

Each attempt used an absent owned scope under `/root/.local/share/agent-builds/rhai/`, passed as absolute `TMPDIR` to the existing `run_scoped.py`. The runner created private `AGENT_RUNTIME_DIR`; source copy, Cargo home and target were isolated there. Both used one Cargo job. The exact runtime and empty session-scope cleanup are recorded. The green run's two preflight snapshots had no Cargo/rustc, 95 GiB available memory and more than 642 GiB free disk. A foreign Tauron Cargo build appeared in the post-run snapshot and was not touched; possible late overlap is explicitly recorded. No owned output or test fixture remains.

At the time of attempt 02 this was a named partial Linux no_index process row, not full R3 or X34 acceptance. Attempt 06 closes the named Linux R3 no-argument and array-overload behavior. Other release targets/platforms/features/MSRVs, Windows custody, and remaining A–F / Ticket03 criteria remain open.
