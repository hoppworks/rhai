## Diagnosis

At the requested source revision, `Invoke-OwnedProcess` waits for the child, refreshes its `Process` object, then reads `ExitCode` in a single condition and again in the error message ([RunSourceFixtures.ps1](file:///Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/tools/windows-scoped-runner/fixtures/RunSourceFixtures.ps1)). The compile step calls that helper for `compile-production-runner` at line 446.

Given the supplied receipt text `compile-production-runner exited ` with no code, the source-level explanation is that the error branch ran while the interpolated `ExitCode` value rendered empty. That is consistent with a null or empty value; this source alone does **not** prove why the runtime exposed it, or that the compiler failed. The 171,008-byte executable and warning-only compiler logs are evidence of output, not proof that this invocation passed its exit check or that subsequent fixtures ran.

A focused fix candidate is to capture and validate the exit code once after `WaitForExit` and `Refresh`, explicitly error if it is null/unavailable, and include that captured value in diagnostics. That addresses the ambiguous receipt; it does not establish the native cause. No fixture was rerun.

## Evidence limits and next read-only checks

- The supplied PID query found no processes for 3192, 4324, or 5380. That supports only the observed absence at query time; it does not prove job closure or complete cleanup.
- The supplied guest-script pin is said to match before execution, but I did not independently inspect the guest or screenshot.
- Read-only follow-up: inspect the exact parent receipt and adjacent job-closure records, compiler stdout/stderr, executable metadata, and any captured PowerShell exception. These may narrow the cause; they still cannot recreate the lost live `Process.ExitCode`.

I read the global/project instructions and Worker role/template. The checkout is at `58deedb4f1c7be458a1fc07af213521c741df501`; requested revision `958a4538` is unavailable here. The specified historical source revision was readable. I made no file changes or process/build/native actions.