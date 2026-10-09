# Linux process completion, exact reaper drop and escaped-pipe cancellation

**Result:** Four exact selectors each reached a meaningful wrong-expectation RED (101) and passed restored-source GREEN (1/1) on native Workhorse Linux x86_64, Rust/Cargo 1.77.2, `testing-environ,sys` plus default features, checked test profile. The combined independent review accepted only these selectors/configuration; see [combined review](combined-review.md).

## Binding and run

Inputs: source archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644` tree-bound to revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`; accepted lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; baseline `tests/sys_process.rs` `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`. Archive/lock were checked before extraction, test source before mutation and after restoration. One scoped `run_scoped.py` invocation built the controlled source, ran all four exact RED selectors, restored source, rebuilt once and ran all four exact GREEN selectors. Bounds were 600 seconds and two Cargo jobs. Build source, Cargo home, target and transient files were under `AGENT_RUNTIME_DIR`; evidence was exported outside it. Native OS, Rust/Cargo versions, exact commands and full test output are in `attempt01/`. Runner exited0 in24 seconds; the exact owned session scope identity matched before/after, was empty and retired.

Selectors:

- `managed_run_succeeds_after_fixture_reaper_reaps_descendants`
- `managed_spawn_final_clone_drop_closes_group_under_fixture_reaper`
- `managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes`
- `managed_spawn_post_reap_cancel_bounds_escaped_capture`

REDs invert only the successful-run report expectation, final-drop group-closure expectation, escaped stdout completion expectation, and post-reap stderr completion expectation respectively. All failed at their named `RED control:` assertion. The original source hash was restored before GREEN; every exact parent test passed 1/1.

## Independent observations

The normal-run fixture proves a zero-exit public Rhai `run` report, complete stdout/stderr and successful return only after a separate fixture reaper exact-waits worker and leaf. The API host remains live for independent PIDFD/member/start-time readback; unrelated sentinel stays live at the API boundary and is reaped afterwards.

The reaper-backed final-clone test proves nonfinal drop preserves the live group, records the final drop at the API boundary, then independently observes PIDFD exit notifications, exact member identities absent, process group ESRCH, exact worker/leaf reaping and live host/reaper/sentinel through closure. Watchdog cleanup is absent; later exact cleanup retires host and sentinel.

The escaped-holder tests challenge a still-live holder after public cancellation. One proves kill of the managed leader does not kill the escaped holder in the unrelated sentinel group and both capture writers reject later writes with EPIPE. The other proves natural leader exit, pending uncancelled waits, public post-reap cancellation that preserves the escaped holder, final incomplete report with `success=true`, and EPIPE on both closed writers. Fixture records and independent exact waits then show the leader, holder and sentinel are reaped.

This package does not cover other X34/X37/X38 selectors, additional feature profiles, Darwin/Windows, interruption custody or full A–F acceptance. Previously accepted rows are retained separately and are not repeated here.
