# Linux X38 escaped-pipe sync proof (2026-10-15)

## Scope

This adds the checked and unchecked sync-profile rows for exactly:

- managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes
- managed_spawn_post_reap_cancel_bounds_escaped_capture

Host: lllm Linux x86_64/Bazzite 44; Rust/Cargo 1.77.2. Integrated fork-main revision: 2a1fce7916e9d6e97404f3d68caaf646dc3077a9. Profiles: testing-environ,sys,sync and testing-environ,sys,sync,unchecked. Revision and lock applicability are recorded in attempt-01/revision-binding.md.

Previously reviewed base-profile rows are reused from the existing X38 proof; they were not rebuilt. The existing unchecked outer runner status 127 remains unexplained and is retained as a limitation. Per-selector Cargo statuses and prior review conclusions are not widened here.

## Results

One scoped runner invocation (run-scoped-status.txt: 0) ran both selectors in both profiles with assertion-sensitivity controls. All four deliberately inverted assertions exited 101; all four restored tests passed 1/1. RED/GREEN durations in seconds were 39.369/2.224 and 2.731/2.733 for checked sync, then 19.265/2.229 and 2.584/2.561 for unchecked sync. Cargo used one job.

The real Rhai API path records leader exit, escaped holder and independent sentinel liveness across the API boundary, challenge responses, and fresh stdout/stderr write probes that observe EPIPE. The post-reap cancellation test observes leader exit before cancellation and keeps the escaped holder until fixture cleanup. Fixture-owned processes and descriptors are explicitly cleaned up and reaped. Full logs and readbacks remain in attempt-01/evidence/.

The owned runtime and exact session scope were removed after evidence export. Capacity snapshots and environment are retained. No foreign process or worktree was modified.

## Independent review and limits

Combined independent review passes these two selectors in the two sync profiles only: attempt-01/combined-review.md. The matching checked and unchecked base rows are reused under the source-binding analysis there. Other X38 assertions, fault breadth, features, operating systems, MSRVs, Windows Job behavior, and A–F acceptance remain open.
