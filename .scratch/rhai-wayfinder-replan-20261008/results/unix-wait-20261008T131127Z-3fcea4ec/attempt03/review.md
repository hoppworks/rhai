# Independent combined review: public Child.wait decoded expansion regression

Darwin review completed 2026-10-08, 13:29:51 UTC.

**Scoped provisional verdict:** no actionable defect found in the new regression, its oracle, input/executable/native binding, or the demonstrated Darwin child closure. The original attempt03 evidence supports the four checked-mode Darwin arm64 Rust 1.77.2 rows (`sys`, `sys,sync`, `sys,no_float`, `sys,sync,no_float`) for this selector. Overall Unix completion remains provisional until the same-source Linux evidence and final cleanup/export receipts are reviewed. No product rerun is warranted for the unchanged Darwin source.

The only reviewed product delta is `tests/sys_process.rs::child_wait_preserves_decoded_expansion_reports_and_committed_primary_cause`, adjacent to the existing lossy-run regression. This is new verification of existing behavior, not a production backend change or proof of a newly discovered product defect. The review covers standards, specification, fixture/resources, oracle and original evidence together. It performs no builds, tests, product edits, cleanup, commits or messaging; only this review result is written.

## Loaded baseline and ownership

The unchanged installed Wayfinder rule revision is `f3fc5632f401156837ee3872f14fe33ccf1024ea`. Its previously loaded `/Users/hoppworks/.agents/skills/wayfinder/SKILL.md` remains SHA-256 `9be7b478c389605a24517d27752f278933588da97a1b5921b165f455edf4c5b7`, matching the revision below `/Users/hoppworks/.local/share/mattpocock-skills/`. The old global agent-skills layer remains disabled; its global AGENTS and central campaign roles were not read.

Read current project `AGENTS.md` (SHA-256 `06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c3f7ce119d7c5de`) for strict public-Engine/real-OS proof, independent observations, assertion controls, bounded fixtures and ownership. Read the current plan's **Unix process closure**, assertion-control and unchecked host-cap requirements (plan SHA-256 `abd684c30562a2adcdbd13a391ffad7676bccc792d7efeeec5ef35e957428ddf`). Later explicit owner authorization permits autonomous implementation and supersedes the plan's historical planning-only status.

The foreign dirty shared fixture remains unchanged at SHA-256 `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`. The archived committed fixture is SHA-256 `1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217`; this distinct committed fixture is what the build receives. No ownership or acceptance of the foreign delta is inferred.

## Regression, specification and resource correctness

The test uses the existing `process_fixture`, registered `SysPackage` and public `Engine`, with only the current executable allowlisted. It clears the child environment and supplies only fixture variables. The fixture writes its actual PID/intended exit record, emits a finite specified invalid-UTF-8 payload and calls real `process::exit(0)`. It neither inherits an infinite/hold fixture mode nor changes the parent environment. Its record lives in the existing scoped `TempDir` guard.

The no-primary case explicitly asserts that raw stdout stays below the Engine string limit while lossy decoded text exceeds it. Public spawn has no forbidden timeout option; wait is bounded at five seconds. FLOAT expressions (`5.0`, `0.0`) are used with floats and INT expressions (`5`, `0`) under `no_float`, matching the registered timed wait overloads. A unit timeout result, non-process runtime error or different cause fails the test rather than counting as success.

The test then requires typed `SysError::Process` / `ProcessCause::OutputLimit`, the decoded-expansion cause, actual exit `Some(0)`, no exit signal, complete stdout/stderr, exact independently constructed raw bytes, empty stderr and no timeout. The three waits use the original handle, a clone and the original handle again; equality of the entire `(cause, ProcessReport)` snapshot checks all report fields remain stable. `assert_child_record` independently rereads the child file and requires `kill(pid, 0) == -1` with ESRCH. That helper rejects permission errors and present/zombie PIDs.

The primary case supplies more raw bytes than the effective capture limit. `parse_options` derives that limit as the minimum of the host cap, per-call 1024 cap and Engine cap. In the reviewed Darwin rows the Engine/effective cap is 228 bytes: no-primary capture is 130 raw bytes (114 invalid bytes plus the 16-byte libtest prefix), while primary capture retains exactly the first 228 bytes of a 470-byte output. Those prefixes still expand beyond the Engine limit when decoded. The source requires the supervisor's `stdout for ...` OutputLimit cause rather than the decoded-expansion cause, exact retained bytes, stable reports and independent reaping. It correctly does not require a normal exit/completeness outcome for an overflow-triggered cancellation. The existing snapshot path returns a committed failure before checking decoded expansion, and the test distinguishes both branches without altering the backend.

Scope-owned child handles drop before the temporary-directory guard, including on assertion unwind. Both cases are finite, their waits are bounded, and the helper's test invocation has a 30-second timeout. Accepted GREEN rows independently prove child-file readback and absence after terminal waits. No broader exceptional-cleanup fault coverage is claimed.

The new test is correctly excluded when `no_index` or `unchecked` makes this Engine-limit scenario inapplicable. This review does not certify an unchecked row or treat a cfg-excluded execution as GREEN. The plan's separate unchanged unchecked host-cap selector, `process_script_output_option_cannot_raise_the_host_cap`, remains outside this review. The delta introduces no host-cap weakening, process policy expansion or new unsafe code. Saved compiler warnings point to unchanged code, not this new function.

## Frozen inputs and original build binding

Independently recomputed the source archive, owned patch, accepted lock and current test-source hashes. All match `inputs.json`. The source archive equals an in-memory `git archive --format=tar` of revision `ef423a516617e128835d54af16d75f559b2b1bce`, which remains current HEAD. The owned patch equals the current `git diff -- tests/sys_process.rs` and contains only the new function. The archived backend and test-support module match current unchanged files; the foreign dirty shared fixture is not in that source archive.

| Input | SHA-256 |
|---|---|
| Source archive | `635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f` |
| Owned patch | `886a5bf343aec87113cffc372f4ac1bce59c4b84bb5a28280a7318b9f6f6bfa6` |
| Accepted lock | `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` |
| Restored/current test source | `f7055a0a6161b6d3b63be9ee03b0aaf0d6611c5cc95af7387d3d68eef5e03bd1` |
| RED test source | `582399a53d8dcf00057dcfc656c070180b66ca5c23665da3332f1076e9a3de3f` |
| Reviewed `verify-wait.py` | `80a3b754bf6dbdbfbb50bdfb69f1c6632bed64c415922574709fc5fc7a4b08cb` |
| Reviewed `payload.sh` | `1000ee99f44b5b88edf0661843ebb593a2e244ba38e36606c1071ca87f8f13d1` |
| Reviewed `inputs.json` | `c09d0950bf593205ccbca51715080423f2ad4923c164d15e9e4a5f06fbe710f4` |

The helper checks frozen inputs, extracts the committed archive into the private runtime, overlays the pinned lock and applies only the owned patch. It verifies the resulting test hash before deriving the phase mutation. Each RED and restored GREEN has its own incremental `cargo +1.77.2 test --locked --features testing-environ,<profile> --test sys_process --no-run --message-format=json` compilation. All eight builds exit zero and end with successful build-finished JSON.

Every build log has exactly one `sys_process` test executable artifact from the owned source, with the intended profile features. All eight saved `--list` outputs contain the exact selector once, and all eight direct invocations select that test with `--exact --nocapture --test-threads=1`. Executable paths match the respective compiler-artifact and list command; cwd remains the private source directory. Cache/home and target are private via the reviewed payload, with two Cargo jobs. The environment records native macOS 27.0.1 arm64, `rustc 1.77.2 (25ef9e3d8 2024-04-09)` and `cargo 1.77.2 (e52e36006 2024-03-26)`. There is no cross target in the command or artifact path. Binary digests below are contemporaneous records; the retired runtime prevents fresh binary hashing in this review.

## Assertion control and four-profile evidence

Independently reconstructed the RED mutation in memory. The selected function contains exactly one `normally completed child exit is preserved` assertion; changing only its `Some(0)` to `Some(1)` produces the saved RED source hash above. Restoring it produces the current GREEN source hash. No global assertion replacement or reusable wrong-expectation switch is added to the real test.

All four RED commands exit 101 at the intended assertion, left `Some(0)` / right `Some(1)`. Their original stdout identifies this selector in the failure inventory and reports exactly one failed test. All four GREEN commands exit zero and report one passed test with no ignored tests. Each GREEN stderr has both `primary_limit=false ... raw_bytes=130` and `primary_limit=true ... raw_bytes=228` observations after the actual assertions and independent record/reap helper. Thus neither branch was silently skipped.

| Profile | RED executable SHA-256 | GREEN executable SHA-256 |
|---|---|---|
| `sys` | `396c42f65a7727937fcee88015ab59150011d5943c2607fd65957afaff078852` | `2ef91d64b6a41252ed707044a3690ec88e8ce97516c51c848fbf88f83900a921` |
| `sys,sync` | `2f83facf1bd3090f1587d64e2c9eb3c1eed9d0ba10a3063e887c5169e4b1f333` | `b04248de4a1c72cec30a86fd8570ff8b51b596c17ce497ac2d5818e7ee9ecbe9` |
| `sys,no_float` | `139ce99c2c59c7748541dfd493462b390cc61b9ee69625c4b6260944b664899c` | `ee568def374d0fa1646651129c3340ee2dcee8888091edcd3c82456e27954ef1` |
| `sys,sync,no_float` | `5501ac9ec0955ecd7ea3ef80e8322e6d85b7c6d20a240d8f676502712c90ce44` | `a929a661af7c5684b5bc4dac0f74a888d8d9cca605944e2758540d46ef976a95` |

The RED stops in the first no-primary case before its final file/reap helper and before the primary case. It is valid exit-oracle sensitivity proof, not independent reap evidence for every assertion or a negative control for the primary-cause branch. The restored GREEN runs provide the independent lifecycle evidence for both cases.

The retained first attempt rejected a forbidden explicit spawn timeout before launching the selected fixture. Attempt02 used the unregistered integer wait overload with floats and failed with `ErrorFunctionNotFound("wait (Child, i64)")` before the intended assertion. Their original stderr and failure analyses agree with those fixture-context classifications. Neither attempt contributes accepted RED/GREEN rows or evidence of a product defect; corrected attempt03 is the acceptance input.

## Cleanup and finalization still open

`runner.status` is zero, the helper records the test source restored, and all eight original build/list/test records remain readable outside the disposable runtime. The saved inner runtime identity is device 16777234 / inode 226039459.

A fresh read-only inspection found `/Users/hoppworks/.local/share/agent-builds/rhai/unix-wait-g8cd4t20/agent-build-7r9fqyx7` absent. The exact owned outer scope `/Users/hoppworks/.local/share/agent-builds/rhai/unix-wait-g8cd4t20` is empty, not a symlink, owned by UID 501, device 16777234 / inode 226039451. This review did not delete it or reprobe historical child PIDs.

The coordinator still needs the final proof/export hash manifest and cleanup receipt, including an immediate matching ownership/identity/emptiness check before any outer-scope retirement and a fresh retirement readback. Preserve the scope if its identity or contents change. Linux same-source platform binding is not yet reviewed in this revision of the report. Windows, unchecked/no_index, broader Unix lifecycle selectors, and the release matrix remain outside this scoped verdict.

## Linux binding and completed cleanup addendum

Completed 2026-10-08, 13:38:43 UTC. This addendum supersedes the provisional platform/cleanup status above. The earlier combined source, specification, oracle and resource analysis stands unchanged; only Linux binding and the now-present export/cleanup receipts were added. The previously loaded rule baseline remains unchanged.

**Final scoped verdict: accepted.** No actionable findings remain for `child_wait_preserves_decoded_expansion_reports_and_committed_primary_cause` and its no-primary decoded-expansion / committed-primary-cause scenarios on native Darwin arm64 and Linux x86_64, Rust 1.77.2, under each of `sys`, `sys,sync`, `sys,no_float` and `sys,sync,no_float` (with the recorded `testing-environ` verification feature). The eight platform/profile rows have valid intended assertion RED, restored GREEN, both semantic branches, independent child-file/ESRCH observations and completed scoped cleanup. This does not accept all Unix lifecycle work, unchecked/no_index, Windows, or the release matrix.

### Same-source Linux binding

Reviewed the original Linux files exported to `../linux`: inputs, helper/payload/launcher, remote input readback, compiler-artifact/list/exact-test logs, result, remote export hash manifest and cleanup receipt. The Linux archive, patch, lock, final test-source, RED test-source, selector and four profiles match the already reviewed Darwin inputs exactly. The actual exported patch and lock also match byte for byte. The source archive's remote readback digest is the previously independently verified committed archive digest `635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f`; source is restored to `f7055a0a6161b6d3b63be9ee03b0aaf0d6611c5cc95af7387d3d68eef5e03bd1` after every GREEN and on helper exit.

The Linux helper differs from the Darwin helper only in selecting direct compiler/Cargo paths for version reporting and compilation. Its input checks, function-specific `Some(0)` → `Some(1)` mutation, phase compilation/listing, exact selector, oracle checks and restoration are unchanged. The original remote input readback also binds that helper and payload: SHA-256 `5f02dc4c6b8ad94241e2fd5212e40417bcdb65760eb1580996fc9b0a4e09fc64` and `07e54fa45e4f3163f057d01911c973fdd0b70dbf48289bdff7fa8171e994dcf0`, respectively.

The saved payload selects Cargo, rustc and rustdoc directly under `/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/`; it clears compiler flags/wrappers and uses private Cargo home/target with two jobs. All eight saved build argv use that exact Cargo path, `--locked`, the respective `testing-environ,<profile>`, `--test sys_process --no-run --message-format=json`. The environment records native `Linux-7.2.8-ogc5.1.fc44.x86_64-x86_64-with-glibc2.43`, machine `x86_64`, rustc 1.77.2 and Cargo 1.77.2 with the same version commits as Darwin. No cross target is supplied.

All eight builds exit zero and have successful build-finished JSON. Each has exactly one `sys_process` test compiler artifact with the intended enabled features and `fresh == false`. Each saved list contains this selector once. Each saved exact-test command uses the matching artifact executable with `--exact --nocapture --test-threads=1`. Command cwd is `/root/.local/share/agent-builds/rhai/unix-wait-29a33c10da/agent-build-0vja0mc5/source`; Cargo's source/artifact metadata reports that same private source tail under its `/var/roothome` prefix. The compiler stderr, artifact source path and command cwd consistently bind the owned source used for these executions; no different source or foreign fixture overlay appears in the recipe.

All four Linux RED originals exit 101 at `normally completed child exit is preserved`, left `Some(0)` / right `Some(1)`, identify the exact selector in the failure inventory and report one failed test. All four GREEN originals exit zero and report one passed, zero ignored tests. Every GREEN stderr records both cases after all their report/file/reaping assertions: no-primary raw bytes 126, primary raw bytes 221, exact bytes, equal cloned/repeated snapshot, and child reaped. These are the path-dependent Engine-cap sizes from the identical test, not changed output oracles. The same recorded source hashes distinguish freshly compiled RED and restored GREEN artifacts.

| Linux profile | RED executable SHA-256 | GREEN executable SHA-256 |
|---|---|---|
| `sys` | `5ca1e9ee51a4d3b4e8b5d6eb44e3c2e04b6c49c9ba3dfe6e8a53e88d415d7487` | `a450f2effdd95d0b7df63e7e34a50e17b6d0fbe38da7fe17a4f79e46046a3c50` |
| `sys,sync` | `a40993f96b2ef7348754f44bc50e3ea81b359b128dddb09905fc5eb8cca4c48c` | `386879b6818d8ea662a33c162d4f1ac2133b3084cc2c5eb7dea62dcbbe0a143a` |
| `sys,no_float` | `b54f891842461014ae8c26aaaf3f161d966878a45337974ed87b9fc4dd8fa614` | `150117c9d97dc3788a7405e8d2630c268d4b1a954046ac0ed7b8c93ce58daa27` |
| `sys,sync,no_float` | `0a648e80c9ed1f52c41f75963aec4e98da3215ebe7b71bf034b91c94d1a80247` | `8cd9ab0d335ad948772bc7ca2c1da2cae22434ef5bf05be47d1350dc28402c23` |

### Export integrity and cleanup closure

Independently recomputed all 82 entries in Linux `remote-export-manifest.json` against the readable local exported files: none missing, all match. Also recomputed all 87 entries in the Linux local `manifest.sha256` and all 83 original entries in the Darwin attempt03 local manifest: all matched before this review addendum. The Darwin manifest's `review.md` entry is refreshed after this addendum; original evidence entries are preserved.

Linux `runner.status` and `ssh-launch.status` are both zero. Hash-verified Linux `cleanup.json` records the inner runtime absent and the exact empty outer scope `/root/.local/share/agent-builds/rhai/unix-wait-29a33c10da` removed with `rmdir`, retired outer identity device 58 / inode 117279741. The original inner runtime identity is device 58 / inode 117279774. It also records original logs readable and GREEN fixture ESRCH. This reviewer relies on that exported contemporaneous remote retirement readback and did not rerun remote commands or reprobe historical PIDs.

Darwin `cleanup.json` records both runtime and scope absent, logs readable and GREEN fixture ESRCH, with retired outer identity device 16777234 / inode 226039451. That matches this review's earlier independent observation of the exact empty outer scope. A fresh local read-only check now confirms both the outer scope and its recorded inner runtime remain absent. The foreign dirty fixture still hashes to `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`.

No build, test, product change, cleanup or historical PID signal was performed by this addendum. No further execution is required for this unchanged regression's reviewed rows.
