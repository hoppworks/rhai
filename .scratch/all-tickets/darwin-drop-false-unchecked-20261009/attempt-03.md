# Darwin X28 `kill_on_drop(false)` under `unchecked`

## Acceptance result

The exact public-Engine test
`direct_spawn_kill_on_drop_false_preserves_child_and_capture` passed on native
Darwin arm64/macOS 27.0.1 (kernel 27.0.0), Rust/Cargo 1.77.2, with
`testing-environ,sys,unchecked`. The script started a real child with
`kill_on_drop(false)`. After dropping both the Rhai `Child` handle and `Engine`,
the test observed the exact child still alive and a challenge ACK in the
independent fixture file. After releasing it, the child wrote an independent
completion record for 524288 bytes on each captured stream; the retained owner
drained both and reaped the exact PID (`ESRCH`). Fixture cleanup also confirmed
the exact PID absent.

## Input identity and commands

- Integrated base revision: `d32f4563677c09631715fe1b76a646604e770e3d`.
- Test-source SHA-256: `a47197f8a2dd7cbdd59a4f1627715721129b62553c0adabc7a847b933f0c012a`.
- Cargo.lock SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Command: `cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process direct_spawn_kill_on_drop_false_preserves_child_and_capture -- --exact --nocapture --test-threads=1`.
- The GREEN run compiled in 12.37 seconds and the test took 0.44 seconds. No build cache was retained.

## Assertion control and harness history

Attempt 02 inverted only the live-child expectation. RED status 101 reached that
assertion after reporting `alive=true`, `challenge_ack=true`, and
`completion_exists=false`; the fixture's panic cleanup then recorded exact-PID
`ESRCH`. The runner status was 1 only because its post-test parser expected a
Rust assertion-expression string that the custom `assert!` message replaces.
Attempt 03 reused that valid RED after matching base revision, test source,
lock, feature profile and host; the unmodified test source was byte-identical.
Cargo GREEN status was 0 and its raw output says `test result: ok. 1 passed; 0
failed`, followed by both-stream byte counts and ESRCH. The runner status was
again 1 only because `--nocapture` interleaved test diagnostics with the
single-line test-name marker; the authoritative Cargo result and behavioral
readbacks were complete. No product assertion failed and no additional test run
is needed.

Attempt 01 was a pre-test invocation-context failure: Cargo ran from the project
checkout rather than the archived source copy and rejected its lock context. No
test ran. Each attempt's exact private scope/runtime was retired after export;
no source checkout, cache, child or fixture was retained.

Raw commands, statuses, checksums, source, lock and logs are in `attempt-01/`,
`attempt-02/`, and `attempt-03/`. Review status is recorded separately.
Acceptance is partial: this adds only the named Darwin X28 unchecked feature
row, not all of X28, Ticket 03, or A–F.
