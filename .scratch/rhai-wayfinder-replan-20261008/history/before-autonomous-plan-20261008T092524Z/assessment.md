# Rhai remaining-work assessment

This is the evidence assessment for [the new map](map.md). The single current
execution instruction is [the autonomous implementation plan](implementation-plan.md).
It replaces no source, prior evidence, accepted ticket or coordinator history.
English is used for repository planning documents.

## Rule and repository baseline

- Wayfinder was loaded from the resolved installed path under
  `/Users/hoppworks/.local/share/mattpocock-skills/f3fc5632f401156837ee3872f14fe33ccf1024ea/`
  (revision `f3fc5632f401156837ee3872f14fe33ccf1024ea`). Its map/ticket rules and
  the local Markdown tracker note were read. The old global agent-skills layer is
  disabled and was not restored. Project `AGENTS.md` and project plans were used
  to preserve product/security facts; their obsolete wrapper and continuation rules
  do not govern this planning request.
- The October 6 report describes Tauron sessions and has no Rhai-specific finding.
  The October 7–8 monitor reports are historical hypotheses. Their useful warnings
  about composed-path checks and output parsers are retained, but current evidence
  supersedes their old X18/X19/X20 state.
- Repository snapshot inspected: branch `task/all-tickets-environment-recovery`,
  HEAD `ef423a516617e128835d54af16d75f559b2b1bce`. The worktree already had changes
  to `.scratch/all-tickets/coordinator-state.md`, `docs/sys-package-plan.md`,
  `examples/sys_process.rs`, and
  `tests/fixtures/sys_process_shared_child_contract.rs`, plus extensive untracked
  evidence. That fixture is foreign work. None of these existing files was changed
  by this plan.
- The current Goal `alle tickets umsetzen` was checked and is already paused. It
  remains paused; no Goal was created or resumed.

## Product requirements retained

The owner-approved source of truth remains Ticket 01–06, the release proposal, and
the requirement inventories in `docs/sys-package-plan.md` and
`docs/net-package-assessment.md`:

- Every behavior is accepted through the public Rhai `Engine`, registered package,
  and real OS fixture. Filesystem writes need fresh host readback; TCP needs an
  independent peer; child behavior needs child records, exact identity/lifecycle
  observations and reaping. Compile success alone is not runtime acceptance.
- Policy is deny-by-default; roots constrain host filesystem calls, not what an
  authorized child can subsequently do. `DirectChild` remains distinct from
  host-selected `Managed` group/job supervision. Cleanup failure and inherited-pipe
  behavior must be truthful. No silent downgrade, unchecked PID sweep, parent
  environment mutation, or arbitrary-script sandbox claim is allowed.
- TCP is separate from `sys`: numeric IPv4/IPv6, host-granted connect and separately
  granted listen, ephemeral port 0, bounded operations/handles, exact bytes and
  partial progress, EOF/half-close, clone/close behavior, sync/cancellation. DNS,
  UDP, HTTP, TLS and async are out of scope.
- Required platform/version boundaries are core Rust 1.66.0 without OS dependencies;
  optional `sys`/`net` Rust 1.77.2 on native Linux, macOS and Windows; `std` required;
  explicit rejection of `no_std` and WASM. `sys + no_object` has an accepted
  intentional diagnostic. `net + no_object` is documented as free-function capable,
  but its proof must be source-bound.
- The accepted semantic feature matrix is package alone and combined; `sync`,
  `no_index`, `metadata+serde`, `only_i32+no_float`, `unchecked`, the
  `no_index+sync+metadata` interaction, and `f32_float` duration bounds. This is
  not a Cartesian product for every behavior test. Exercise each combination where
  it changes registration, types, limits, sharing or duration semantics; negative
  rows must fail with the intentional diagnostic.
- Ticket 06 also requires real native process cancellation/reaping evidence and
  Windows test-run ownership after interruption. That ownership outcome remains
  binding. The old proposed supervisor/monitor implementation is not itself a
  product contract.
- Previously authorized destination and attribution remain: private fork
  `hoppworks/rhai`, `main` only, lowercase `hoppworks`; never write the public
  upstream. This planning request authorizes none of those writes.

## Old assumptions: confirmed, rejected, and open

| Claim | Finding and source | Consequence |
|---|---|---|
| X18 was still blocked because its parser could not see RED. | The current `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/proof.md` binds the same source/test/lock/features for valid RED in attempt 02 and restored GREEN in attempt 03. The earlier attempt 01 used the wrong Cargo cwd and never reached Cargo. The combined review is READY. | Reuse the accepted Linux and Darwin rows. No X18 rerun. Other platforms/features/MSRV remain open. |
| X19 Linux was only one of many rows or the old run should be repeated. | `.scratch/all-tickets/darwin-x19-deadline-20261008/proof.md` and the Linux attempt-10 proof accept eight Linux and eight Darwin direct `run` timeout RED/GREEN rows: Rust 1.77.2 and 1.93.0 × standard, `no_float`, `sync`, `sync+no_float`, same test/lock and real-child readback/reaping. Combined reviews are READY. | Reuse those exact direct-timeout rows. They do not close other X19 paths or all of Ticket 03. A 100 ms API deadline is not a scheduler latency promise. |
| X20 was complete, or its mutation collision meant its results were invalid. | Linux attempt 01 selected a same-named assertion in multiple tests before Cargo; attempt 02 isolates the intended test and is accepted for eight rows (Rust 1.77.2/1.93.0 × four profiles). Darwin attempt 01 is accepted for the named standard 1.93 row. Both bind the same test/lock, expected RED/restored GREEN, child record and ESRCH. | Reuse these named rows; X20 remains partial. Do not rerun X20 wholesale or mark the ticket complete. |
| A parent counter such as 1/6 proves little work was accepted. | The current 6.7 criterion crosswalk records rows through X38 and several combined reviews; it has named applicability, not a parent completion count. | Use criterion/source/test/platform/feature binding as the status. Do not infer completion from a count. |
| The latest X23 `no_float` stop was a runner failure. | `.scratch/all-tickets/darwin-x23-x24-20261008/attempt-01/outcome.md` records explicit source cwd, pinned archive `ef423a516617e128835d54af16d75f559b2b1bce`, lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, Darwin arm64/macOS 27.0.1, Rust 1.77.2. `sys` and `sys,sync` passed; `sys,no_float` reached Rhai parsing and rejected `child.wait(0.0)` before readback. This is an actual example/feature mismatch. | The dirty `examples/sys_process.rs` change chooses `child.wait(0)` under `no_float` at all three call sites. It is unverified; verify only affected `no_float` rows after source review. Reuse the unchanged standard rows. X24 has separate accepted evidence and was not run in this attempt. |
| Windows has completed native package acceptance because its baseline tests were green. | `.scratch/stdlib-wayfinder/windows-vm/README.md` records Windows 11 Pro 26H2/build 26300.9457, Rust 1.93 MSVC, 21 policy + 5 env + 19 fs tests, and a controlled filesystem write/truncate/append check with independent readback. The other 44 baseline tests had no individual failing controls. The README says process, TCP, symlink/junction and release matrix remain unverified. Current live VM/guest readiness was not checked in this planning pass. | Reuse the named filesystem proof only at its pinned inputs. It is not the package MSRV or process/TCP acceptance. First do a later read-only live readiness check before any guest command. |
| The proposed Windows C# runner and independent monitor are required implementation architecture. | `.scratch/windows-scoped-runner/acceptance.md` records a static candidate only, no native execution, and no independent monitor. `windows-runner-gate.md` states the proposal, not a tested guest behavior. A separate saved screenshot was black; the VM README later records cold-boot/desktop history. These are historical and do not establish current guest state. | Preserve the accepted ownership/interruption outcome. The new route ticket selects the current public lease-client/monitor sources after static inspection; native readiness and interruption are not yet proved. Old fixed deadlines and harness architecture are not independent product requirements. Prior consumption remains history. |
| Old monitor reports establish today's Rhai root cause. | Oct 6 is unrelated Tauron work. Oct 7–8 provide date-bound hypotheses; the accepted X18–X20 artifacts and current X23 outcome resolve those named cases. | Keep original causes and results; do not inherit unrelated SQLx/UI/AUTHZ findings or stale X18 pending labels. |

## Reusable proof and artifact status

| Area | Reuse | Still open |
|---|---|---|
| X18 stdin `()` | Accepted Linux named rows and Darwin standard row; same-source RED/GREEN, actual child EOF, child-written PID/exit, independent file readback and ESRCH. Proof exists. | Only rows not represented by those proofs. No compiled target cache exists under the inspected X18 proof root. |
| X19 direct deadline | Eight named Linux and eight named Darwin rows across the two supported Rust endpoints and four semantic profiles; accepted proof files exist. | Other X19 paths and unrepresented platform/feature rows; don't recast direct-only as whole-ticket acceptance. |
| X20 normal-before-deadline | Eight named Linux and one Darwin standard row; accepted proof files exist. | Other X20 paths and unrepresented rows. |
| X21–X31 | Use each row's exact entry in `docs/sys-package-plan.md` §6.7. The crosswalk records partial/accepted Linux and Darwin cases for caps, signals, spawn/wait/try_wait/kill/drop, script throw, descriptor stability and sharing/wait-entry. | Only the listed open platform, feature, MSRV and lifecycle cases. Do not rerun a whole target to repair a wrapper's output classification. |
| X32–X33 | No native Windows embedded-quote argv or `.exe` suffix/PATH proof is recorded. | Both Windows behaviors. |
| X34–X38 | Named Linux and Darwin cases are accepted for several managed cancellation, setup-failure and escaped-pipe behaviors. §6.7 lists the exact rows. | Windows Job behavior, plus explicit feature/platform/fault gaps in §6.7. |
| Windows base | Historical image/toolchain and filesystem proof are retained in the Windows README. | Current live availability, native `sys`/process/TCP coverage, Windows-only policy/path rows and package-minimum feature proof. No guest cache reuse is verified. |
| Net and shared file handles | Existing ticket 04/05 decisions, Linux proofs, current net source and the named Darwin default sys/net coexistence proof remain available. | Only uncovered TCP authority/API/read/write/EOF/feature/native rows. Source/lock applicability must be checked before reusing older no-object or Linux examples. |
| Metadata/docs/examples and core compatibility | Current plan records accepted Darwin metadata/process-example rows integrated at fork main `04d9a797…`; existing core-minimum proof and relevant docs/readbacks remain available. | Only deltas since those exact proofs and the final integrated crosswalk; no example/metadata rebuild absent changed inputs or a concrete missing assertion. |
| Builds | Read-only `find` found no `target/` under the four inspected X18–X20 evidence roots. Prior records say other private targets/scopes were retired after export. | Proof/logs are reusable; compiled builds are not claimed reusable. Windows guest paths/caches were not verified. |

## Follow-up source findings

The autonomous-plan follow-up inspected the current product and runner sources,
not the live guest. Three concrete gaps affect the future route:

- `src/packages/sys/process.rs` registers its backend only under Unix; SysState
  cleanup/Child export are Unix-only and no Windows backend file exists. The
  Windows process example is currently a successful no-op. Windows requires
  implementation, not just another acceptance launch.
- No IPv6 cases were found in the inspected TCP integration targets. The accepted
  numeric IPv6 contract still needs real native loopback connect/listen or a
  truthful missing-infrastructure record; IPv4 evidence does not close it.
- The focused public `Child.wait` no-primary decoded-expansion test remains
  unverified. The historical Package B attempt03 result at its previously cited
  path is unavailable. Its startup/scope failures do not prove a product defect.
  Add the focused regression to the existing fixture layout; do not reconstruct
  an obsolete multi-stage launcher or treat a spent agent repair count as a new
  permission boundary.

The Windows route decision is recorded only in
[Choose the minimum safe native Windows acceptance route](issues/01-windows-custody-route.md).
It selects existing sources; it does not pass native custody. Old source pins,
wrapper roots and fixed execution estimates are repaired only where required for
that composed path. Foreign work, exact ownership and accepted readbacks stay
binding.

The default-core proof and its on-disk evidence-04 lock were also read back. The
lock SHA-256 is the same accepted `2ba4b3a0…` used by optional package proofs;
there is no need for a new separate resolution. The older `8bd35…` lock predates
the root libc dependency. A Windows-only optional dependency change still needs
a targeted core-minimum isolation check and exact lock provenance.

## Current execution proposal

The [autonomous implementation plan](implementation-plan.md) supersedes the
initial package outline in this new assessment. It is the only command sequence,
failure policy, matrix and completion crosswalk for later execution; no parallel
inventory or second coordinator plan is created here.

Its coherent packages are:

1. Verify the existing X23 no_float example correction on Darwin1.77.2; reuse
   unchanged standard/sync controls and complete only the two missing profiles.
2. Complete uncovered Unix process/report/lifecycle rows and the focused public
   Child.wait regression, using one bounded private build per compatible input set.
3. Prove the source-selected native Windows custody prerequisite with a small
   finite fixture and independent interruption/export/readback before Cargo.
4. Implement the missing Windows process backend and its native lifecycle, argv,
   capability-cwd, managed Job, report and real example acceptance.
5. Close only missing base sys and streaming file-handle native/semantic rows.
6. Close missing TCP native/semantic rows, including real IPv6 coverage.
7. Reconcile applicable proof and affected feature/MSRV/docs deltas, perform one
   integration review, then publish verified owned changes atomically to fork main
   under the later implementation instruction and existing repository boundary.

Every package defines observable results, exact existing target/selector entries,
planned missing tests, prerequisites, retained evidence, combined review and
export/cleanup. Native guest access and symlink privilege are not fabricated.
Independent Unix/sys/net work can proceed if a Windows prerequisite is missing.
No new human preference is unresolved and no routine approval loop is introduced.

## Retained execution principles

A repeat needs changed relevant input, an invalidated proof, an uncovered criterion
or a new unresolved assertion. Session/plan changes and parser errors alone do not
justify product reruns. Exact cwd and selected test presence are prerequisites;
RED uses exit status, intended assertion and final failed-test inventory rather
than same-line text. Pre-assertion infrastructure stops remain distinct from
product failures. New failure preparation is checked as a complete chain before
another expensive selection; another wrapper is not the default repair.

Related control/restoration/profile checks reuse an owned finite build when
inputs permit. Immutable build outputs and mutable fixture data remain separate.
Measured current capacity determines scheduling. Old invocation exceptions expire;
old agent budget estimates do not create new user approval requirements. Explicit
human ownership, access, publication and security boundaries remain binding.
Evidence is exported/read back before exact own-resource cleanup, and a valid
review/OS assertion is retained at its original applicability.

## Critical path and first later action

Current critical path: verify the X23 patch/inputs and its two missing profiles →
remaining Unix/process semantic rows → native Windows custody admission → missing
Windows backend and native contracts → uncovered sys/TCP and integrated matrix/docs
closure → owned fork-main integration. Base sys/TCP and Unix packages do not wait
for Windows if their own inputs are ready.

The most exposed assumptions are live Windows console/toolchain availability,
the composed monitor entry and native capability-cwd/Job guarantees. They have
small explicit admission controls and fail-closed handling in the implementation
plan. No Windows build can substitute for those observations. Native evidence is
not claimed by this planning decision.

First later action is the read-only X23 diff/input check in the plan's **Start and
freeze** section, followed by the two named no_float example commands only after
implementation authorization. Do not perform that first action during planning.

## Coverage check

All original P1–P14, E1–E5, F1–F23, X1–X38, R1–R7 criteria (87 numbered IDs),
Tickets01–06, file-handle extensions, TCP authority/lifetime/data, process
cause/report/compatibility, native platforms, required semantic features/MSRVs,
documentation/examples/performance and owner boundaries remain represented in
the implementation plan's complete coverage crosswalk. Named accepted Linux,
Darwin and Windows proof is retained; uncovered rows stay open. The plan is not
an executed acceptance result or a release-completion claim.
