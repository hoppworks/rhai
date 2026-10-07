# Escalation 21: api-metadata-contract-assertions

## Question
How can the generated public TCP documentation metadata contract be asserted
accurately across all overloads without repeated incidental wording mismatches,
while preserving meaningful missing-comment RED and complete documented limits?
Select one minimal bounded follow-up for existing Standard, not a new framework.

## Why escalated
- Two completed corrections failed independent affected source checks for the
  same metadata literal-assertion cause: 8bf and07862c3a8.
- The second still expects underlying io error kind but public comment uses I/O.
- No native run was allocated for either corrected-schema frozen candidate.

## Context by reference
- /Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/stdlib-api-docs-review.md (affected8bf and current078 review)
- /Users/hoppworks/projects/rhai/.worktrees/stdlib-api-metadata/tests/net_metadata.rs
- /Users/hoppworks/projects/rhai/.worktrees/stdlib-api-metadata/src/packages/net/{stream,listener,error}.rs
- /Users/hoppworks/projects/rhai/.worktrees/stdlib-api-metadata/tests/sys_policy.rs
- /Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/coordinator-state.md

## Constraints and decisions
Read ~/.agents/AGENTS.md, project AGENTS.md, config/roles.toml and relevant
campaign/tdd review rules before action; current known skills revision6830c49.
Read-only diagnosis; no edits except answer, no native/SSH/Cargo, no installs,
process actions or foreign cleanup. Frozen07862c3a8ed3707956aba16f1d4bd9f66cd57cbb
is candidate. Dirty unix Child comments excluded. Existing API compatibility and
unchanged example proof remain applicable. Strict public Engine JSON seam is
agreed; real generated metadata plus independent read-back and meaningful RED
required. No keyword removal merely to obtain GREEN; per-overload coverage stays.

## Tried so far
Stable cause api-metadata-contract-assertions; first escalation for this cause.
Original docs/test8bf -> source NOTREADY: clones/direction/peer/kind/message
literal mismatches, plus inaccurate EOF/effective cap docs. Correction1.
Frozen078 -> those corrected, source NOTREADY: io vs I/O literal mismatch.
Correction2. Existing reviewer consolidating any additional findings separately.
Native1 wrong JSON key is schema infrastructure cause1, not either correction;
native2 admission setup aborted143, native3 gate expired unallocated; retain all.
Cumulative active/cost unknown; prior proofs untouched; no budget reset.

## Deliverable
Write verdict, concise diagnosis and one specific permissible follow-up to
/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/escalations/21-api-metadata-contract-assertions.answer.md.
Return at most15 lines plus path. Include a deterministic lightweight contract
alignment check covering all current per-overload requirements before native,
without duplicating runtime implementation or replacing real metadata proof.

## Budget
Expert named role;15-minute active diagnosis checkpoint (planning estimate),
no native launch. Stop once minimal cause/repair is clear. One bounded follow-up
will be dispatched to same Standard after answer, preserving cumulative history.
