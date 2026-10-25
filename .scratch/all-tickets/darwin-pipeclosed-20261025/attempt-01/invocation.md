# Native pipe-closed descendant contract

Public boundary: real Rhai Engine `run` with host-selected DirectChild/Managed
scope. Existing re-exec leader starts worker/leaf with stdout/stderr redirected
to null and waits for explicit identity acknowledgment. The observer reads native
kernel PID/PPID/group/microsecond start identities twice before allowing leader
exit. At API return DirectChild must retain the same live descendants, while
Managed must have closed them. Captures must be complete and the successful leader
reaped; host and unrelated sentinel remain live. Fixture custody finishes before
contract assertions and uses bounded exact-PID cleanup, never host-group signals.

First executable control changes only the managed test's actual scope to
DirectChild while retaining its closed-descendant expectation. It must reach the
named lifecycle RED after real public run and exact fixture cleanup. Restore the
original source hash, then run the stable complete base sys_process target (both
new tests included), followed by the two new tests in sync, unchecked and both.
No separate duplicate base GREEN is planned. No product/dependency/shared-fixture
change; patch is tests/sys_process.rs only. Pinned libc0.2.189 and local SDK headers
already provide the native read-only libproc interface; no install is needed.

One owned scoped invocation, two Cargo jobs, outer hard timeout600s. Each public
run has an8s timeout, observer readiness4s, existing leader-ack5s, fixture release
grace2s plus exact cleanup wait2s. Use one private source/target/Cargo-home runtime;
export each result before deletion. Additional peak estimate8GiB is provisional,
not a user cap/reservation; preflight measured252000488KiB available and85% memory
free, no Cargo/rustc process observed. Exact measured launch capacity is exported.
Do not interrupt foreign work or change any shared service/agent configuration.

The new unsafe kernel-buffer read and fixture signal ownership receive source
review before execution; the same combined review adopts final live receipts.
Expected RED is a successful known-broken control, not a failed correction. An
unexpected compile/setup/runtime outcome stops this invocation for diagnosis;
there is no automatic whole-run retry. Preserve earlier cause/budget history.
Independent post-run observer validates36 recorded PIDs and four managed groups,
then retires only the owned empty scope. Token/cost totals are unavailable.
