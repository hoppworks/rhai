Completed the sampler3 source-only follow-up and committed it as `a6fc667f0ac234e0876600f85bc8a36a860cc607` (`hoppworks <daniel@hoppworks.de>`).

The pinned Python suite passed the short-lived-descendant regression and census, cleanup, and dispatch controls; `git diff --check` passed. The staged manifest also matches all eight input files. The observer terminate/wait/kill/reap block is byte-identical to sampler2, so prior signal evidence applies to that block only.

The sampler3 stage is at `.scratch/all-tickets/current-darwin-sys-net-behavior-2f795ece-sampler3-20261002/`. No build scope or native run was used; the cumulative native launch count remains 2. Native sampler and behavior acceptance remain unverified pending the root’s combined review. The pre-existing first-stage and sampler2 untracked artifacts remain untouched. No push.
