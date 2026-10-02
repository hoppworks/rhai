No actionable findings. Source-only acceptance of the correction in [docs/sys-process.md:84](/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/docs/sys-process.md:84).

- Direct execution wraps failures in `SysError::Process { cause, report }`: [unix.rs:2290](/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/src/packages/sys/process/unix.rs:2290). Spawned-child waits use the same variant: [unix.rs:1783](/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/src/packages/sys/process/unix.rs:1783).
- Output overflow uses `ProcessCause::OutputLimit`: [unix.rs:2733](/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/src/packages/sys/process/unix.rs:2733); script classification remains `"OutputLimit"`: [process.rs:173](/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/src/packages/sys/process.rs:173).
- `error.process` is supported: [error.rs:169](/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/src/packages/sys/error.rs:169). Public exports and report registration are present: [mod.rs:45](/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/src/packages/sys/mod.rs:45), [mod.rs:95](/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/src/packages/sys/mod.rs:95).

Confirmed current instruction revisions by SHA-256: global `373f36f813b65fa1f0d2016a5a2d93e2bd56694e2d6a683707937a5c2a34fc95`; project `d1f6f0da5edfe418579c92f7c2f905db879e71cdd830ffbf9e808f1bc2bee58f`.

OCR preview succeeded despite Apple Git diagnostics, but excluded Markdown as unsupported; manual affected review completed with OCR’s default rules. Scoped coverage: 1 file reviewed, 0 skipped, 100%.

Inspected runtime sources are unchanged from baseline `4c9d87dcb1d5b46681135b282c47e27790c24faf`. No builds, native acceptance claims, source writes, or Git mutations. Existing runtime evidence is unaffected by this documentation-only change.