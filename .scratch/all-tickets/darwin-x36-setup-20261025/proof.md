# Darwin X36 setup-failure acceptance

Status: combined independent review PASS for the sixteen named profile rows.

## Exact scope

Darwin arm64/macOS27.0.1 (kernel27.0.0), Rust/Cargo1.77.2; the four existing
selectors below pass under `testing-environ,sys`, `testing-environ,sys,sync`,
`testing-environ,sys,unchecked`, and `testing-environ,sys,sync,unchecked`:

- `managed_scope_setup_failure_never_executes_unmanaged_child`
- `managed_scope_partial_setup_failure_cleans_created_group`
- `managed_scope_fchdir_failure_cleans_created_group`
- `managed_scope_kernel_setpgid_denial_cleans_created_group`

The source archive is integrated fork revision
`7638f2684ff2f06bb7587359eeb8c82e9c86a360`. Cargo.toml SHA-256:
`cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`;
canonical lock: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`;
Unix source: `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`.
The graph is retained at `../core-current-msrv-evidence-04/Cargo.lock`.
No product or test change was applied to the worktree.

## Public behavior and independent observations

Each GREEN registers the real SysPackage in a Rhai Engine and invokes public
`run` and `spawn` with a real OS child. Both operations report the expected setup
Io error without running the marker-writing program. The parent freshly reads
the child-written identity receipt and observes marker absence, retired launch
reservation, and exact child PID/group absence before the helper returns.

The first two seams inject EPERM before and after successful setpgid. The third
closes only the child's inherited cwd fd and reaches real fchdir EBADF. The fourth
calls real setsid and reaches kernel setpgid EPERM for the session leader. The
proof distinguishes the injected failures from kernel-generated errors.

All sixteen GREEN invocations returned 0 and each reports one passed test and
both public run/spawn cleanup records. A separate Python observer ran after the
scoped invocation: all 32 GREEN and four RED recorded PIDs/groups were absent,
accepting absence only for ESRCH. Its exact source and result are retained as
`attempt-01/postrun-readback.py` and `attempt-01/evidence/post-run-readback.txt`.

## Native assertion controls

In the isolated runtime source only, each named test's final marker-absence
expectation was inverted. Each control reached the intended assertion *after*
the public run error and helper cleanup, exited 101, and reports exactly one
failed test. The complete four-line mutation, descriptive record and mutated
source hash are exported. No production branch or helper logic was changed.

After the four native base-profile REDs, the original source was restored and
its complete SHA-256 verified before any GREEN. The same unchanged assertions
then pass in all four profiles. There is no fresh profile-specific RED claim for
sync/unchecked; native base controls transfer at identical selector/assertion,
OS, compiler and lock scope. The controls initially stop on public run; each
restored GREEN subsequently verifies both run and spawn. The earlier accepted
Darwin Rust1.93 base kernel-denial packet is retained without repetition.

## Command, build reuse and cleanup

`attempt-01/run.sh` archives the revision into the owned runtime, applies the
assertion controls, restores source and executes the exact Cargo selectors.
The result classifier checks exit status, assertion substring and libtest result
separately; it does not require the test name and FAILED on the same output line.
Twenty statuses and original logs are exported immediately as each case ends.
The shared scoped runner returned 0; its SHA-256 remains
`25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.

One cold Cargo preparation took 20.49s; source restoration reused dependencies
and took 1.61s. New sync, unchecked and sync+unchecked builds took 7.97s, 7.15s
and 7.38s; other preparations reused the existing target and took 0.03–0.04s.
Individual test executions took 0.00–0.02s. Summed Cargo preparations were
45.10s and libtest executions 0.18s; the filesystem-timestamp wall envelope was
48.907s before the independent observer/review (`usage.json` records the method).
All commands shared the same private
source/target/Cargo-home runtime under the 600s outer limit with two Cargo jobs.
Finite limits and resource estimates are recorded in `attempt-01/invocation.md`.

The runner removed its private runtime; the independent observer confirmed the
exact session scope empty and retired it with rmdir. No reusable build/cache is
retained. The worktree source remained unchanged. Other native process criteria,
Windows custody, other platform/MSRV/feature combinations, X36 overall, Ticket03
and packages B/C/D/F remain open.
