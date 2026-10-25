# Invocation boundary

One scoped invocation on lllm; outer hard timeout 600 seconds and each Cargo
selector timeout 300 seconds, one Cargo job. These are finite invocation limits,
not a new campaign allowance. Source archive: 2cb6b67a; current coordinator c22011d4
has byte-identical Unix library/test source and Cargo.toml. No product patch.
The three base-unchecked selectors cover before/after setpgid and real fchdir
EBADF; the accepted kernel-denial row is reused. Prior reviewed assertion controls
are reused at unchanged selector/helper/source scope; this run claims only fresh
GREEN behavior for the missing profile.

Preflight: lllm Bazzite44, existing Rust/Cargo1.77.2 direct binaries; available
space 263039468 KiB on the actual source/build filesystem and about 77014 MiB
available RAM, no Cargo/rustc process observed. Additional peak estimate 8 GiB,
not a user cap/reservation; one Cargo job limits demand while swap is nearly full.
No shared process/service is changed. Source, target and Cargo home are private
under the runner runtime; evidence is exported before its cleanup. Exact empty
session scope is retired after the run. Token/cost totals are unavailable.
