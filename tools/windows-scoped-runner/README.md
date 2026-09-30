# Candidate Windows guest scoped runner

`ScopedRunner.cs` is a static candidate for the authorized `rhai-win11-quality`
guest. It is **not accepted or ready to run**: the guest console was black during
this task, so it was not compiled or exercised. No package build was run.

The intended call shape is:

```text
ScopedRunner.exe --source <read-only-source-directory> --exe <relative-executable> -- <arguments...>
```

It copies the source tree (rejecting reparse points encountered below its root)
to a generated `C:\RhaiQuality\runs\scoped-<guid>` runtime, sets `CARGO_HOME`,
`CARGO_TARGET_DIR`, `TEMP`, and `TMP` below that runtime, and uses the runtime as
the child working directory. It creates an unnamed job with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, creates the exact payload suspended,
assigns it before resume, propagates the payload exit code, terminates job members
on its fixed 30-minute deadline, and terminates the exact suspended process if
job assignment fails. It refuses assignment fallback. A successful payload exit
with residual job members returns 125 after terminating those members.

Compile only inside an exact private runtime on the guest, for example with the
guest's already installed Framework C# compiler, and export compiler output and
the runner binary only as needed for the proof. That bootstrap path has not been
validated. No compiler, runtime, or Windows build command was invoked in this
task.

## Blocking supervision requirement

The job's last-handle close is the kernel process-tree fallback if this runner
dies; SSH process-group handling is not relied on. However, this implementation
does not provide the separately owned guest monitor required to verify job
emptiness after runner/connection death, export diagnostics, and remove only the
recorded runtime. The runner deliberately leaves runtime data behind rather than
claiming safe cleanup without independent read-back. It also has no native proof
of job membership, source/runtime ACLs, descendant behavior, deadline behavior,
or failure cleanup. The mechanism for an independently supervised guest lease
and exact runtime cleanup remains a design decision. Do not use this candidate
to launch package builds until those requirements are implemented and proven.

## Acceptance record

Evidence and the current native gate status are recorded in
`.scratch/windows-scoped-runner/acceptance.md` in the owning worktree. Static
source review is not native acceptance.
