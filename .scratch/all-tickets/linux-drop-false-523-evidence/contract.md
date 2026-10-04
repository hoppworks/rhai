# Linux `kill_on_drop(false)` final-drop proof

This bounded package runs only the two exact existing public Engine tests from
baseline `523608648dcae99bc0f6b46eaf2bb91fa4ecc752`:

- `direct_spawn_kill_on_drop_false_preserves_child_and_capture`
- `managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit`

The required Linux-only test handshake is applied as a temporary test-source
patch in the private extracted source. No production source or fixture behavior
is changed. Each case runs a wrong-expectation control first; the control must
panic at its named survival assertion before it creates an observer request.
The restored handshaked source then runs once for that case. A bounded observer
thread checks the held challenge response, fixture-root identity and live
`/proc` PID/start/PGID tuple before writing an acknowledgement that echoes the
complete request text. The test compares that complete expected acknowledgement
byte-for-byte; this is content binding, not a cryptographic digest. Each
request includes the test PID/start and all named child PID/start/PGID values.
After the test exits, the observer records fresh exact PID/start and owned-group
readbacks. Request and acknowledgement directories are unique and empty per
invocation; the observer also binds the test host's parent PID to the recorded
Cargo command.

Scope: native Linux x86_64, Rust 1.77.2, features `testing-environ,sys`,
without `no_index` or `no_float`. The four exact Cargo invocations are two
controls (expected status 101) and two green tests (expected status 0). The
source archive comes from baseline 523. That revision has no tracked root
`Cargo.lock`; the separate compatible accepted lock is pinned by SHA-256.

Bounds: outer launcher 600 seconds; `run_scoped.py` 585 seconds; helper 540
seconds including setup/export, with 510 seconds for work and a 30-second
export reserve; Cargo jobs 2; at most 16 descendants; one-second resource
sampling; preemptive private-storage stop at 1,572,864 KiB and hard storage/RSS
stops at 2,097,152 KiB. Rustup, Cargo, target, HOME, TMPDIR, and fixture temp
files stay inside the central private scope/runtime. Export original stdout,
stderr, statuses, process observations and partial receipts before scoped
teardown on success, failure, exception or signal. Partial evidence is not
acceptance. Independent original collection, fresh process/group/scope
readback and exact stage retirement are separate required steps.

No run has been performed by preparing these recipes. Windows coverage remains
separate; retained macOS evidence applies only to macOS.
