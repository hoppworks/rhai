# Invocation boundary

One owned native Darwin arm64/macOS27.0.1 scope, Rust/Cargo1.77.2, two Cargo jobs,
outer hard timeout 600 seconds. Execute only eleven uncovered GREEN rows:
managed kill in checked/unchecked sync (2), final-clone drop in checked sync,
base unchecked and sync+unchecked (3), and two escaped-capture selectors in those
three profiles (6). All source is unchanged from integrated c0fc47e4.

Reuse applicable accepted Darwin X25 base/base-unchecked, X27 managed final-drop
base (also covers its X37 host/sentinel requirement), and X38 base evidence and
native assertion controls. Their sources/oracles, relevant OS/compiler and lock
are bound in `../source-binding.json`. No fresh RED or base rerun is claimed.
The historical X25 unchecked proof's pending header was superseded by the recorded
combined PASS in coordinator-history and the current canonical plan.

Measured preflight: 252091696 KiB available on the actual output filesystem, 84%
memory free on 32GiB; no Cargo/rustc process observed. Estimated added peak 8GiB
is a planning estimate, not a user cap/reservation. Existing tests use public
Engine spawn/kill/wait and real OS processes with fixture-owned roots and sentinel
guards. Use the unchanged scoped supervisor, owned source copy, target and Cargo
home. Export each status/log before runtime deletion. A separate retained observer
checks all 38 recorded PIDs plus ten explicitly recorded process groups using
signal zero (ESRCH only), then retires only the exact empty owned scope.

No product/test worktree change, shared process/service or foreign resource is
modified. Preserve earlier causes, budgets and proof. Cost/tokens are unavailable.
Overall X25/X27/X34/X37/X38, Windows custody, Ticket03 and A–F remain open outside
these named selector/profile rows.
