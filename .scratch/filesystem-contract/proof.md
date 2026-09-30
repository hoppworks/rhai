## E2E proof: filesystem path and fixture contract repairs

**Entry point**: `cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs` invokes public Rhai scripts through `Engine`, the registered sys package, and the host OS.

**Stack exercised**: Rust integration test → Rhai `Engine` script call → public sys filesystem API → `cap-std` confined roots or `std::fs` unrestricted paths → macOS filesystem.

**Steps performed**:
1. Added the configured-root symlink/parent regression and ran it against old code. It read the lexical sentinel and failed where the expected OS-selected root payload was required; see `configured-root-red.log`.
2. Removed lexical normalization before opening configured roots and ran the regression again. It passed, with independent host read-back of the created file only under the OS-selected directory; see `configured-root-green.log`.
3. Added unrestricted absolute/relative symlink behavior coverage for reads, write-through, copy and link removal, then ran the target test successfully; see `unrestricted-slice-compile-and-pass.log`. Added an additional `symlink/..` sentinel regression and ran it successfully; see `unrestricted-symlink-parent.log`.
4. Temporarily changed the configured-root assertion to the wrong literal. The integration test failed with exit 101; after restoring the expected literal it passed with exit 0. Logs: `false-green-control.log`, `configured-root-correct.log`.
5. Ran the complete configured sys suite before the two final focused regressions; all then-present tests passed. The macOS prefix-alias test exercised both `/var` and `/private/var` spellings, confirming read permission and denied write with host read-back. Added and passed a nested-root alias regression; see `nested-root-alias.log`.
6. Reran `test_non_utf8_file_name` with `--nocapture`. The host filesystem rejected the invalid-byte fixture with `EILSEQ` (macOS error 92), so the test took the explicitly reported unsupported-filesystem skip. This run does not verify public `NotUtf8` behavior; see `nonutf8-nocapture.log`.

**Evidence**:
- Logs: `configured-root-red.log`, `configured-root-green.log`, `unrestricted-slice-compile-and-pass.log`, `unrestricted-symlink-parent.log`, `nested-root-alias.log`, `nonutf8-nocapture.log`, `false-green-control.log`, `configured-root-correct.log`, `full-sys-suite.log`.
- Independent host observations are assertions in `tests/sys_policy.rs::test_configured_root_symlink_then_parent_uses_os_resolution` and `tests/sys_fs.rs::test_unrestricted_symlinks_follow_host_semantics`.

**Reused proof (if any)**: Review repro `../rhai-review-sys-windows/.scratch/review-sys-windows/repro.log` provided known-broken evidence for the original unrestricted symlink reads and configured-root lexical selection; its unchanged behaviors are preserved as public regression assertions. New mutation behavior is verified by the independent host reads in this run.

**Independent read-back**: `std::fs::read` confirmed the configured-root write existed under `real/allowed` and not the lexical sentinel directory; it confirmed unrestricted writes affected the symlink target, copy created the expected independent file, removal deleted the link while preserving its target, and the alias test's denied write left its payload intact.

**False-green check**: The configured-root payload assertion was changed temporarily to `wrong expected value` and failed (exit 101); the correct assertion was restored and passed (exit 0). The earlier pre-fix failure also showed the accepted contract catches the original lexical redirection.

**Data reset**: Each integration test owns a unique `TempDir`; its guard removes only that fixture. `run_scoped.py` supplied a private temporary source/build/Cargo home and cleaned the runtime at command exit. No shared service, parent test environment, other worktree or remote was modified.

**Verified**: macOS configured root preserves symlink/parent OS resolution; unrestricted absolute and sibling-relative symlinks and symlink/parent paths follow host behavior for tested operations; `/var` and `/private/var` aliases preserve both single-root and nested-root permissions; configured sys tests preserve confined relative/absolute symlink denial and other existing sys contracts. The unsupported-name guard skips only raw `EILSEQ` codes 84 or 92 and fails for other fixture creation errors.

**Unverified**: The public `read_dir` → `NotUtf8` behavior could not run on this host because its filesystem rejected creation of the required fixture (EILSEQ 92). Windows and other OS behavior, other filesystem variants, and the separately tracked release OS/feature/MSRV matrix also remain unverified.
