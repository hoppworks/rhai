# Native Linux filesystem follow-up

## Source and environment

- Tested revision: `98f66acae6d571b304e92c52471a001191386a99` (the integrated HEAD when this run began). It includes filesystem commits `7b707cffe3ef398e3068f8dacc2f942366ad7976` and `17287a96b5314c3192653ed2d706b23b1626c121`. The later `98f66aca` changes in this range are proof/coordinator records; the relevant filesystem implementation and regression are those two commits.
- Workhorse source archive SHA256: `876c3e60bb868cc7750ab52a698a8b2d54a4969c6d9327b7b9ec09597d590384`.
- Native host: `workhorse`, Bazzite 44, x86_64; kernel `7.2.4-ogc3.1.fc44.x86_64`.
- Rust: `rustc 1.97.1 (8bab26f4f 2026-07-14)`; Cargo `1.97.1 (c980f4866 2026-06-30)`.
- Source, `CARGO_HOME`, `CARGO_TARGET_DIR`, and temp paths were scoped under the remote `run_scoped.py` runtime.

## Results

The affected native targets passed with exit status 0:

```sh
cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_fs -- --nocapture
```

All 25 `sys_fs` and 24 `sys_policy` tests passed. `test_unrestricted_relative_paths_after_cwd_is_unlinked` passed on Linux: its child first signals readiness, then the parent removes the child's owned current-directory entry and releases it; the child successfully reads `std::fs::metadata(".")` and the public Rhai `exists(".")` and `is_dir(".")` results. The public `test_non_utf8_file_name` also passed, with no `EILSEQ` skip output.

The full command output and host details are in [sys-fs-policy-98f66aca.log](sys-fs-policy-98f66aca.log). The macOS deleted-cwd red reproduction remains preserved in the integrated source revision at `.scratch/filesystem-contract/unlinked-cwd-red.log` (SHA256 `0e746a84301c09a07eb213ee6d674349fbc3ffb14a9af3780c4140749b6c9d85`). It was not modified by this Linux run.

The previous environment result remains applicable: `tests/sys_env.rs` is byte-identical between the earlier proven source `f7aed036027beb500a3fbd0e538cd181b7f8a184` and this revision. The `test_non_utf8_file_name` body is also byte-identical, so the earlier wrong-variant control (exit 101 with the actual `NotUtf8` diagnostic) and restored assertion pass (exit 0) in [native-linux-sys.log](native-linux-sys.log) still establish that assertion's sensitivity. This follow-up did not repeat that control.

## Platform limits and cleanup

The two macOS system-prefix alias tests and Windows-only `test_windows_paths` are excluded on Linux. The Linux-only `/proc/self/fd` check ran. This proof covers the affected filesystem and policy integration targets; it does not certify the full release matrix or unrelated process, TCP, or handle behavior.

Runner status was 0. Read-back confirmed launcher PID `381413` had exited and `/tmp/agent-build-x4wwri9v` was absent after scoped cleanup. Temporary runner copies and the earlier empty staging directory created while pinning the source were removed. The source archive and canonical log remain at `/root/rhai-linux-sys-proof-task/revision-98f66aca/`; the historical source archive and evidence under `/root/rhai-linux-sys-proof-task/` remain intact.
