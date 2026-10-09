# X24 Darwin `testing-environ,sys` — Rust/Cargo 1.77.2

Accepted scope: `direct_spawn_try_wait_returns_unit_until_child_exits` through
the public Rhai `Engine`/`spawn` API on native Darwin arm64. The restored GREEN
is from the full `sys_process` target at source commit
`8da9a8750e38709551a6db31736cc869a60fc3f5`, with `testing-environ,sys`, Rust
and Cargo 1.77.2, and lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. It passed
48, failed 0, ignored 1. Its recorded `uname` is Darwin arm64/kernel 27.0.0;
the GREEN metadata did not capture macOS `ProductVersion`, so this record does
not claim that exact OS product-version value for GREEN.

## Assertion sensitivity and GREEN observations

The fresh RED used an owned source copy, the same lock and Unix product source,
and changed only the final cached-`wait()` expected exit code from 0 to 7. The
intended assertion failed (`left: 0`, `right: 7`), Cargo status 101, scoped
runner status 0. The RED environment recorded Darwin arm64, kernel 27.0.0,
macOS 27.0.1, and Rust/Cargo 1.77.2. RED output SHA-256:
`352352bfd6aab3c3565856ef26ceb7588e6372412905c565d4e9d6d2f0d122c8`.

The GREEN log records the real child alive before `try_wait()`, unit returned
while it remained alive, terminal exit code 0 observed by `try_wait()` before
any `wait()`, cached `wait()` exit code 0, and exact-PID `ESRCH` after reaping.
GREEN log SHA-256:
`11ca29f2e1fd4f9865f6c78f88b3fd9b6a42042aa678ddcdd10383e867ccb698`; status
0. Run metadata SHA-256:
`d2599c8ac0aa43e394dae4df40b4e763b90ff70bec956bbbf3b39234f0421c85`.

RED and GREEN bind the same lock and product source
`7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`. The
entire test file changed after GREEN (`a8fdc21e…` current), but the exact X24
function remains byte-identical (SHA-256
`8496b362f16e9369567076bf3cc1b3886d3319ee058c28e56835534b55c5f9cd`). The
added Darwin stdin fixture branch requires `RHAI_SYS_PROCESS_CLOSE_STDIN_DARWIN`;
X24 launches with `env_clear: true`, does not set that variable, and sets the
separate resource-hold/release variables. The combined reviewer confirmed this
change is unreachable on the X24 path. Review was corrected to acknowledge the
whole-file hash mismatch and limits the claim to this test and profile.

## Evidence and limits

- RED: `attempt-02/red.log`, `.status`, `environment.txt`, and `source-sha256.txt`.
- GREEN: `../writezero-unit-20261009T2025Z/darwin-followup/sys-process.log`,
  `.status`, `run-info.txt`, and `sys-process.sha256`.
- Attempt 01 was preparation-only (missing evidence parent, then an incorrect
  executable-bit assumption for the Python-invoked runner); it ran no test.
- The exact attempt-02 owned session scope and private runtime were retired;
  no compiled cache is retained.

This accepts only X24 on the named Darwin native profile. It does not close
other X24 feature/OS/MSRV rows, Ticket 03, Package B/C, or A–F. The older 1.93
RED with lock `4ff0…` was not used in this pairing.
