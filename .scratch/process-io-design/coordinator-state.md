# Process I/O design coordinator state

## Goal and budget

Close the bounded production Rust I/O design prerequisite from `.scratch/all-tickets/briefs/process-io-design.md` with a source-grounded design and concrete failing native test for cancellation. No production code, build, fixture, process launch, or new calibration is allowed.

- Original start: 2026-09-30 14:20:09 UTC
- Fixed deadline: 2026-09-30 14:50:09 UTC
- Worktree: `/Users/hoppworks/projects/rhai-process-io-design`, branch `task/process-io-design`, base `ed56cbf018207c211f296c41dda8fe904a41eba5`
- Required author and committer names: `hoppworks` (lowercase); preserve configured email.

## Completed

- Read repository `AGENTS.md`, process contract, release proposal, process source gate review, and accepted prototype source/evidence.
- Corrected accepted evidence attribution: Python controller/custodian and Python I/O workers ran; Rust executable was invoked only in fixture modes, and its historical bare main was not run. Thus accepted proof does not establish Rust I/O-worker cancellation, poll-plus-wake, bounded production capture, Windows/Linux behavior, MSRV, or Rhai Engine behavior.
- Reviewed official Rust `Child` and Unix `CommandExt` docs; Microsoft `CancelIoEx`, synchronous cancellation, job object, and suspended process creation docs; current `libc` MSRV; and official `windows-sys` 0.61.2 manifest/features and windows-rs version guidance. Recommended optional target-specific windows-sys 0.61.2 (MSRV 1.71) for the optional 1.77.2 surface, isolated from core 1.66; exact 1.77.2 toolchain is not installed and remains unverified. This is a dependency design candidate, without Cargo edits.
- Wrote `.scratch/process-io-design/design.md` with private owner/adapter boundary, bounded input/output and N/N+1 behavior, cause precedence, POSIX wakeable nonblocking polling, Windows overlapped cancellation/completion lifetime, pinned managed-scope identity, dependency assessment, exact evidence limits, and a cleanup-safe native Linux acceptance test.

## Current step

Complete accuracy/diff review and commit both design records atomically using command-local Git name configuration. Report immutable commit ref and remaining native gates. Do not push or merge.

## Remaining native gates

1. Standalone Rust poll-plus-wake cancellation proof on native Linux with active reader/writer handshakes, inherited-pipe holder, large concurrent input/output, bounded capture, pinned group identity, cleanup-safe missing-wake control, and exact independent child cleanup.
2. Equivalent native macOS Rust proof for the wake descriptor; accepted Darwin package proves Python I/O worker behavior only.
3. Native Windows proof must exercise overlapped cancellation and completion lifetime.
4. Production Engine contract acceptance, including managed process group/job behavior, cleanup/setup failure, output/deadline precedence, bounds, and independent fixture readback.
5. Rust 1.77.2 exact dependency resolution and feature/MSRV release matrix; current local toolchains do not include 1.77.2. Core-only Rust 1.66 feature-isolation proof also remains pending.

The design closes only this documentation prerequisite. It does not claim the full cancellation gate or implementation acceptance.
