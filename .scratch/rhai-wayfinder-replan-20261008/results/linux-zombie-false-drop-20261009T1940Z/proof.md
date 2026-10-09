# Linux held-zombie closure, Child.kill, escaped deadline holder and false-drop policy

**Result:** Four exact selectors each reached a deliberate wrong-outcome assertion RED (101) and passed restored-source GREEN (1/1) on native Workhorse Linux x86_64, Rust/Cargo 1.77.2, `testing-environ,sys` plus default features, checked test profile. Pending combined independent review; no wider acceptance follows.

## Bound inputs and execution

Source archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644` is tree-bound to revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`; accepted lock SHA-256 is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; baseline `tests/sys_process.rs` SHA-256 is `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`. Payload verifies source/lock before mutation and source after restoration. One scoped invocation contains one RED build, four exact RED controls, source restore, one GREEN build and four exact GREENs. Boundaries were 600 seconds and two Cargo jobs. Source, Cargo home, target and private caches were in `AGENT_RUNTIME_DIR`; evidence remains outside it. Native environment and tool versions are saved. Runner status0 after33 seconds; exact scope identity matched before/after, was empty and was retired.

Selectors:

- `managed_run_reports_while_fixture_reaper_holds_stopped_zombies`
- `managed_child_kill_reports_group_closed_under_fixture_reaper`
- `managed_run_deadline_cancels_escaped_pipe_holder_under_fixture_reaper`
- `managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit`

REDs invert respectively the accepted-API-outcome predicate, killed-child report predicate, post-deadline EPIPE challenge predicate, and live-group `kill_on_drop(false)` predicate. Each reached its named control assertion. Panic-path guards released only fixture gates and reaped owned children; every subsequent restored-source GREEN passed exactly one parent selector.

## Contract observations

The held-zombie test observes a live managed host whose direct leader is reaped while the fixture subreaper owns the exact worker and leaf as stopped zombies in the original group. The public call returns a typed process I/O error classified as `TimedOut` for `observe process group closure`, with the accepted diagnostic that the managed scope remains present under retained ownership. This is the previously owner-approved incomplete-cleanup outcome; the test then permits exact reaping and verifies cleanup.

The public `Child.kill` test returns a host-bound unsuccessful child report with complete captures. Exact PIDFDs report exited; leader/worker/leaf identities are absent; the independent reaper records exact worker/leaf waits; host/reaper/sentinel remain live at the API boundary; final cleanup leaves no group and reaps the sentinel.

The deadline/escaped-pipe test returns a timeout report with partial markers and incomplete captures after closing the managed group. A separately recorded escaped holder remains alive in the unrelated sentinel group and answers a fresh challenge with EPIPE on both output writers. It is then released and exactly reaped; host, leader, holder and sentinel identities and sentinel group are absent after cleanup, with watchdog cleanup excluded from the boundary.

The `kill_on_drop(false)` test observes all three members live after dropping the final public client, receives challenge acknowledgements from those exact PIDs in the recorded group, then releases the leader and observes ESRCH for leader/worker/leaf while the sentinel remains live. Fixture-owned guards clean all resources.

Acceptance remains limited to these four Linux selectors/configuration. Preserve all accepted earlier packets separately. Other process selectors, feature variants, Darwin/Windows rows, interruption custody and A–F remain open.
