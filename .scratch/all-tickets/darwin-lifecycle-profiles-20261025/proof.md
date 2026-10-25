# Darwin managed lifecycle and capture profiles

Status: combined independent review PASS for the eleven named new profile rows.

## Scope

Native Darwin arm64/macOS27.0.1 (kernel27.0.0), Rust/Cargo1.77.2. This packet
adds only the missing selector/profile rows:

| Selector | Newly executed profiles after `testing-environ,sys` |
|---|---|
| `managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel` | `sync`; `sync,unchecked` |
| `managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not` | `sync`; `unchecked`; `sync,unchecked` |
| `managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes` | `sync`; `unchecked`; `sync,unchecked` |
| `managed_spawn_post_reap_cancel_bounds_escaped_capture` | `sync`; `unchecked`; `sync,unchecked` |

The first row covers the named X25 managed kill contract, the second its X27/X37
clone/host/sentinel contract. The latter two cover the named X38 capture paths.
These oracles contribute to X34 only where its exact kill/drop/capture requirement
matches; they do not establish other deadline/output-limit/fault paths.

## Source, controls and accepted-row reuse

The integrated archive is `c0fc47e403f685624c611d94783aa5dffc609c64`. Source hashes:
Cargo.toml `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`;
lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`;
Unix source `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`;
complete process test file `3c22dd7428b0a3299905d384e661d845bf7510ba488d58c23d1aa83700124172`.
The tracked canonical graph remains at `../core-current-msrv-evidence-04/Cargo.lock`.
No worktree product/test source was modified or mutated.

Reuse these existing native rows and assertion controls without rerunning them:

- X25 base: `../darwin-x25-rust177-20261009/proof.md`, attempt02 expected RED101
  and attempt03 GREEN0. The wrapper's parser-only status1 on RED remains history.
- X25 base unchecked: `../darwin-x25-unchecked-20261010/attempt-01/`, expected
  RED101/GREEN0 and retained log hashes. Its historical pending header was
  superseded by the combined PASS recorded in coordinator-history and the plan.
- Managed final-clone-drop base: `../darwin-x27-managed-final-drop-20261009/attempt-01/`,
  expected RED101/GREEN0 and retained log hashes. The same selector/oracle also
  proves this named X37 host/sentinel subset; no second native base run is needed.
- Both X38 base selectors: `../darwin-escaped-capture-cleanup-20261025/proof.md`,
  accepted native RED reuse and final attempt03 GREENs after fixture correction.

`source-binding.json` verifies the kill/drop test bodies and relevant fixture,
record, liveness and cleanup helpers byte-identically against their accepted
source at 76fdebd7. The Unix runtime is unchanged; its sole source-file delta is
an unrelated internal unit-test cfg. The complete current capture test file is
identical to the accepted native base receipt. Original log hashes and statuses
were inspected. Assertion sensitivity transfers at unchanged assertion/OS/compiler/
lock scope to the new feature profiles; no fresh profile-specific RED is claimed.
The old missing Rust1.93 X25 proof path is not used.

## Real behavior and independent readback

Every new invocation uses a real Rhai Engine and registered host package, real
child processes, fixture roots, stdout/stderr pipes and an unrelated sentinel.
The kill cases observe leader/worker/leaf absent after public kill and bounded
non-unit unsuccessful wait, while the sentinel is still live at API return.
The clone cases observe all members live after nonfinal drop, then absent after
final drop, with sentinel survival followed by explicit reap. The capture cases
observe escaped holder/sentinel operation, retained markers and incomplete capture,
Darwin EPIPE after endpoint closure, direct-leader reap and exact fixture cleanup.

All eleven Cargo selectors and the scoped runner exited0; each selector reports
one passed test. A separate observer ran after the invocation and checked all
38 recorded PIDs plus the ten explicitly recorded kill/drop process groups using
signal zero, accepting absence only for ESRCH. Capture cases contribute their
three terminal PIDs each; no separate capture-group readback is claimed. Observer
source and its original readback are retained in attempt01.

## Build/resource lifetime

One scoped invocation archives the integrated source and uses private target and
Cargo home throughout, with two jobs and an outer600s limit. Initial preparation
23.45s; additional feature preparations8.25/8.23s; remaining commands reused the
target at0.04s. Summed Cargo preparation40.25s. The filesystem-timestamp wall
envelope was46.437s before the independent observer/review; `usage.json` records
the method, scope and unavailable token/cost fields.

The runner removed its private runtime. The observer confirmed the exact owned
session scope empty and retired it with rmdir. No build/cache remains. Source,
original receipts, limits and accepted proof remain outside the disposable scope.
Other native/feature/MSRV paths, X25/X27/X34/X37/X38 overall, Windows custody,
Ticket03 and the full A–F acceptance remain open.
