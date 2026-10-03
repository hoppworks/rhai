# Linux managed deadline with escaped capture pipes proof

Native109 completed at immutable source
523608648dcae99bc0f6b46eaf2bb91fa4ecc752 with reviewed frozen recipes
19764c1f57116350352a942e0f826ddb3c857889. Independent combined actual acceptance review ACCEPTED this named criterion. Test SHA-256:
5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb.
Source archive:998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b.
Native Linux7.2.7 x86_64, private Rust/Cargo1.77.2 and accepted lock2ba4b3a0.

## Real entry point and observed effect

The integration test
`managed_run_deadline_cancels_escaped_pipe_holder_under_fixture_reaper`
executes a real Rhai script through public Engine and host managed run. A
fixture-owned escaped holder keeps both capture pipes open outside the managed
leader group. At API return, the typed timeout report retains both markers,
honestly incomplete captures and timed_out=true. Exact original PID/start/group,
PIDFD and reaper receipts distinguish API cancellation from fixture cleanup.
The managed group is absent and leader reaped; holder, host, reaper and unrelated
sentinel are live. Independent post-return writes receive EPIPE on both endpoints,
proving the capture readers closed without killing the escaped holder. Exact
release/reaper wait and sentinel cleanup occur before every outcome assertion.
Watchdog fallback is rejected, rather than counted as API cleanup.

One deliberately wrong timeout assertion fails101 at its named assertion after
full fixture cleanup. Exact source restoration precedes four new-test GREEN
rows: testing-environ,sys; plus sync,metadata; plus f32_float; plus unchecked.
Prompt success, held zombies and explicit kill with escaped capture pipes also
pass. Three private toolchain setup commands pass: eleven commands total, one
intended sensitivity RED and seven GREEN tests.

## Original evidence and independent retirement

[Original evidence](linux-managed-escaped-pipe109-evidence/) preserves actual
stdout/stderr/status, commands, source restoration, seven original closure files
and process custody receipts. Root independently rehashed71 original files/five
subdirectories against the fresh remote inventory and custody manifest.
Readback records199 helper/command identity rows and two launcher PID/start rows
absent. Seven original closures are compared to fresh observations, never repaired.
The old retained-pipe regression emits no original start ticks or closure file:
its three exact receipt PIDs must be NotFound (existing/reused PID or observation
error rejects) and both groups empty. No start ticks or closure are fabricated.

Collector collect0/cleanup0. Hash-gated exact retirement removes71files/fivedirs;
fresh remote-cleanup.json confirms stage/scope absence and empty groups1713581,
1713653,1720249,1720251. No retained build or input stage remains. Original launcher
output includes an optional disappeared /proc/1713650/stat warning; subsequent
independent exact launcher custody/cleanup passed. Outer, scoped runner, runtime,
PID readback and scope cleanup statuses are zero.

Helper elapsed76.596seconds. The93 resource samples have maxima924544KiB RSS,
969292KiB storage and8 descendants; these are sampled maxima, not continuous
peaks. Bounds600/585/540seconds include30seconds export, two Cargo jobs,
16 descendants,1572864KiB storage preemption and2097152KiB hard RSS/storage.
The finite measured two-heavy-run exception expired at terminal109 without
modifying any foreign process.

## Applicability and history

This closes only the named Linux managed deadline/escaped-reader criterion. Tests and fixtures changed from53b;
production inputs are unchanged. Three affected base regressions were rerun;
prior unaffected accepted proof remains applicable. No no_float/no_index,
macOS/Windows or full current-source release matrix is claimed.

Native107 failed infrastructure receipt prefix parsing before GREEN rows; native108
recovered that prefix but stopped on wrong retained-report wait_unit polarity
after three base GREENs. Native109 recovers that second cause with truthful exact
wait_unit=false and complete four feature rows. Each cause retains its single
unsuccessful occurrence and successful first bounded recovery; no product
correction failure or budget reset. Unix109/escaped-native3 cumulative.

Combined independent review: [review](linux-managed-escaped-pipe-review.md).
Remaining stdin/postspawn faults, lifecycle/performance/docs/examples, other native
platforms, features/MSRV and final release gates remain open.
