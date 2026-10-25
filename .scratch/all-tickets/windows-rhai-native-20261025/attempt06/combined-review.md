# Independent combined review: native Windows sys integration targets

Verdict: **PASS for the current-source native Windows `sys_policy`, `sys_env` and `sys_fs` target slice**. Reviewed 2026-10-25. This does not close other Windows behavior, feature/MSRV rows, A–F or release readiness.

The reviewer independently rehashed all 13 exported original files and the raw 214-frame serial export. The three-target `--no-run` compilation completed. A wrong expectation caused the named `sys_fs` test to fail at its intended assertion after an independent host-file readback; restored GREEN passed 6 `sys_env`, 29 `sys_fs` and 21 `sys_policy` tests, with no failures or ignored tests. Relevant tests and support files remain unchanged from the bound source commit.

All eight public journal records have valid lengths and CRC32s, ending in `REMOVE_INTENT` and `REMOVED`. The exact runtime identity matches the public Driver and observer. The Driver exited 0; the observer drained pipes, disposed the process, found no pending custody or observer kill, and checked runtime absence. The test fixtures use owned temporary roots and independent `std::fs` readback.

The outer guest attempt scope and own host media/stage remain for evidence-first retirement. The accepted tuple is source `25e78217`, lock `2ba4b3a0…`, public build manifest `90e10dd7…`, Runner `f3adeb06…`, Driver `9d4afceb…`, Windows 11 Pro build 26300, Cargo/Rustc 1.93.0, and `testing-environ,sys,metadata`.
