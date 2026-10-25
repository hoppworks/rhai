# Combined independent review — PASS

Standards: PASS. Spec/acceptance: PASS for only the named native Darwin X35
DirectChild/Managed pipe-closed-descendant subset across base/sync/unchecked/
sync+unchecked profiles, arm64/macOS27.0.1, Rust/Cargo1.77.2. No actionable findings.

The complete package manifest verifies. Worktree source is exactly the reviewed
216-line Darwin-only test addition against9527d655. Owned patch and corrected
source hashes match inputs/receipts. Cargo.toml, Unix runtime and lock are unchanged.
The kernel-buffer read, native libc/SDK ABI, ownership exclusion, scoped observer
join and bounded exact-PID cleanup were reviewed before execution. The missing
evidence-directory preflight finding was fixed before the sole build launch.

The known-broken control exits101 at the intended managed-closure assertion after
the API boundary records leader absent, worker/leaf live, successful public run
and host/sentinel alive. Cleanup then records every exact fixture PID absent
before that assertion fails. The exact source is restored before GREEN.

The full base target passes52 tests, zero failures, one pre-existing ignored
measurement and includes both new tests. Six additional exact selectors pass
1/1 across sync/unchecked/both. In each profile DirectChild retains the same live
kernel identities at API return, whereas Managed has closed worker/leaf there.
The contract uses pre-cleanup snapshots and therefore cannot be satisfied by
fixture cleanup. Both modes preserve the host/sentinel boundary and retire all
exact fixtures afterward.

The retained independent observer confirms all36 recorded PIDs and four Managed
groups absent, accepts ESRCH only and retires the exact empty owned scope.
Scoped runner status is0. Reviewer made no edits and ran no builds/tests.

Current central rules remain d6024420 plus applicable local uncommitted core/skill
updates; project AGENTS37f95ff6… is unchanged. X35 overall, Windows, other
platforms/MSRVs/features, Ticket03 and full A–F acceptance remain open.
