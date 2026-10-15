# X34 managed Child.kill Linux sync-profile proof (2026-10-15)

This proof covers only `managed_child_kill_reports_group_closed_under_fixture_reaper`
on Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, at source revision
`eee64f0f832f673ed60ae01ebf4ecca75d2a75fd`. It has two exact feature rows:
checked `testing-environ,sys,sync` and `testing-environ,sys,sync,unchecked`.

One scoped `run_scoped.py --timeout 1200` invocation used the absent owned
session `/root/.local/share/agent-builds/rhai/linux-x34-kill-sync-20261015`,
absolute `TMPDIR`, one Cargo job, and private source/Cargo home/target under
the runner's runtime. Each exact test had a 300-second bound. Capacity at
preflight (2026-10-15 10:21 UTC) was 95 GiB available RAM and 671 GiB free disk;
no other Cargo/rustc process was active. The run exited 0. The runner removed
its private runtime, and the exact empty session scope was removed after export.
The preexisting `/home/Daniel/.rustup` Rust 1.77.2 toolchain was used.

For each profile, RED inverted only the public `killed_report` assertion and
returned 101 at the marked assertion after lifecycle observations and cleanup.
Restored GREEN returned 0 with one test passed. Each pair records exact
leader/worker/leaf PIDFD exit, group ESRCH, worker/leaf waits by the fixture
reaper, an unsuccessful public child report with complete stdout/stderr,
host/reaper/unrelated sentinel live at API return, and sentinel cleanup after
return. The four raw logs, statuses, source hashes, environment, capacity and
runner status are retained in `attempt-01/evidence/`.

Combined independent review passes for both sync profiles; see `attempt-01/combined-review.md`. These rows do not close other X34
selectors, platforms, Windows Job behavior, X25, or the overall A-F/Ticket03
work.
