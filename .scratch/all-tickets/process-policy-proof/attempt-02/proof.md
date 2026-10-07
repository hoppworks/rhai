# P2/P10 public Engine process-policy proof

This evidence covers one Linux x86_64 slice of P2 and P10. It does not close the
strict native OS, MSRV, or required feature matrix.

## Tested behavior

The test `default_and_nonmatching_process_policies_deny_public_run_without_starting_child`
uses the public Rhai `Engine` and `run` API. The default process policy and a
nonmatching exact allow-list each return `SysError::Denied`; distinct child marker
files remain absent after each call. The exact allow-list control runs the current
test executable as a real child. The test reads its PID and exit record, then
checks `kill(pid, 0)` fails with `ESRCH`, showing the direct child has been reaped.
The marker is a real child-written read-back; by itself it cannot detect a child
that might be spawned and killed before fixture code starts. The Unix `run`
implementation checks `ProgramPolicy` and returns `Denied` before child creation
(`src/packages/sys/process/unix.rs`, around line 2241); native OS/MSRV/feature
coverage remains open.

## Test-first and restored result

Command:

```text
cargo test --locked --features testing-environ,sys --test sys_process default_and_nonmatching_process_policies_deny_public_run_without_starting_child -- --exact --nocapture --test-threads=1
```

The isolated broken-default control changed only the staged test copy's default
Engine configuration to allow the current test executable. It failed at the
expected `sys_err` assertion (exit 101), confirming the test detects a default
policy that permits the child. Restoring the reviewed source passed the same
target: `1 passed; 0 failed`. The captured output reports both denied marker paths
absent and child PID `1680620`, exit code 0; the in-test read-back independently
confirmed that PID was absent (`ESRCH`).

Attempt 01 stopped before assertions because the new test compared the
`Result<bool, _>` returned by `Dynamic::as_bool()` with `Some(true)`. That compile
failure and its raw outputs are preserved in `../attempt-01/`. Attempt 02 changes
the assertion to compare with `Ok(true)`. The first stop was a source compile
correction, not product behavior or a failed test assertion.

## Inputs and environment

- Source base: commit `1f8205277f411ab91b50ca1962bbf0f053790f72`.
- Tested `tests/sys_process.rs` SHA-256: `60182121c6bec272e198a791f85f7a3ac5b799d23c2bb347314d945e563ed401`.
- Staged source archive SHA-256: `d4a1378c68ba17eb9e716f0b20d5a912aa64e753404fabd78548fe0fd73707a0`.
- Pinned `Cargo.lock` is preserved as `Cargo.lock.accepted`, SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, from accepted Package A attempt 05; Cargo manifests were unchanged since that proof.
- Workhorse: Linux `7.2.7-ogc1.1.fc44.x86_64`, Rust `1.96.0`, Cargo `1.96.0`.
- The scoped runner was Workhorse `tools/run_scoped.py`, SHA-256 `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.
- Agent Skills revision: `14617043b70d1ba2d40b720832cbad294fa8c008`; exact rule hashes and point-in-time resource admission are recorded in `remote-preflight.json`.
- Raw RED/GREEN output and exit files, Cargo metadata, source hash, command, tool-version captures, and the exact test launcher/preflight helper are in this directory.

The runner removed its private build runtime. After output hashes were read back
and no Cargo, rustc, or scoped runner process remained, the owned Workhorse
session scope was removed. No compiled artifact is retained or reusable.
