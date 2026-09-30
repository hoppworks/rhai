# Native Linux optional package minimum Rust proof

## Result

At immutable source revision `293172363f4929acb166e33e0aa34fff5fc7e1cc`, the native Linux x86_64 `sys` + `net` selected Engine/real-OS targets compile and pass on Rust 1.77.2 with `testing-environ,sys,net,metadata` and the accepted lockfile. This is the Linux minimum-Rust result for these eight selected targets only; it does not establish combined-feature coexistence, the full feature matrix, or Linux sys-f32.

The single scoped invocation was launched through SSH as exec handle `94647`, at 2026-09-30 17:06:49 UTC, and completed before the 17:19 UTC execution deadline. The exact completion timestamp was not recorded. Remote `outer-status.txt`, `run-scoped.status`, PID readback launcher/status are all `0`. All runner stages and the control/restored test statuses are captured under `remote-evidence/`.

| Target | Passed |
| --- | ---: |
| `sys_policy` | 24 |
| `sys_env` | 7 |
| `sys_fs` | 35 |
| `net_connect` | 4 |
| `net_listen` | 7 |
| `net_reads` | 7 |
| `net_writes` | 10 |
| `net_metadata` | 1 |

The deliberately wrong-expectation control exited 101 and showed actual `abc` against `wrong expectation`; the restored exact targeted test passed (1/1). This confirms the test exercised the expected real file-read behavior.

## Frozen inputs and environment

- Driver/source-gate commit: `df0e5da7e3238d35f258c3d48898df674591a3ea`.
- Complete source archive SHA256: `fe8ad5aa459e525e484d84c7a5a90f144ab142b10a96392ec30f5e75c77a4577`.
- Accepted/final exported `Cargo.lock` SHA256: `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa` (the final copy is `remote-evidence/Cargo.lock`).
- Native host: Linux x86_64, kernel `7.2.4-ogc3.1.fc44.x86_64`.
- `rustc 1.77.2 (25ef9e3d8 2024-04-09)`, host `x86_64-unknown-linux-gnu`; `cargo 1.77.2 (e52e36006 2024-03-26)`.
- Installed toolchain, cargo registry/cache, source extraction, and build outputs were confined to private runtime `/tmp/agent-build-qnkw2mdf` and removed by `run_scoped`.
- Resource samples: maximum sampled private storage `826684 KiB` (`du -sk`, 1-second sampling); maximum sampled owned descendants 7 (1-second PID/PPID ancestry sampling), under configured limits. These are sampled maxima, not guaranteed instantaneous peaks.
- Exact recorded PID/start-tick identities were all absent at readback; scoped PGID live process list was empty; run-scoped PID was absent. Private runtime path was absent after invocation. The exact remote stage was removed only after verifying all 39 exported evidence-file hashes and all six staged input hashes against local frozen sources; a separate SSH readback confirmed `/root/rhai-linux-optional-msrv-proof-task` absent.

## Evidence index

`remote-evidence/` contains the raw target/control logs and statuses, toolchain install and version receipts, the final exported lock copy (SHA256 verified), exact PID/process identities and samples, storage samples, and runner/cleanup statuses. `input-identities.sha256` records the staged source archive, lock, driver, launcher and scoped-runner hashes. The remote stage was removed after successful local export and independent absence readback. No production files changed, and no push or merge was performed.
