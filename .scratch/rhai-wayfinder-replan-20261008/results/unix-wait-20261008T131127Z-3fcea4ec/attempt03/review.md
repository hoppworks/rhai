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


## Darwin package-minimum process and native i32 correction addendum — 2026-10-08

**Scoped verdict: accept the meaningful selected lifecycle/report/feature outcomes below, with the two explicit evidence restrictions recorded here.** Retain the initial **53 raw GREEN executions / nine profiles** and intended X20 RED101, then the separately completed **three Darwin and three Linux i32 GREEN executions**. Exclude the one directly invoked idle scenario helper from semantic acceptance, and keep actual already-waiting sync cancellation unproven. Neither restriction invalidates the original Child.wait decoded-expansion acceptance or the other source-bound native results. No A–F, all-Unix, Windows or integrated release completion is inferred.

This is appended to the actual existing combined report in `attempt03/review.md`; no review.md exists at the Unix result root and no duplicate root report was created. The entire earlier 18,956-byte report prefix, SHA `e35c2779a059292b6fcf8cff46fcb0df94c92e763ccd139ab6b35a0e01a543e9`, remains verbatim. Current project AGENTS SHA remains `06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c3f7ce119d7c5de`; loaded installed Wayfinder remains revision `f3fc5632f401156837ee3872f14fe33ccf1024ea` / SKILL SHA `9be7b478c389605a24517d27752f278933588da97a1b5921b165f455edf4c5b7`. Read the current plan's Unix-process/matrix/readiness/ownership requirements, now SHA `2743742720a62511a3eba707d62eb75382217adede77bbca10862f8f900ba32e`. Owner autonomous implementation authorization remains governing; the disabled old global layer was not read. This review performed no builds/tests/native processes, cleanup, product edits or commits.

### Frozen sources, cast and original integrity

Reviewed the original evidence in `../../darwin-process-minimum-20261008T153851Z-a0169b56/`, its `i32-correction/` and `linux-i32/`: proof/failure analysis, inputs, helpers/payloads, original command/compiler-artifact/list/test logs, status/result/cleanup, scopes, and Linux launcher/admission/export manifest. Independently verified every **305 manifest entries**, SHA `0b624fa2da4e18069b71b27ccab4ca2269b7efe25cc35929077dfa2a0569c721`; only the manifest itself lies outside its coverage. Independently recomputed all **30 native Linux exported files** by byte length and SHA against remote-export-manifest.json, SHA `afb2fa2a12f4e48fcb0ec3e6888be60fef0bb2a74a68808255c4d1050b9f65cf`.

The retained ef423 source archive is SHA `635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f`, previously independently verified. Every invocation uses accepted lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` and the byte-identical owned patch `e57f1efff98d7457229fe5512ed556ba5c09defe44155f1c5651c56b5b8a17d6`. Independently matched that patch to the exact committed ef423→da115 example/net-connect/net-listen/sys-process diff. It contains no dirty foreign fixture or backend overlay. The source-revision field denotes `da115c618c39fb1eca93aeba90a92478f09f5e29`; unrelated later net instrumentation is not incorporated into these process builds or claimed as TCP proof.

All three saved source bindings match current unchanged production/report inputs, the committed fixture, and the applicable test phase:

| Bound input | SHA-256 |
| --- | --- |
| Initial/committed tests/sys_process.rs | `f7055a0a6161b6d3b63be9ee03b0aaf0d6611c5cc95af7387d3d68eef5e03bd1` |
| Corrected/current tests/sys_process.rs | `45eb313e2352d148d0506b01a4f6ede917811336944cb1f84e49f77de9423220` |
| tests/sys_process_report.rs | `b081e8de1174433bd8ef5668945bfdda7b81fdcdeb6ef1b1d92a2c04d6f5c53f` |
| Committed shared child fixture | `1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217` |
| src/packages/sys/process/unix.rs | `55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713` |
| Cargo.toml | `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e` |
| build.rs | `78adf9eeea2957e1aa1bd96ee260e43806476a07d665c2ed27db55bc101ed335` |

The entire corrected file equals the committed initial file with exactly one replacement: `libc::SIGKILL as i64` → `libc::SIGKILL as rhai::INT` in the real signal/reap assertion. Both frozen correction copies and the current working source are identical. SIGKILL remains the same expected numeric signal; default-width INT is unchanged, while only_i32 now compares matching types. No implementation, signal, exit, timeout, output or reaping expectation was weakened. The foreign dirty shared fixture remains SHA `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2` and was neither used nor changed.

### Explicit evidence exclusions and readiness finding

**[P2, evidence classification] Direct `shared_child_contract::scenario_entry` is an idle helper pass.** The baseline skip regex excludes fixture/isolated/measurement/resource_census names but misses this helper. Its committed body immediately returns unless its scenario environment variable is supplied. The original `row0-sys_process-28` is a direct standalone invocation with empty stderr and 0.00-second libtest completion, without a scenario/fixture readiness/closure observation. Preserve its raw GREEN status, but do not count it as lifecycle verification. Therefore baseline41 consists of **40 supported assertions plus one idle helper**, and the initial53 contain **52 meaningful selected assertions plus that helper**. The separately selected real controller tests explicitly env_clear/set the scenario and exact child entry, exercise Engine operations, inspect child records and check controller/fixture ESRCH; their evidence remains valid. This correction to accepted counts needs no rerun.

**[P2, readiness] The archived sync waiter signals before public wait entry.** In committed `sync_wait_cancel`, after the barrier the worker sends started_tx and only then calls Engine `child.wait(10.0)` (or INT under no_float). The main thread treats that signal as entered wait and immediately calls public `child.kill()`. A schedule in which kill completes before wait begins still returns the cached terminal report, passes waited.is_ok(), joins and reports final reap. Original `row1-sys_process-1` has no actual wait-entry/pending observation, so this pass accepts shared-handle kill, successful bounded waiter return/final wait and ESRCH, **not cancellation of an already outstanding wait**. The canonical X31 requirement expressly includes shared wait-entry cancellation. Keep that criterion open until source-owned, bounded actual-entry evidence is available. This is an oracle gap, not proof of a backend lock/cancellation defect; no foreign fixture change is adopted to repair it here.

The baseline's deliberately excluded names are the fixture entries, opt-in overhead measurement, previously accepted new decoded-expansion selector, and `scenario_panic_releases_and_reaps_the_owned_fixture` (its name matches fixture). The latter is a real regression, so it is unexecuted by this package and remains outside its verdict, even though the panic-expectation control ran. Exact GREEN outputs all have zero ignored tests, but a zero-ignored raw pass is insufficient to make the idle scenario helper meaningful. Darwin cfg-absent Linux reaper/census/poll cases and other unselected setup/fault/lifecycle selectors also remain open.

### Native control and selector binding

Independently checked every listed compiler artifact, command cwd and features, successful build-finished record, unique selected name in each original --list, matching executable path, exact test argv and native status. All **59 raw GREEN executions** (53 initial + 3 Darwin correction + 3 Linux correction) execute one exact listed selector with `--exact --nocapture --test-threads=1`, report one passed, zero failed and zero ignored. None are zero-test filters. Excluding the idle helper leaves **58 supported selected assertion executions**, with the one sync wait-entry claim restricted as above. Report/configuration assertions are distinguished from actual child execution below.

Darwin environment readbacks identify native macOS27.0.1/arm64, Rust1.77.2 and the existing Rust1.93.0 endpoint toolchain. Compiler argv use the respective `cargo +<version>`, --locked, exact features with testing-environ, and only sys_process/sys_process_report targets. Linux identifies native Linux7.2.8/x86_64, actual rustc1.77.2, and directly pins cargo/rustc/rustdoc under `/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/`. This package saves rustc --version readbacks and the selected Cargo route, rather than a separate Cargo --version transcript. No cross target is used. Linux compiler paths consistently resolve the private source suffix under /var/roothome while command cwd/target use /root, as in the already accepted native evidence.

| Native profile | Raw exact GREEN count | Accepted scope |
| --- | ---: | --- |
| Darwin1.77.2 sys | 41 | 33 actual process/control selectors + seven report/configuration selectors; one idle scenario helper excluded |
| Darwin1.77.2 sys,sync | 3 | Empty normal output; shared kill/wait/reap with wait-entry restriction; Send/Sync representation |
| Darwin1.77.2 sys,no_float | 1 | Empty normal output with feature-correct integer option |
| Darwin1.77.2 sys,sync,no_float | 1 | Same normal-completion/shared-build endpoint |
| Darwin1.93.0 sys,sync | 1 | Retained promised X20 normal-completion endpoint |
| Darwin1.93.0 sys,no_float | 1 | Retained promised X20 integer endpoint |
| Darwin1.93.0 sys,sync,no_float | 1 | Retained promised X20 shared/integer endpoint |
| Darwin1.77.2 sys,net,no_index,sync,metadata | 3 | Real scalar process cwd/reap and omitted run_raw; scalar report/diagnostic access; Send/Sync representation |
| Darwin1.77.2 sys,net,unchecked | 1 | Script output option cannot raise host stdout/stderr cap |
| Darwin1.77.2 sys,net,only_i32,no_float correction | 3 | Previously stopped empty completion, host caps and corrected real signal/reap |
| Linux1.77.2 sys,net,only_i32,no_float correction | 3 | Same frozen source and same three public/OS oracles |

The initial X20 control changes only the selected empty-output function's unique `!timed_out` assertion to `timed_out`. Its original build/list succeeds and selected test exits **101** at that exact assertion, naming run_io_contract_empty_output and one failure. In-memory reconstruction yields RED test SHA `6d7791de6ac19bcdaf2f63474aca90bc86c3961d91b3b4067e86225af167ee6b`; this is reconstruction from the pinned helper/source, not a separately saved phase-file hash. Recorded RED executable SHA is `335cf64ae3db32d63077cb18ecbf085b166732665770ecd9c4325a46f83faa20`. The helper restores the exact original source, checks its saved hash, rebuilds and runs baseline's corrected X20 (`row0-sys_process-19`) with executable SHA `8bc892204dc33ceecd65bfaaced1d7da678bcce9240a3d2b03ff57935f1196f6`, exit0, actual empty streams, child-written exit0 record and ESRCH. This is a source-rebuilt wrong-oracle control, not a same-binary claim or a product defect reproduction.

### Supported public lifecycle/report assertions

Public run/run_raw/spawn operations use the actual registered SysPackage/Engine and real OS. Independent child records/host reads and exact exit/reap checks substantiate success/nonzero exit, absent exit code for SIGKILL, raw separate streams including invalid UTF-8, lossy decoding, empty output, string stdin, concurrent blob stdin/output and immediate stdin EOF. Default/nonmatching allowlist denials and missing executable/cwd cases require typed Denied/NotFound and absent protected markers, with a successful child-record control proving those markers work. The argv fixture compares fresh NUL-delimited host bytes including empty/space/quote/metachar arguments and absent shell-expansion marker. Child-only environment clear/override/removal preserves parent environment and compares explicit removed-versus-inherited PATH records. Capability cwd replacement compares against the opened permitted directory; the scalar no_index case checks host canonical cwd, child-record ESRCH and missing raw collection API.

Output-limit selectors distinguish exact cap from cap+1 separately for stdout/stderr, require the OutputLimit primary cause and exact bounded prefix/completeness, compare independent stress input records and require ESRCH. The same host-cap test passes unchecked and corrected i32 without allowing a larger script option to increase host authority. Finite timeout fixtures have active stdout/stderr and blocked stdin, require bounded partial bytes/incomplete capture/timed_out and independent child reaping; unit timeout legitimately disables only the configured deadline for its finite hold fixture. No primary-cause or text-limit branch is silently substituted for those assertions.

Managed lifecycle originals include real leader/worker/leaf and group identity observations, shared final/nonfinal-drop liveness probes, both kill_on_drop policies, public kill/normal leader-exit/escaped-leader handling, and a separately alive sentinel preserved until fixture-owned cleanup. Escaped holders remain alive outside the managed group while capture is bounded/closed; original readbacks include actual pipe-probe EPIPE, leader ESRCH, and subsequent exact fixture release/reap before terminal cleanup. Post-reap cancellation does not pretend an ordinary wait completed while a held pipe remained open. Direct-child drop-false/try_wait originals similarly prove actual readiness, live challenge response, eventual completion and final ESRCH.

The committed shared controller module isolates environment in its bounded controller child, supplies actual atomic ready/exit/challenge records, and compares stable cloned wait/try_wait snapshots after complete finite I/O. Script throw has a fresh live-child challenge and intended Rhai error, with wrong-message control rejected and parent/controller/fixture reaping independently observed. Panic-expectation rejects both successful and wrong-panic controllers; those intentional nested panic101s are controls inside an outer GREEN, not unexplained crashes. The unselected intended-panic regression itself is not accepted by this package. The sync waiter outcome has the specific readiness limitation above.

The seven baseline report/configuration tests and the changing feature report cases construct Rust ProcessReport/causes and expose them through Engine or Rust accessors. They support old-error classification, primary-cause/snapshot fields, copied blob/diagnostic immutability, absent/signal getters and Send/Sync sharing. **They do not launch a native child** or independently prove real failure cleanup diagnostics. Their narrow API/accessor outcomes are accepted, without turning constructed reports into lifecycle evidence.

### Honest partial status, i32 repair and cleanup

The initial invocation remains runner.status **1** / result.accepted=false. Its last row9 build exits101 before any selector, with original E0308 at tests/sys_process.rs:4580: expected i32, found `libc::SIGKILL as i64`; the extra compiler error is the abort summary. This is test-source feature incompatibility, not a meaningful runtime RED. Nine preceding rows and their 53 raw assertion statuses are preserved without relabelling the entire run GREEN.

The correction compiles/runs only sys,net,only_i32,no_float's two previously stopped selectors plus the affected signal selector; it repeats no previous baseline/X20 profile. Darwin correction executable SHA `a2ef2c8eb1537ce4c1eb5e63a7bc92833af680b391be4b1a3cf6b0fea6329919` and Linux SHA `6782216ad35b590bcc4c538a0290a9fdb44e0af1b274bb8b9307676c69e31ee0` each bind their three exact GREEN0 originals. Signal logs on both OSes observe signal9, unit code, success=false, timed_out=false, complete streams, child-record PID and actual kill(pid,0)=-1/errno ESRCH. The two correction runners exit0 and accept true. Same expected signal/default-width semantics justify retaining earlier rows without a broad rebuild.

All helpers operate in an owned source copy with private Cargo home/target, two jobs, disabled Python bytecode and cleared compiler override flags. Cargo and selected tests have 600-second and90-second subprocess bounds. Shared controllers have a24-second external watchdog and exact Child kill/wait guard, fresh scenario roots and closure receipts; successful fixtures independently release/reap before deleting owned records. Linux launcher has a600-second scoped-runner bound and source admission observes no compiler process, adequate available memory/disk. Stored runtime byte counts are final samples, not continuous quotas: initial4,083,937,280; Darwin correction962,572,288; Linux correction1,205,227,520, each below the helper's checked8GiB final limit.

Initial Darwin exact runtime `/Users/hoppworks/.local/share/agent-builds/rhai/darwin-process-minimum-qug9u80c/agent-build-escdy770` is inode226392365; outer scope is device16777234/inode226391685/uid501. Darwin correction runtime `/Users/hoppworks/.local/share/agent-builds/rhai/darwin-process-i32-k8o3xflp/agent-build-0slycd5o` is inode226434992; outer inode226433742/uid501. Native cleanup receipts bind their matching original scope identities and runner1/0 respectively, retain originals and report exact runtime/scope absence. Fresh read-only local checks confirm all four exact paths are absent. Linux native cleanup verifies outer identity device58/inode117323067/uid0 before exact empty rmdir and records runner0 plus absence of runtime inode117323072 and outer scope. This review relies on that exported native receipt, performs no remote re-execution or historical PID signal, and does not infer interruption/process-tree closure solely from directory absence.

**Updated acceptance boundary:** supported selected Darwin package-minimum and promised X20 endpoint outcomes, plus the exact corrected i32/no_float public signal/normal-output/host-cap outcomes on Darwin and Linux. Keep idle helper counts out of semantic proof, actual sync wait-entry cancellation restricted, unselected setup/fault/census/first-cause/full feature cases and Windows/A–F/release gates open. The original decoded-expansion eight platform/profile acceptance remains unchanged. Only this report was extended; the original attempt03 manifest's review.md entry will need its new report hash refreshed by the coordinator, while its original execution entries remain untouched.
