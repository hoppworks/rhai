# Current-source standalone Sys package gate on macOS and Linux

Status: accepted after one independent combined Standards/Spec review. This proof covers the five named integration targets under `testing-environ,sys` on each POSIX host. It does not close the remaining feature, Windows process, SDK or release criteria.

## Input binding and commands

Both runs used the 448-file source archive SHA-256 `6ff82b95cbbf65ba919161932a63d74f668f8e6e6d88682418797eca93565384`, manifest `b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd`, and exact lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`. [macOS preflight](macos-sys-alone-attempt01/preflight.json) compared every archived source file byte-for-byte with fork-main `669c10a783481845e9e4aa407574c4838a75ef42`; Linux used those same exported inputs and its own [preflight](linux-sys-alone-attempt01/preflight.json). Neither run changed product or test source. The working tree has no `Cargo.lock`, so both used the prior accepted generated lock copied into the private source.

On macOS 27.2 arm64 and Workhorse Linux 7.2.11 x86_64, the scoped runner compiled `sys_policy`, `sys_env`, `sys_fs`, `sys_process`, and `sys_process_report` with Rust/Cargo 1.77.2 using `cargo +1.77.2 test --locked --features testing-environ,sys` and explicit `--test` selectors. Each run then executed the exact `sys_fs::test_open_file_default_preserves_contents_and_shares_cursor` with `RHAI_FILE_HANDLE_WRONG_EXPECTATION=1`: public Rhai Engine file operations changed an owned real file; a fresh host readback was `original XYyload`, and the deliberate `wrong expectation` assertion failed with exit 101. Restoring the environment yielded exit 0 for each of the five entire targets; compile, RED and GREEN used the same `sys_fs` executable within each host's private build. [macOS commands](macos-sys-alone-attempt01/commands.json), [Linux commands](linux-sys-alone-attempt01/commands.json), [test source](../../../tests/sys_fs.rs).

| Host | `sys_policy` | `sys_env` | `sys_fs` | `sys_process` | `sys_process_report` | Total |
|---|---:|---:|---:|---:|---:|---:|
| macOS | 26 | 7 | 34 | 52 passed, 1 ignored | 7 | 126 passed |
| Linux | 24 | 7 | 35 | 61 passed, 3 ignored | 7 | 134 passed |

## Original results and cleanup

The macOS Cargo commands all returned the expected exits and summaries. Its outer helper exited 1 **after** GREEN because it required the file-handle test name and `ok` on one line, while `--nocapture` printed the independent host readback between them. [Original log](macos-sys-alone-attempt01/green-sys_fs.log) shows the test name, readback, `ok`, and target summary in order. [Independent replay](macos-sys-alone-attempt01/readback.json) verifies the exact stored command exits, RED left/right bytes, all five original GREEN summaries and executable identity; the runner retired its exact own scope. No rerun was needed for the parser defect.

The Linux outer runner returned 0. [Original result](linux-sys-alone-attempt01/result.json) and [independent readback](linux-sys-alone-attempt01/readback.json) confirm RED101, all five GREEN0s, full target summaries, same executable and 19 hash-verified exported originals. The Linux readback selected unfiltered target summaries (`0 filtered out`) to avoid mistaking child-controller subtest output for the outer target. Its exact stage and scope were retired after export; [host readback](linux-sys-alone-attempt01/cleanup-readback.txt) confirms both absent. macOS build/test commands used 28.281 seconds in total; Linux used 43.430 seconds. The private compilation and fixture roots were not retained.

The [combined review](posix-sys-alone-review.md) found no actionable issue. It checked original Cargo outcomes separately from the macOS post-test helper status and selected Linux's unfiltered outer process summary rather than its child-controller summaries. The executable paths were recorded, but executable hashes were not retained. The ignored process cases remain ignored. This proof establishes the named standalone Sys package target suites only; it does not imply every P/E/F/X or release-matrix criterion is complete.
