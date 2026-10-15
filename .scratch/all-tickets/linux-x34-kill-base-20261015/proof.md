# X34 managed Child.kill Linux base-profile proof (2026-10-15)

This proof is limited to `managed_child_kill_reports_group_closed_under_fixture_reaper`
on Linux x86_64/Bazzite 44 with Rust/Cargo 1.77.2, Cargo default checked
profile and `testing-environ,sys` at fork-main source revision
`fc441c5115302d277c62ff653f9a242700146fce`.

One `run_scoped.py --timeout 900` invocation used the exact owned session scope
`/root/.local/share/agent-builds/rhai/linux-x34-kill-base-20261015`, absolute
`TMPDIR`, one Cargo job, and source/Cargo home/target below its private runtime.
Each exact test invocation had a 300-second bound. Before launch, observed
capacity was 95 GiB available RAM and 671 GiB free disk; a one-job foreign
Tauron Cargo build was active and preserved. The run completed with runner status
0; the exact runtime and empty owned session scope were removed after evidence
export. The preexisting `/home/Daniel/.rustup` 1.77.2 toolchain was used.

The RED source inverted only the public `killed_report` assertion. The named test
returned 101 at that marked assertion after independent process observations and
fixture cleanup. Restored GREEN returned 0 with 1 test passed. Both boundaries
record exact leader, worker and leaf identities and PIDFD exit; group `ESRCH`;
worker/leaf waits by the fixture reaper; unsuccessful public child report with
complete stdout/stderr captures; host, reaper and unrelated sentinel alive at API
return; and sentinel cleanup afterward. The logs include full API and cleanup
records. `statuses.txt`, source hashes, environment, runner status and raw logs
are retained in `attempt-01/evidence/`.

The combined independent review passes for this selector in checked and unchecked profiles; see `attempt-01/combined-review.md`. This row does not close other X34 selectors,
feature profiles, platforms, Windows Job behavior, X25, or the overall A-F and
Ticket03 work.
