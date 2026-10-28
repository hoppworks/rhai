# Native Windows direct-child timeout and pipe completion

Attempt19 used 439 source files (manifest SHA-256
`b8599b404e97b635cdd399d06213e038cf11493ac583781639e7dd2fa60c575c`,
archive `763db52705e6252d8e9dec8c4ec2db578af4d160dec89bfba6681475150a33b1`),
candidate lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`
and the previously accepted public runner/driver build. Native Cargo/Rust
1.93.0 ran `testing-environ,sys,metadata` on the Rhai Windows guest.

The public Engine `run_raw` test started a real child, observed its child-written
PID, opened the exact process handle while it was alive, and independently
observed its termination and exit code 1 after the five-second deadline.
The restored assertion verified a typed `Timeout`, `timed_out=true`, the
expected retained stdout prefix, a report exit code matching the exact handle,
and no cleanup diagnostics. The deliberately wrong `timed_out=false`
expectation failed at its named assertion with exit 101. The GREEN log also
prints capture-completion flags, but this test does not assert their values.
The full `sys_process_report` and `sys_process_windows` targets passed 7 + 8
tests. Six Windows unit tests passed, including native pipe cancellation after
aborted pending I/O, an already completed byte read, and pipe closure. A gated
real-pipe helper test also passed after its deliberately wrong overlap
expectation failed; it proves helper-level overflow precedence when a ready
read and expired deadline are observed together, not the entire public
supervisor overlap contract.

The bounded Driver exited 0 in 109.507 seconds, with exact exit, drained and
disposed pipes, no pending custody, stopped owned executables and the exact
runtime removed. Original COM1 bytes are 362,407 bytes, SHA-256
`60674d96a7d58069c0524391843920dfa244a411200d13c8d6d6622cae7eab7f`.
All 215 frames were ordered and all 15 original files passed length/SHA-256
readback. Independent checks validated the lengths and CRC32s of all eight
journal records through `REMOVED`. The exact host stage and ISO were retired
after original export, hash checks, all-domain reference checks and restoration
of the original sdc. The outer guest scope remains pending exact retirement.

The current test source differs from the native archive only by a conditional
attribute on the existing `set_max_array_size` call. The independent reviewer
verified that the native standard profile executes that statement identically;
the attempt19 proof remains applicable to it. Windows-target Rust 1.77.2
cross-checks passed for standard, `no_index`, and, after adding that attribute,
`unchecked` profiles; these establish compilation only. The first unchecked
cross-check failed because that Engine API is unavailable under `unchecked`,
and its original log is retained in `../../windows-timeout-20261028/`.

Combined independent review is in [combined-review.md](combined-review.md).
This accepts only the named native direct-child `run_raw` timeout slice and
the listed helper tests at the stated source/profile. Managed Jobs, public
same-step overflow/deadline behavior, cancellation failures, retained-custody
faults, other overloads/features/toolchains, Ticket03 and release remain open.
Attempt18 established the false timeout flag and exact child exit but did not
print its cleanup diagnostics; its precise original cause remains unknown.
The code corrections address independently identified EOF and completed-read
handling defects and preserve already committed primary causes.
