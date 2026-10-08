# Independent combined review of the X23 integer-only example correction

Reviewed on 2026-10-08; final read-only inspection at 12:59:55 UTC.

**Verdict:** no actionable defect found in the owned example patch, its standards/spec compliance, the saved oracle, input/native execution binding, or the demonstrated child closure. The existing raw evidence supports accepting the two Darwin Rust 1.77.2 rows `sys,no_float` and `sys,sync,no_float`. The coordinator must still save `proof.md`, the final file-hash manifest and `cleanup.json`, and independently retire/read back the verified empty owned outer scope before marking those rows finally accepted. No execution repeat is warranted for this unchanged input.

This review is independent of the implementation/proof producer. It reads the owned patch and original saved evidence together; it does not rely on the unsaved final answer from the earlier reviewer. No builds, tests, product edits, cleanup, commits, network writes, or other-session messages were performed. Only this review result was written.

## Rules and reviewed scope

Loaded the unchanged installed Wayfinder skill from `/Users/hoppworks/.agents/skills/wayfinder/SKILL.md` and confirmed that its bytes match `/Users/hoppworks/.local/share/mattpocock-skills/f3fc5632f401156837ee3872f14fe33ccf1024ea/wayfinder/SKILL.md`: SHA-256 `9be7b478c389605a24517d27752f278933588da97a1b5921b165f455edf4c5b7`, installed rule revision `f3fc5632f401156837ee3872f14fe33ccf1024ea`.

Loaded project `AGENTS.md` for public-Engine/real-OS acceptance, strict assertion controls, bounded fixtures, ownership and cleanup (SHA-256 `06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c3f7ce119d7c5de`). Loaded the current `implementation-plan.md` **Example correction** and assertion-control requirements (plan SHA-256 `abd684c30562a2adcdbd13a391ffad7676bccc792d7efeeec5ef35e957428ddf`). The later owner authorization for autonomous implementation supersedes the plan's historical planning-only status. The old global agent-skills layer is disabled and was not loaded; `/Users/hoppworks/.agents/AGENTS.md` and old central campaign rules were not read.

The only product delta reviewed is `examples/sys_process.rs`: add `nonblocking_wait_expression()` and replace its three `child.wait(0.0)` callsites. The foreign dirty `tests/fixtures/sys_process_shared_child_contract.rs` remains untouched, with SHA-256 `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`. This report does not adopt or accept that foreign delta, X24, other platforms/profiles, or the overall release matrix.

## Standards, specification and security/ownership

The selector supplies `child.wait(0)` under `no_float`, matching the integer overload registered by `src/packages/sys/process/unix.rs`; otherwise it preserves `child.wait(0.0)` and the float overload. Both overloads express a zero-duration poll. All three affected sites use the same selector: readiness-time pending observation, the bounded terminal poll, and the guarded cleanup poll. The patch does not alter authority policy, package configuration, process backend, result assertions, timeouts or fixture ownership.

The example continues to register a real `SysPackage` into a public `Engine`, allowlist only its own executable, and clear the child environment except for the explicit fixture variables. `run`, `spawn`, child ID and waits are evaluated through the script API. The new helper keeps the script expressions valid for the enabled numeric type. There is no new production interface or resource allocation to review.

Readiness is a child-written atomic record with the child PID, compared against the public child ID before the pending wait. Release is a host-written file; the child records that it observed release. Polling has explicit deadlines. The existing cleanup guard still releases/kills and polls on exceptional paths; the new selector also fixes that path's numeric expression. No new guard fault-injection claim is inferred from these normal completion rows. Saved compiler warnings concern unchanged library/backend code, not the owned example delta.

## Input, build and native binding

Independently recomputed all three frozen-input hashes and all three `recipe.sha256` entries. All match. The source archive equals a fresh in-memory `git archive --format=tar` of recorded revision `ef423a516617e128835d54af16d75f559b2b1bce`; current HEAD is still that revision. The owned patch bytes equal the current `git diff -- examples/sys_process.rs`. The current example, Cargo manifest, build script and relevant process backend hashes match `inputs.json`. All nine recorded current working-file hashes match, including the preserved foreign fixture. The committed source archive contains the committed fixture, not the foreign dirty delta.

| Bound input | SHA-256 |
|---|---|
| `source.tar` | `635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f` |
| `owned.patch` | `885978cdd5e46442e04bf92a1a60ebeb8d88b84d5e721fcd8fe12ac216dc0f90` |
| `Cargo.lock.accepted` | `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` |
| Patched example | `02f6b6b77341977248c46fb06e0b3c51b258c9cf33ba3023f53c12c5fc3de2a4` |

The reviewed helper creates an owned source directory, extracts only the committed archive, overlays the pinned lock, checks/applies only the owned patch, and checks the patched example hash before compilation. Each saved build command uses `cargo +1.77.2 build --locked --features <profile> --example sys_process --message-format=json`. Both command exits are zero and both JSON logs end with successful `build-finished` records.

Each build log has exactly one `compiler-artifact` for executable example `sys_process`, from the owned source path, with the intended enabled features: `default,no_float,std,sys`, or `default,no_float,std,sync,sys`. The Rhai library artifact has the same respective feature set. The helper obtains the executable from that record, and the saved RED/GREEN command paths match it. All six commands use the owned source cwd `/Users/hoppworks/.local/share/agent-builds/rhai/example-c58997ha/agent-build-6enomxxh/source`; Cargo home, target and temporary directory are within that private runtime. Cargo jobs are two; no external compiler flags or deployment-target override is recorded.

The saved environment reports native macOS 27.0.1 build 26A434, arm64, `rustc 1.77.2 (25ef9e3d8 2024-04-09)` and `cargo 1.77.2 (e52e36006 2024-03-26)`. No cross target is specified. The commands, artifact paths, real execution output and this environment record support the stated Darwin package-minimum binding. Runtime removal means executable hashes are contemporaneous recorded digests, not freshly recomputed binary hashes in this review.

## Oracle and independent OS observations

The control changes only `RHAI_SYS_PROCESS_EXAMPLE_EXPECTED_EXIT` from 8 to 7; no source/oracle recompilation is needed for that runtime control. The helper supplies that value explicitly. The source retains its unconditional real exit-code assertion of 7 and then compares against the phase expectation. Thus RED does not weaken the normal contract: the deliberately wrong expected 8 fails only after all run/spawn assertions and readbacks. Both RED stderr files name `RED control changes only the expected exit` and show left 7 / right 8 at the intended assertion. They exit 101; they are not parse, build, readiness or cleanup failures. Both GREEN stderr files are empty and both exits are zero.

| Profile / phase | Expected / exit | Spawn PID / saved post-exit observation | Binary SHA-256 |
|---|---|---|---|
| `sys,no_float` RED | 8 / 101 | 80141 / ESRCH | `b00a4ae71cfcaa2423b2aaf0f4edb6cce3b4a651f4b75786374a0aa5820f4d21` |
| `sys,no_float` GREEN | 7 / 0 | 80146 / ESRCH | `b00a4ae71cfcaa2423b2aaf0f4edb6cce3b4a651f4b75786374a0aa5820f4d21` |
| `sys,sync,no_float` RED | 8 / 101 | 80170 / ESRCH | `6f3e4b6e3652eba129000cb42c59646697afcd35591446e52fefcfdbbbdfe134` |
| `sys,sync,no_float` GREEN | 7 / 0 | 80174 / ESRCH | `6f3e4b6e3652eba129000cb42c59646697afcd35591446e52fefcfdbbbdfe134` |

Within each profile, RED and GREEN share the same recorded executable digest and patched example digest. The second profile is compiled before its own two phases. All four original stdout files contain fresh host file-read results for `run child wrote its record\n` and `spawn child observed release\n`, with a distinct spawn PID, plus the pending-to-completed identical-clone result message.

These messages are supported by inspected code, not only output-string matching: `fs::read_to_string` reads the child-written files independently of the package's result map; the source asserts their exact contents. Spawn remains blocked awaiting explicit release when the early public wait returns unit. Both cloned handles are then waited through the Engine and all shared result fields are compared; spawn exit 0, output completeness and stdout/stderr are asserted. The real `run` child writes its own record and exits 7, which is returned as data with `success == false` and `timed_out == false`.

The helper performs `os.kill(pid, 0)` immediately after each example command and accepts only ESRCH; presence and permission errors fail. The four ESRCH records therefore provide independent contemporaneous absence observations following terminal waits. This review did not signal or reprobe those historical numeric PIDs. This RED demonstrates sensitivity of the exit expectation; it is not a claim that every independent assertion has its own negative control.

## Cleanup and remaining finalization

`runner.status` is 0. No phase stderr reports bounded cleanup failure. RED occurs after the spawned child has already reached terminal waits, so it also exercises unwinding after the final wrong-exit assertion. The package's child termination/reaping behavior and the contemporaneous ESRCH records support closure for these four observed child runs.

A fresh read-only `lstat`/directory inspection during this review found the recorded inner runtime `/Users/hoppworks/.local/share/agent-builds/rhai/example-c58997ha/agent-build-6enomxxh` absent. The outer scope `/Users/hoppworks/.local/share/agent-builds/rhai/example-c58997ha` exists as an empty directory, is not a symlink, is owned by UID 501, and has device 16777234 / inode 225778809. Original exported inputs, recipes, command records and logs are readable outside that runtime. The original runtime identity in `result.json` is device 16777234 / inode 225781619.

The reviewer did not remove the outer scope. The coordinator must recheck this exact outer identity, ownership and emptiness immediately before any `rmdir`, preserve it if anything changes, and save the fresh retirement readback with the final proof/manifest/cleanup receipt. Until then, outer-scope retirement remains open. This is finalization of valid existing proof, not missing product evidence or a reason to rerun Cargo.

No actionable findings require a product change or new verification run. Scope is limited to the owned X23 example correction and these two native Darwin integer-only rows. Existing standard/sys+sync X23 evidence and independent X24 evidence remain separate; Linux, Windows, other feature combinations and pending-child exceptional cleanup fault coverage are not newly certified by this report.
