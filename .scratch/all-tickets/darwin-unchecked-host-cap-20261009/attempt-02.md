# Darwin unchecked host output-cap proof

## Scope

This attempt addresses only the native Darwin X21 host-cap row for
`process_script_output_option_cannot_raise_the_host_cap` with
`testing-environ,sys,unchecked`. The test runs the real Rhai Engine and sys host
package, asks the script to raise `max_output` to twice the configured 4096-byte
host cap, and launches a real self-exec child separately for stdout and stderr.
Before asserting the retained output prefix, the test reads the child's independent
record and proves the child was reaped. The expected prefix is exactly 4096 bytes;
stdout includes the libtest prefix and stderr contains the `e` payload.

## Bound run

- Host: `Daniels-MBP-2.fritz.box`, Darwin arm64, macOS 27.0.1 / kernel 27.0.0.
- Rust/Cargo: 1.77.2; features: `testing-environ,sys,unchecked`.
- Test source: `attempt-02.sys_process.rs`, SHA-256
  `a47197f8a2dd7cbdd59a4f1627715721129b62553c0adabc7a847b933f0c012a`.
- Lock: scoped `attempt-02.Cargo.lock`, SHA-256
  `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Command: `cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process process_script_output_option_cannot_raise_the_host_cap -- --exact --nocapture`.
- Private scoped runner timeout: 600 seconds; Cargo jobs: 2. RED and restored GREEN ran in one invocation/runtime.

## Results and control

The wrong-prefix control replaced the expected prefix with an empty vector. It
failed at the intended equality assertion (RED exit 101), after the child record
and reap checks. The restored current source passed the exact test (GREEN exit 0;
1 passed, 0 failed). Thus the host cap held independently for stdout and stderr
even with `unchecked`; the negative control was assertion-sensitive, not a compile
or fixture failure.

The runner exited 0, exported raw logs/statuses and source/lock copies, and retired
the exact owned scope
`/Users/hoppworks/.local/share/agent-builds/rhai/ticket03-darwin-unchecked-host-cap-20261009T210002Z-retry`.
The evidence file set is verified by `attempt-02.SHA256SUMS`. No compiled cache
was retained. The root checkout has no `Cargo.lock`; the run used the exact
hash-pinned lock copy above.

## Prior preparation failure

Attempt 01 stopped before the selected test ran: the Darwin stdin-only test helper
used `Engine::set_max_string_size`, which is unavailable with `unchecked`. Cargo
exited 101; this was a test-matrix compile/setup failure, not product RED. The
test and its Darwin-only helpers were gated with `not(feature = "unchecked")`;
attempt 02 compiled the corrected source and completed the expected RED/GREEN.

## Review and applicability

Combined independent Standards/Spec review passed with no blocker; details are in
[`attempt-02-review.md`](attempt-02-review.md). This closes only the named Darwin
X21 `testing-environ,sys,unchecked` host-cap row. Other X21
features/platforms/toolchains and Ticket 03/A–F remain open.
