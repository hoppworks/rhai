# Revision binding

The isolated source copy was created from fork-main revision
`fc441c5115302d277c62ff653f9a242700146fce`. The base checked profile used
`testing-environ,sys` plus Cargo defaults, lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, current
`src/packages/sys/process/unix.rs` SHA-256
`2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`, and
restored `tests/sys_process.rs` SHA-256
`9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe`.
RED differs only by the deliberate inversion of the public `killed_report`
assertion. Its source hashes are retained in `attempt-01/evidence/`.

Historical Linux base-profile evidence in
`../linux-managed-deadline105-evidence/` independently ran this exact named
test and observed GREEN under the same lock. The archived test function and the
relevant `terminate_managed_child`, `close_managed_group`, and
`request_managed_close` implementations match current source byte-for-byte.
The current-source RED/GREEN pair below now supplies the assertion control and
full readback for the base profile itself; the historical result is corroborative.
