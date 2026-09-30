# Native Windows scoped execution gate

Status: implementation and native proof required before another Windows build.

## Proposed mechanism

Use a small native guest supervisor that owns an unnamed job object with
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. Keep its handle private and non-inheritable.
Create the payload suspended, assign its process handle to the job, and resume only
after assignment succeeds. On failure, terminate and wait for the suspended process;
never start unowned work. A stopped supervisor closes the last job handle so owned
members are terminated. Normal completion also closes remaining task members.

This follows Microsoft's documented
[job lifetime and membership](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[process creation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)
and [job assignment](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)
APIs; it remains a design proposal, not tested guest behavior.

## Resources

- Allocate an exact unique effort-owned runtime below C:\RhaiQuality\runs.
- Copy the source under that runtime. Scope CARGO_HOME, CARGO_TARGET_DIR, TEMP and
  TMP there; generated Cargo.lock/build source must stay in the source copy.
- An independent guest monitor retains runtime ownership after supervisor death,
  confirms no active owned job members, exports evidence, and removes only that
  recorded runtime. Stopping SSH alone cannot fulfill this role.
- Never touch baseline-source-v2, baseline-source, backups or unrelated processes.
- Export logs, exit status and explicit cleanup outcomes before deleting runtime.
- Keep native compilation and reused test binaries in one bounded invocation.

## Required proof

1. Payload and grandchild report actual job membership before acceptance work.
2. Success, failure and guest deadline stop all owned members and remove runtime.
3. Deliberately stop supervisor while grandchild is alive; independently confirm
   termination plus runtime cleanup, preserving a separately owned sentinel.
4. Exercise assignment failure and nested job context; no silent fallback.
5. Abort controlling connection while work is running; guest lease/watchdog still
   bounds work and exports diagnostic status.
6. Negative assertion control must fail; restored assertion must pass.

## Unverified

All implementation, interruption/lease behavior, native runtime cleanup and
integration with this project's Windows test command remain unverified.
