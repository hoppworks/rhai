# Windows monitor custody correction

## Task

Implement the single local correction justified by the Windows custody Expert
answer. This is source implementation and source review preparation, not native
acceptance or permission to run guest fixtures.

## Context by reference

- Coordinator: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/coordinator-state.md
- Expert answer: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md
- Candidate: task/windows-scoped-runner at 2e65cb45, owned checkout
  /Users/hoppworks/projects/rhai-windows-scoped-runner
- Earlier brief: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/briefs/windows-scoped-runner.md

## Constraints

Read project AGENTS.md and applicable tdd/e2e-proof instructions. Reuse the
candidate's owned worktree if clean and correctly identified. Preserve all other
work. No remote writes, guest input/execution, credentials, administrator work,
agent-home/configuration change, new tools or package builds. No new Expert
escalation for this cause. Implement only the monitor/client custody contract
specified by the answer; do not claim that a partial design satisfies it.

## Deliverable

Monitor/client split, creation-time job assignment, bounded host lease and state
machine, independent exit/cleanup receipts, exact journal/runtime ownership and
handle-based safe staging/removal. Follow all fail-closed requirements in the
answer. Start new behavior with meaningful contract tests where executable tooling
already exists; use only the prescribed scoped runner for such builds/checks.
Do not run an unsafe/unowned bootstrap to obtain tests. If no safe native compiler
exists, preserve source fixtures and explicitly leave RED/GREEN/native proof
unverified. Static text assertions are not behavioral proof.

Commit atomically as configured user. Report source refs, tests actually run,
exact remaining limitations, owned resources and source-review entry points.
No native workload may start before independent source review and all launch,
bootstrap, custody and guest-access gates pass. If implementation cannot close a
required invariant, retain the exact boundary and stop rather than adding an
unreviewed workaround. A source-only boundary does not consume a completed
failed native correction; a completed failed correction must be recorded.
