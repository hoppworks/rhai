# Linux X34 managed deadline and OutputLimit proof: sync checked profile (2026-10-15)

## Scope

This proof covers the existing selectors
managed_run_deadline_reaps_group_under_fixture_reaper and
managed_run_output_limit_reaps_group_under_fixture_reaper under
testing-environ,sys,sync, with unchecked disabled. Host: lllm x86_64,
Bazzite 44; Rust/Cargo 1.77.2; default profile; integrated fork-main revision
aedf7857e3aca48797b6f3ee178c4209aad90ea1.

This completes a distinct checked sync profile for those two Linux selectors.
It does not claim broader X34, platform, toolchain, Windows, Ticket03 or A-F
acceptance. Other accepted rows are documented in
linux-x34-base-current-20261015/, linux-x34-unchecked-20261015/, and
linux-x34-sync-unchecked-20261015/.

## Inputs and execution

The runner used a private source copy from git archive HEAD and the preserved
X35 lockfile fixture (SHA-256
2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425).
Cargo.toml SHA-256:
cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e.
Unix process source SHA-256:
2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6.
Restored tests/sys_process.rs SHA-256:
9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe.

One run_scoped.py invocation used a new owned session scope, absolute TMPDIR,
and private source, Cargo home and target below AGENT_RUNTIME_DIR. Cargo used
one job; the outer bound was 900 seconds. Four exact selector commands shared
one compile. Full source hashes, environment, capacity snapshots and raw logs
are retained in attempt-01/.

## Results and independent OS observations

- Deadline RED exited Cargo 101 at its deliberately inverted public timeout
  assertion after the real fixture recorded timeout, partial output, exact
  leader/worker/leaf PIDFD exit, process-group ESRCH (errno 3), live host,
  reaper and unrelated sentinel, exact fixture-reaper waits, and no watchdog
  cleanup.
- OutputLimit RED exited Cargo 101 at its deliberately inverted public
  OutputLimit assertion after recording the typed result, exact 4096-byte
  prefix, honest incomplete captures, PIDFD/group closure, live host/reaper/
  sentinel, exact fixture cleanup and no watchdog cleanup.
- Restored deadline and OutputLimit each passed 1/1 with Cargo status 0 and the
  same lifecycle observations.
- Outer scoped runner status was 0. The compile-containing first RED took
  39.759 seconds; subsequent selectors took 0.091, 3.070 and 0.086 seconds.
  Total Cargo command time was about 43.0 seconds.

Preflight showed 95 GiB available RAM, 673 GiB free disk, 32 CPUs and no
Rhai Cargo processes. A separate one-job Tauron build was active; it was left
untouched while this one-job run proceeded. The runner retired the exact owned
runtime and session scope, leaving no Rhai build process or cache.

The post-run source hash command first ran from the project directory, where
the private-copy Cargo.lock is absent; it was a readback-command cwd error, not
a Cargo result. Direct comparison then confirmed the fixture lock, product
source and restored test source against the recorded hashes. A separate cosmetic
status-print command also had a shell syntax error; runner, assertions, revision,
source and lock were independently read back.

## Review and limits

Combined independent review: PASS; see attempt-01/combined-review.md. Acceptance is limited to these two named
selectors under the Linux checked sync profile at this revision and input set.
