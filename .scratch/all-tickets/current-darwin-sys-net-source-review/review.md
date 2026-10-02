# Darwin sys/net prepared source review

Disposition: source package is **not ready for acceptance dispatch**. Three high-severity coverage/cleanup defects and one medium-severity receipt defect need a consolidated correction and affected source recheck. No native outcome is established by this review.

## Reviewed identity and instructions

- Immutable prepared commit: `2d52bf0b87a684b87222436795dcfc73875a7ce8`.
- Parent: `abbad1ec2d2dac83b64a481b7c8580d5ea95304c`.
- Owner checkout: `/Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai`; clean when inspected, no edits made.
- Frozen production/test archive revision: `a2d7a8c2ace21e63c18b2e64cdce74e5e10afc94`; archive SHA-256 `551c03dbe3f4550db1b144b3e65d83f5bc66c132c1a9cffa59c83fce16bc41e1`; compatible lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Current agent-skills revision confirmed: `958a4538b0191c53f2ccb2cd00d96c15045fbf68` (`Clarify owned build cleanup and explicit retention limits`). Read disk `config/common/AGENTS.md`, project `AGENTS.md`, `config/roles.toml`, updated `config/codex/agents/expert.toml.tmpl`, OCR-delegate, campaign and e2e-proof. No descendants spawned.
- Scope: one independent combined source review only. No Cargo, Rustup installation, native API tests, process fixtures/controls, measurement 85, build dispatch, source mutation, readiness-gate mutation, upstream communication, push, or merge.
- `git diff a2d7a8c2 2d52bf0 -- src tests Cargo.toml build.rs codegen` was empty, establishing that the inspected affected code/test inputs match the frozen revision.

## Material findings

### F1 — High — Actual EILSEQ early returns are accepted as successful coverage

Primary location: `.scratch/all-tickets/check-current-darwin-sys-net-behavior.py:397` and `:419` (parser lines 386–426).
Affected dependency: `tests/sys_fs.rs:731`–`:734` at frozen a2d7. Supporting test gap: `.scratch/all-tickets/test-current-darwin-sys-net-behavior.py:62`–`:73`.

When Darwin rejects the non-UTF8 filename with EILSEQ, the frozen test emits `filesystem rejects non-UTF-8 fixture with EILSEQ: ...` and returns normally. Libtest reports it as passed, with **zero ignored tests**. The runner only detects libtest `... ignored` lines/counts. Its positive commands correctly include `--nocapture`, so the diagnostic is exposed; the defect is failure to classify that diagnostic, not hidden captured-success output.

The pure regression injects the real diagnostic and a successful two-test summary. The current parser returns `coverage_found=true` and `ignored_tests=[]`. Thus a required assertion never runs while its Darwin row may be accepted. The shipped source check passes because it invents a libtest ignored result that the frozen test does not produce.

Related coverage holes in the same parser: it does not inventory named tests or reconcile names/counts; a one-test successful summary for `sys_fs` is accepted despite missing the frozen target's remaining tests. Repeated summaries are accepted because only the last summary for a target is used. Pure injections reproduce both outcomes. The exact-target check catches repeated `Running` headers, but not duplicate summaries or missing individual tests.

Correction: retain `--nocapture`, explicitly recognize the real early-return marker and record the named test/row as uncovered; reconcile a frozen, feature/OS-specific named inventory and exactly one summary per target. Make the source regression model the frozen test's actual successful-return output, plus missing/repeated named coverage. Do not relabel that early return as native acceptance.

### F2 — High — Cleanup readback treats unknown process state and reparenting as disappearance

Location: `.scratch/all-tickets/readback-current-darwin-sys-net-cleanup.py:21`–`:22` and `:44`–`:45`.

`identity()` maps permission errors, timeouts, malformed output, and other query failures to `None`. `main()` treats `None` as absence and can print `cleanup_readback=PASS` for every recorded identity even though no reliable query succeeded. This conflicts with the current rule that permission errors do not prove stopped membership.

The complete tuple comparison also includes PPID and PGID. A recorded process with the same PID/start identity and command that survives after reparenting is treated as absent because its PPID changed. A mocked live helper with original start/command/PGID but PPID 1 produces `cleanup_readback=PASS`.

Pure receipts show both defects without invoking `ps` or creating processes. They also establish that an injected `PermissionError` becomes `None`.

Correction: distinguish confirmed absence, observed identity, and query failure; fail closed on unknown state. Use stable PID/start identity for survival matching; PPID/PGID are custody observations, not evidence of a new process. Explicitly verify the owned group/descendants needed for the claimed cleanup scope. Currently the helper records itself, its supervisor, and direct command PIDs; sampled descendants are counted but not recorded individually. The supplied readback therefore establishes only those enumerated identity checks, even after its false-pass behavior is corrected. It does not independently enumerate all leftover group members or descendants.

### F3 — High — Scoped TMPDIR makes the Darwin system-prefix alias tests vacuous

Location introduced by this runner: `.scratch/all-tickets/check-current-darwin-sys-net-behavior.py:555`–`:564`.
Affected frozen assertions: `tests/sys_policy.rs:325`, `:339`, `:341`.

The helper gives all normal test fixtures a TMPDIR inside the private runtime under `/Users/hoppworks/.local/share/agent-builds/rhai/...`. The two Darwin-specific policy tests derive their alleged `/private/var` spelling by replacing `/var/` in the fixture path. There is no `/var/` in this scoped path. The replacement is a no-op, so the alleged two spellings are identical. The tests exercise same-path reads and permissions twice, without exercising the Darwin `/var` versus `/private/var` alias behavior that their names promise.

The pure path transformation reproduces identical paths. This is a concrete interaction between the new environment custody and unchanged frozen tests, rather than an assertion about observed native results. General ancestor-symlink tests still exercise their own distinct cases, but cannot substitute for these system-prefix cases.

Correction: use meaningful distinct Darwin paths with explicit assertions that the spellings differ, while preserving private resource custody. A separate bounded read-only real-system alias proof can avoid foreign writes; alternatively revise the fixture design and frozen source provenance deliberately. Until such proof exists, report the system-prefix alias requirements as uncovered. Do not move temporary resources outside the owned runtime without defining their exact custody and cleanup.

A concrete scoped correction candidate is available under `cfg(target_os="macos")`: for the existing absolute fixture `/Users/.../runtime/tmp/fixture`, derive `/var/../../Users/.../runtime/tmp/fixture` and `/private/var/../../Users/.../runtime/tmp/fixture`. On the usual Darwin `/var -> /private/var` layout, both traverse back to `/` and then the same owned fixture, while retaining distinct real system-prefix spellings. Before constructing the Engine root or attempting any operation, assert the two strings differ and independently canonicalize both to the exact owned fixture. Create/read fixture contents using its ordinary central-runtime path; configure and exercise policy via the two verified spellings. The existing API already tests OS resolution of configured roots and absolute parent components, so this is consistent with that intended contract, subject to a meaningful regression and native proof. Fail explicitly if the host layout does not satisfy the canonical assertions; do not fall back to duplicate paths. This changes test sources, so update source/archive pins honestly and invalidate affected test proof; preserve unrelated Linux proof where applicable. No such change or native query was made in this review.

### F4 — Medium — Exported receipts contradict the execution and acceptance contract

Locations: `.scratch/all-tickets/check-current-darwin-sys-net-behavior.py:665`, `:484`–`:486`, `:679`–`:685`; contract `:12`–`:17`.

All nine positive Cargo commands use `merge_streams=True`, which directs stderr into stdout and leaves the advertised stderr file empty. The contract promises separate stdout and stderr for every Cargo command. The metadata does honestly record `merge_streams`, but the original separate streams cannot be recovered for independent readback.

Exported `successful_positive_rows` and `all_positive_rows_succeeded` depend only on status 0, ignoring `coverage_found`. A coverage-rejected status-0 row is counted as successful; if that happens on row nine, the exported summary can say all rows succeeded despite the helper's failure. Separately, final `result.json` unconditionally lists five `uncovered_runtime_rows`, including rows just successfully executed; two names do not even match `TEST_ROWS`.

Correction: align the contract and preserved logs, preferably retaining separate streams plus an ordered combined parsing receipt. Compute success from status **and** accepted coverage, and derive uncovered rows from actual execution/coverage rather than stale constants. Keep source-only receipts explicitly distinct from native acceptance.

## Nine rows and five controls

All nine declared rows match the intended non-process package: baseline; no_index; net/no_object; metadata+serde; sync; only_i32+no_float; unchecked; no_index+sync+metadata; f32_float. Target selection is explicit. Empty targets, Cargo ignored/measured/filtered counts, missing target headers, and failed command statuses are rejected. Individual named-test completeness and internal skips are not currently enforced (F1).

The five controls select exact named tests with `--exact --nocapture --test-threads=1`. Their environment seams are present in frozen inputs: capped filesystem read (`sys_fs`), peer text read (`net_reads`), exact peer blob write (`net_writes`), fresh host file readback (`combined_sys_net`), and independent no_object peer bytes (`net_no_object`). All are enabled in their selected feature sets. The intended assertion payloads agree with those tests. Classification requires status 101, the named panic at the corresponding test file, exactly one failed test summary, a named failure entry and the intended diagnostic context. A skipped control/status 0 or an incidental compile error is rejected. The provided source tests meaningfully demonstrate incidental-101/context rejection, but do not prove any control ran natively.

The filesystem read control compares Engine output against independent fixture truth and rereads the unchanged host file; the write/combined controls observe real peer/file state separately from the script operation. Policy denial tests observe protected host state. Environment fixtures run in cleared child environments, so they do not mutate the parent environment. Those environment fixtures are test-harness child processes, not process API acceptance fixtures or measurement 85.

## Custody, immutability, deadlines, export and error paths

- Staged source and lock are digest-checked; lock and seven-manifest provenance is recorded and rechecked around commands. The private toolchain installs Rust 1.77.2 with `--profile minimal --no-self-update`, using private RUSTUP_HOME/CARGO_HOME/HOME; direct rustc/cargo binaries and native Darwin arm64 versions are verified.
- Child commands use an explicitly built environment rather than inheriting arbitrary Cargo/Rust flags. Paths for HOME, Cargo/Rustup homes, target, source and temporary fixtures derive from AGENT_RUNTIME_DIR. Shared rustup is used only as the existing executable; installation homes are private. Runner package hashes match the current existing run_scoped/pyguard files inspected on disk.
- Archive extraction rejects absolute/upward paths, unsupported members and links escaping the source root. For this digest-pinned git archive, no material extraction defect was identified. Existing worktrees/foreign caches are not cleanup targets.
- Resource limits are periodic observations, not continuous maxima: jobs 2, 16 descendants, 2 GiB RSS, storage preemption 1.5 GiB, storage hard cap 2 GiB. Sampled maxima are honestly labeled. A whole group cleanup belongs to the outer run_scoped supervisor; helper error paths terminate/reap the active direct child, not the whole group themselves.
- Helper has a 510-second cooperative work deadline and 540-second cooperative export-inclusive deadline. Some hashing/extraction/copy work and 5-second monitoring queries occur between checks. Launch must supply the existing runner's explicit whole-invocation timeout within the approved custody package; cooperative helper checks alone are not a strict wall-clock bound.
- Early runtime/helper/supervisor receipts precede stage validation. Command statuses and partial rows/controls are exported on ordinary failures and cooperative interruption where possible. Export destination collision fails rather than overwriting prior evidence. A partial export must remain incomplete; the final result alone is not acceptance. Independent readback needs F2 correction and must also verify raw row/control receipts, source/lock/helper identity, outer status, runtime absence, owned group emptiness and empty-only scope retirement.
- No new implicit setup approval gate is warranted. These are concrete source readiness corrections and execution prerequisites within the existing authorized package. Native execution remains outside this review.

## Coverage and retained evidence

| Changed file | OCR result | Review result |
|---|---|---|
| check-current-darwin-sys-net-behavior.py | Reviewable, system Python rules | Reviewed; F1/F3/F4 |
| readback-current-darwin-sys-net-cleanup.py | Reviewable, system Python rules | Reviewed; F2 |
| test-current-darwin-sys-net-behavior.py | Reviewable, system Python rules | Reviewed; F1 regression gap |
| current-darwin-sys-net-behavior-contract.md | Excluded: unsupported_ext | Manually reviewed; F1/F4 contract mismatch |
| current-darwin-sys-net-behavior-source-prep.md | Excluded: unsupported_ext | Manually reviewed; source-only receipt limitation |

`total_files=5`, `reviewed_files=5`, `skipped_files=0`, `coverage_rate=100%`. OCR alone selected 3/5; both exclusions were manually covered. `ocr-preview.json` and `ocr-rules.json` preserve deterministic discovery/rule resolution; the fork origin was confirmed as `https://github.com/hoppworks/rhai.git`. No OCR installation or provider call occurred.

Affected context inspected: all ten selected Rust test targets (sys_env, sys_fs, sys_policy, net_connect, net_listen, net_reads, net_writes, combined_sys_net, net_no_object, net_metadata); sys_support fixture helpers; relevant sys filesystem alias resolution/file-read code; existing scoped supervisor and pyguard; ticket06 and release-proposal. This was an impact-based source review of the new acceptance package, not a repeated repository-wide production review.

Original compiler/example proof remains preserved by reference in the root checkout `/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai`: `.scratch/all-tickets/current-feature-compilation-evidence/root-readback.json` and `.scratch/all-tickets/current-msrv-examples-root-readback.json`. These receipts were read narrowly; their compiler/example applicability remains unchanged. They do not prove these nine Darwin behavior rows. Linux acceptance remains Linux-only.

Original review artifacts are in this unique directory: immutable five-file extracted `snapshot/`; OCR preview/rules; `pure-regressions.py`, `pure-receipts.json`, `pure-regressions.stdout`; `prepared-source-tests.stdout`; this review. The prepared source tests pass, while injected regressions reproduce the real orchestration defects. One rerun initially hit an owned fixture-directory collision after adding the alias regression; the pure helper was adjusted to create unique owned fixture directories and reran successfully. This was a source-test setup correction, not a native launch or implementation correction.

## Launch prerequisites after correction

1. Consolidate F1–F4 fixes and recheck affected classifier, cleanup and scoped alias behavior against an immutable revised package. Preserve unchanged control/production review conclusions.
2. Explicitly identify whichever real Darwin system-prefix proof replaces the vacuous checks; update archive/provenance if test sources change, or report that requirement uncovered.
3. Stage exact reviewed helper/contract, pinned archive/lock and existing scoped-runner inputs under the prescribed unique real stage. Verify content hashes independently before dispatch, not merely its basename.
4. Supply exact `DARWIN_PROOF_STAGE`, private `INTERRUPT_REQUEST=<stage>/outer-evidence/interrupt.request`, absent owned session scope, TMPDIR custody and explicit scoped timeout. Check the one-heavy-run Machine slot. Do not touch shared-home toolchains or foreign resources.
5. After native execution, independently read raw exact rows/named tests and intended controls, native versions, provenance and cleanup. Remove only this run's exact empty scope after reliable absence/group checks. Until then all nine Darwin rows/five controls remain unverified; full release acceptance and other platform/process requirements remain open.
