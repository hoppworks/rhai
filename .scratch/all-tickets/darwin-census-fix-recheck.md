**SOURCE REJECTED** for `b01b95a`: the dispatch gate still has blocking gaps.

- **High:** [dispatcher:25](/Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai/.scratch/all-tickets/dispatch-current-darwin-sys-net-behavior.py:25) misses `build-script-build` and `headless_shell`. Both reproduced through the actual dispatcher, reaching mocked scope creation and workload dispatch.
- **Medium:** [dispatcher:79](/Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai/.scratch/all-tickets/dispatch-current-darwin-sys-net-behavior.py:79) accepts an incomplete inventory missing the dispatcher’s own PID; that control also reached dispatch.

Cleanup rejection, fresh command identity, stop/reap, census failure controls and subprocess status semantics passed.
All 11 affected files reviewed; eight pins and primary copies matched. Observer cleanup bytes remain unchanged from the accepted baseline.
Loaded instruction revision: `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. OCR succeeded.
Native collector, finite churn, nine positive rows and five RED controls remain unverified; native package consumption remains **2**.
No writes, edits, native launches, commits, pushes or child agents.
