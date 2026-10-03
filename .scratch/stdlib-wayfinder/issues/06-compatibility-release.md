# Choose supported platforms, features and release gates

Type: grilling
Label: wayfinder:grilling
Status: resolved (specification only)
Parent: [Plan a reliable Rhai host standard library](../map.md)
Blocked by: none

## Question

Which platform, Rust-version and Rhai-feature combinations must sys and net support,
and what evidence is required before a release is declared ready?

## Context

Core MSRV is 1.66.0; sys documents 1.77.2. Existing sys decisions exclude no_std,
no_object and wasm. The network reference fails metadata, sync, only_i32 and unchecked
builds. GitHub Actions are disabled on the fork. Native Windows baseline evidence
now covers 45 selected sys tests on Rust 1.93.0/MSVC, with an assertion control for
write/truncate/append (../windows-vm/README.md); it does not certify the release matrix.

## Resolution requirements

Define required versus intentionally unsupported combinations, preserve core MSRV,
and decide gated-package MSRV/dependency policy. Choose a bounded feature matrix
based on semantic interactions, including sync/no_index/metadata/integer modes.
Agree how Linux/macOS/real-Windows evidence will be obtained without implying Wine
or a cross-compile proves native execution. State release blockers explicitly.

Clarify API review and documentation requirements for sys file-handle compatibility
and TCP. Do not introduce a CI service or enable fork settings without authorization.

## Process API and release obligations from ticket 03

The owner requires managed process groups/jobs in the first version, alongside
explicit direct-child supervision. Review exact host-config spelling and the proposed
`SysError.process` report without implying existing Rust enum variants can change
without compatibility assessment. Native scope setup, cancellation, retained pipes,
normal completion and cleanup failures must pass on every supported OS. An unavailable
managed mechanism fails explicitly; silently downgrading supervision is prohibited.

## Verification resource lifecycle

Before another Windows build, adapt scoped execution to the guest: identify owned
process trees, bound their lifetime, isolate Cargo outputs/caches and fixtures, export
proof, and clean on success, failure and interruption. The POSIX run_scoped.py runner
cannot clean guest descendants merely by stopping an SSH process. Preserve the
accepted baseline and diagnostics until replacement evidence is accepted. Validate
the adapter's interruption cleanup before relying on it for native release gates.

## Owner resolution — 2026-09-30

The owner accepted the recommended concrete specification in
[the approved proposal](../../all-tickets/release-proposal.md).
Implementation, documented behavior and strict native/feature/MSRV proof remain
open campaign requirements. No remote publication is authorized.

## Current-source optional compiler prerequisite — 2026-10-02

Native Darwin arm64 Rust/Cargo1.77.2 successfully ran
`cargo check --locked --lib --features testing-environ,sys,net` at frozen source
`9f84aa6d8163257b4e3f3c2fe4a1c7d7b7c3cce6`, with compatible lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
Original logs, direct versions, command statuses and seven manifest hashes are in
`../../all-tickets/current-optional-msrv-evidence/`; `root-readback.json` confirms
outer0, every command0, exact runtime absence and empty-only scope retirement.
No relevant source, build script or Cargo-manifest change exists between that
revision and integration1928c068, so this compile evidence applies there too.
The private toolchain and caches were disposable, with no shared-home install.

This closes only the current sys/net library compiler prerequisite on Darwin.
Script behavior, tests/examples, other feature combinations and native platforms
remain open. Native process invocation count84 is unchanged; no fixture/control
or overhead measurement was run. The earlier release specification stays intact.


## Current Darwin optional compiler acceptance

The frozen4baf source passes direct private Rust/Cargo1.77.2 on Darwin arm64
for the previously accepted sys+net baseline plus all ten uncovered optional
feature rows. Original evidence: `.scratch/all-tickets/current-feature-compilation-evidence/`;
`rows.json` and independent `root-readback.json` identify every command, status,
version, compatible v3lock2ba4, manifests and exact runtime cleanup. Sampled
maximaRSS735200KiB/storage733948KiB/descendants7; export74.811s. Compiler-only
prerequisites are closed narrowly. Feature behavior, current native Linux/
Windows, process lifecycle, docs/examples and strict release acceptance remain
open. Earlier valid unchanged proof is retained.

## Current Darwin optional examples acceptance

Frozen source `1ca21e32eed2aa40287ba7e1282000add1dd49c7`, private direct
Rust/Cargo1.77.2 Darwinarm64 and accepted v3lock2ba4 passed one combined
`cargo build --locked --example sys --example net --features testing-environ,sys,net`.
The resulting examples execute the real Engine, scoped filesystem and loopback
peer. Fresh host readback observes `Rhaiting data`; independent peer receives
`ping`, and the script receives `pong`. Wrong file contents and wrong peer bytes
each produce their named assertion/status101; default expectations restored
produce status0. Assertion-only seams are compiled into private binaries;
production/example sources in the worktree are unchanged.

Original commands/logs/versions/source-lock-restoration/resource receipts:
`../../all-tickets/current-msrv-examples-evidence/`.
Independent readback: `../../all-tickets/current-msrv-examples-root-readback.json`.
Outer0, helper34.951s,49periodic samples, observed maxRSS794064KiB,
storage754776KiB,descendants6. Exact runtime and own empty scope absent.
This closes the current optional-MSRV examples execution requirement on Darwin
only. Other platforms/features/process/docs/API review and full release remain
open; no process fixture/control/measurement invocation85 was consumed.

## Current Linux optional compiler acceptance

Frozen source1ca21e32, accepted v3lock2ba4 and private direct Rust/Cargo1.77.2
Linuxx86_64 pass all11 positive feature rows. The unsupported sys/no_object
combination returns101 with its exact intentional diagnostic. Original evidence:
`../../all-tickets/linux-current-feature-v2-evidence/` and launcher-evidence;
independent root-readback verifies row statuses, seven manifests, lock and unchanged
relevant sources at integratedf6ad9e9b. All20 recorded PID/start identities are
absent, ownPGID1566099 empty, exact runtime and scope absent. Outer/scoped0;
export64.206s, sampled maximaRSS803384KiB/storage761640KiB/descendants4.
This closes compiler compatibility only; Linux current examples, native behavior,
Windows, process lifecycle and final release remain open. No native85 consumed.

## Current Linux optional examples acceptance

Frozen source `1ca21e32eed2aa40287ba7e1282000add1dd49c7`, compatible v3lock2ba4
and private direct Rust/Cargo1.77.2 Linuxx86_64 pass one combined locked sys/net
examples build. Real Engine file writes have fresh host readback `Rhaiting data`;
the independent loopback peer receives `ping`, and the script receives `pong`.
Both deliberate wrong expectations fail at their named independent assertions
with status101; both restored expectations return0. Original evidence is in
`../../all-tickets/linux-current-msrv-examples-evidence/` and launcher-evidence;
`../../all-tickets/linux-current-msrv-examples-root-readback.json` checks all8
commands, direct versions, reviewed helper, source/manifest/lock restoration and
current source applicability. All110 recorded PID/start identities are absent,
owned groups empty, exact private runtime/scope absent. Outer/scoped0, export
33.911s,49periodic samples maxRSS900108KiB/storage769428KiB/descendants7.
This closes Linux current optional-MSRV examples only. Native process count84
is unchanged; Windows, final feature behavior, process lifecycle, overhead and
release acceptance remain open.

## Linux combined baseline partial native acceptance

Frozen1ca21e32, private Rust/Cargo1.77.2, v3lock2ba4 and Linux7.2.7 completed
seven successful targets: combined_sys_net1, net_connect4, net_listen7,
net_reads7, net_writes10, sys_env7 and sys_fs35 (71 tests, zero ignored/filtered).
Intended filesystem, TCP read/write and combined wrong-expectation assertions
failed before restored positive execution. The no_object control also failed
as intended, but its positive feature row was not reached.

sys_policy failed two canonical-root path tests (21 passed/2 failed), leaving
the combined feature row open. Later rows were not executed. Original evidence
is in ../../all-tickets/linux-current-sys-net-behavior-followup-evidence/;
launcher evidence and followup-root-readback.json confirm owned cleanup. Root
independently matched all seven frozen manifest hashes, lock and helper bytes.
Successful Engine/OS slices remain valid within their source/environment scope;
filesystem corrections require affected filesystem/combined rechecks.

## Linux current root-alias correction and seven native feature rows

Frozen a2d7a8c2 with private Rust/Cargo1.77.2 and v3lock2ba4 completes seven
real Engine/OS feature rows: baseline95, no_index42, net/no_object3,
metadata/serde26, sync91, only_i32/no_float88 and unchecked85. All430 test
executions pass; five deliberate wrong-expectation controls fail as intended.
The two prior canonical-root failures and new ancestor-alias regression pass,
including denied-write independent host readback. Production candidate bytes,
seven manifests, source/archive, lock and executed helper were independently
matched. Original proof and terminal/cleanup receipts are retained under
`../../all-tickets/linux-policy-package-evidence/` and launcher-evidence;
`../../all-tickets/linux-policy-package-root-readback.json` records raw summary
checks and fresh native readback of21 absent identities and removed runtime/scope.

The finite package stopped at its storage preemption while compiling
no_index/sync/metadata; f32 was not run. These two rows, the wider platform/process
matrix and release acceptance remain open. Seven completed rows may be reused
while their relevant source/check/environment remain unchanged.

## Remaining Linux non-process feature rows — 2026-10-02

Frozen a2d7a8c2 with lock2ba4, private Rust/Cargo1.77.2 on native Linux7.2.7 passed combined-no-index-sync-metadata (82 tests) and combined-f32 (89 tests). Independent raw target/test coverage and live exact PID/start/group/runtime/scope cleanup readback are accepted in ../../all-tickets/linux-current-sys-net-policy2-review.md. Original proof commit84b8671f and receipts in ../../all-tickets/linux-current-sys-net-policy2-evidence/ preserve the single invocation. The seven prior rows and five meaningful assertion controls remain applicable unchanged: nine planned non-process rows, 601 successful executions. Current production/test/build inputs match frozen source. This closes this Linux filesystem/policy/TCP feature package only; process, other-platform and final release requirements remain open.

## Native Linux scalar process feature rows — 2026-10-03

Frozen2a8fdc49, private Rust/Cargo1.77.2 and compatible lock2ba4 pass the exact public scalar process test under no_index and combined sys/net/no_index/sync/metadata. Each meaningful wrong-CWD assertion failed101, exact test bytes were restored and the real Engine/child execution passed. Child PID record/CWD readback, ESRCH reaping, complete output/success/code0 and absence of run_raw are covered. Fresh independent closure checks confirm131 PID/start identities and four child PIDs absent, groups empty and runtime/scope removed. Original logs and proof applicability are in ../../all-tickets/linux-scalar-process-proof.md. Unix cumulative native count85; historical measurement85 remains unlaunched. This closes these two narrow process feature criteria; wider process/platform/release requirements remain open.

## Linux integer-only and unchecked process subset — 2026-10-03

Native invocation 93 uses frozen `6c451c5c` plus the exact reviewed test patch
`5cf5d453`; production is unchanged. Private Rust/Cargo 1.77.2, compatible lock
`2ba4`, and three rows (`sys`, `sys+only_i32+no_float`, `sys+unchecked`, each with
`testing-environ`) pass 32 original exact tests and 33 intended assertion controls.
Independent combined review accepts the targeted feature compatibility and host
output-cap criteria. Scripts requesting 8192 bytes cannot raise the host's
4096-byte cap for either stream; real child records and reaping precede exact
prefix/error checks. The helper's INT-width and unchecked Engine API compiler
regressions are reproduced separately and repaired in tests.

Fractional deadlines under `no_float` are host defaults; fractional per-call
script values are not proven. The unchecked Engine expansion criterion is
excluded, not passed. Existing normal-row sensitivity from invocations 89/90 is
reused; new feature controls cover selected branches, not every prior assertion.
Original evidence, combined review, all source/overlay identities and independent
445 PID/start plus 42 fixture-PID closure receipts are referenced in
`../../all-tickets/linux-process-feature-proof.md`. All 251 owned stage files and
five subdirectories were retired after export verification. Failed preparation
invocations 91/92 and their causes remain preserved without product acceptance.

This partially closes the Linux process feature requirements only. Managed
groups, remaining fault/lifecycle criteria, performance, other native platforms
and final release acceptance remain open.

## Current Linux MSRV held-zombie boundary — 2026-10-03

Native invocation 95 at frozen `257edf69`, private Rust/Cargo 1.77.2 and
`testing-environ,sys` passes the exact held-zombie integration test after two
meaningful wrong-expectation controls fail at their intended assertions. Real
Engine/OS observations bind live host, reaped direct leader, exact held worker/
leaf zombies, typed closure TimedOut, direct exit 0, complete captures and final
fixture reaping. Source restoration, original receipts and independent combined
acceptance are recorded in `../../all-tickets/linux-managed-zombie-proof.md`.
Fresh readback confirms 99 exact PID/start identities absent, four groups empty,
and all owned stage/runtime/scope resources removed. Invocation 94 remains an
infrastructure output-parser failure; its originals and consumption are retained.

This closes only the current Linux MSRV held-zombie criterion. Ordinary managed
success, remaining managed/fault/lifecycle paths, other feature/native-platform
rows, performance and final release acceptance remain open. Prior valid proof
and stopped cause/budget histories retain their recorded applicability.

## Linux managed final-clone drop — native102, 2026-10-03

The final-clone-drop public Engine test passed in four selected Rust 1.77.2
Linux feature rows, with a named post-cleanup wrong-control and three affected
base regressions. The proof records exact process identity/group closure,
nonfinal-drop preservation, host/reaper/sentinel liveness through observed
closure, source restoration, eight original closure records, and fresh owned
resource cleanup. See `../../all-tickets/linux-managed-final-drop-proof.md` and
the preserved native originals `../../all-tickets/linux-managed-final-drop102-evidence/`.
The combined independent acceptance review remains pending.

This is one partial managed lifecycle criterion only. Ticket 06's broader
feature/platform matrix and final release gates remain open.
