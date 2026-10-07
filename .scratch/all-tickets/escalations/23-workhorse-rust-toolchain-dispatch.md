# Escalation 23: Workhorse Rust toolchain dispatch

## Question
Why do the two Package B Workhorse invocations stop after the Rust 1.77.2 installer reports success, before the reviewed RED/GREEN case leaves durable version or test evidence? Identify the smallest safe correction that preserves the same public Engine/real-OS acceptance within the remaining authorized follow-up, and separate verified cause from inference.

## Why escalated
- Two Package B setup recoveries on 2026-10-07 (08:42:05Z and 08:43:38Z) did not reach a durable test assertion; the required two-recovery escalation trigger is met.
- Both outer logs end after `rustup` reports `1.77.2` installed. The second recipe used absolute binaries under private `RUSTUP_HOME`, but neither run left version/control evidence in the persistent remote evidence directory.
- The live run reported `rustup is not installed at <private CARGO_HOME>`, but this exact stderr is absent from the retained outer logs; Package A's historical `package-result.json` errors are a different run and must not be mistaken for Package B evidence.
- The missing Package B assertion is an infrastructure/setup outcome, not a product correction or test RED. No product source changed in Package B.
- Historical escalation 07 concerned macOS component-download timeouts; determine whether it is materially distinct from this post-install Workhorse failure rather than reusing or resetting its history.

## Context by reference
- `/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/coordinator-state.md` (current Package B section)
- `/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/docs/sys-package-plan.md` (section 6, especially 6.6)
- `/Users/hoppworks/projects/rhai/.worktrees/process-first-cause/.scratch/all-tickets/process-first-cause-evidence/package-b-child-wait-01/inputs/run.sh`
- `/Users/hoppworks/projects/rhai/.worktrees/process-first-cause/.scratch/all-tickets/process-first-cause-evidence/package-b-child-wait-01/{infrastructure-setup-01.log,outer-attempt-02.log,admission.json,admission-retry.json}`
- `/Users/hoppworks/projects/rhai/.worktrees/process-first-cause/.scratch/all-tickets/process-first-cause-evidence/package-b-child-wait-01/inputs/{source.patch,Cargo.lock,SHA256SUMS}`
- `/Users/hoppworks/projects/rhai/.worktrees/process-first-cause/.scratch/all-tickets/process-first-cause-evidence/package-b-child-wait-01/inputs/source.tar`; `tests/sys_process.rs` and the Package B review recorded in coordinator state
- Workhorse scope `/root/.local/share/agent-builds/rhai/rhai-child-wait-20261007-083819`; read-only listing found only pinned inputs and an empty `evidence/` directory after both runner exits
- `.scratch/all-tickets/escalations/07-rust-toolchain-setup.md` and its answer
- `/Users/hoppworks/.agents/AGENTS.md`, `/Users/hoppworks/projects/rhai/AGENTS.md`, `/Users/hoppworks/.agents/skills/campaign/references/escalation-brief-template.md`

## Constraints and decisions
- Preserve Package A's accepted proof and Package B's reviewed test/source pins; no product-source edit, assertion weakening, or changed acceptance.
- Use the existing scoped runner, private `CARGO_HOME`, `RUSTUP_HOME`, `CARGO_TARGET_DIR`, HOME and TMPDIR; no shared Cargo/Rustup cache writes, Agent-home changes, global installs, or public-upstream writes.
- Keep the existing outer/runner bounds (600/585 seconds), two Cargo jobs, process/resource limits, Workhorse machine-wide concurrency, and exact source/lock/runner hashes. Recheck live capacity before any later heavy launch.
- Do not touch foreign processes or sessions, and do not add transport/wrapper layers. Preserve the real-OS wrong-expectation RED, restored GREEN and independent child/readback acceptance.
- No commits, pushes, merges, new Goal, or release claim. This Expert review is read-only. The Coordinator may use at most one bounded follow-up repair package after the answer; no second Expert chain for this cause.

## Tried so far
- Stable cause: `workhorse-rust-toolchain-dispatch` (root cause still unverified).
- Launch 1, 08:42:05Z: fresh admission passed; exact Rustup install reported 1.77.2 installed; invocation stopped before any durable Package B version/test evidence. One infrastructure recovery; zero product corrections; zero accepted assertions. Outer log: `package-b-child-wait-01/infrastructure-setup-01.log`.
- Launch 2, 08:43:38Z: fresh admission passed; recipe switched to direct toolchain-bin paths; installer again reported success, then no durable version/control evidence remained. One additional infrastructure recovery for the same observed stop point; zero product corrections; zero accepted assertions. Outer log: `package-b-child-wait-01/outer-attempt-02.log`.
- The persistent remote `evidence/` directory is empty after runner cleanup. The live error string was observed but not preserved in the outer log; do not treat the unrelated older Package A `RuntimeError: baseline-red-direct requires exactly one raw child receipt` as this Package B failure.
- No compiled artifact is retained; both scoped private runtimes were removed. The pinned source archive, patch, lock, recipe and local logs remain owned by the writer.

## Deliverable
- Write the full answer to `.scratch/all-tickets/escalations/23-workhorse-rust-toolchain-dispatch.answer.md`.
- Format: verdict first, then evidence-based reasoning, then the concrete lowest-overhead next action and finite stop condition.
- Return to the Coordinator in at most 15 lines plus the answer path. Do not execute or mutate anything.

## Budget
Expert per `/Users/hoppworks/projects/agent-skills/config/roles.toml`; one read-only diagnosis, at most 15 minutes, zero build/install/test launches. Stop if the retained records cannot distinguish the failure stage; state what exact non-invasive evidence would settle it and do not propose an unbounded retry.
