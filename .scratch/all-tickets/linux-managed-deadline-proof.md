# Linux managed run deadline acceptance

Native105 is accepted for the public Engine managed run deadline criterion at
source31a61e752d0ffb747be827475278e3fc5d9dbe30, testSHA
8d6af23f45ac24ce640ca624800b3e40daff9e10941047a786ce5f7bd233f02b,
archiveaa3916aeb2cfb842cb2572032e398fc1c3f43f3811e6c60abc3e73d51dba4796.
Frozen recipes75033a91184fd7e42175990611a6f5a31b950f1b plus collector filename
repair50341e87be03f907079e6a594d46b42e8a98eb3f were executed on workhorse,
native Linux7.2.7 x86_64 with private Rust/Cargo1.77.2 and accepted lock2ba4b3a.

## Covered behavior

`managed_run_deadline_reaps_group_under_fixture_reaper` runs a real Rhai script
through Engine and the registered host package. The managed0.75s timeout returns
an unsuccessful timed-out result with both captures honestly incomplete and
retained stream markers. Independent exact PID/start/PIDFD/group observations,
reaper wait receipts and live host/reaper/unrelated sentinel prove termination
and reaping without exceptional fixture watchdog cleanup substituting for the API.
The named wrong-timeout assertion fails101 only after complete fixture cleanup;
restored source passes. Observed0.78s test durations are observations, not a
scheduler-independent latency guarantee.

Four GREEN features: testing-environ,sys; plus sync,metadata; plus f32_float;
plus unchecked. Four affected base regressions pass: prompt success, held-zombie
boundary, Child.kill and final-client-lease drop. Three private toolchain setup
commands pass; twelve commands total, one meaningful RED and eight GREEN tests.

## Original evidence and retirement

Originals: [native105 evidence](linux-managed-deadline105-evidence/).
Independent combined acceptance: [review](linux-managed-deadline-review.md).
Original source-restoration, command/status/stdout/stderr and boundary records
are retained. All78 original files/five directories match independent remote
hashes. Nine preexisting closure artifacts record53 exact fixture identities,
all absent;150 helper/command and two launcher PID/start records are absent,
exact groups1190144/1190156 empty. Hash-gated ownstage retirement and fresh
stage/scope/group absence are saved in remote-cleanup.json. No retained build.
The optional /proc1190153/stat exit-race warning remains in original outer.log;
later exact census and retirement are complete. Helper/export elapsed49.005s;
resource samples are observations, not continuous peaks. Limits600outer/585runner/
540helper including30export reserve, jobs2,desc16,1.5GiB preemption and2GiB
hard RSS/storage remain unchanged.

## Scope and history

This closes one Linux managed deadline/partial-output criterion and the four
identified base regressions at this source. Native103 compiler failure and
native104 watchdog observation failure remain preserved. Native105 resolves the
stable watchdog cause after one failed correction without resetting history.
No no_float/no_index/only_i32, macOS/Windows, whole process-ticket or release
acceptance is claimed. OutputLimit, escaped pipes, setup failure, remaining
lifecycle/fault/performance and final platform matrix remain open.
