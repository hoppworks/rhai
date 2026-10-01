# Monitor-owned Windows job creation prerequisite

## Task
Continue the existing source-only Windows custody correction with one concrete prerequisite: a monitor-owned payload job and creation-time job association with exclusive exact process/thread/job handle ownership. Use existing Expert02 answer, not a new design or escalation. Implement a cohesive source candidate and source contract fixtures; no native run or compilation.

## Context by reference
- Expert: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md
- Existing correction: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/briefs/windows-monitor-implementation.md
- Owned inactive clean worktree: /Users/hoppworks/projects/rhai-windows-scoped-runner, task/windows-scoped-runner, frozen8f75da530c91c34fc3062e29d45bb865e2d411e4.
- Current source boundaries: tools/windows-scoped-runner/README.md section Remaining custody and proof boundaries; MonitorStagingHandoff.cs, MonitorTransport.cs, WindowsCustodyBackend.cs; old creation mechanism ScopedRunner.cs is only a source reference.
- Root state: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/coordinator-state.md

## Requirements
Monitor must exclusively create/hold a private noninheritable unnamed payload job with kill-on-last-close. Payload must be associated at creation using JOB_LIST and suspended; no create-then-assign or unmanaged fallback. All setup failure/unwind paths retain exact handles until safe termination/observation and close every initialized attribute allocation. Never authorize runtime removal from PID disappearance or a boolean: exact job closure proof remains gated. Integrate only where existing host challenge/lease/staged identity transitions establish prerequisites; leave payload resume disabled when any prerequisite remains unavailable. Do not produce a fake executable acceptance path or replace missing behavior with successful no-ops. Document precisely what source is implemented and what remains unverified.

## Scope and limits
Existing user authorization covers ordinary reversible source implementation and necessary delegation. Earlier11:17–11:47 Windows allowance is exhausted and remains preserved; this is a new agent-selected30-minute active-work planning checkpoint for source-only prerequisite progress, justified by confirmed clean owned source and concrete missing mechanism. No native invocation allowance is revised. No guest/SSH/UI input, native build, unsafe bootstrap, packages, services/admin, credentials, global/home/config changes, broad cleanup or second Expert chain. Preserve history; no reset. Read project AGENTS.md and applicable instructions. Reuse the exact owned worktree; root does not edit it. No push/merge until root source review; commit as hoppworks <daniel@hoppworks.de> with no attribution. Existing safe scoped source checks may be used; tests uncompiled/unexecuted must be reported as such.

## Deliverable
One bounded source candidate with paths/hashes, source fixtures, checks actually run, failure-path review and exact remaining boundaries. Keep a compact .scratch/windows-monitor-job-owner/coordinator-state.md in your owned worktree. At checkpoint review concrete progress/capacity; do not silently expand scope or claim native proof. Report before build/run. Fresh Standard implementation context; no new Expert review for cause02.
