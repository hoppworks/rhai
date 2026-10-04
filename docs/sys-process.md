# Child process access

The optional `sys` package currently registers process execution on Unix. The
Windows production adapter and its native acceptance checks remain in progress.
This page describes the implemented Unix API; it does not certify the final
platform, feature or minimum-Rust-version matrix.

## Host configuration

`SysConfig::programs` selects the permitted programs. The default denies every
program. `ProgramPolicy::AllowList` compares the script's program string exactly;
a bare name is subsequently resolved through `PATH`. Arguments are passed
directly to the selected program. A shell is used only if the host permits one
and the script explicitly launches it.

An allow-list entry grants the selected program the host process's OS authority.
Filesystem roots restrict the package's file operations, not the launched
program's subsequent access. Managed groups do not provide a sandbox. Prefer
host-configured absolute executable paths when `PATH` resolution is undesirable;
the allow-list does not pin an executable's file identity or contents.

`SysConfig::process_scope` selects `DirectChild` (the default) or `Managed`.
Scripts cannot change this selection. `DirectChild` supervises the launched
child. On Unix, `Managed` creates and supervises a process group: cancellation
and normal completion include closure of that group. A process that deliberately
leaves the group is outside this scope. Failure to establish managed supervision
is an error; it does not select direct-child supervision instead.

`default_timeout` supplies the deadline for `run` and `run_raw` when the script
omits one. The default is no deadline. `max_output` caps each captured output
stream independently, at 8 MiB by default. Script options can lower the output
cap but cannot raise it above the host cap. Checked builds may apply a lower
Engine string or array limit; `unchecked` retains the host cap.

## Script operations

| Operation | Result |
| --- | --- |
| `run(program, args, options)` | Waits for completion and returns a result map with lossy UTF-8 output. |
| `run_raw(program, args, options)` | Waits for completion and returns a result map with byte blobs. |
| `spawn(program, args, options)` | Returns a shared `Child` handle while I/O and process supervision continue. |
| `child.try_wait()` | Returns `()` while pending, or the completed result map; execution failures raise an error. |
| `child.wait()` | Waits for the completed result map or an execution error. |
| `child.wait(seconds)` | Returns `()` if the wait expires while pending; this does not cancel the process. |
| `child.kill()` | Requests cancellation. Use `wait` to observe its outcome. |
| `child.id` | The original child PID; this value alone is not proof that the process remains alive. |

Arguments and options may each be omitted. Argument arrays contain strings.
With `no_index`, array-argument overloads and `run_raw` are unavailable, while
the string-based operations remain registered. `wait(seconds)` takes a floating
point duration in ordinary builds and an integer duration with `no_float`.

Result maps contain `success`, `code`, `signal`, `timed_out`, `stdout`, `stderr`,
`stdout_complete` and `stderr_complete`. An unavailable code or signal is `()`.
A nonzero exit code is a completed result with `success == false`. The
completeness fields describe reaching EOF, rather than merely capturing some
output. Spawned-child result maps contain text output.

## Options

| Option | Meaning |
| --- | --- |
| `cwd` | A directory string checked against the host filesystem policy. |
| `env` | A map of string names to string values added to the child environment. |
| `env_clear` | A Boolean selecting an empty starting environment; defaults to `false`. |
| `env_remove` | An array of string names removed before additions; unavailable with `no_index`. |
| `stdin` | A string or blob written to the child's input; omitted or `()` selects null input. Blobs require indexing support. |
| `timeout` | A finite, non-negative duration in seconds for `run`/`run_raw`; `()` selects no deadline. `spawn` rejects this option. |
| `max_output` | A non-negative integer cap per stream, clamped to the host and applicable Engine limits. |

Unknown options and invalid types are rejected. Child environment options affect
only the launched process, not the embedding host's environment. Spawned handles
have no execution deadline inherited from `default_timeout`; a timed `wait`
bounds that caller's wait only.
OS process creation happens synchronously before `spawn` returns the handle and
has no bounded duration.

The `run` deadline starts immediately before OS process creation and includes
input transfer, execution and output collection. Process creation and OS cleanup
can themselves stall, so the duration is not a hard wall-clock guarantee.
Successful timeout cleanup returns a result with `timed_out == true`; incomplete
cleanup raises an error with the available process report instead.

A zero output cap permits empty output and fails on the first byte. Exceeding
either stream's cap requests cancellation and raises `SysError::Process` with
`ProcessCause::OutputLimit`, retaining at most the allowed prefix per stream in
the report. Scripts observe `kind == "OutputLimit"` and can inspect `error.process`;
Rust callers match the `Process` variant to access its cause and report. If readable output
reveals overflow in the same supervision step as deadline expiry, overflow takes
precedence. No ordering between independent stdout and stderr events is promised.

## Shared lifetime and failures

Cloning a `Child` shares one process and its captured result. The host selects
this lifetime policy with `SysConfig::kill_on_drop`; scripts cannot change it.
The default, `SysConfig::kill_on_drop(true)`, requests cancellation when the final
client handle is dropped. With `SysConfig::kill_on_drop(false)`, dropping that
handle lets execution continue under the cleanup service. Handle and package
destruction do not synchronously wait for every retained process to be reaped.

Execution and cleanup failures can carry an immutable `ProcessReport` in
`SysError.process`. Inspect its `stdout`, `stderr`, completeness fields,
`exit_code`, `exit_signal`, `timed_out` and `cleanup_diagnostic(index)`.
With indexing support, raw byte getters and the `cleanup_diagnostics` array
are also available. A diagnostic records its `operation`, `io_kind` and
`message`. A report snapshot does not change as background cleanup progresses.

Managed completion can fail even after the direct child has been reaped. For
example, stopped group members may remain as zombies under a foreign parent.
The API reports incomplete cleanup instead of certifying group closure; direct
reaping, captured output and cleanup diagnostics remain separate facts. Errors
without a process report expose `()` through `SysError.process`.

## Runnable process example

On Unix, run the self-contained Engine example with
`cargo run --example sys_process --features sys`. It allow-lists only its own
absolute executable path, treats a child's exit code 7 as a completed `run`
result, and starts a second copy that waits for a parent-created release file.
The parent observes a pending timed wait, releases the child, then reads the
completed result through two cloned handles and compares the cached results.
The spawned child writes its readiness record to a sibling temporary file and
atomically renames it before the parent reads the record and releases the
child. Both child-written records are read independently by the host before
the example's temporary directory is removed. The example uses no shell or
external program and has finite fixture and cleanup waits.

The process API is currently registered on Unix. The example needs the `sys`
feature and ordinary object maps; its timed-wait call also requires floating
point support, so `no_float` builds are not covered. The non-Unix binary prints
an explicit unsupported-platform message. This example demonstrates the
documented public behavior on the platform where process access is implemented;
it does not certify Windows, every feature combination, or the full process
lifecycle contract.
