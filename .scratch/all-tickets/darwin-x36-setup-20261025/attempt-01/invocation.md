# Darwin X36 invocation boundary

One owned scoped invocation, outer hard timeout 600 seconds, two Cargo jobs.
Four native assertion-only RED controls run in the base profile; restored source
then runs four named selectors across checked/unchecked base and sync profiles.
Only isolated runtime source is mutated. The four wrong marker expectations
occur after public run setup failure, no marker execution and helper cleanup.
Classify expected RED as successful controls, never as product defects/retries.

Use archive 7638f2684ff2f06bb7587359eeb8c82e9c86a360, the unchanged canonical
optional-package lock and existing Rust/Cargo1.77.2. No product/test changes are
applied to the worktree. Native Darwin arm64/macOS27.0.1 is newly covered at
this compiler; retain the accepted Rust1.93 kernel-denial baseline.

Preflight measured 252099596 KiB available on the actual output filesystem,
83% system memory free on 32GiB, 10 logical CPUs. A previously observed rustc
process had ended at exact-PID readback; no foreign process was interrupted.
Estimated additional peak 8GiB is a planning estimate, not a reservation or user
cap. Scripts, original receipts and accepted proof remain outside the runtime.
Source/target/private Cargo home and temporary fixtures stay inside it. Export
each status/log immediately; export all proof before runner cleanup. Independent
post-run readback checks recorded PIDs/groups with signal zero (ESRCH only), then
retires only the exact owned empty session scope with rmdir. No build is retained.

No claim of full X36, Windows custody, Ticket03 or A–F completion follows from
these sixteen profile rows. Existing cumulative histories remain in the canonical
coordinator history. Token/cost totals are unavailable.
