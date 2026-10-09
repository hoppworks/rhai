# Combined independent review — Linux zombie and false-drop boundaries

Verdict: accepted for the four named selectors at native Linux x86_64 Rust/Cargo1.77.2, testing-environ,sys plus defaults, checked test profile. No blocker found. Review read committed source and original saved evidence; no tests/builds or product edits were performed.

## Current instructions

Freshly loaded central Agent Skills AGENTS/common rules, project AGENTS, build-efficiently, TDD, resource-lifecycle and both memory entrypoints. Observed central HEAD `1b6e1da85f87cad25f7aafc91aa782319ac6ef93`; SHA-256 prefixes: project AGENTS `37f95ff6a80be28b`, common rules `f71e8f97beba0cd7`, build-efficiently `58f676b48691ea2e`, TDD `a4d82ea3d2e25bea`, resource lifecycle `102bc29d25f4d416`. No claim about other sessions' loaded rules. Historical memory does not renew fixed slots or permission.

## Binding and failing controls

Source revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`; tree-bound archive `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644`; accepted lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; restored test source `86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41`. Input/restoration checks are explicit. Reconstructing the four scoped semantic inversions from Git source independently reproduces RED SHA `77f7d096c0a19f70ee4dbd427b9bbeac8c239b900bf9f954ef04844040caa045` exactly.

Native OS/compiler records agree; Cargo records confirm default,std,sys,testing-environ, opt-level0, debug assertions and overflow checks enabled. Both builds returned0 (19.02s/1.44s). All four exact selected parent tests reached intended behavioral assertion RED101, followed by restored-source GREEN0/1passed. Nested fixture tests are separate subprocess observations, not replacement parent acceptance. Existing manifest verified before adding this review.

## Contract verdicts

- `managed_run_reports_while_fixture_reaper_holds_stopped_zombies`: public API returns typed Process Io, operation observe process group closure, kind TimedOut, matching retained-ownership diagnostic, complete capture and direct exit0. Independent live PIDFD/start-time observations establish direct leader reap and exact worker/leaf zombies held by the foreign-parent fixture subreaper in the original still-present group. Only after boundary observation does the fixture permit exact reaping. This is the explicit owner-approved incomplete-cleanup error, not a new product defect and not proof the group was absent at API return. RED inverts the actual recognized API outcome; GREEN retains the exact observed error. The test allows either historical success-report or matching error branch, but this recorded run specifically proves the approved error branch.
- `managed_child_kill_reports_group_closed_under_fixture_reaper`: public kill produces a host-bound unsuccessful child report with complete capture. Independent exited PIDFDs, absent members, exact worker/leaf waits and live host/reaper/sentinel are observed; subsequent cleanup has empty group, absent host and reaped sentinel. RED inverts the killed-report predicate.
- `managed_run_deadline_cancels_escaped_pipe_holder_under_fixture_reaper`: real timeout report retains partial markers/incomplete captures; exact leader PIDFD exits and managed group is ESRCH while escaped holder PIDFD remains live in the separate sentinel group. Fresh challenge returns both write results -1/EPIPE32; watchdog cleanup is absent through challenge. Fixture exact-waits holder, then confirms host/leader/holder/sentinel absence and sentinel-group ESRCH. Holder receipt records wait_status25856; acceptance concerns exact reaping, not a successful holder exit. RED inverts the actual EPIPE predicate.
- `managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit`: real final public-client and Engine drops preserve running members. A fresh challenge receives three acknowledgements with the recorded leader/worker/leaf PIDs and group; this establishes live operation rather than relying on elapsed sleep. Natural leader release subsequently closes all three while sentinel survives; guards reap owned resources. RED inverts the live-members/challenge predicate. This selector uses PID records/probes/challenge, not PIDFD identities.

## Cleanup and limits

One600-second scoped invocation shares RED/GREEN compilation and all controls; source, Cargo home, target and transients are inside AGENT_RUNTIME_DIR and durable evidence outside. Runner returned0 after33seconds. Exact scope device58/inode119741977/uid0/gid0/mode700 matches before/after, is recorded empty and retired. Panic guards preserve exact fixture cleanup; no foreign work is implicated. This proves successful-run disposition, not interruption custody.

Acceptance is limited to these four Linux selectors/configuration. Other process cases, variants, Darwin/Windows, interruption and full A–F remain open. Preserve accepted earlier packets separately; no unrelated reruns are warranted.
