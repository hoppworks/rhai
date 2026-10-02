**SOURCE REJECTED** for `a6fc667f` against `8aa0bfda`: three blocking findings.

- **High — Cleanup can falsely pass:** [readback:112](/Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai/.scratch/all-tickets/readback-current-darwin-sys-net-cleanup.py:112) compares a digest with the new start-text receipt. A live recorded PID passed cleanup. The new absence-check function is unused.
- **High — Stale PID cache accepts failed identity:** [helper:453](/Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai/.scratch/all-tickets/check-current-darwin-sys-net-behavior.py:453) accepts an unavailable current command identity when that PID was previously recorded. Validate the immediate receipt and stop/reap on failure.
- **High — Unknown inventory permits dispatch:** [dispatcher:137](/Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai/.scratch/all-tickets/dispatch-current-darwin-sys-net-behavior.py:137) accepted PID `-1`, start `"unknown"`, then attempted scope creation and dispatch. No real inventory collector was supplied for review.

All three reproduced with write-free mocks. Same-census descendant RED/GREEN and seven failure controls passed; eight stage pins, primary copies, and unchanged observer lifecycle bytes matched.
Coverage: all 16 changed files accounted for; unchanged archive/lock/runner integrity reused.
Instruction revision confirmed: `958a4538b0191c53f2ccb2cd00d96c15045fbf68`.
Native light control and nine-row/five-RED acceptance remain unverified; cumulative native launches remain **2**. No edits, report files, native launches, commits, pushes, or child agents.
