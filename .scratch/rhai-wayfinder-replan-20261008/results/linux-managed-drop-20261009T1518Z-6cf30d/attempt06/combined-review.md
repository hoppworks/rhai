# Combined independent acceptance review — Linux X35 attempt06

**Verdict: X35 accepted for the recorded Linux 1.77.2 configuration.** This review applies only to the three X35 selectors below. It does not close the remaining Unix, Windows, TCP, integration, release, or overall A–F criteria.

## Review rules loaded

Central Agent Skills repository HEAD on Mac and Workhorse: `1b6e1da85f87cad25f7aafc91aa782319ac6ef93`. Global `AGENTS.md` SHA-256 `fa1c6e65…`; `config/common/AGENTS.md` `f71e8f97…`; project `AGENTS.md` `37f95ff6…`. `build-efficiently/SKILL.md` `58f676b4…`; TDD skill read on Workhorse (and Mac) `a4d82ea3…`; resource-lifecycle document `102bc29d…`.

## Binding and execution

The packet records source revision `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`, source archive SHA-256 `68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644`, accepted lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, features `testing-environ,sys` with Cargo defaults, target `x86_64-unknown-linux-gnu`, and Rust/Cargo 1.77.2. The archive's `tests/sys_process.rs` hash equals the recorded base-source hash `86f1142f…`; the executed lock equals `Cargo.lock.accepted`; both compiler-artifact readbacks report exactly `default,std,sys,testing-environ`. RED and GREEN used the same owned source-copy path, lock, target and executable path; distinct executable hashes confirm the source-state rebuild. The 9-file attempt-input manifest and current 93-entry package output manifest validate.

The source revision is independently bound to the archive by the durable read-back `../source-archive-tree-readback.json` (SHA-256 `5bebd137777bef67a7f49411fc4fc8888e4d437477fa54c0c18a36b2b80f7540`). Using the exact commit fetched read-only from the verified fork origin `https://github.com/hoppworks/rhai.git`, `git archive --format=tar 34e0fa61a3d12fe6c41902c44618ff44e20d73d4` was compared against the Workhorse archive at `/var/roothome/rhai-evidence/wayfinder-20261009/linux-managed-drop-20261009T1518Z-6cf30d/source.tar.gz`: all 9,199 files matched, with zero missing or extra files and zero content, executable-mode, or symlink-target mismatches. The second verified Workhorse copy is `/var/roothome/rhai-evidence/linux-managed-drop-attempt02-20261009T1733Z-a7c3e1/linux-managed-drop-20261009T1518Z-6cf30d/source.tar.gz`; both retained copies were confirmed to have the recorded archive SHA before the 145 MiB local duplicate was removed.

The execution record shows explicit source cwd, `--locked`, one RED and one restored GREEN build, and exact `--exact` selector commands. Build and list phases exited 0. Native host evidence identifies Workhorse Linux x86_64, kernel 7.2.8-ogc5.1, and the recorded toolchain. Source revision, complete archive tree, accepted lock, features, target and toolchain are therefore bound by the recorded evidence.

## RED/GREEN and behavior

Each RED was the intended assertion control in its named function, exited 101 after the named test started, and printed the corresponding assertion diagnostic. Each restored-source GREEN ran the same exact selector and passed `1 passed; 0 failed`:

- `managed_run_closes_worker_after_leader_exit_and_preserves_sentinel`: inverted the unrelated-sentinel assertion; RED reports `RED control expects unrelated sentinel to be killed`. GREEN confirms the managed leader, worker and leaf are gone at API return while the unrelated sentinel remains live; the test then reaps its own sentinel.
- `managed_run_closes_pipe_closed_worker_before_return`: inverted the PIDfd liveness assertion; RED reports an exact managed member unexpectedly exited before API return. GREEN observes three acquired PIDfds for leader/worker/leaf and requires all exited at API return, despite closed captured pipes.
- `direct_run_returns_with_pipe_closed_worker_live_control`: inverted the direct-child descendant control; RED reports the managed member remained live at API return. GREEN requires the direct leader exited while worker and leaf remain live at API return, establishing the contrast to managed scope closure.

The archived source exercises the public Rhai `run` API through an Engine and the registered system package. It launches the real test executable and OS child fixtures. Readback uses child-written PID/parent/group records, Linux `/proc` identities, pidfds, and post-run process-group scans, rather than mocks. The cleanup observer independently confirms all exact fixture roots are absent, expected groups have no remaining readable members, recorded worker/leaf/leader cleanup matches the PIDfd identities, and the sentinel is alive after the managed call then absent after its owned cleanup. Both phases are complete.

## Lifecycle and remaining scope

The runner was reaped with status 0, the cleanup observer exited 0, no signals were recorded, and the exact scope identity `(device 58, inode 119644406, uid 0, gid 0)` is recorded retired. No additional build or test is warranted for this criterion absent a relevant source, assertion, lock, feature, toolchain, or environment change.

X35's three listed rows are now supported by this packet. The broader plan remains open, including X34 timeout/output-limit rows, X36 setup and refusal handling, X37 managed kill/final-drop lifecycle cases not covered by this package, X38 escaped-pipe behavior, cross-platform and feature/MSRV matrices, and the remaining A–F requirements. The source archive is exactly bound to the recorded Git revision by the tree read-back above.
