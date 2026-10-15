# Combined independent review — Linux X38 unchecked

**Decision: Standards PASS; ACCEPT the two named Linux unchecked rows only.**

The evidence binds the restored test source (SHA-256
ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf), Unix
product source (7abd009f…) and lockfile (2ba4b3a0…) to the current
integrated source. Both selectors are byte-identical to the accepted Linux
base-profile tests. The intervening stdin-pump code is not exercised by them.

Attempt 02 contains the intended assertion REDs and X38 restored GREEN.
Attempt 04 contains post-reap Cargo status 0 and the passing test with leader,
holder, sentinel, capture-writer and cleanup observations. The recorded scope
and runtime are absent. Attempt 01 was a compile stop; attempt 03 was a PATH
failure before Cargo.

The outer run_scoped.py status 127 for attempt 04 remains unexplained and
must not be described as a successful runner invocation. It does not invalidate
the separately evidenced Cargo result and lifecycle/readback for these named
rows. No wider X38, feature, toolchain or OS acceptance follows.
