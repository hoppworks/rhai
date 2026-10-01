# Shared Child development RED source review

Status: preparation gate incomplete; invocation44 has not launched. This is independent development evidence with installed direct stable tools, not optional1.77.2 or platform/release acceptance. Cause07 procurement remains stopped and cumulative43 preserved.

Reviewed mutable inputs from `/Users/hoppworks/projects/rhai-process-unix-run`: `tests/fixtures/sys_process_shared_child_contract.rs`, `.scratch/process-unix-run/shared-child-spawn-red.py`, wrapper and activation note; documented contract in `docs/sys-package-plan.md`. Same responsible context owns corrections.

Required corrections before freeze:

- `Scope::remove` is generic; explicitly remove a `Dynamic` instead of leaving an uninferrable type parameter.
- Do not move the controller out of the scoped runner process group. Its hard watchdog must retain custody. The initial missing-public-spawn RED creates no OS fixture child; future GREEN needs complete child cleanup coverage before activation.
- A consumed/reaped controller must not be treated as live by Drop or cause a numeric retired group signal.
- Independently verify exact controller absence, fixture root containment/identity and absence, and final source hashes; retained initial hash output alone does not prove unchanged inputs.
- Execute finite wait while stdin remains blocked, before the release-input event, to match the stated acceptance requirement.

Expected first RED must compile and execute exactly the named public Engine test, return101 for missing `spawn`, reap its exact controller, and remove its exact fixture root. A setup/compiler failure is not behavioral RED; a generic expected nonzero status is insufficient. Current source is uncompiled/unrun. Preserve separate RED classification and original release requirements.
