# Linux X35 pipe-closed worker sync-profile proof (2026-10-15)

## Scope

This attempt adds checked and unchecked sync-profile evidence for the existing paired selectors:

- direct_run_returns_with_pipe_closed_worker_live_control
- managed_run_closes_pipe_closed_worker_before_return

Host: lllm Linux x86_64/Bazzite 44; Rust/Cargo 1.77.2; integrated source revision b289e6ab88890bbd469375acac561bdd950aa1e0. Profiles: testing-environ,sys,sync and testing-environ,sys,sync,unchecked. Source, lock and tool binding is in attempt-01/revision-binding.md.

The previously accepted base and unchecked rows are retained for reuse only if the independent reviewer confirms the target assertions and implementation paths remain unchanged. No other feature, platform or Ticket03 row is covered.

## Results

One scoped invocation, with Cargo jobs 1 and a 900-second outer bound, ran three cases per profile. The DirectChild control used an intentionally inverted liveness expectation: both REDs exited Cargo 101 at the exact PIDFD assertion that the worker remained live at API return. Restored DirectChild GREEN passed 1/1 in both profiles. The paired Managed selector GREEN passed 1/1 in both profiles.

Every run acquired PIDFDs for the exact leader, worker and leaf with recorded PID/start-time/parent/group identity. DirectChild GREEN asserts the leader exited while worker and leaf remain live at API return; Managed GREEN asserts all exact members exited before return. Fixture teardown is bounded and reaps the recorded members. Per-run times: checked sync RED/GREEN/Managed GREEN 41.143/2.313/0.159s; unchecked sync 20.039/2.389/0.268s. Outer scoped runner returned 0. No product changes were made.

Capacity after the run showed 92 GiB available memory and 669 GiB free disk. A separate Tauron one-job build appeared during this run and was preserved; this Rhai invocation used one Cargo job. The runner removed its private runtime and the exact owned session scope was removed after evidence export.

## Review and limits

Combined independent review passes these two selectors under the two sync profiles only; see attempt-01/combined-review.md. Raw commands, outputs, result/status records, hashes and capacity snapshots are retained in attempt-01/. This proof does not close all of X35, Ticket03, A–F, or any other platform/feature/MSRV row.
