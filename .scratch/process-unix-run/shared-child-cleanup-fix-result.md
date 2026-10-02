# Shared Child cleanup source correction result

## Scope and revision

Applied the three material findings from
`.scratch/process-unix-run/shared-child-cleanup-review-summary.md` to immutable
revision `58dbf90f671281fc9a8845f7546f23f225c34b4b`. The agent-skills revision
read for this work was `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. Changes are
limited to the shared-child fixture, its existing activation note, and the
prior repair report. Production `src/packages/sys/process/unix.rs`, the global
runner, other worktrees, installed skills and agent homes were not changed.

## Corrections

- Expected-panic acceptance requires a failed controller status, the exact
  intentional panic payload, the controller's scenario-tagged cleanup event,
  fixture `ESRCH`, and a controller-issued receipt matching scenario, exact
  controller PID, fixture PID and fixture root. A successful controller is
  rejected explicitly. A source-level control covers both an ordinary
  successful controller incorrectly expected to panic and an unrelated panic.
  Neither control has been run natively.
- `ControllerGuard` releases only the two synchronization paths within its
  unique owned fixture root regardless of initial PID publication. It refreshes
  the recorded PID throughout bounded grace and after exact controller reap,
  signals only its owned `ControllerChild`, and retains records when PID or
  closure evidence is missing. The outer normal receipt is labeled as an outer
  observation and binds scenario and process identities; it is not described as
  controller-issued. Receipt files alone do not establish custody.
- Corrected the timeout description: hold mode has one 18-second deadline;
  blocked-input mode has two distinct 18-second waits and a blocking stdin read.
  The 24-second value is the outer polling deadline, followed by bounded cleanup
  grace and potentially blocking output collection. No whole-package or
  hard-watchdog bound is claimed.

## Checks and limits

- `git diff --check`: passed.
- `rustfmt --edition 2021 --check tests/fixtures/sys_process_shared_child_contract.rs`:
  parsed the source but reported formatting differences, including existing
  untouched sections. No whole-file formatting was applied. Changed sections
  were inspected directly.
- No Cargo, compiler, test, native, or process-fixture execution was performed.
  This is source-only correction, not native acceptance; compiler/MSRV
  compatibility remains unverified.
- The first source correction was rejected. Preserve that history as **1 failed
  source correction**; native accounting remains **84 consumed / 85 allocated
  but unlaunched**, with hard budgets unchanged.
- External process custody, forced controller-death recovery, scoped-runner
  whole-process-group interruption custody, sync blocking-wait entry, and
  compiler/MSRV behavior remain open.

## Next review

Request the affected source review against the resulting fixture and activation
note. Keep native execution closed until the separately required process
custody prerequisite is satisfied; no native launch was authorized in this
source task.
