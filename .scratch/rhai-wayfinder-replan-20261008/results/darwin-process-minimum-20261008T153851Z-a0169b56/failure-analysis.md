# Package-minimum partial result and precise fixture correction

The first invocation completed the meaningful X20 control (RED101), then 53 exact
GREEN selections across nine admitted rows. Its last integer-width row stopped
at E0308 before any product assertion: the signal test compared Rhai INT=i32 with
`libc::SIGKILL as i64`. This is a test-source feature incompatibility, not evidence
of a process runtime defect. Original JSON compiler diagnostics, command/status
and all prior passed rows remain retained; the outer status1 is not GREEN.

Correct only that assertion to `libc::SIGKILL as rhai::INT`, preserving the same
expected signal. The targeted follow-up compiles/runs only the previously stopped
`sys,net,only_i32,no_float` profile's empty completion and host-cap selectors, plus
the affected public signal/reap selector. No prior baseline or X20 profile rerun.
The accepted default-width signal rows remain applicable because the cast has
identical type/value there. Scope and immutable lock/source bindings are recorded
in i32-correction; independent combined process review precedes closure.
