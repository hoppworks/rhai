# Native Linux scalar process proof — 2026-10-03

Accepted source revision: 2a8fdc49a37b780c63e5c30b141c345321a876d0.
Native Linux 7.2.7-ogc1.1.fc44.x86_64, x86_64 GNU/Linux; private Rust/Cargo 1.77.2.
Compatible v3 lock SHA256 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.

One scoped invocation ran the exact public integration test
`scalar_run_with_cwd_works_without_collections` with:

- `testing-environ,sys,no_index`
- `testing-environ,sys,net,no_index,sync,metadata`

Each Cargo command used `test --locked --features <row> --test sys_process scalar_run_with_cwd_works_without_collections -- --exact --nocapture`.
The real Rhai script calls registered scalar `run` with CWD, env_clear, custom RECORD environment and shell stdin. The child writes its PID record and reports CWD. A fresh host read obtains that record; independent canonicalization supplies expected CWD. The test checks ESRCH after reaping, complete stdout/stderr, success and exit0, and verifies run_raw is unavailable with no_index. This proves these exercised paths, not every option or lifecycle edge case.

Each row first used a wrong CWD expectation in the private source only. Both exited101 at the intended stdout assertion with actual path and `<deliberately-wrong-cwd>` diagnostics. Exact original source bytes were restored; each positive execution passed one test, none ignored/filtered. All four child PID receipts were independently found absent after the runner ended.

Original command/status/stdout/stderr and source/input/restoration/resource records:
`linux-scalar-process-evidence/`. Launcher records:
`linux-scalar-process-outer-evidence/`. Independent fresh readback:
`linux-scalar-process-root-readback.json`.
The public test hash matches the frozen Git source, all manifest hashes match before/after and the compatible lock remains unchanged. Input/archive/base-helper pins and staged helper/launcher hashes were independently checked before dispatch.

The single package finished export after49.105 seconds. Limits outer600/scoped585/helper540 including30s export reserve, work510/jobs2/desc16/2GiB policy were retained. Periodic sampled maxima: RSS853820KiB, storage868060KiB, descendants10; these are not continuous peaks. Both scoped and outer status0. Fresh independent checks found all131 PID/start records absent, scoped groups empty, four child PIDs absent and exact runtime/session scope removed. Source review and affected recheck are recorded in linux-scalar-process-review.md; nine source-flow checks pass.

Unix native invocation85 consumed (cumulative85). Historical overhead measurement85 remains allocated but unlaunched under its original identifier; no stopped cause chain or calibration allowance is renewed. This closes two scalar process feature-row criteria only. Full process lifecycle, Windows production/native behavior, Darwin final behavior, remaining process feature matrix, overhead and release acceptance remain open.

Independent acceptance-evidence review confirms both stated row criteria may close; interruption export remains source-ready but was not exercised by this successful run. Exact staging cleanup hash-matched56 files, removed8 directories and confirms stage absence in linux-scalar-process-stage-cleanup.json. Three Python bytecode files created inside the uniquely owned stage caused the initial fail-closed cleanup inventory check to reject; the cause was diagnosed and only those exact files were added to cleanup. For future invocation the launcher now disables bytecode before runner/helper imports. The actually executed launcher remains unchanged in linux-scalar-process-outer-evidence/executed-launch.sh; no additional native run was performed for the prospective environment flag.
