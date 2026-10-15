# Linux X34 managed deadline and OutputLimit proof: standalone unchecked (2026-10-15)

## Accepted scope

This proof covers only the existing selectors
managed_run_deadline_reaps_group_under_fixture_reaper and
managed_run_output_limit_reaps_group_under_fixture_reaper under
testing-environ,sys,unchecked with no sync feature. Host: lllm x86_64,
Bazzite 44; Rust/Cargo 1.77.2; default profile; integrated fork-main revision
197bd802d8ca4f91c47b577d2a70700b62908e61.

The same selectors have accepted Linux evidence for testing-environ,sys
(linux-x34-base-current-20261015/) and
testing-environ,sys,sync,unchecked
(linux-x34-sync-unchecked-20261015/). This run fills the distinct standalone
unchecked row only; it does not close other X34 cases, features, platforms,
toolchains, Windows behavior, Ticket03 or A-F.

## Inputs and execution

The run used a private source copy from git archive HEAD, plus the preserved
X35 lockfile fixture. Cargo.lock SHA-256:
2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.
Cargo.toml SHA-256:
cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e.
Unix process implementation SHA-256:
2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6.
Restored tests/sys_process.rs SHA-256:
9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe.

One bounded run_scoped.py invocation used an absent, owned session scope,
absolute TMPDIR, source copy, CARGO_HOME and CARGO_TARGET_DIR below
AGENT_RUNTIME_DIR, one Cargo job, 900-second runner bound, and four exact
selector invocations. The first RED compiled the target. The complete commands,
environment, preflight capacity and logs are retained in attempt-01/.
The initial direct runner invocation was denied by its non-executable file mode;
no build or test ran then. The supported python3 tools/run_scoped.py entry
was used for the successful attempt.

## Results and independent operating-system observations

- Deadline RED: Cargo 101, 0 passed/1 failed at the deliberately inverted
  public timeout assertion. Before that assertion, the nested fixture recorded
  timeout result, partial captures, exact leader/worker/leaf PIDFD exit,
  process-group ESRCH (errno 3), live host/reaper/unrelated sentinel, exact
  fixture-reaper waits and no watchdog cleanup.
- OutputLimit RED: Cargo 101, 0 passed/1 failed at the deliberately inverted
  public OutputLimit assertion. Its nested fixture recorded typed OutputLimit,
  the exact 4096-byte prefix, honest incomplete captures, exact PIDFD exit and
  group ESRCH, live host/reaper/sentinel, exact fixture cleanup and no watchdog
  cleanup.
- Restored deadline GREEN: Cargo 0, 1 passed; the complete boundary log includes
  the same exact PID/group, capture, sentinel, reaper and cleanup observations.
- Restored OutputLimit GREEN: Cargo 0, 1 passed with the 4096-byte prefix,
  exact lifecycle observations and cleanup.
- Outer scoped runner: status 0. The compile-containing RED invocation took
  39.556 seconds; subsequent RED/GREEN selector invocations took 0.094, 2.968
  and 0.101 seconds respectively. Total Cargo command time was approximately
  42.7 seconds.

A pre-run sample showed 96 GiB available RAM, 673 GiB free on the source and
scope filesystem, load average 3.51/4.22/4.92 and no matching Cargo/rustc or
runner process. One job was used. After export the exact session scope and
private runtime were absent, and no Cargo/rustc process remained. No foreign
process or resource was touched.

## Review and limits

Combined independent review: PASS; see attempt-01/combined-review.md. Acceptance is limited to the two named
selectors for the Linux standalone unchecked profile at the revision and
inputs above. Native Windows custody and all other unlisted acceptance paths
remain open.
