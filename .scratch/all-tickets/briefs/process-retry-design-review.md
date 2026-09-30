# Question

Can the proposed process supervision design safely support the one newly
owner-authorized correction attempt, including whole-runner interruption?

# Why escalated

The original proof was rejected and the first correction stopped before execution.
The owner explicitly authorized a further bounded attempt with pre-reviewed
supervision. This is that required design review, not a reset of cause history.
The draft explicitly excludes orchestrator/scoped-runner death cleanup; determine
whether this contradicts the accepted requirement and supply the smallest safe
amendment if possible. No fixture may run while supervision remains unsafe.

# Context by reference

- /Users/hoppworks/projects/rhai-process-prototype/.scratch/process-prototype/evidence/retry-design.md at 2a3996cd.
- /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/01-process-prototype-proof.answer.md.
- /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/coordinator-state.md.
- /Users/hoppworks/projects/rhai-all-tickets/.scratch/stdlib-wayfinder/issues/03-process-contract.md.
- /Users/hoppworks/projects/agent-skills/tools/run_scoped.py.
- /Users/hoppworks/projects/rhai-process-prototype/AGENTS.md.

# Constraints and decisions

Review only; no builds, fixture execution, guest changes or remote writes.
Use first-party sources for OS safety facts. Preserve existing proof limitations.
The orchestrator, guardian, workload, anchor, holder and workers must all have
safe exact ownership, bounded cleanup and applicable independent readback.
Signal identity cannot depend on a reaped PID, check/use liveness or unproven
lease startup. Runner interruption must not orphan separately grouped fixtures.

# Tried so far

Original 35a8cf52 proof rejected for five validated issues. Expert answer supplied
one correction plan; 501fa184 stopped without implementation or execution.
Owner then authorized one further bounded attempt. Design-only 2a3996cd now
proposes a guardian alarm, unreaped workload leader, WNOWAIT and narrow controls.

# Deliverable

Write process-retry-design-review.answer.md beside this brief. State approve or
reject, exact safety blockers, and a minimal amended design if supportable.
Explicitly assess whole-runner death, partial spawn/lease setup, signal masking,
PID/group lifetime including zombie leader, and how a worker shutdown is bounded.
Return at most 15 lines plus the answer path.

# Budget

One read-only design review. Do not start another escalation or implementation.
The remaining owner-authorized implementation attempt follows only a safe design.
