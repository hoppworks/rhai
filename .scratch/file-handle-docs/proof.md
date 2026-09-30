# Streaming file documentation and example proof

Work started at **2026-09-30 13:21:01 UTC** with a 30-active-minute limit ending
at **2026-09-30 13:51:01 UTC**, including review. Worktree:
`/Users/hoppworks/projects/rhai-file-handle-docs`, branch `task/file-handle-docs`.

## Result

`examples/sys.rs` registered a real `SysPackage` limited to one unique temporary
directory. A Rhai script opened an existing file in `r+`, sought, wrote `Rhai`,
sought back, and read four bytes. It returned `Rhai`; a separate host read then
asserted the complete contents were `Rhaiting data`. A drop guard removes the
temporary directory, including when an earlier operation returns an error.

## Verification

The final scoped invocation used
`python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 900 -- bash .scratch/file-handle-docs/run-example.sh`.
Inside the runner, a private source copy, `CARGO_HOME`, `CARGO_TARGET_DIR`, and
`TMPDIR` were used, with `CARGO_BUILD_JOBS=2`. The build tree was measured at
723268 KiB at the end of the run; this is the target directory's end size, not a
peak measurement. Peak storage and combined runtime-directory size were not
measured. The runner reported `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-6o4bxcjz`;
that complete runtime path was confirmed absent after completion.

Both commands completed and printed the script result and independent host
read-back:

- `cargo run --example sys --features sys`
- `cargo run --example sys --features sys,no_index`

The wrong-payload control exited 101 at the host-content assertion. Its captured
assertion reports actual `Rhaiting data` versus expected `wrong payload` in
[`wrong-host-payload-control.log`](wrong-host-payload-control.log). The control
was inspected for the expected assertion and both exact values. This proves the
host read-back assertion detects a wrong expectation.

Environment: macOS Darwin arm64; `rustc 1.93.0` and `cargo 1.93.0`. The `no_index`
build emitted an existing `dead_code` warning for `os_to_string` in
`src/packages/sys/fs.rs`; it completed successfully. Minimum-version behavior
and the full native OS/release feature matrix were not verified here. The example
uses one temporary directory and one file per run, sequentially; no environment
mutation, child process, shared file, or network operation was used.

Full command output: [`example-run.log`](example-run.log). Commands:
[`commands.txt`](commands.txt). The completed scoped runner removed its private
source copy, cache, target, and fixture tree.
