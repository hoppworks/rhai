Native macOS sys package-alone feature proof

Source revision: efddae9e7a7b18f86d4ff1901ae7c28b4c22fc9f
Source archive SHA-256: b52a810f167219dd6d4cc16401f55bd1cdb3eeface903accd15c012331d1c796
Cargo.lock SHA-256: 8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa
Platform/toolchain: see native-versions.txt (macOS arm64, current Rust 1.93.0).

Feature rows: baseline, sync, no-index, metadata-serde, only-i32-no-float, unchecked, no-index-sync-metadata, f32-float.
Each row compiled all three integration targets and ran sys_policy, sys_env, and sys_fs serially with nonzero harness counts; commands.tsv and outcome-summary.tsv provide every command, raw exit code, harness count, and result.

The negative control failed only on the deliberate wrong expectation (101, actual "abc", expected "wrong expectation"); the restored exact test passed (0). Each sys_fs fixture log includes fresh host readback "original XYyload".

Terminal wrapper status: 0 (execution-handle.txt). Cleanup readback: private runtime removed, all recorded owned PIDs absent, owned process group empty (cleanup-readback.txt).
Sampled private storage peak: 783812 KiB; sampled owned descendant maximum: 6. One-second sample maxima, not physical peaks.

Existing platform-specific cfg behavior was preserved; test logs retain each native harness output and any explicit platform-dependent diagnostic.
