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
- Read back nine planning/glossary files; local links resolve and dependency graph
  is acyclic. The main checkout is clean after relocating the new own files.
- Existing evidence: ../../docs/sys-package-plan.md and
  ../../docs/net-package-assessment.md; prior assessment state remains untouched.

## Current step

Map charted. No decision ticket claimed or resolved in this charting turn.
Next session starts with the first unblocked, unclaimed ticket by number.

## Decisions and constraints

- Verification strict; own pushes automatic; Coordinator merges automatic only green.
- Worktree: /Users/hoppworks/.codex/worktrees/stdlib-net-assessment/rhai.
- Branch: task/stdlib-net-assessment; origin: https://github.com/hoppworks/rhai.git.
- No implementation, merge, upstream action, new dependency, or tool installation.
- Strict verification config is still absent; ticket 01 proposes the real non-UI
  entry point, independent read-back, false-green check and safe fixture reset.
- Four sys review findings remain unresolved: configured-root symlink/parent semantics,
  permissive symlink handling, macOS configured-root aliases, and non-UTF-8 fixtures.
  Review source: /Users/hoppworks/projects/rhai-review-sys-windows;
  captured details: /Users/hoppworks/projects/rhai-review-sys-windows/.scratch.
- Real Windows verification is outstanding; Wine is diagnostic evidence only.
- No new research tickets needed yet: prior source inventory and runtime diagnostics
  already answer reuse facts. Delegate research only when a decision exposes a gap.

## Next action

Read map.md, select and claim issues/01-acceptance-contract.md, agree and record the
acceptance contract with the owner. Resolve at most one non-research ticket per session.
