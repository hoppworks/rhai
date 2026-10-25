# Native Darwin pipe-closed descendant ownership

Status: final combined independent review PASS for the named native X35 subset.

## Behavior and source

The two new public-Engine integration tests exercise the same existing re-exec
leader/worker/leaf fixtures used by the Linux proof. Worker/leaf stdout and stderr
are redirected to null. The leader waits for an explicit native observer
acknowledgment before exiting successfully. DirectChild must return complete
captures while the same descendants remain live; Managed must close them before
API return. The direct leader is reaped in both cases, and the host/unrelated
sentinel remain live. These are native X35 rows, not a UI or mocked-process test.

Platform: Darwin arm64/macOS27.0.1 (kernel27.0.0), Rust/Cargo1.77.2. Source is base
`9527d655c715348da519e414f55a7fa3207550c2` plus the reviewed tests-only patch:
`57efff4d3fa2ba0819c76a3d466da63594ad8c3c4a1bed571dbe246a118559fd`.
Correct test-source SHA-256 is
`06dc0ed35c2a6edbbe16e54eda59bd3a278eab8d07cef619b99caa7589cd8f43`.
Cargo.toml, Unix runtime and canonical lock are unchanged (lock
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, retained in
`../core-current-msrv-evidence-04/Cargo.lock`). No dependency, production code or
shared fixture body changed. Added helpers/tests are Darwin-only.

## Independent identity and API-boundary observations

Pinned libc0.2.189 already binds proc_pidinfo/PROC_PIDTBSDINFO/proc_bsdinfo.
SDK declarations/layout and the libSystem symbol were independently source-reviewed
before execution; SDK hashes are exported. The new observer reads kernel PID,
PPID, process group, state and second/microsecond start identities for all three
members, validates the host→leader→worker→leaf relationships and selected scope,
then rereads them before acknowledging readiness. It rejects the host and sentinel
PIDs before recording fixture custody. It does not use second-resolution ps output
as the new identity oracle. Permission/malformed reads are errors, not absence.

All observations in `darwin_pipe_return` occur before fixture release or fallback
cleanup. The captured booleans are asserted only after the cleanup guard finishes,
so cleanup cannot manufacture success for the API-return contract. Managed rows
show worker/leaf absent at that boundary. DirectChild rows show the same live
kernel identities with no longer live leader, complete capture and successful
public run. The host identity and sentinel are independently preserved there.

## Meaningful RED, restored GREEN and regression

The first executable control changes only the managed test's configured scope to
DirectChild while retaining its fixed closed-descendant expectation. Public run
succeeds, the leader is absent and both descendants are still live at API return.
The guard then releases/reaps exact fixture members and sentinel before the named
managed-closure assertion fails. Cargo exits101 with exactly one failed test and
the intended assertion message. This is a successful known-broken contract control.

The complete source is restored byte-identically before GREEN. The stable complete
`sys_process` base target passes52 tests, zero failures, one pre-existing ignored
measurement. That single broad run includes both new base GREENs and existing
regressions without a duplicate targeted base run. The two new tests additionally
pass individually under sync, unchecked and sync+unchecked. Thus eight new native
GREEN rows are covered across `testing-environ,sys` and those three combinations.
The base RED sensitivity transfers at unchanged assertion/OS/compiler/lock scope;
no fresh per-profile RED is claimed. Existing accepted proofs remain scoped and
unchanged outside the new native behavior.

## Ownership, bounds and readback

The native fixture guard publishes release markers, waits2s, and on an exceptional
path rereads exact PID/group/microsecond start identity before per-PID SIGKILL,
then waits another2s. It never sends a group signal to DirectChild's inherited
host group. It retains honest diagnostics for identity errors/zombies rather
than treating them as stopped. Scoped observer threads are joined; root cleanup
and sentinel reap precede contract assertions, including the known-broken RED.

The separate retained post-run observer checks all36 recorded RED/GREEN member
and sentinel PIDs plus four Managed groups after the invocation, accepts absence
only for ESRCH, verifies the session scope empty, then retires it with rmdir.
All36 PID and four group checks pass. Its source and original results are retained.
The scoped runner exits0; no build/cache is retained.

One600s invocation with two Cargo jobs shared source/target/private Cargo home
across eight Cargo commands. Summed preparation52.36s; observed wall envelope
66.744s from preflight receipt to result (excludes later observer/review). The
finite limits, source restoration, commands, statuses, SDK/runner hashes and
usage methodology are exported in attempt01. The cheap source review identified
missing evidence-directory creation and it was fixed before any build launch;
there was no failed build/retry or product failure. Cost/token totals are unknown.

This packet accepts only the named native DirectChild/Managed X35 subset at these
four profiles. Other OS/MSRV/features, remaining managed
lifecycle/capture criteria, Windows custody, Ticket03 and A–F remain open.
