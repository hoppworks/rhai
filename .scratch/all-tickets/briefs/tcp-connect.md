# First accepted TCP vertical slice

## Requirement

Implement optional NetPackage/NetConfig independent from sys: numeric endpoint
validation, default denial, exact connect grants, finite positive host connect
ceiling, shared logical socket close and catchable NetError fields. Prove a real
Rhai script establishes only an authorized connection, independently observed by
an owned TCP peer; denial and invalid ports produce no peer acceptance; clones
share idempotent close. Leave listener and byte-transfer contracts explicitly open.

## Context

Read AGENTS.md and .scratch/all-tickets/tcp-proposal.md and release-proposal.md.
Public test seams are approved. Follow existing stateful SysPackage registration
style, but do not depend on sys. Core MSRV must remain unchanged. Reuse established
Cargo integration-test proof method, through real Engine and real OS sockets.

## Scope and workflow

Own worktree /Users/hoppworks/projects/rhai-tcp-connect, task/tcp-connect, based on
e45c675c. Implement via meaningful TDD RED then GREEN, preserve proof and wrong
expectation control. Use the tdd and e2e-proof skills from agent-skills. Keep related
corrections in this context. Derive routine Rust API spelling from package patterns;
do not change approved contract or invent additional public behavior. Document
unimplemented listener/read/write requirements accurately. No merge/push/remote
writes. Commit atomically as configured human author without attribution.

## Limits

Fresh feature slice, not a process repair. 60 active minutes total including
independent coordinator review, measured from start. Private scoped builds only
via /Users/hoppworks/projects/agent-skills/tools/run_scoped.py, owned source copy,
CARGO_HOME and CARGO_TARGET_DIR under AGENT_RUNTIME_DIR. Max 15 minutes per scoped
invocation, 2 GiB private build storage, eight live fixture sockets, no shared
services; explicit readiness and bounded cleanup/join. Do not touch agent homes.
Record launches/time/resources and cause diagnoses in existing local state. No
default launch-count cutoff; stop after two consecutive launches without new
diagnosis or closed checks, contradictory evidence, hard-cap exhaustion or a
required uncovered decision. No new Expert chain without coordinator consultation.

## Deliverable

Committed ref, exact changed files, proof path and commands, independent peer
readback/control, fixture cleanup and limitations. Do not claim whole net package,
feature matrix or native three-OS acceptance. Report when source/RED exists so
coordinator can review during the same slice.
