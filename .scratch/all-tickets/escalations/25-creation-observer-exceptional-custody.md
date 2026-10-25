# Escalation 25: creation-observer-exceptional-custody

## Question
Give the smallest complete exceptional-cleanup correction for the new native Windows creation-failure observer, so the actual atomic-association/no-unowned-execution acceptance can run. Preserve existing real entry, exact Process identity, bounded streams, pending ownership, independent readback and honest retained-runtime semantics. No new wrapper/platform or general plan.

## Why escalated
- Two source corrections for this same observer exception/custody cause remained incomplete in combined independent review; no native control has launched.
- Initial global pending owner was published after throwable Writer cleanup; first correction published before Start and retains readers as acquired.
- Reviewer now finds Flush+Dispose in one try can skip Dispose, yet confirmed process exit/drain can clear the global owner and lose an open Writer channel.
- Source-only findings are not native product failures; consumption and prior unrelated evidence remain preserved.

## Context by reference
- Global rules: /Users/hoppworks/projects/agent-skills/config/common/AGENTS.md
- Relevant rules: same repository skills/{implement,mattpocock-code-review,delegate-within-agent}/SKILL.md; docs/agents/resource-lifecycle.md; config/roles.toml.
- Project: /Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai/AGENTS.md
- Source: tools/windows-scoped-runner/fixtures/RunCreationFailureControl.ps1 (especially lines60–125).
- Contract/source: tools/windows-scoped-runner/MonitorPayloadJob.cs; .scratch/all-tickets/windows-runner-gate.md.
- Existing package: .scratch/all-tickets/windows-creation-failure-20261025/{binding.json,Start.ps1,verify-results.py,production-equivalence.json}.
- Current state: .scratch/all-tickets/coordinator-state.md.

## Constraints and decisions
Read the global/project/rule entries fresh before acting, central revision d6024420 plus applicable uncommitted rules (global SHAe1a3b95a…). Plan/source diagnosis only: do not edit product/tests/config, build, execute guest controls, launch other agents or touch other sessions/processes. Normal C# body already equals accepted base57ee7c364. Existing Driver/Payload cache original host expiry2026-10-25T12:13:54.403215UTC, never silently renew. Fork main only, no upstream writes. Process/pipe unknown state must remain strongly owned; log I/O exceptions must not bypass ownership.

## Tried so far
Stable cause `creation-observer-exceptional-custody`, no prior Expert.
1. Initial pending owner after finally -> source review found Flush/Dispose could throw before publication.
2. Publish before Start, update acquired Readers, catch combined Flush+Dispose -> exact-process lifetime now sound, but Flush failure skips Dispose and may clear global file owner.
Native launches0, profile compilers0; one obsolete unexecuted ISO preparation1.5s. No native retries consumed.

## Deliverable
Write verdict, rationale and one concrete minimal patch recipe to `.scratch/all-tickets/escalations/25-creation-observer-exceptional-custody.answer.md`. Check all exceptional exits in the affected cleanup, avoid further piecemeal proposals. Return <=15lines plus path. No source edits or execution.

## Budget
Fresh non-fork Expert, actual roles.toml Expert mapping; one bounded read/answer, 10minute planning estimate. Stop after complete minimal correction/any genuine unresolved outcome decision. Root then has one bounded followup repair with targeted combined review; no second Expert chain for this cause.
