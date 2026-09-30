# Native Windows execution ownership gate

## Task
Implement and prove the scoped guest execution adapter required by ticket 06,
before any further Rust/package build in the Windows guest. This is an independent
prerequisite; no release matrix or API proposal is accepted by this task.

## Context by reference
- Coordinator worktree: /Users/hoppworks/projects/rhai-all-tickets.
- AGENTS.md: strict proof, private local/workhorse only, scoped resources.
- .scratch/all-tickets/windows-runner-gate.md: proposed mechanism and required proof.
- .scratch/stdlib-wayfinder/windows-vm/README.md: prior authorization, exact owned
  domain, resources, baseline evidence and console access. Preserve all baselines.
- /Users/hoppworks/projects/agent-skills/config/roles.toml and tools/run_scoped.py.

## Constraints
Use a fresh owned worktree on task/windows-scoped-runner based on task/all-tickets.
No remote Git writes. No credentials, no admin changes, installs, global config,
shared-service restart or VM reset/reseed. Only the authorized owned Windows VM and
workhorse may be used. Inspect current hypervisor and actual guest state before
operating. No package builds until the adapter is verified. A small supervisor
bootstrap may compile native interop in its own exact temporary directory; document
how bootstrap itself is bounded and cleaned. Do not touch agent homes.

The adapter must establish private job ownership before payload runs, preserve
exit status, scope output/cache/source, terminate only owned task members on
success/failure/deadline/interruption, and retain independent guest cleanup/runtime
ownership after supervisor/connection death. A host SSH process group cannot
substitute for guest cleanup. Exact handles/job membership, not broad process scans.
Keep an unrelated owned sentinel alive until its own cleanup. No silent fallback
on assignment failure or nested job restrictions. Do not run unsafe candidates
before supervision is established. Never ask for or use a password.

## Acceptance
Native proof for every row in windows-runner-gate.md, including a deliberately
wrong assertion, restored success, live grandchild interruption, runtime readback,
connection/lease loss and nested/assignment failure context. Export exact commands,
OS/toolchain, statuses, membership and cleanup observations. If console access is
not safely available, preserve implemented source and report unverified gates;
do not claim native acceptance from compilation or docs.

## Attempt history and escalation
No prior adapter implementation attempts. Count underlying failures. After two
same-cause failures or contradictory evidence, report a focused escalation to the
Coordinator; do not create your own Expert chain or retry indefinitely.

## Deliverable
Reusable source/entrypoint and scoped proof under .scratch/windows-scoped-runner,
atomic commits, exact resource inventory, clean worktree, at most 15 lines report
with HEAD, proof path, verified and unverified gates. Do not integrate or push.
