# Ticket 03 X11 `env_remove` — Linux partial proof

## Accepted scope

This proof covers only Ticket 03 X11 on Workhorse Linux x86_64 with Rust/Cargo
1.93.0 and the `testing-environ,sys` feature set. Other operating systems,
MSRVs, and feature combinations remain open. No production source change was
needed.

The public Engine integration test is
`tests/sys_process.rs::run_removes_inherited_environment_variable_from_public_child`.
It starts the test executable by absolute path through Rhai's public `run` API,
without `env_clear`, and requests removal of the inherited `PATH`. The child
writes its environment observation to a separate file. A second public `run`
without `env_remove` proves the test host's inherited `PATH` reaches a control
child. Each child also writes its PID and exit code, and the test confirms direct
child reaping.

## Reproduction and results

The exact acceptance command was:

```text
cargo test --locked --features testing-environ,sys --test sys_process run_removes_inherited_environment_variable_from_public_child -- --exact --nocapture --test-threads=1
```

Inputs were frozen from source revision
`8702248b508a7d02b87cb23f70b3853022e11a0e`. The test overlay SHA-256 is
`b585903b21aa64d3725cd5c1bfb883f71c40104273f928404e1ba86997ba16e7`, the
accepted lock SHA-256 is
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, and the
canonical `run_scoped.py` SHA-256 is
`25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.

The sensitivity run changed only the `env_remove` loop in `run_map`; the separate
`spawn_child` path remained intact. That run exited 101 at the intended
environment assertion: the child observed `variable=PATH present=true` while
the assertion expected `variable=PATH present=false`. The helper restored the
exact product source bytes (SHA-256
`d4fc28906b624f6e9368d0bef16e82e3fc29cada5142da67406fd95962153115`) before
the restored GREEN run, which exited 0 (`1 passed; 0 failed`).

Independent readback from GREEN recorded:

```text
removed child: child-pid=1721513 child-exit=0
removed environment: variable=PATH present=false
control child: child-pid=1721515 child-exit=0
control environment: variable=PATH present=true
direct_children_reaped=ESRCH
```

The paired run took 19.959 seconds. Periodic samples observed a maximum of six
owned processes, 865,048 KiB RSS, and 1,375,680 KiB private runtime storage.
These are sampled maxima, not continuous peaks. Each remained below the
recorded limits. The process exited with outer status 0; the scoped runner
removed its private runtime.

Captured output and its per-file checksum list are under
`remote-output/out/attempt-02/`; all listed hashes were verified after readback.
The exact preflight receipt is `preflight-attempt-02-final.json`. The exported
run manifest and result are in the same output directory.

## Earlier setup outcomes

The first helper launch exited before Cargo because it searched for a nonexistent
`pub fn run(` signature. A source inspection identified `fn run_map(` as the
public `run` path, and the next helper uses that exact path. Two subsequent
read-only staged preflight attempts then refused because the local preflight
expected a stale helper hash; no build or assertion ran in those attempts. The
correct staged helper hash is
`8002d97ada5c1883728b52f70b6a34d4a55435eb7ca6bc82f26c36214f8a88ca`; the stale expected
value was `8002d97ada5c1883725cd5c1bfb883f71c40104273f928404e1ba86997ba16e7`. After
updating the exact pin, the fresh staged preflight passed at
2026-10-07T14:45:21Z with no active heavy process, 91,739,724 KiB available RAM,
and 610,134,118,400 bytes free on the scope filesystem. No further run is
planned for this unchanged Linux slice. After checksum-verified export, cleanup removed only the exact owned scope: 22 files (155,887,388 bytes), no live sampled process identities, and no private runtime; the scope itself was removed with `rmdir` at 2026-10-07T14:48:08Z.
