# Escalation 14: linux-managed-receipt-custody

## Question
Identify the smallest source-driven correction that makes the managed-success helper and collector accept genuine frozen success/held receipts and reject corrupted receipts without weakening strict OS acceptance. This advances local process/release tickets 03/06 and the overall all-tickets goal. Diagnose the whole affected receipt grammar once, including dependent custody checks; recommend one bounded follow-up repair.

## Why escalated
- Two completed corrections failed the same receipt/custody check: a2b1/72ad and 4cdd/2016.
- The latest parser omits actual ` cause=none diagnostic=none` before the API newline.
- Synthetic positives modeled an abbreviated receipt, so they passed while actual source-format receipts reject.
- No native execution, staging or build occurred; this is a harness correction cause, not product failure.

## Context by reference
- /Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/AGENTS.md
- /Users/hoppworks/.agents/AGENTS.md
- /Users/hoppworks/projects/agent-skills/config/roles.toml
- /Users/hoppworks/projects/agent-skills/config/codex/agents/expert.toml.tmpl
- /Users/hoppworks/.agents/skills/campaign/SKILL.md
- /Users/hoppworks/.agents/skills/campaign/references/repair-package.md
- /Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/coordinator-state.md (Current step and next action)
- /Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/linux-managed-success-review.md (last two affected rechecks)
- /Users/hoppworks/.codex/worktrees/linux-managed-success/rhai/tests/sys_process.rs (success API outcome around 1621, newline around 1650, final receipt around 1893)
- /Users/hoppworks/.codex/worktrees/linux-managed-success/rhai/.scratch/all-tickets/linux-managed-success-proof.py
- /Users/hoppworks/.codex/worktrees/linux-managed-success/rhai/.scratch/all-tickets/collect-linux-managed-success.py
- /Users/hoppworks/.codex/worktrees/linux-managed-success/rhai/.scratch/all-tickets/linux-managed-success-stage.sh
- /Users/hoppworks/.codex/worktrees/linux-managed-success/rhai/.scratch/all-tickets/linux-managed-success-launch.sh
- /Users/hoppworks/.codex/worktrees/linux-managed-success/rhai/.scratch/all-tickets/linux-managed-success-prepare.md
- /Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/linux-managed-zombie95-evidence/proof-evidence/managed-zombie-green.stderr

## Constraints and decisions
Read current global/project rules, relevant campaign instructions and Expert template before action; confirm loaded faba3db revision. Read-only diagnosis: do not edit source/recipes, SSH, stage, build, allocate native96, touch other work or restart processes. Local pure reproductions may execute actual parser functions without bytecode writes. Frozen source003da06421fbd11c26e0c96ab5013416c0939a1d stays unchanged. Strict host/start/group/code/capture/cleanup binding and success-only malformed negatives under combined stderr must remain. Preserve current baseline hashes and history. Only fork main is writable by Coordinator after verification; no upstream writes. Native bounds remain 600s outer/585s runner/540s helper including 30s export reserve, jobs2, descendants16, storage preempt1572864KiB, RSS/storage hard2097152KiB. One Expert chain and one follow-up for this cause; do not renew stopped unrelated macOS/Windows causes.

## Tried so far
Stable cause: linux-managed-receipt-custody. Initial69fc/5613 submission identified receipt-count and custody/export gaps. First completed correction a2b1/72ad failed (shared start ticks, list/items, undefined remote names, unbound success API): correction count1. Second completed correction proof4cdd64b3be763c317568abab15f763b17b03a4e629e9a27d47934d347bcb446a / collector2016e5406da01889fea1316c3b7286334193c84433dca6209a8835e94225ba9b fixes three defects but rejects actual cause/diagnostic suffix: correction count2. Stage52483695, unchanged launcher27e1ee59, prepare1494a730. No prior Expert for this cause, no native consumption for these corrections. Cumulative Unix95 preserved; prospective96 unallocated. Earlier wrong-anchor source correction is a distinct preserved cause.

## Deliverable
Write verdict, reasoning and exact next repair/check steps to /Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/escalations/14-linux-managed-receipt-custody.answer.md. Give source-derived complete positive grammar and meaningful malformed negative cases; identify any other concrete affected blocker in the actual helper/collector path. Return at most15 lines plus answer path. No broad new framework or review pipeline.

## Budget
Named Expert per current roles.toml, fresh non-fork. One independent diagnosis with a 15-minute active-work planning checkpoint; stop once a concrete minimal route and affected checks are established. This is a planning estimate, not a user cap. Usage unavailable remains unknown. The Coordinator will record/apply one bounded follow-up repair after this answer.
