# X24 Darwin `testing-environ,sys,unchecked` — Rust/Cargo 1.77.2

Accepted scope is limited to
`tests/sys_process.rs::direct_spawn_try_wait_returns_unit_until_child_exits`
through the public Rhai Engine and `spawn` API on Darwin arm64/macOS 27.0.1
(kernel Darwin 27.0.0), Rust/Cargo 1.77.2.

The RED source copy changed only the final cached-`wait()` expected exit code
from 0 to 7. The real child was observed alive while pending `try_wait()`
returned unit; terminal `try_wait()` observed exit code 0 before `wait()`. The
mutated assertion then failed with `left: 0`, `right: 7`. Cargo exit was 101.
RED log SHA-256:
`690cec2917e31a1afb88eb68b9d0cba13d90becd09acb70b5fe55f3faffb03f4`.

Restored GREEN passed the exact test 1/1 (46 filtered), Cargo exit 0. It
independently logged the live child and pending unit, terminal `try_wait`
before `wait`, cached exit 0 and exact PID `ESRCH` after reaping. GREEN log
SHA-256: `c3b4a3624f116790b760849b7fc8b88347cf298f9deab3ffa22d143bcaaab448`.
Environment readback records the OS, feature toolchain and versions;
environment SHA-256:
`df1015aa9651854a852c55b78dc93c923d5b9005d413381f2943a5c19d8f8e6c`.

Both source identities bind lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` and
unchanged Unix process source SHA-256
`7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`. The
test-file hashes differ only because the RED contains the one expected-value
mutation; restored GREEN test-file SHA is the current committed
`a8fdc21e73b56bf12c82603c941b7c22b01c942a56d5f649ff2ec98b494c935c`.

RED and GREEN shared one scoped Cargo invocation. The exact owned session scope
`ticket03-x24-darwin-unchecked-20261009T231500Z` was retired and read back
absent; the runner removed its private runtime. No cache was retained. The
combined independent review is pending. This accepts no other X24 profile,
OS/MSRV row or Ticket 03/A–F requirement.
