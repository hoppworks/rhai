# Standard library wayfinder state

## Goal

Chart an implementation-ready plan for sys completion and a separate TCP package,
with high quality, low maintenance, strict verification, and Rhai conventions.

## Done

- Owner accepted both recommendations on 2026-09-30: initial scope sys plus TCP;
  scripts are owned or reviewed, with explicit host authority and no OS sandbox claim.
- Read wayfinder, grilling, domain-modeling, local tracker and ponytail checkpoint.
- Reused the session-owned worktree and preserved all existing scratch evidence.
- Created map.md and six decision tickets. No production code changed.
- Owner accepted the concrete acceptance contract; ticket 01 is resolved, indexed
  from the map, and its E2E configuration is recorded in AGENTS.md.
- Owner accepted the exact filesystem path contract; ticket 02 is resolved and
  indexed. The sys plan records P14/F22/F23 and historical implementation limits.
- Read back nine planning/glossary files; local links resolve and dependency graph
  is acyclic. The main checkout is clean after relocating the new own files.
- Existing evidence: ../../docs/sys-package-plan.md and
  ../../docs/net-package-assessment.md; prior assessment state remains untouched.

## Current step

Tickets 01–03 are resolved. The owner explicitly included managed process groups/jobs
in the first version after reviewing advantages, security and performance effects.
Three decision tickets remain open. No implementation or native process proof has
started. Maximum quality takes precedence over effort.

## Decisions and constraints

- Verification strict; own pushes automatic; Coordinator merges automatic only green.
- Worktree: /Users/hoppworks/.codex/worktrees/stdlib-net-assessment/rhai.
- Branch: task/stdlib-net-assessment; origin: https://github.com/hoppworks/rhai.git.
- No production implementation, merge, upstream action or new library dependency.
  Owner explicitly authorized Windows VM provisioning on workhorse.
- Strict verification config is accepted and recorded in AGENTS.md. No runtime
  acceptance proof has been claimed in this planning step.
- Four sys review findings remain unresolved: configured-root symlink/parent semantics,
  permissive symlink handling, macOS configured-root aliases, and non-UTF-8 fixtures.
  Review source: /Users/hoppworks/projects/rhai-review-sys-windows;
  captured details: /Users/hoppworks/projects/rhai-review-sys-windows/.scratch.
- Real Windows verification is outstanding; Wine is diagnostic evidence only.
- No new research tickets needed yet: prior source inventory and runtime diagnostics
  already answer reuse facts. Delegate research only when a decision exposes a gap.

## Windows environment provisioning

The owner authorized SSH work on workhorse and a Windows VM on 2026-09-30.
SSH works; KVM/QEMU/libvirt/UEFI/TPM are present. Created the owned domain
`rhai-win11-quality` (4 vCPUs, 8 GiB, sparse 100 GiB disk) and seed ISO under
`/var/lib/libvirt/images/rhai-win11-quality`. The owner reports a Windows Pro license. The Enterprise Evaluation download was
stopped; official multi-edition retail media is downloading for Pro installation.
Verify the published SHA-256 before boot. Installation and native
Windows readiness are not yet verified. Details: windows-vm/README.md.
No existing workloads were stopped, and no host tools were installed.

## Next action

Current step: finish and verify the owned Windows Pro VM installation.
After that: claim issues/04-tcp-authority.md and settle TCP permissions.
Ticket 06 must review process host-config spelling, error-report compatibility and
managed-scope native platform release gates. Cancellation/reaping and scope-setup
prototypes remain implementation gates, not completed evidence. Do not implement
production code during wayfinder planning.
