# Linux optional MSRV proof state

Goal: prove Rust 1.77.2 native Linux x86_64 sys+net selected Engine/real-OS targets at immutable source `293172363f4929acb166e33e0aa34fff5fc7e1cc`.

Budget: original 2026-09-30 16:54–17:24 UTC, including independent root review. Execution deadline was 17:19 UTC; run launched 17:06:49 UTC and completed before the deadline (exact completion timestamp was not recorded). No extension.

Done: read the campaign brief, checkout `AGENTS.md`, release proposal, optional MSRV source review and accepted Mac proof. Confirmed clean exact checkout and accepted lock SHA256 `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa`. Frozen adapted driver and custody scripts at commit `df0e5da7e3238d35f258c3d48898df674591a3ea`; root reviewed and approved before staging/build. One scoped remote invocation completed with outer status 0. All eight requested targets passed (see `proof.md`); wrong-expectation control failed as expected (101), restored targeted test passed. Exact lock preserved; scoped runtime and owned processes verified absent. All 39 exported evidence-file hashes and six staged-input hashes matched the remote stage before cleanup. Exact remote stage `/root/rhai-linux-optional-msrv-proof-task` was removed after export; a separate SSH readback confirmed it absent. Final lock copy retained locally and SHA-verified.

Launch/cause history: one scoped execution launch; no implementation or infrastructure recovery launches. Remote toolchain and crates were fetched only within the private runtime. No production changes, push or merge.

Next: root integration/readback; no rerun is required absent a concrete evidence discrepancy.
