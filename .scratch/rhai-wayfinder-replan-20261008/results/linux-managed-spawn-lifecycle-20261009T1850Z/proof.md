# Linux managed-spawn group-kill and clone-drop lifecycle

**Result:** Both exact selectors have meaningful semantic REDs and restored-source GREENs on native Workhorse Linux x86_64, Rust/Cargo 1.77.2, `testing-environ,sys` plus default features and checked test profile. Acceptance is pending the combined independent review and applies only to these selectors/configuration.

## Bound inputs and run

The run used archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644` (tree-bound to revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`), lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, and restored test source SHA-256 `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`. The one bounded `run_scoped.py` invocation compiled the two deliberate assertion inversions, ran both exact RED selectors, restored and rehashed the source, compiled once again, and ran both exact GREEN selectors. Limits were 600 seconds and two Cargo jobs. Source, target and Cargo home were within `AGENT_RUNTIME_DIR`; logs were exported outside the runtime. Runner status 0, elapsed 23 seconds. Workhorse preflight, tool versions, commands and output are in `attempt01/`.

Exact selectors:

- `managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel`
- `managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not`

Each RED changed only its final expected group-cleanup boolean to the wrong value. Both exited 101 at the intended `RED control:` assertion after observing real lifecycle behavior. Restored source matched the baseline before GREEN; each exact selector passed 1/1.

## Independent behavior observed

For public `Child.kill`, the test records live leader/worker/leaf identities, then independently observes ESRCH for each after kill while the unrelated sentinel remains live. It then waits/reaps its own sentinel and fixture descendants.

For clone-drop behavior, the test independently observes all three exact members live after the nonfinal clone is dropped and the surviving shared handle performs a bounded wait. Dropping the final handle then yields ESRCH for leader, worker and leaf while the unrelated sentinel remains live; the fixture reaps its own resources. Full logs contain the observed PIDs and cleanup readbacks.

Unchanged Darwin selectors remain bound to their own prior proof. This run does not cover other Linux X34/X37/X38 selectors, feature variants, interruption, Windows, or full A–F acceptance. Do not treat this package as accepted until the combined review is recorded.
