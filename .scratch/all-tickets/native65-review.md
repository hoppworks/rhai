# Native process false-policy lifetime review

Invocation65 proves the narrow public direct and managed `kill_on_drop(false)` contracts on development macOS. It does not close ticket03, owner retirement, the affected full regression suites, MSRV, Linux, Windows or release integration.

## Inputs and execution

Owner worktree: `/Users/hoppworks/projects/rhai-process-unix-run`, branch `task/process-unix-run`. Behavioral production source is unchanged from af18bb36; the Unix source change adds a test-only owner-retirement case. Frozen Unix file SHA256: `0c56c929cab30f134ac86cadbe8de55736ef3ed2678e1f4eca8bb5a12577315f`; integration tests: `6f1a04b70c7f971abf5f00b508bfb78e93a642d321dc08a8a0165b4a86d0a9b0`; harness: `e461c0a3987dcc7ce95fee3a9c001a44d715a5f6ca042d9ff1fe29dcf680a7c8`; wrapper: `0f9a0dbcfdebcd68268f97bc92fc8d9c87ed7030af81144cb42b86961d8ba598`.

The scoped run retained the 600s outer, 540s aggregate Cargo, jobs2 and sampled storage stop1572864KiB limits. It used the accepted lock `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa` plus the direct libc edge only, private lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. Six-path private manifest is retained in the raw log. This is the existing Rust1.93 development toolchain, not optional1.77.2 acceptance.

## Verified narrow behavior

Both force-final-drop-kill controls returned101 at the intended public survival assertion with exact fixture cleanup. Restored direct spawn drops its sole client and Engine, responds to a fresh child challenge, successfully writes and flushes 512KiB to each captured stream, records completion and is reaped. This proves drainability; the public handle is gone, so this case does not prove retained captured-byte equality.

Restored managed spawn drops its sole client and Engine while leader, worker and leaf remain live. All three provide fresh PID/group-bound challenge acknowledgements. Releasing only the leader then yields exact ESRCH for all three associated members. The independently owned sentinel remains alive until exact fixture cleanup. The controls establish that unconditional final-drop termination fails these assertions.

The corrected classifier was independently executed through AST extraction against all four actual logs, with the exact Cargo fixture parent bound to RUNTIME/tmp. All four receipts passed. The earlier native64 parent mismatch is an infrastructure failure, preserved by the coordinator state at a9e1dea4; its control test itself reached its intended RED.

## Raw artifacts and independent cleanup

All paths below are relative to the owner worktree. Base: `.scratch/process-unix-run/evidence/direct-drop-false.LzUJ8Q`.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Base raw log |34748|06d7eac27fba3a6febbbf382d130c9218b674c80825586fe977d8eb9994d727b|
| `.cargo.log.wrong-kill-on-drop-direct.log` |7222|dea001ce168449468b540cf73e289a140722023be090856e0a91f78f54e1d0a8|
| `.cargo.log.wrong-kill-on-drop-managed.log` |4202|0be8411dccdfd1a5b1a2b304ecf090ddf9d123a7fa4cd30b6079fb34b8a0059b|
| `.cargo.log.restored-kill-on-drop-direct.log` |3816|d522973236d6edd33486047fc65bcb57b7bc48b459e3fc58ff695974995e9800|
| `.cargo.log.restored-kill-on-drop-managed.log` |3897|36d8e899694cbff7953c0587a11592c9adbfc6c996826ab3367b43983dcfe696|
| `.cargo.log.restored-kill-on-drop-owner.log` |1278|0708db50d499cc9aecea0dea1c22963918f3a9a6e9bf703c92f00dae6dfec652|

Independent signal-zero readback found all22 emitted exact PIDs absent: 35824,35832,35833,35846,36122,36123,36150,36152,36153,36154,36155,36156,36162,36250,36255,36291,36294,36295,36296,36297,36298,36358. Exact runtime `/private/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-p7pa_4od` is absent. Sampled maximum250376KiB is not a continuous peak.

## Remaining acceptance

The owner-unit step failed compilation because its new assertion used an undeclared ProcessExit name. No owner assertion executed, and the full sys_process regression step did not run. Wrapper status1 and cleanup-status1 include the missing unexecuted full-suite log; independent process/runtime readback above establishes observed cleanup. Classify this as the first test setup compilation failure for this cause, not an executed implementation failure. Correct only the enum name/import, preserve the accepted public cases by unchanged-source/check applicability, and run owner plus affected integration regressions under the same scoped limits. No production merge is accepted by this review.
