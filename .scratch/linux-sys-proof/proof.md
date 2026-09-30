# Native Linux sys contract proof

## Source and environment

- Source revision: `f7aed036027beb500a3fbd0e538cd181b7f8a184` (`task/all-tickets`).
- The workhorse source archive SHA256 was `52b5ca5e668d152950e8e35926236d44c215990685a469b596b42f939ecfef38`.
- Native host: `workhorse`, Bazzite 44, x86_64; kernel `7.2.4-ogc3.1.fc44.x86_64`.
- Rust: `rustc 1.97.1 (8bab26f4f 2026-07-14)`; Cargo `1.97.1 (c980f4866 2026-06-30)`.
- The source archive was extracted inside `run_scoped.py`'s private runtime. `CARGO_HOME`, `CARGO_TARGET_DIR`, and temp paths were inside that runtime.

## Results

The native command passed with exit status 0:

```sh
cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs -- --nocapture
```

It passed 7 `sys_env`, 24 `sys_fs`, and 24 `sys_policy` tests. The Linux invalid-byte fixture was created successfully and `read_dir(".")` returned `NotUtf8`: changing the expected variant to `SysError::Io` caused the focused test to fail with exit 101 and the observed error text `NotUtf8: directory entry "bad\\xFF.txt"`. After restoring `tests/sys_fs.rs` byte-for-byte, the same focused test passed with exit 0. The restored file SHA256 (`241d914bc2361c51cc9ab75983aee9d34c96e873202e00a77a85fe54babbcf11`) matches the source revision.

The full output, source identity, commands, versions, and statuses are retained in [native-linux-sys.log](native-linux-sys.log). The first wrapper attempt also passed the suite and both assertion runs but exited 1 during redundant log self-copy; that harness diagnostic is retained in [attempt1-finalization-diagnostic.log](attempt1-finalization-diagnostic.log). The corrected wrapper run is the accepted run.

The self-copy error happened after Cargo had finished and was limited to evidence export. The first attempt's contract output and statuses remain valid in its retained log; they could have been used without another cold build. The later accepted run independently records the same suite and control results. The retained runner has since been hardened to require exit 101 and both the exact `NotUtf8: directory entry "bad\\xFF.txt"` diagnostic and the named test failure before it accepts the negative control. This harness-only check was validated against the retained log and with `bash -n`; Cargo was not rerun for this export/status-check change.

## Platform limits and cleanup

This Linux run excludes `test_root_accepts_macos_system_prefix_aliases` and `test_nested_roots_keep_permissions_through_system_prefix_aliases` (`target_os = "macos"`), plus `test_windows_paths` (`cfg(windows)`). The Linux-only `/proc/self/fd` handle-leak check ran. This is not release-matrix evidence and does not certify process, TCP, or file-handle behavior beyond the listed tests.

The runner recorded status 0. Read-back confirmed its launcher exited and `/tmp/agent-build-ol392c2n` no longer existed after `run_scoped.py` cleanup. The temporary extracted staging source and copied runner were removed after the run. The exact source archive and logs remain on the workhorse at `/root/rhai-linux-sys-proof-task/`; the accepted test log is also retained in this directory. No remote Git writes or global cache changes were made.
