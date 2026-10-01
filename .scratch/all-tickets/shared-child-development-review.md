# Shared Child development RED source review

Status: initial RED source gate conditionally released for the exact hashes below; invocation44 has not yet been observed launched. This is independent development evidence with installed direct stable tools, not optional1.77.2 or platform/release acceptance. Cause07 procurement remains stopped and cumulative43 preserved.

Reviewed mutable inputs from `/Users/hoppworks/projects/rhai-process-unix-run`: `tests/fixtures/sys_process_shared_child_contract.rs`, `.scratch/process-unix-run/shared-child-spawn-red.py`, wrapper and activation note; documented contract in `docs/sys-package-plan.md`. Same responsible context owns corrections.

Required corrections before freeze:

- `Scope::remove` is generic; explicitly remove a `Dynamic` instead of leaving an uninferrable type parameter.
- Do not move the controller out of the scoped runner process group. Its hard watchdog must retain custody. The initial missing-public-spawn RED creates no OS fixture child; future GREEN needs complete child cleanup coverage before activation.
- A consumed/reaped controller must not be treated as live by Drop or cause a numeric retired group signal.
- Independently verify exact controller absence, fixture root containment/identity and absence, and final source hashes; retained initial hash output alone does not prove unchanged inputs.
- Rust Result::expect formats the error using Debug; the harness originally expected Display text. Emit the exact typed missing-function error and its Display diagnostic or classify the actual specific Debug variant/signature.
- Before future GREEN, use independently known libtest stdout framing (existing tests/sys_process.rs LIBTEST_QUIET_START) instead of asserting that self-executed test binaries emit only fixture bytes.
- Execute finite wait while stdin remains blocked, before the release-input event, to match the stated acceptance requirement.

Expected first RED must compile and execute exactly the named public Engine test, return101 for missing `spawn`, reap its exact controller, and remove its exact fixture root. A setup/compiler failure is not behavioral RED; a generic expected nonzero status is insufficient. Current source is uncompiled/unrun. Preserve separate RED classification and original release requirements.

## Initial RED gate

Independently read corrected source, Python AST, zsh syntax, and unchanged production Unix SHA-256 `a41c1c9dc237d9d6b54344399f8bee929cb2f507ed7f04572f173375f64eb265`. Corrections now explicitly remove Dynamic, keep controller in runner group, avoid signaling retired numeric groups, compare injected source against its pre-Cargo expected hash, independently verify controller ESRCH/root containment/absence, and issue timed wait before input release. Error Display now produces the classifier's specific missing-spawn text.

Conditional release to the same owner for exactly one NEW development invocation44 after freezing/recording these identities:

- Fixture: `0b87c969997880ffdd853cc3d26dff2bd3974923f4d39521ba72c3969884e9a7`
- Harness: `62a5fe7a5b435285d9aaf281f963f8a7e59938a2d980f4582371ff1ae67b30cc`
- Wrapper: `e67fb577c4e8b6d6864a13589c08f20bdb768e63d78b4a66977eb462814d4734`

Changed identities require final focused read before launch. Outer600s, Cargo540s, jobs2, private homes/source/lock/target/temp, inherited group, existing2GiB policy and sampled1572864KiB stop. Direct installed stable tools only; executed versions must be retained. No transfer/install and no production source edits before actual specific RED. Future GREEN fixture/libtest framing and descendant cleanup remain open and are not accepted by this gate.
