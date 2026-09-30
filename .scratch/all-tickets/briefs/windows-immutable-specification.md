# Bounded immutable launch specification source

Continue the existing Windows custody correction in its owned worktree and
responsible context. Read AGENTS.md and the retained Expert answer, especially
Private launch and control protocol. Disposition and Running renewal were source
reviewed; none is native accepted. Implement the next bounded source requirement,
not payload launch or a new escalation.

## Contract

Define a private immutable specification containing only source directory,
relative executable and literal arguments. Policy limits come from the fixed
production policy and cannot be raised by input. Runtime/evidence/cleanup paths,
PIDs, job handles, environment expansion, shell commands and host-generated
authorization are not specification fields. Future monitor allocation must remain
the sole source of runtime identities.

Use a versioned, explicit bounded representation and parser without new packages.
Bound total encoded input to 8192 bytes, individual fields, argument count and
decoded command-line length. Reject unknown version/fields, duplicate fields,
trailing bytes, malformed UTF-8, NUL/control characters, missing/empty required
paths, invalid source path form, unsupported executable path syntax and overflow.
Reuse the existing path validation rules where applicable, keeping this parser
free of filesystem I/O and resource allocation. Validating syntax does not prove
source identity, existence, staging, executable validity or authority.

Deep-copy caller input and keep collections/bytes private. Mutation of original
arguments or values returned to a caller must not change the accepted snapshot.
Literal arguments are passed to CreateProcess using established Windows quoting;
never interpret them as shell input. Keep representation/limits explicit in the
README, including a future transport adapter boundary under the existing 512-byte
frame, 32-frame/8192-byte queue bounds. Do not increase existing queue limits.
Do not integrate a specification into workload execution or locally renew leases.

## Fixture and delivery

Author fixture source first: valid empty/nonempty arguments and Unicode; immutability;
exact input/argument/command bounds; wrong version, truncation, malformed UTF-8,
duplicate/unknown fields, trailing bytes, invalid source/executable path, controls,
overflow and attempts to supply cleanup/policy overrides. Require intended
diagnostics rather than catch-all failure acceptance. Round-trip valid values and
assert no parser I/O/runtime allocation. Identify unsupported future wire integration
explicitly instead of claiming a working host connection.

No compiler, fixture, build, native/guest command, install, measurement, remote
write or workload launch. Preserve disabled public entry and exact-job proof gate.
Commit atomically as the configured human author. Report source checks and
unexecuted fixture limitations. Apply related source corrections in this context;
do not claim executed RED/GREEN, custody acceptance or a completed ticket.
