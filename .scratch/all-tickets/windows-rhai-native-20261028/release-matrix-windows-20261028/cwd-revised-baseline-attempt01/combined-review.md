# Independent readback of revised Windows cwd REDs

The original observer correctly reports `accepted=false`: its root-log check
requires the underlying Denied message even though that test prints only the
`ErrorRuntime` payload type. Do not alter the original observer or interpret
its `baseline_reproduced=false` and `product_test_run=false` flags as success.

The independently inspected original command output reports compilation exit
0 and each of three Cargo test exits 101. Each original log shows exactly one
failed test. The direct-run baseline prints typed `Denied("unsupported Windows
process option `cwd`")`. The root test first successfully renames an unpinned
sibling, then records Windows sharing violation 32 when renaming the configured
root, and subsequently fails with an `ErrorRuntime` carrying `SysError`. The
exact Denied text is not present in that root log; the cause is inferred from
the same frozen source, selector and baseline rather than observed in that log.

The denial test records an outside request with `Denied` and no child marker,
with Job totals 2 before and after. Its missing-directory assertion then fails
because it receives unsupported-option Denied instead of NotFound. The positive
Job-count calibration is not reached: the observed equality is not accepted as
a complete no-child-start proof.

Driver exit 0, closed process custody and removed runtime are reported by the
original Driver and observer. The original journal has eight valid framed
records through `REMOVED`; all 17 exported originals were independently read
back. No extra native execution is necessary to establish these observations.
They cover only the reached DirectChild cases, no GREEN, Managed, spawn, Reparse
resistance or final cwd acceptance.
