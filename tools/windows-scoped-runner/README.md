# Candidate Windows guest scoped runner

`ScopedRunner.cs` is a source candidate for the authorized `rhai-win11-quality`
guest. It is **not accepted or ready to run**. The source has not been compiled
or exercised, and no package build was run.

The intended call shape is:

```text
ScopedRunner.exe --source <read-only-source-directory> --exe <relative-executable> -- <arguments...>
```

The candidate copies sources into a generated runtime below
`C:\RhaiQuality\runs`, sets Cargo and temporary paths below that runtime, and
uses it as the payload working directory. It creates an unnamed job with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. The payload is created suspended with that
job in `PROC_THREAD_ATTRIBUTE_JOB_LIST`, membership is checked, and resume is
allowed only when `ResumeThread` reports the expected previous suspend count of
one. There is no later assign call. Setup failure terminates the exact job,
waits for the exact process with a finite timeout, and checks that the job is
empty; closing the job handle retains kill-on-close as a fallback. The candidate
also has a fixed 30-minute payload deadline and terminates residual job members
after payload exit.

`fixtures/RunProcessCreationFixtures.ps1` and `fixtures/PayloadFixture.cs` are
Windows-side behavioral fixture sources for job-list creation failure and a
failure after membership verification but before resume. The harness accepts
prebuilt runner and payload binaries; it does not compile or bootstrap them.
It checks expected failure diagnostics and payload non-execution. The test-only
pre-resume cleanup receipt is produced by the candidate itself, so it is not
independent process/job read-back. The harness restores the test-root environment
variable and preserves its exact fixture directory and logs on failure.

Do not build or run these fixtures on the guest until the independent launch,
bounded bootstrap, guest-access and review gates are authorized and satisfied.
No compiler, fixture, runtime, or Windows build command was invoked for this
source change. External observation of the exact process handle and job
membership, the wrong-expectation/restored run, and all native behavior remain
unverified.

## Remaining custody work

This substep does not implement the independent monitor/client split, host lease,
challenge protocol, journal, independent evidence export, or handle-based source
staging and runtime removal. The candidate deliberately retains runtime data
rather than claiming safe cleanup without independent read-back. It has no
native proof of job membership, ACLs, descendant behavior, deadline handling,
or failure cleanup. Do not use it to launch package builds until the full custody
design is implemented and all native gates pass.

Layout references: [JOBOBJECT_BASIC_ACCOUNTING_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information),
[JOBOBJECT_BASIC_LIMIT_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information),
[IO_COUNTERS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-io_counters),
and [JOBOBJECT_EXTENDED_LIMIT_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information).
