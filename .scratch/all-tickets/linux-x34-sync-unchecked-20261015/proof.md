# Linux X34 managed deadline and output-limit proof: `sync,unchecked` (2026-10-15)

## Bound execution

This named Linux profile slice ran at integrated fork-main revision `6af3cae30a233880eafc92c4f742534a926e6a88` on lllm x86_64/Bazzite 44 with Rust/Cargo 1.77.2 and features `testing-environ,sys,sync,unchecked`. Cargo used the preserved X35 lock (SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`), one job, a private source copy, Cargo home and target under one `run_scoped.py` runtime. Two pre-run capacity snapshots 10 seconds apart found no active Cargo/rustc build. Inputs, source hashes, commands and capacity snapshots are in `attempt-01/`.

## Results

`managed_run_deadline_reaps_group_under_fixture_reaper` first ran with only its `api_is_timed_out` assertion inverted in the private copy: Cargo exited 101 at the named RED_CONTROL after the log recorded timeout result, preserved markers, incomplete captures, all exact managed PIDFD identities absent, group ESRCH, live host/reaper/sentinel, and exact fixture-reaper cleanup. The restored test exited 0 with 1 passed.

`managed_run_output_limit_reaps_group_under_fixture_reaper` exited 0 with 1 passed. It recorded the typed OutputLimit, exact retained prefix, honest incomplete captures, exact leader/worker/leaf identities and group closure, live host/reaper/sentinel, and exact reaper cleanup. The `postrun-verification.txt` records each required marker and status. The scoped runner exited 0; the runtime and owned empty session directory were removed.

The machine had about 100 GB MemAvailable and only a few MB SwapFree, but both preflight snapshots showed no competing build and the run used one Cargo job. No other process was touched.

This accepts only these two Linux X34 cases for `testing-environ,sys,sync,unchecked`. Other X34 profile/platform/fault rows, Windows Job behavior and broader Ticket03 remain open. The no_index-gated selectors were not run; they are not part of this profile and are cfg-disabled when that feature is selected.

Independent combined review: `attempt-01/combined-review.md`.
