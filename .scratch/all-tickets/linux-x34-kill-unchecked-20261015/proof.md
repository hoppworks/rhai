# Linux X34 managed Child.kill proof: standalone unchecked (2026-10-15)

## Scope and inputs

This proof covers only
managed_child_kill_reports_group_closed_under_fixture_reaper under
testing-environ,sys,unchecked, with sync disabled. Host: lllm Linux x86_64,
Bazzite 44; Rust/Cargo 1.77.2; default profile; integrated fork-main revision
29d3a44096fb35c315931926af142b2af00300bf.

The selector drives public Rhai Child.kill/wait through the registered host
package, closes a real managed leader/worker/leaf group, checks a failed child
report and complete captures, and preserves an unrelated sentinel at the API
boundary before fixture cleanup. This is one Linux feature row; it does not
close other X34/X25 selectors, platforms, toolchains, Windows behavior,
Ticket03 or A-F.

The private source copy came from git archive HEAD plus the preserved X35 lock.
Cargo.lock SHA-256:
2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.
Cargo.toml SHA-256:
cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e.
Unix process source SHA-256:
2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6.
Restored tests/sys_process.rs SHA-256:
9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe.

## Results and readback

One scoped runner invocation used an absent owned session scope, absolute
TMPDIR, private source/Cargo home/target under AGENT_RUNTIME_DIR, one Cargo job
and a 900-second outer bound. The deliberate wrong-report assertion RED exited
Cargo 101 after boundary and cleanup readbacks. Restored GREEN passed 1/1;
outer runner status was 0. RED compile/test took 38.216 seconds; incremental
GREEN took 2.223 seconds.

The logs record exact host/reaper ownership, leader/worker/leaf PIDFD identities
and exit, group closure, exact descendant waits, public failed Child report,
complete captures, host/reaper/sentinel liveness at return, exact sentinel
reaping afterward and host/group cleanup. Preflight showed 96 GiB available
RAM, 671 GiB free disk, 32 CPUs and one unrelated Tauron build; that work was
preserved. The exact private runtime and session scope were removed; no cache
was retained. Full environment, commands, source hashes and raw logs are in
attempt-01/.

## Review and limits

Combined independent review: PASS; see attempt-01/combined-review.md. Acceptance is limited to this named
Linux standalone unchecked selector at this revision and source/lock inputs.
