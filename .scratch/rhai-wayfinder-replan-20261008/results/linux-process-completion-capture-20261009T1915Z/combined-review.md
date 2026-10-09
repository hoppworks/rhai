# Combined independent review — Linux process completion and capture

Verdict: accepted only for the four selectors listed below on native Linux x86_64 Rust/Cargo1.77.2 with testing-environ,sys plus defaults and the checked test profile. No blocker found. Review used saved originals and committed source, without builds/tests or source edits.

## Current rules observed

Central Agent Skills HEAD `1b6e1da85f87cad25f7aafc91aa782319ac6ef93` was observed and its AGENTS/common global instructions freshly read, together with project AGENTS, build-efficiently, TDD, resource-lifecycle and both memory entrypoints. SHA-256 prefixes: project AGENTS `37f95ff6a80be28b`; common instructions `f71e8f97beba0cd7`; build-efficiently `58f676b48691ea2e`; TDD `a4d82ea3d2e25bea`; resource-lifecycle `102bc29d25f4d416`. Memory remains historical context. No other session's loaded revision is certified.

## Binding and controls

Source revision is `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`; tree-bound archive SHA `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644`; accepted lock SHA `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; restored test source SHA `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`. Payload verifies inputs before extraction and restoration before GREEN. Independently reconstructing its four semantic expectation inversions reproduces RED SHA `48447b235c62cdfbef5a3e96930822444f11e7f4c5394d3f9c1fca746b76bca8` exactly.

Version records establish native Workhorse Linux7.2.8 x86_64 and Rust/Cargo1.77.2. Both Cargo artifact records show actual features default,std,sys,testing-environ; opt-level0, debug assertions and overflow checks enabled. Both builds returned0 (18.56s/1.39s). Each exact selector was listed and executed: RED101 at its intended changed behavioral expectation, then restored-source GREEN0 with exactly1 parent test passing. Nested process_fixture passes are fixture subprocess outputs and are not substituted for parent acceptance.

## Accepted behavior

- `managed_run_succeeds_after_fixture_reaper_reaps_descendants`: real public Rhai run returns a successful zero-exit report with complete captures. Separate fixture subreaper exact-waits worker/leaf; parent holds live PIDFDs, then independently checks member absence and host/reaper/sentinel custody at return. Later fixture cleanup and sentinel reap are recorded. RED inverts the actual successful-report expectation.
- `managed_spawn_final_clone_drop_closes_group_under_fixture_reaper`: real managed shared Child handles preserve the group after nonfinal drop, then final drop records return and independently observed closure. GREEN shows exact PIDFD/start identities, exited PIDFDs, worker/leaf exact waits, process-group ESRCH, no watchdog cleanup, host/reaper/sentinel live through closure and later exact cleanup. RED inverts the observed final-members-live expectation.
- `managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes`: public kill/wait closes the managed leader and returns incomplete captures while an escaped holder remains operational in the separate sentinel group. Fresh post-return challenge yields holder-written stdout/stderr write results -1/EPIPE32; independent readback validates holder PID and both EPIPE results. Exact fixture release/waits and ESRCH for leader/holder/sentinel follow. RED changes stdout_complete's expected false to true.
- `managed_spawn_post_reap_cancel_bounds_escaped_capture`: natural leader release/exit is independently recorded and ESRCH observed. Uncancelled timed waits remain unit while holder/sentinel survive. Public cancellation then returns the retained success=true report with incomplete captures while holder survives and answers the fresh challenge with EPIPE on both writers. Exact fixture waits and terminal ESRCH follow. RED changes stderr_complete's expected false to true.

The two escaped-holder fixtures use owned PID records, real OS probes, fresh challenge/readback and exact fixture waits; they do not acquire PIDFDs. The stronger PIDFD/start-time evidence belongs to the two reaper-backed selectors. No blanket PIDFD or interruption claim is warranted.

## Resource disposition and limits

One600-second scoped invocation includes all REDs, restoration and all GREENs; source, Cargo home and target are inside AGENT_RUNTIME_DIR, evidence outside. Runner returned0 after24seconds; scope device58/inode119725619/uid0/gid0/mode700 is identical before/after and recorded empty, with successful exact rmdir retirement. Existing manifest verified before adding this review. Saved RED paths also show exceptional fixture cleanup, without affecting the valid restored GREENs.

Acceptance covers these four selectors/configuration only. Other X34/X37/X38 cases, feature/toolchain/platform rows, interruption custody and full A–F remain open. Prior accepted proof remains separate and reusable; no unrelated rerun is justified by this review.
