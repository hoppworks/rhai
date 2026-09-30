# Environment fixture isolation proof

## Change

Environment integration tests now relaunch their exact Rust test name with
`current_exe`, a cleared child environment, and explicit fixture variables.
The parent asserts child success and returns without evaluating the Rhai
assertions. The child executes the preserved public `Engine`/script assertions.
The shared helper bounds fixture execution to 30 seconds and kills/reaps a
timed-out child. Non-UTF-8 values are configured only on Unix.

No test changes the parent process environment or working directory. The
fixture environment includes only the fixture marker and explicitly supplied
variables; absent variables remain absent.

## Environment

- OS: macOS 27.0, arm64
- Rust: `rustc 1.93.0 (254b59607 2026-01-19)`
- Cargo output and cache were under `AGENT_RUNTIME_DIR` using `run_scoped.py`.
- Build source was copied into the private runtime. The runner cleaned the
  source copy, target directory and Cargo home after every invocation.

## Results

- `cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs --no-run` — passed.
- `cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs` — all 7 `sys_env` tests passed. The pre-existing `sys_fs::test_non_utf8_file_name` failed on this macOS host with `Illegal byte sequence`; Cargo did not proceed to the policy executable in this invocation.
- `cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env` — all 7 `sys_env` tests passed. `sys_policy::test_env_allow_list` passed as part of the suite; the suite's unrelated `test_symlinked_root` failed, leaving 22 of 23 policy tests passing.
- False-green control: temporarily changed the expected `env_var("RHAI_SYS_TEST_E1")` value to `deliberately-wrong`; the exact test failed, reporting actual `value` versus expected `deliberately-wrong`. Restored the assertion and reran the same exact test; it passed.
- `git diff --check` — passed.

Detailed captured output is in `verification-relevant.log` and
`false-green-run.log` in this directory. The wrong-expectation output is also
retained in `false-green.log`.

## Limits

The environment fixtures and non-UTF-8 case were exercised on macOS arm64.
Windows behavior and the full sys suite on other operating systems were not
verified. The two unrelated macOS failures above remain unresolved and were
not changed by this task.
