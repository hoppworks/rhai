# Linux X25 managed kill sync profiles (2026-10-15)

## Scope

This adds the named public managed spawn → kill → wait selector managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel on lllm Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, integrated source revision 12adebd79b7454384e1d8c1d8a06e30fd6a7393a. Profiles: checked testing-environ,sys,sync and unchecked testing-environ,sys,sync,unchecked. This run establishes these exact Linux rows; it does not claim reuse of another X25 test's behavior.

## Results

One scoped invocation with one Cargo job ran one assertion-sensitivity RED and restored GREEN in each profile. The RED intentionally inverted the assertion that all managed members were gone, exited Cargo 101 at that assertion, and logged the exact leader, worker and leaf absent while the unrelated sentinel remained live and bounded wait returned. Both restored GREEN runs passed 1/1 and asserted exact managed-member absence, non-unit unsuccessful wait result, sentinel survival at the API boundary, then fixture-owned sentinel reaping. Durations: checked sync RED/GREEN 39.311/2.202s; unchecked sync 18.685/2.103s. Outer scoped runner returned 0.

Environment and capacity, all four raw outputs, source receipts, status and result files are retained in attempt-01/. The runner removed its private runtime and the exact session scope was removed after evidence export.

## Review and limits

Independent combined review PASS for exactly these two Linux sync-profile rows; see attempt-01/combined-review.md. No claim extends to other X25 selectors, feature profiles, OS/MSRV rows, Windows, Ticket03 or whole A–F acceptance.
