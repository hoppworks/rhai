# X30 Linux unchecked profile evidence

Status: execution evidence assembled; combined independent review pending.

## Binding

- Fork-main source: `202d01a8c260ed7547ba505ee701851d85282641`.
- The owned source copy came from `git archive` of that commit. The original `tests/sys_process.rs` SHA-256 is `3758585e5038f70a01f22bb6cafaa12794375bc6ee42de64930991ccbc49cb08`, matching `git show HEAD:tests/sys_process.rs`.
- `Cargo.toml` SHA-256 is `62fc31d2eaf0d74aa9f631032606ded135ab910bbaf0ac09493427b975d47c81`. `Cargo.lock` SHA-256 is `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`, copied from the accepted current-source release input at `windows-rhai-native-20261028/release-msrv-20261028/media-input/Cargo.lock`; that input records the same manifest hash.
- Host: Bazzite 44.20260825.0, Linux x86_64, kernel `7.2.0-ogc6.1.fc44.x86_64`; Rust/Cargo 1.77.2.
- Features: `testing-environ,sys,unchecked`.
- Test: `tests/sys_process.rs::repeated_public_run_calls_keep_fd_count_stable`, which starts the ignored census in a fresh process and exercises the public Rhai Engine API against `/bin/true`.

## Assertion sensitivity and restored result

Both invocations used the same exact command:

```text
cargo test --locked --features testing-environ,sys,unchecked --test sys_process repeated_public_run_calls_keep_fd_count_stable -- --exact --nocapture --test-threads=1
```

The temporary source-copy mutant changed only the expected descriptor count from `baseline.1` to `baseline.1 + 1`. The mutant exited 101 at the intended assertion: actual `left: 6`, expected `right: 7`, with the descriptor-count assertion message. The source copy was restored byte-for-byte from its saved original before GREEN.

Restored GREEN exited 0. The exact isolated census test passed, and the outer test summary reports one passed test. Its readback marker records 200 sequential public `run("/bin/true")` calls, tasks `3 -> 3`, FDs `4 -> 4`, and cleanup workers `1 -> 1`. This closes only the X30 Linux x86_64, Rust/Cargo 1.77.2, unchecked profile slice if the combined review accepts applicability.

## Execution custody and parser history

The run used the existing `tools/run_scoped.py` with a unique session `TMPDIR`, an owned source archive, `CARGO_TARGET_DIR` and `CARGO_HOME` below `AGENT_RUNTIME_DIR`, and two Cargo jobs. One invocation contained the assertion control and restored GREEN. It ran from 2026-10-29T22:59:13Z to 23:00:01Z. The scoped runner removed its private runtime. The owned scope was verified empty and removed with `rmdir`; no Cargo/rustc/test process remains. Raw outputs and the standalone evidence evaluator are in this directory.

The outer runner returned 1 only after both Cargo invocations succeeded/failed as intended: the run script required the outer harness name and `ok` on one line, but `--nocapture` interleaves the successful inner-test output before the outer `ok`. The logs contain the exact inner isolated-test `ok`, its one-passed summary, and the 200-call marker. A first evaluator summary also reused its match variable; `evaluation-history.txt` records both reporting errors. `evaluation.txt` is corrected against the raw logs. No test or build was repeated to correct either parser/reporting error.

## Limits

This does not close X30 on macOS or Windows, another Rust/MSRV row, any other feature profile, or the full release matrix. It does not certify Windows handle stability. No product or test source was changed in the repository by this run; mutation and restoration occurred only in the private source copy.
