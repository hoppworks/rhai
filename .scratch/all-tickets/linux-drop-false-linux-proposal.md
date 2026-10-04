# Linux `kill_on_drop(false)` final-drop proof proposal

## Scope and immutable source

Run only these two existing public-Engine tests from accepted baseline
`523608648dcae99bc0f6b46eaf2bb91fa4ecc752`:

- `direct_spawn_kill_on_drop_false_preserves_child_and_capture`
- `managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit`

Use the exact baseline test source (SHA-256
`5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb`),
not the current writer test file (SHA-256
`c247551b421e6ca9d973fcdbad9a0fd21a2841c59db89c3f3824bbd6d26b221f`),
which includes a separate later stdin-closure change. The accepted baseline
tests require `testing-environ,sys`, Unix, and neither `no_index` nor
`no_float`. They exercise `spawn` through a real Engine and OS child
fixtures; no product or fixture edit is indicated.

The source-523 note
[`linux-drop-false-next.md`](linux-drop-false-next.md) records that the
named test bodies, their helpers, and relevant production dependencies are
byte-identical to accepted macOS source `e5b55460ff8f94dba5d35564ced640e6ac8ea3ee`.
The retained macOS evidence is useful for Darwin acceptance. It does not close
Linux native execution. It independently reads back the direct PID and
sentinel, but does not independently read back managed leader/worker/leaf PIDs
or their group. The Linux IO89/options90 cases are different tests, and
final-drop102 tests a different managed clone-drop behavior.

## Existing behavior asserted

The direct test already proves: after dropping the only `Dynamic` and Engine,
the exact child remains live and acknowledges a challenge before fixture
release; it has not completed; after release it writes 524288 bytes to each
captured stream, publishes its completion record, exits, and is reaped.

The managed test already proves: after dropping the only public child handle
and Engine, leader, worker, and leaf remain live in their exact managed group
and all answer a challenge while a separately grouped sentinel remains live;
after releasing the leader, all three fixture members disappear while the
sentinel remains live; the test then explicitly kills and reaps that sentinel.
These existing assertions are sufficient for the API contract. Add no Rust
assertions unless a later concrete review finding identifies a gap.

## Observer handshake required for deterministic readback

The current fixture has a race for an external observer. In the direct test,
the child remains blocked until the parent immediately writes `release` after
its challenge assertion. In the managed test, the parent writes `release-leader`
immediately after its challenge assertion. The 20-second and 15-second child
watchdogs bound fixture lifetime, but they do not hold the post-drop observation
phase open: an external poller could miss it. Therefore the existing tests alone
cannot guarantee the proposed independent live snapshot.

Add one Linux-only, opt-in handshake to these two test bodies (and no production
code or fixture-script behavior):

1. The proof launcher supplies a fresh, empty `RHAI_DROP_FALSE_OBSERVER_DIR`
   for each Cargo invocation. After the test has checked its fixture challenge
   and its own `pid_is_running`/member-liveness predicates, it atomically writes
   one request file in that directory. The direct request binds test PID, child
   PID, fixture root, and the already observed challenge acknowledgement. The
   managed request binds test PID, sentinel PID/PGID, leader/worker/leaf PIDs,
   their recorded start ticks and PGIDs, fixture root, and the successful
   challenge acknowledgements. Use the existing atomic-record helper.
2. The test waits at that point for the matching observer acknowledgement, with
   an 8-second deadline. It must write no child or leader release marker before
   receiving the acknowledgement. If the environment variable is absent, the
   normal cross-platform test behavior remains unchanged; the Linux proof
   launcher always sets it and requires the matching request/ack receipts. The
   request name includes the test name and test PID; the launcher rejects a
   non-empty directory before starting Cargo, so stale acknowledgements cannot
   satisfy the wait.
   Insert the direct call after its existing final-drop challenge/liveness and
   incomplete-record assertions, immediately before writing `release`. Insert
   the managed call after its existing member challenge assertions and
   sentinel-live assertion, immediately before writing `release-leader`.
3. A small observer thread in the bounded proof driver watches only the known
   request paths while Cargo runs. It parses each complete request, independently
   reads `/proc/<pid>/stat` and start ticks for all named children, verifies
   exact PID/start/PGID tuples and that they are non-zombies, checks fixture-root
   identity under the run's private runtime, then atomically writes an ack bound
   to the request hash. Any missing, malformed, reused, inaccessible, or
   inconsistent identity is a failed observation and does not release the test.
   The test-side wait accepts only an ack whose request digest matches the
   request it wrote. Keep the observer on the existing proof driver's already
   owned process; do not add a second Cargo runner or general-purpose monitor.
4. After Cargo exits, the same observer path performs the fresh terminal PID,
   group, fixture-root, runtime, and scope readbacks already required below.
   Preserve the request, observer receipt, Cargo output/status, and cleanup
   receipt before scoped teardown. The test's own cleanup guards/watchdogs still
   apply if the observer fails or the assertion panics.

Run each intentional wrong-expectation control with a separate empty handshake
directory. It should fail at the named survival assertion before writing a
request; the existing RAII cleanup releases and reaps its fixture. A successful
green run must contain exactly one request and one matching independently
written acknowledgement before the corresponding release marker.

For an implementation, add one Linux-only test helper that returns immediately
when the observer directory variable is absent. When present, it writes a
complete request via the existing atomic-record helper, waits at most 8 seconds
for `<case>-<test-pid>.ack`, and checks the ack names the same case and test PID.
The direct fixture's existing `Drop` implementation writes its release marker
and waits up to 6 seconds if this barrier panics; the managed fixture's `Drop`
implementation writes both release markers and waits up to 3 seconds, while
the existing sentinel guard kills and waits its exact child. Preserve these
guards unchanged. This leaves a bounded cleanup path if the observer is absent,
malformed, or times out.

The frozen patch now emits complete RED custody rows from the actual process
identity tuples: direct host/child PID, start ticks, parent and PGID; managed
host, sentinel, leader, worker and leaf identities, with each member's parent
and PGID. The live request carries leader/worker/leaf PGIDs and binds the
managed group to the leader PID. The bounded driver stores Cargo command
identity separately and publishes it to the observer only for green handshake
runs. Observer, terminal and RED-control receipts are written incrementally;
read failures retain the successful observations with `complete: false` and an
error, without producing a success receipt.

The stage script discovers the repository with `git -C "$script_dir"
rev-parse --show-toplevel`, then uses the exact helper, archive helper and lock
pins below that checkout. The helper pin is c5422e; the proof, observer and
patch pins are SHA-256 `61d828673fa032db6160263b7ba3585e826099fa6baf38f05aa7a0115c972d53`,
`07d2ab6e1f2015a18b1ee83f59585b16b97852a00cc45dfb5778f836d78ad0d2`, and
`78d7f123c570e5efb94563b77c737fd4ed97ac9a594090c4a7dba664b461e9dd`.
The custody program pins the same staged inputs, tokenizes command lines for
exact script-path provenance, binds complete managed/sentinel group census to
the saved observer/RED request, and checks the physical stage path after
retirement. These are local recipe corrections; native Linux execution remains
unverified. The frozen proof driver now applies the test-only patch through strict `git apply --check --whitespace=error` followed by `git apply`; the local equivalence probe uses an isolated PATH containing Git only and verifies the exact 523 output digest, with no external `patch` executable required. It records the original Cargo identity
first, publishes its complete PID/start-time identity, and only then starts
the observer thread for a green handshake. Local coupled probes passed for
direct and managed cases with requests both before and after that callback;
they verified the exact ACK before command return and terminal readback, and
rejected missing Cargo identity, wrong Cargo start time, and wrong host-parent
identity. These probes are synthetic. The root-owned preflight pin refresh and
Linux native execution remain outstanding.

The exact test-only source delta is preserved in
[`linux-drop-false-observer-handshake.patch`](linux-drop-false-observer-handshake.patch).
It was generated against baseline 523's `tests/sys_process.rs` hash
`5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb`; `patch
--dry-run -p1` succeeded against a fresh copy of that exact file. The patch
adds no production changes. It is not compiled or executed here. Recipe-level
handshake coupling is locally validated at the frozen proof revision. Continue
only after the separately owned preflight is pinned to that revision; this
does not establish Linux native acceptance.

## Bounded Linux sequence

Reuse the accepted Linux process proof route, its exact stage/scope custody,
private Rust 1.77.2 setup, lock pin, resource limits, original export, and
fresh cleanup checks. Pin source to 523 and use the compatible accepted lock
already verified against that source's manifests; keep `--locked`. The exact
test commands are:

```sh
RHAI_DROP_FALSE_OBSERVER_DIR="$observer_dir" cargo test --locked --features testing-environ,sys --test sys_process \
  direct_spawn_kill_on_drop_false_preserves_child_and_capture -- \
  --exact --nocapture --test-threads=1

RHAI_DROP_FALSE_OBSERVER_DIR="$observer_dir" cargo test --locked --features testing-environ,sys --test sys_process \
  managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit -- \
  --exact --nocapture --test-threads=1
```

Use a different empty `$observer_dir` for every control and green command; keep
it in that invocation's exported evidence until the handshake and terminal
receipts have been checked.

Run a meaningful wrong-expectation control for each named case against a
private copy of the exact 523 source before its restored green run. In the
direct case, invert only the expected post-final-drop survival predicate
(`alive_after_drop && ack_matches`); in the managed case, invert only the
expected post-final-drop member-survival predicate (`members_live`). Require
each control to exit 101 at its named assertion with the deliberate
expectation mismatch, then require fixture guards to release/stop/reap their
owned child/group and sentinel. Restore the two test source files byte-for-byte
to their pinned original hashes before compiling and running the green cases.
Never alter production behavior for these controls. The existing macOS
wrong-implementation controls are retained evidence for their platform; the
private wrong-expectation rows here make sensitivity explicit on Linux.

Keep the red rows, byte restoration, and both green rows within one bounded
scoped run using the existing runner. Preserve full original stdout/stderr,
exit status, exact test names, diagnostics, source/lock/manifest hashes, and
each cleanup receipt before runner teardown. Do not treat an expected red
control as a failed product correction.

## Independent live and terminal readback

With the handshake above, the proof helper can watch a durable request while
the test is blocked and independently sample `/proc/<pid>/stat`. Validate:

- direct child PID is distinct from the test host and has a positive observed
  start time; its fixture root is the exact test-owned runtime child;
- managed sentinel, leader, worker, and leaf PIDs are distinct; sentinel PGID
  equals sentinel PID, managed leader PGID equals the owned group, and all
  three managed members have that group;
- the observer request follows the test's successful after-final-drop
  challenge, and the test remains blocked until its identity-bound observer
  acknowledgement arrives;
- after each test/control finishes, fresh `/proc` reads show every original
  child identity absent (or the same PID reused with a different start time),
  and `ps -e -o pid=,pgid=` shows no process remaining in the managed or
  sentinel group; inaccessible or malformed reads are unknown and fail closed;
- exact fixture roots, the private runtime and central scope are absent only
  after original logs/readbacks are preserved.

The managed test's own `ESRCH` checks and sentinel `wait` remain required;
the separate observer adds independent Linux host readback rather than
replacing those assertions. This package would close only these two Linux
final-drop cases at the exact integrated revision. Windows remains separate;
the previously accepted macOS cases remain valid on macOS.


## Executable recipe alignment (2026-10-04)

The archived initial proposal above described a digest acknowledgement and start-tick fields before the first patch implemented them. The current test-only patch and driver supersede that detail: the test request carries test PID/start and each relevant child PID/start/PGID; the observer independently validates those fields against live `/proc` identities and sends an acknowledgement containing the complete request text followed by `observer_ack=true`. The test compares the complete expected acknowledgement byte-for-byte. This is exact content binding in the private, fresh per-invocation directory, not a cryptographic digest. The driver also records that the observer's test-host parent PID is the Cargo command PID.
