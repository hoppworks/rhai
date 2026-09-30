# Authorized TCP listener slice

## Requirement

Extend the accepted optional NetPackage with separately granted numeric listen
and bounded accept. See AGENTS.md, tcp-proposal.md and release-proposal.md. Default
deny remains; exact IP/port grant with explicit port-zero permission, validation
before OS bind, actual local address, accepted NetStream with inherited policy,
shared idempotent listener close and shared package stream/listener quota.
Prove a real script listener accepts only an authorized independent client, and
no-client accept times out with catchable NetError. This slice does not implement
stream bytes, but must preserve outgoing-connect acceptance.

## Work and scope

Fresh owned worktree task/tcp-listener based on the coordinator's integrated HEAD
at /Users/hoppworks/projects/rhai-all-tickets. Create it at
/Users/hoppworks/projects/rhai-tcp-listener. Do not touch foreign worktrees.
Use tdd and e2e-proof skills, real Engine plus independent real sockets. Reuse
source registration, error and quota conventions. No blocking operation may hold
a shared lock preventing clone close. Include exact denial/no-bind side-effect,
ephemeral port readiness, shared quota for accepted streams, listener final-drop,
close and finite accept checks, and a wrong independent-peer assertion control.
Document uncovered full-package contracts. No push or merge; human-authored commits.

## Finite limits

60 active minutes including coordinator review from recorded start; <=900 seconds
per scoped invocation (explicit --timeout 900), <=2 GiB private build storage,
CARGO_BUILD_JOBS=2 and <=12 owned live fixture sockets. Use python3
/Users/hoppworks/projects/agent-skills/tools/run_scoped.py with source copy,
CARGO_HOME/CARGO_TARGET_DIR inside AGENT_RUNTIME_DIR. Record size observations
with units and method; do not label cumulative size or an end measurement a peak.
Export logs before cleanup. Record every launch and diagnosis in local state;
stop after two consecutive launches without diagnosis/closed check or hard limits.
No new Expert chain without coordinator consultation; no native guest changes.

## Deliverable

Report RED and draft source early. Return committed ref, proof commands, independent
readback, wrong control, cleanup, resource accounting and unverified gates.
