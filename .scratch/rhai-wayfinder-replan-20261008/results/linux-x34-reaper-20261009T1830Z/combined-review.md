# Combined independent review — X34 Linux fixture-reaper package

Verdict: accepted only for `managed_run_deadline_reaps_group_under_fixture_reaper` and `managed_run_output_limit_reaps_group_under_fixture_reaper` on the recorded native Linux x86_64 configuration. No acceptance blocker found. This review used saved original outputs and committed source; no builds or tests were launched.

## Rules loaded

Central Agent Skills HEAD: `1b6e1da85f87cad25f7aafc91aa782319ac6ef93`. Read its AGENTS.md, common global instructions, build-efficiently, TDD and resource-lifecycle guidance, current project AGENTS.md and both memory entrypoints. Observed SHA-256: project AGENTS `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`; common instructions `f71e8f97beba0cd7612310667d83c016ece4a5f390d1f2e45526f36ef19feec8`; build-efficiently `58f676b48691ea2ed476f67f13ef68aedcdb73cd4cabf13925db1927c9ccaf04`; TDD `a4d82ea3d2e25bea6e8f10b9240ee2d189592c3cedb448dd978ad570f997e715`; resource lifecycle `102bc29d25f4d416ac6d4e952cb575d70f28a69a1435f2aaa5689bc931ae7939`. Memory provides historical context, not fixed slots or renewed permission. These are observations on this review host, not a certification of other sessions.

## Source and execution binding

Both phases use revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`, previously tree-matched archive `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644`, lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, and restored test source `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`. Payload checks archive/lock before extraction and the baseline before RED and GREEN. Independently reconstructing its two Boolean expectation inversions from committed source reproduced RED hash `6fae78a9930998057e2d3d49099e54e0da7887b308bbd319b867bd65a8ed4586` exactly.

Native environment records Linux workhorse 7.2.8 x86_64 and Rust/Cargo 1.77.2. Cargo artifact records confirm actual features `default,std,sys,testing-environ`, opt-level0, debug assertions and overflow checks enabled. Both builds returned0 (19.83s and1.39s); commands select the exact listed test names. Each RED returned101 at its deliberately inverted semantic timeout/OutputLimit expectation; each restored GREEN returned0 with exactly its named parent test passing. Nested `process_fixture` executions are real fixture subprocesses, not substitute parent acceptance results. The packet's existing 44-entry manifest verified before this review file was added.

## Behavioral and lifecycle evidence

Committed fixture code drives real Rhai `run` through Engine and the registered managed process package. Readiness uses recorded host/reaper/member identities and an explicit PIDFD acknowledgement, with bounded polling. A separate fixture subreaper uses identity-checked exact waits; the parent independently checks retained live PIDFDs and their exit notifications, member start times, original process-group ESRCH and a live unrelated sentinel. Exceptional/watchdog cleanup is explicitly excluded from the accepted API boundary.

Deadline GREEN records a normal timeout report map (`api_success=true`, `timed_out=true`, `success=false`), partial markers on both streams, both captures incomplete, all exact group members absent/exited, exact worker/leaf reaping, and host/reaper/sentinel live through observation. OutputLimit GREEN records a typed Process OutputLimit, exactly4096 captured stdout bytes matching the expected prefix, both captures incomplete, no timeout, and the same independent group/reaper/sentinel observations. Both then record successful fixture-reaper completion and sentinel reaping. The deadline result is a timeout report map, not a typed Timeout error; proof.md's phrase “typed timeout result” should be changed to “timeout report” for accuracy.

One 600-second scoped invocation contains both REDs, restoration and both GREENs. Source, target and Cargo home are inside the runner runtime; saved evidence is outside. Runner returned0 after25seconds. Exact scope device58/inode119693205/uid0/gid0/mode700 matches before/after; recorded scope emptiness and successful rmdir establish retirement. This proves successful-run disposition, not interruption behavior.

## Applicability limits

Accept only these two selectors at Linux1.77.2 with the recorded default checked features. Other X34 cases, Darwin/Windows, no_float/sync/no_index/unchecked variants, interruption/native custody and the complete A–F package remain open. Existing X35 and other accepted proof remain separate and need no repetition from this review.
