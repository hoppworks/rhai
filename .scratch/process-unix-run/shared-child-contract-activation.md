# Prepared shared `Child` contract fixture

`tests/fixtures/sys_process_shared_child_contract.rs` contains the public `spawn`/shared `Child` contract cases. The sys-only global-call parser allowance is in `src/types/token.rs`, with compatibility coverage in `tests/tokens.rs`; invocation45 passed sys, sys+no_custom_syntax, and non-sys parser tests. Invocation48 passed the injected six-test module on macOS with development Rust1.93, including blocked-stdin/wait snapshots, nonfinal clone drop, both final-drop policies, and sync waiter cancellation. Evidence is `.scratch/process-unix-run/evidence/shared-child-first-green.0la0r5`; fixture SHA-256 is `d7ea90f54b0d4398daa4afc0ba25260c7a06c8f9ff1a1221ec3e0a4803a37d6a`. This is not MSRV/release acceptance. The sync case does not prove the waiter entered the blocking part of `wait` before cancellation.

Invocation45 selected only the spawn case and reached the public Engine call, failing with `Function not found: spawn`; the harness confirmed no OS fixture spawned. Invocation47 passed the earlier blocked-stdin/wait fixture after source-only validator replay corrected its output matcher. Invocation48 passed the expanded fixture and wrong-control after the temporary clone corrections. All four fixture children and controllers were independently reaped. Broader direct-child and descendant lifecycle coverage remains open.

The historical invocation48 wrong-control removed public `spawn`; it is not
evidence for the planned cached-exit-code assertion control.

To activate in the test source, add `#[path = "fixtures/sys_process_shared_child_contract.rs"] mod shared_child_contract;` to `tests/sys_process.rs` under the same `all(feature = "sys", unix, not(feature = "no_index"))` gates. The focused suite uses `--features testing-environ,sys,sync` and the scoped runner. Preserve exact child records, process ownership and cleanup receipts.

Assertion mapping:

- `spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable` uses an 8 MiB stdin payload. The real child publishes readiness before reading, and input and exit releases are separate. The test requires prompt `spawn`, verifies input remains pending, checks finite `wait(0.02)` returns unit while stdin remains blocked, releases input, then checks final `wait` and `try_wait` maps. It mutates a returned map and checks later snapshots are unchanged. The child independently records its PID, bytes consumed, validation result and exit; the controller verifies ESRCH. A bounded exact-Child controller watchdog remains in the runner's inherited process group. This guard does not claim escaped-descendant custody.
- `nonfinal_child_clone_drop_keeps_the_real_child_available` drops one `Dynamic` alias, then requires a fresh nonce challenge/reply through the remaining alias.
- After the direct child has exited and its PID is independently reaped, the blocked-input case calls public `child.kill()` twice, then obtains fresh `wait()` and `try_wait()` maps. Both must retain exit code 17, nonzero success, exact stdout/stderr, and complete-capture flags; the test rechecks `ESRCH`. The focused wrong-control changes the expected cached code only and must fail at that assertion after reap.
- `final_drop_honors_both_kill_on_drop_policies` checks bounded direct-child absence when the final client is dropped with host `kill_on_drop=true`; with `false`, it proves the child answers a fresh challenge after final-client drop, then releases it and checks eventual reaping.
- `sync_waiter_can_be_cancelled_through_another_shared_child_handle` (`sync` only) races a public timed waiter with cancellation through a cloned handle and requires bounded waiter completion, final wait and direct-child ESRCH. Its start-channel receipt shows the waiter is about to call `wait`, not that it has entered the blocking part before cancellation.

Readiness and completion records use temp-write plus rename. The fixture directory is inside `AGENT_RUNTIME_DIR`; Rust Drop removes the exact directory, and the scoped runner removes the private runtime if its hard watchdog interrupts the test. All fixture waits are bounded. Invocation48 ran the wrong-control and all six injected module tests serially, checking controller/fixture ESRCH and owned roots. Full lifecycle, escaped-descendant, managed, Windows and MSRV/release acceptance remain open.


## Registered contract — current acceptance pending

The fixture is now registered in `tests/sys_process.rs` under the target's
`sys + unix` gate and the module's `!no_index` gate. The previous source-discovery
check failed because `mod shared_child_contract` was absent; after registration,
the gate and both exact self-reexec target names pass the static check.
This is discovery evidence only; no compiler or native process was launched.

With `no_float`, the blocked-input case calls integer `wait(0)` while the child
is independently held before reading stdin, and the sync waiter uses integer
`wait(10)`. Normal floating-point builds retain `wait(0.02)` and `wait(10.0)`.
The input release, stable cached snapshots, mutation isolation, repeated kill,
clone/drop and independent OS records are unchanged. The sync readiness
limitation documented above still applies; it is not a blocking-wait entry proof.

Next native acceptance uses private Rust 1.77.2, serial execution and scoped
output/cache isolation: the focused blocked-input test with its wrong cached
exit-code control, then the registered module under `testing-environ,sys,sync`
and `testing-environ,sys,sync,no_float`. Preserve original logs, public Engine
readback and every exact child/controller cleanup identity. Allocate this run
only when the machine's heavy slot is free. The new feature-selected scripts
and module registration require current native verification; historical injected
module results do not close that acceptance or the release matrix.

## Independent activation review and affected corrections

`shared-child-activation-review.md` accepts commit dd2a44fc source-only and
records three inherited acceptance prerequisites. The direct-drop challenge
constant now has the same feature gate as its process-fixture use, removing
the identified `no_float` unresolved-name mismatch. Successful controllers
now export their captured stdout/stderr to the enclosing test log before
fixture records are removed. Source recheck confirms both corrections remain
in place; affected native/compiler verification is pending.

Exceptional controller cleanup now catches scenario unwinds inside the
controller, releases only its owned synchronization files, and waits for exact
`ESRCH` while the package cleanup worker retains the OS `Child`. The normal
controller path records closure only after its exact-child reap check. The outer
guard releases before its bounded wait and termination of the exact controller;
it never promotes post-termination PID absence to production-reap proof. Fixture
records are removed only after a controller-side production-reap check and
`ESRCH`; otherwise the directory and records are retained with cleanup logged as
unverified. This does not prove cleanup if the controller is forcibly terminated
before its worker reaps, or if the scoped runner's hard watchdog interrupts the
process group. Do not launch the module until the runner's broader process-group
custody prerequisite is satisfied.

A new panic-cleanup regression exercises this recovery through the public Engine
and self-reexecuted OS fixture; it requires an exited child record, exact
`ESRCH`, and the controller-side production-reap receipt. It has not been run.

The source recheck confirms successful controller stdout/stderr remains
emitted, and `DIRECT_DROP_CHALLENGE_ENV` remains gated by `unix && !no_index`,
matching its process-fixture use. The sync blocking-wait-entry limitation also
remains open.
