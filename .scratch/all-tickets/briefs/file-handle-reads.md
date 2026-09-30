# Bounded streaming file reads

## Requirement

Complete read_string([len]) and read_blob([len]) for the accepted shared handle
API. Omitted/zero length reads toward EOF; positive length bounds bytes from the
current cursor. Text requires valid UTF-8, blobs preserve bytes and are omitted
under no_index. Negative length fails before allocation or cursor movement.
Engine nonzero string/array limits continue bounding checked reads. Resource
bounds remain active under unchecked; do not call absent Engine limit getters.
Preserve all already accepted open/write/seek authority and error contracts.

## Context and first action

Worktree /Users/hoppworks/projects/rhai-file-reads, task/file-reads, e365008a.
Read project AGENTS.md, file-handle-compatibility.md, release-proposal.md, current
fs.rs/config.rs and accepted file-handle-open-review.md. Role Standard, fresh
bounded feature requirement; use campaign, tdd and e2e-proof. No old cause reset.
Before changing public configuration, send a short concrete bounded-read design
and the exact existing limit behavior. SysConfig currently has no file read cap.
Proposed engineering choice: additive host max_file_read builder, finite 8 MiB
default, applicable to streaming reads in checked and unchecked, min with nonzero
Engine limit when available. Describe zero host-cap semantics explicitly and
avoid allocating requested INT::MAX or unbounded read_to_end. Do not change whole
file read_file APIs in this slice. Coordinator review of the proposal precedes
public API implementation; unrelated design investigation/TDD may proceed.

## Proof

Start with a meaningful failing real Engine/script read contract. Real private
files and independent fixture truth prove cursor advancement/clone sharing,
positive and omitted/zero lengths, EOF, invalid UTF-8 errors and lossless blob,
negative rejection without cursor movement, host and Engine caps, checked INT
boundaries where applicable. Preserve open handles after a path is replaced or
removed only using platform-supported real operations with honest applicability.
Target sys_fs full suite plus sync/no_index and unchecked affected checks; combine
related builds/checks/wrong independent payload control into a bounded scoped
invocation. Use --test-threads=1 for a measurable fixture-resource cap. No mocks,
fixed sleep readiness or unsafe broad cleanup. Report native/release gaps.

## Bounds

Maximum 60 active minutes including coordinator review from actual start, each
scoped invocation <=900 seconds, private storage <=2 GiB, <=16 simultaneous owned
fixture files/handles, CARGO_BUILD_JOBS=2. Use python3 agent-skills/tools/run_scoped.py
with source copy/CARGO_HOME/CARGO_TARGET_DIR/TMP under AGENT_RUNTIME_DIR. Export
required logs before cleanup. Record every launch, source diagnosis, active time
and stop conditions in .scratch/file-reads/coordinator-state.md. End storage is
not peak; disclose measurement limits. Stop at hard limits, contradictory proof,
two consecutive launches without diagnosis/closed check, or uncovered decision.
One Expert chain only if needed and within original allowance. No installs,
agent-home changes, credentials, shared services, remote writes or merges.

## Deliverable

Send proposal and RED early; atomically commit source/tests as configured human
user without attribution. Report exact ref, changed files, proof and wrong-control
logs, private runtime cleanup and remaining acceptance. Keep needed private proof.
