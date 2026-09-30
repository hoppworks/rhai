# Running lease renewal source correction

Continue in the existing responsible candidate context after disposition review
corrections are committed. Read the project AGENTS.md and retained Expert answer
02-windows-runtime-custody.answer.md. This is a related substep of the existing
incomplete custody correction, not another escalation or native attempt.

## Required behavior

The Running protocol state currently cannot issue a challenge, so a live payload
would expire at its initial short lease. Support fresh periodic host challenges
in Running, with phase binding, one outstanding nonce/sequence, response expiry,
single consumption, and no create/resume authorization from a renewal. Preserve
irreversible Stopping, EOF/client-death behavior, fixed production policy, setup
deadline and independent absolute deadline. Never renew past the absolute cap.

Author fixture source first. Prove in the authored assertions that timely fresh
Running responses maintain Running beyond the initial lease and setup deadline,
but cannot extend the absolute deadline. Assert every intended response succeeds
and each pre-deadline tick remains Running; the old early-expiry loop is not
absolute-deadline coverage. Include replay, wrong phase/nonce/sequence, exact
expiry boundary, a blackholed live client, and responses after terminal stopping.
Fixtures are protocol behavior only, not proof of OS/process/job supervision.

## Constraints and deliverable

No compiler/build/fixture/native/guest execution, installation, remote writes or
workload launch. Keep the public payload entry disabled. Do not issue exact-job
closure proof or relax filesystem custody. Reuse existing bounded policy/test
seams and transport architecture; do not introduce a new runtime or dependency.
Commit atomically as the configured human author and report source diff checks,
unexecuted fixture coverage and remaining monitor/native gates. Apply related
source corrections in this same context. Do not claim TDD RED/GREEN or ticket
acceptance from authored assertions.
