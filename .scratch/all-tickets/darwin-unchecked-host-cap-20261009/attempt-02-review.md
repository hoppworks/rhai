# Combined independent review — Darwin X21 unchecked host cap

**Result: PASS.** Review covered the current test-source change, attempt 02
evidence and X21 applicability. No Standards or Spec blocker was found.

The evidence binds Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2,
`testing-environ,sys,unchecked`, source SHA-256
`a47197f8a2dd7cbdd59a4f1627715721129b62553c0adabc7a847b933f0c012a`, and
lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
Checksums verify. The wrong-prefix control fails at the intended equality
assertion; restored GREEN passes. Both stdout and stderr independently read the
child record and verify reaping before checking the exact 4096-byte prefix. The
script requests twice the host cap, and the host bound remains effective under
`unchecked`.

The Darwin-only `not(feature = "unchecked")` gates cover the stdin test and
helpers that use `Engine::set_max_string_size`; the host-cap test remains
enabled. This is partial acceptance for the named Darwin X21 unchecked host-cap
case only. Other X21 paths/features/platforms/toolchains and Ticket 03 remain
open. The reviewer reread current agent-skills revision
`1b6e1da85f87cad25f7aafc91aa782319ac6ef93`, common AGENTS SHA
`f71e8f97…feec8`, and project AGENTS SHA `37f95ff6…bba37c` before review.
