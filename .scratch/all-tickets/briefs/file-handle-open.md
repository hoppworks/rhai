# File handle open/write/cursor slice

## Requirement

Implement the accepted compatible subset's open foundation: open_file(path[,mode]),
shared handle and cursor, write(string/blob when indexed), seek and position. Default
w+ creates without truncating. Preserve all documented modes from the pinned upstream
compatibility report and implicit final-drop closure. Resolve paths through existing
FsState capability authority, enforce read/write grants according to requested mode
before opening; never bypass cap-std or modify protected paths on denial. Single
write returns actual count with checked INT conversion; negative seek clamps zero.
Read methods and their allocation limits are a subsequent requirement, not this slice.

## Context

Own worktree /Users/hoppworks/projects/rhai-file-handles, task/file-handles, e45c675c.
Read AGENTS.md, .scratch/all-tickets/file-handle-compatibility.md and accepted
release-proposal.md, docs/sys-package-plan.md phase4. Owner accepted recommendations
including rejecting negative read lengths and retaining resource bounds under
unchecked. Preserve those later read requirements; no explicit close API is approved.
Existing public test seams are approved. Use tdd and e2e-proof from agent-skills;
start with a failing real Engine/script contract test and independent host file
readback. Keep related corrections in this responsible context. Reuse current
filesystem routing, errors and registration patterns; do not weaken authority.

## Scope and proof

Real OS fixtures verify default no-truncate/create, all modes including exclusive
create and append, read-only-root denial before mutation, outside-root denial,
shared cursor/clones, counts, negative seek clamp, final-drop/reopen. Relevant
metadata comments and no_index/sync feature paths need honest compilation/script
proof; full three-OS/MSRV acceptance remains open. Demonstrate wrong independent
file payload assertion fails then restore and pass. No mocks, fixed sleeps or
unbounded fixture subprocesses. Do not expose incomplete read behavior.

## Bounds

Fresh feature slice, maximum60 active minutes including independent review from
start; <=15min each scoped invocation, <=2GiB private build storage and <=16 owned
fixture files/handles. CARGO_BUILD_JOBS=2; source copy and Cargo home/target under
AGENT_RUNTIME_DIR, using unchanged agent-skills/tools/run_scoped.py. Export needed
proof before runtime exits; exact cleanup of owned resources only. No shared
service, remote push, merge, credentials or agent-home changes. Record all launches,
elapsed/remaining time, cause history in .scratch/file-handles/coordinator-state.md.
There is no default launch-count cutoff; stop at two consecutive launches without
new diagnosis/closed checks, contradictory evidence, unsafe conditions, hard-cap
exhaustion or an uncovered decision. No new Expert chain without consultation.

## Deliverable

Send source/RED early. Commit atomically as configured human user without
attribution. Report ref, changed files, proof path, independent readback/control,
cleanup and unverified requirements. Do not claim complete streaming handles or
release acceptance, and do not merge.
