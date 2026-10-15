# Current-source X34 Linux base-profile deadline and output-limit proof (2026-10-15)

## Scope and inputs

This accepts only `managed_run_deadline_reaps_group_under_fixture_reaper` and `managed_run_output_limit_reaps_group_under_fixture_reaper` on Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default checked profile, features `testing-environ,sys`, at integrated fork-main revision `eeb2d65184762361e3c50e4a19c454471415e49b`. The profile includes Cargo defaults. Source and preserved lock hashes are recorded in `attempt-01/evidence/environment.txt` and `source-input-readback.txt`.

Each test invokes the public managed `run` API through Rhai and owns a real fixture reaper, child process group and unrelated sentinel. Deadline RED and OutputLimit RED each invert only the corresponding expected public result assertion in a private source copy. Both produce Cargo exit 101 at their named `RED_CONTROL`, after boundary observations and fixture cleanup. Restored GREEN for each selector exits 0 with one test passed.

## Independent lifecycle observations

The deadline boundary log records timeout report, preserved stdout/stderr markers with incomplete captures, exact leader/worker/leaf PIDFD exit, process-group `ESRCH`, live host/reaper/unrelated sentinel at the API boundary, exact worker/leaf fixture-reaper waits and no watchdog cleanup. The output-limit boundary records typed OutputLimit, exactly 4096 retained stdout bytes, honest incomplete captures, exact group/PIDFD closure, live host/reaper/sentinel at the boundary, exact reaper waits and no watchdog cleanup. The fixture then reaps the sentinel. The RED logs include successful nested fixture output before the outer deliberately failing assertion; phase status plus exact RED marker and final outer libtest result classify them correctly.

## Scope custody and caveat

One `run_scoped.py` invocation used an absent owned session directory under `/root/.local/share/agent-builds/rhai/`, absolute `TMPDIR`, private source/Cargo home/target under `AGENT_RUNTIME_DIR`, one Cargo job and a 900-second outer bound. It covered both assertion controls and both restored tests. The runtime and exact owned empty session scope were removed; runner status was 0. Two preflight snapshots showed 95 GiB available memory, 628 GiB free disk and no Cargo/rustc. A foreign `cargo-chef` build appeared in the post-run process snapshot and may have overlapped the latter part; it was not touched. The evidence records this caveat. Do not start another heavy build before checking current shared capacity.

The earlier accepted X34 `testing-environ,sys,sync,unchecked` pair remains separately documented in `.scratch/all-tickets/linux-x34-sync-unchecked-20261015/proof.md`. Together these are still only named Linux X34 profile rows. Other X34 selectors, features, OS/MSRV variants, Windows Job behavior and broader A–F/Ticket03 remain open.
