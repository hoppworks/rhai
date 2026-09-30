# Question

What is the smallest safe independent Windows guest monitor/lease mechanism that
closes the current scoped adapter's runner/connection-death and exact-runtime
cleanup gap without credentials, admin setup, services or global configuration?

# Why escalated

The bounded Windows adapter deliverable stopped with this requirement undesigned.
It cannot be used for package builds. Static ABI defects were corrected, but the
accepted guest ownership gate remains unmet. This is a Windows Job Object/runtime
custody design question, separate from POSIX signal/group identity and runner-copy
permission. Do not reopen the pending POSIX boundary or release/API decisions.

# Context by reference

- /Users/hoppworks/projects/rhai-windows-scoped-runner/tools/windows-scoped-runner/ScopedRunner.cs at 2e65cb45.
- /Users/hoppworks/projects/rhai-windows-scoped-runner/tools/windows-scoped-runner/README.md.
- /Users/hoppworks/projects/rhai-windows-scoped-runner/.scratch/windows-scoped-runner/acceptance.md.
- /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/windows-runner-gate.md.
- /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/briefs/windows-scoped-runner.md.
- /Users/hoppworks/projects/rhai-all-tickets/AGENTS.md.

# Constraints and decisions

Read-only design review; no guest inputs, fixture launches, builds, installs,
credentials, admin changes, service changes or remote Git writes. Guest desktop
is currently unavailable; black captures are authoritative, not old baseline UI.
Use first-party Win32 sources. Required ownership: suspended spawn/assign before
payload execution, exact job handles and wait statuses, bounded lease and cleanup,
runtime/evidence custody after runner/connection death, unrelated sentinel safety.
No name-based process scan, PID-tree guessing or silent fallback. Explicitly
separate process termination from filesystem cleanup and runtime path/ACL safety.
Abrupt loss of all supervisors may retain recoverable exact data, never imply a
false successful cleanup receipt. Preserve existing baselines and foreign work.

# Tried so far

Candidate 97fe3f93 supplies kill-on-last-job-handle-close but intentionally leaves
runtime data. Static correction 2e65cb45 fixes job struct ABI and unbounded waits.
No native compilation/execution occurred. No infrastructure recovery is active.
One guest wake left the exact domain's framebuffer black. No owned live resources.

# Deliverable

Write 02-windows-runtime-custody.answer.md beside this brief. Supply a concrete
minimal topology/handshake, which actor creates/holds each process/job/runtime,
partial-setup cleanup, connection-loss detection and finite independent lease,
native interruption/readback cases and any remaining owner/external-state blockers.
Explain what can be implemented locally now and what requires native validation.
Return at most 15 lines plus the answer path. Do not implement source or execute.

# Budget

One focused design review for this Windows-specific cause. No delegated child
agents or further escalation chain. No native measurements or calibration.
