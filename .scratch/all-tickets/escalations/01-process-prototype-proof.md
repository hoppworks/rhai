# Question

Which corrections are necessary before accepting the macOS process prototype's evidence?

# Why escalated

Independent review found a mismatch between claimed concurrent I/O and fixture behavior,
and cleanup hazards on exceptional paths. Resolve this once before another implementation attempt.

# Context by reference

- Immutable prototype commit 35a8cf52, branch task/process-prototype.
- /Users/hoppworks/projects/rhai-process-prototype/.scratch/process-prototype/src/main.rs
- Same directory: run-scoped.sh, README.md, evidence/*.log.
- /Users/hoppworks/projects/rhai-all-tickets/AGENTS.md
- /Users/hoppworks/projects/rhai-all-tickets/.scratch/stdlib-wayfinder/issues/03-process-contract.md

# Constraints and decisions

Private local work only; no production implementation. Accepted evidence requires exact
owned cleanup on assertion failure, bounded execution and honest coverage. Do not rewrite
foreign worktrees or install tools. Run scoped checks only if necessary, never leave escapees.

# Tried so far

One native prototype run plus wrong-assertion control; no correction attempt yet.
Reviewer observed: stream fixture read_to_end completes before stdout/stderr writes;
this does not prove simultaneous bidirectional backpressure. Escaped descendant is
forgotten and only cleaned near successful end, so early panic can leave it outside
the runner's process group. kill_group is called after try_wait has reaped the group
leader in the normal-exit case, exposing a stale group identity. sh set -e with a
binary | tee pipeline may report tee success after binary failure. Scoped runner
invocation lacks an external timeout while wait/join can block indefinitely.

# Deliverable

Read-only focused review. Write 01-process-prototype-proof.answer.md beside this
brief, with validated findings and the smallest correction plan. Identify which
claims can remain accepted and which must be rerun. Return at most 15 lines plus path.

# Budget

One Expert escalation for prototype-proof cause, then one responsible implementation
attempt. No further Expert chain for this cause. Keep review bounded to these observations.
