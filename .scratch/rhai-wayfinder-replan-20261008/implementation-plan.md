# Autonomous implementation and acceptance plan for Rhai

Status: autonomous implementation authorized by the owner on 2026-10-08.
The user instruction “planinhalte implementieren (autonome Umsetzung)” triggers
execution of this plan. No new Goal is needed; the historical Goal remains paused.
Previously produced results remain available and are not repeated for replanning.

This is the single executable companion to [the Wayfinder map](map.md). It
supersedes the proposed execution order in [assessment.md](assessment.md), not
the accepted product contracts, previous results, or historical attempt records.
An explicit later implementation instruction is the execution trigger; it need
not create a Goal. During execution, record results per package below `results/`.
The earlier versions of these new planning documents are retained in
[planning history](history/before-autonomous-plan-20261008T092524Z/implementation-plan.md).

Planning validation records appear at the end. A readable command sequence and
resolved links do not prove native execution. Existing tracked modifications and
historical evidence remain unchanged by this planning pass.

## Destination, authority and next action

Finish the owner-approved `sys` and TCP `net` contracts on native Linux x86_64,
Darwin arm64 and Windows x86_64 MSVC, with applicable public-Engine/real-OS
evidence, then integrate verified changes into `hoppworks/rhai` fork `main`.
Keep every still-open criterion open until its observable outcome is proved.

Ordinary implementation, fixture repair, precise test selection, private build
setup and integration on that fork may proceed autonomously after the execution
trigger. Do not request routine approvals for those steps. Do not write to public
upstream, enable Actions, publish, deploy, change credentials/admin rights, reset
the Windows image, change shared services, stop foreign work or stage foreign
changes. A real missing access prerequisite is a blocker, not implied authority.

Current accepted checkpoints include Linux shared Child lease/wait on revision
`34e0fa61a3d12fe6c41902c44618ff44e20d73d4`, Rust/Cargo1.77.2, standard/sync;
and X24 Linux standard reuse plus four RED/GREEN feature rows (sync, no_float,
sync+no_float, only_i32+no_float) and native Darwin arm64/macOS27.0.1 standard at
Rust/Cargo1.77.2. The full X24 packet review, exact source/lock bindings and attempt
history are in `results/linux-x24-features-20261009T1729Z/`; Linux shared-child
review is in `results/linux-shared-child-contracts-20261009T2025Z/`. Existing
Linux X31 Condvar-entry evidence is reused only at its reviewed source binding.
X24 and X31 remain partial overall; other Darwin profiles, Windows, and A–F remain
open. Continue with the next uncovered native Unix/process row; do not repeat these
unchanged X24 selectors. Windows custody is an independent prerequisite.

Rule baseline reloaded 2026-10-09: central Agent Skills HEAD
`1b6e1da85f87cad25f7aafc91aa782319ac6ef93`, project `AGENTS.md`, and only the
relevant current skills. Project contracts and explicit human boundaries remain
binding. Use current build-efficiently/resource-lifecycle instructions, including
owned TMPDIR scopes, `run_scoped.py`, and actual `AGENT_RUNTIME_DIR` outputs. Legacy
setup/Hermes text, duplicate model mappings, expired run exceptions and fixed
machine-wide heavy-run counts are not active policy. Do not install or sync rules
as part of this work. Future reviewers must read the current sources before action.

Previous finite invocations and their consumption remain history. Agent-generated
PENDING/blocked labels and estimates do not create human approval gates; preserve
actual hard limits and consumed work. A repeat needs a changed relevant input or
an unresolved assertion.

## Observed starting state and proof reuse

Inspected worktree:
`/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery`.
Branch `task/all-tickets-environment-recovery`, HEAD
`ef423a516617e128835d54af16d75f559b2b1bce`; origin fetch/push points to
`https://github.com/hoppworks/rhai.git`. These are observations, not permanent pins.

Existing dirty tracked files: coordinator-state, sys-package-plan, sys_process
example and `tests/fixtures/sys_process_shared_child_contract.rs`. The shared
fixture is foreign work. Preserve all four; only adopt a reviewed, explicitly
owned delta. Keep untracked proof exports. Never use `git add -A`, reset, stash
everything or copy the whole dirty worktree into a build.

Known reusable inputs:

| Input | Existing location / binding | Use |
|---|---|---|
| Optional-package lock | `.scratch/all-tickets/process-io-contract-evidence/attempt-01/stage/Cargo.lock.accepted`; SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` | Overlay into an owned source snapshot; require `--locked`. Do not resolve dependencies afresh. |
| Core minimum lock | `.scratch/all-tickets/core-current-msrv-evidence-04/Cargo.lock`; same SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, verified present | Accepted core proof uses the same v3 lock. Preserve its exact graph; no separate dependency re-resolution for core. |
| Committed source archive | `.scratch/all-tickets/darwin-x21-cap-20261008/attempt-01/source.tar`; revision `ef423a516617e128835d54af16d75f559b2b1bce`; SHA-256 `635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f` | Reference for historical applicability. Make a new snapshot only for actual changed inputs. |
| X18 | `.scratch/all-tickets/darwin-x18-unit-stdin-20261008/proof.md` and linked Linux proof | Retain bound Linux rows and Darwin standard: attempt02 RED + attempt03 GREEN. Wrong-cwd attempt01 is infrastructure history. |
| X19 | `.scratch/all-tickets/darwin-x19-deadline-20261008/proof.md`, linked Linux attempt10 | Retain eight direct-timeout rows on each OS: 1.77.2/1.93.0 × standard, sync, no_float, sync+no_float. |
| X20 | `.scratch/all-tickets/darwin-x20-20261008/attempt-01/proof.md` and `.scratch/all-tickets/linux-x20-direct-20261008/attempt-02/proof.md` | Retain eight Linux rows and Darwin 1.93 standard row for `run_io_contract_empty_output`. Both proof files exist and were read. |
| Latest X23 example | `results/example-20261008T090938Z-zmj63_0i`: inputs, compiler logs, four status/stdout/stderr rows, `result.json`, runner log/status | Darwin1.77.2 `sys,no_float` and `sys,sync,no_float` each have expected-exit8 RED101 and expected-exit7 GREEN0, fresh host records and ESRCH. Final combined review, manifest and cleanup receipt remain open. The helper's `accepted: true` is not final acceptance. |
| X21–X38 and process diagnostics | `docs/sys-package-plan.md` §6.7, named proof files and original logs | Reuse only the exact accepted subset in each row. Partial is not complete. |
| Linux non-process feature behavior | `.scratch/stdlib-wayfinder/issues/06-compatibility-release.md`, Linux policy-package and policy2 evidence/reviews | Nine accepted semantic rows; retain relevant source/test/lock applicability. |
| Darwin optional compile/examples, metadata | Same release ticket; API metadata evidence and integrated `04d9a797…` proof | Retain unchanged compile/example/doc assertions. Recheck only affected dependency closures. |
| Windows filesystem | `.scratch/stdlib-wayfinder/windows-vm/README.md`, native-baseline.log, guest source/lock at `f548fc13`/Rust1.93 | Historical write/truncate/append control only after input applicability. Other 44 diagnostic passes are not full controlled release acceptance. |

There is no inspected reusable `target/` cache under the X18–X20 proof roots.
Do not assume a cache, guest build or historical runtime still exists. Existing
local Darwin toolchains include 1.66.0, 1.77.2 and 1.93.0. The historical guest
has 1.93 MSVC; guest 1.77.2 and current live readiness are unverified.

Current read-only workhorse observations, 2026-10-08: SSH logs in as `root`;
Rust/Cargo1.77.2 and1.93.0 binaries exist and their version readbacks match under
`/var/home/workhorse/.rustup/toolchains/<version>-x86_64-unknown-linux-gnu/bin/`.
The intended VM UUID matches, state is `shut off`, with four vCPUs/8 GiB, owned
`/var/lib/libvirt/images/rhai-win11-quality/system.qcow2`, existing optical devices,
127.0.0.1 VNC autoport and the existing serial log path. No guest was started or
queried. Host Python is `/usr/bin/python3` 3.14.7 and `genisoimage` exists;
`xorriso` and `rg` are unavailable there. A capacity sample showed approximately
80 GiB available host memory and 508 GiB free on `/var/home`; this is not a
reservation. Guest compiler, token, space, console and caches remain unverified.

For the latest example, its recorded runtime is absent and its outer scope
`/Users/hoppworks/.local/share/agent-builds/rhai/example-c58997ha` exists empty.
No build binary survives there. The retained Linux X20 input/evidence root
`/root/.local/share/agent-builds/rhai/x20-linux-direct-20261008-01` exists; no target
cache is claimed. Later retirement requires ownership, complete export and no
live use. Do not touch the other historical workhorse X36 root without establishing
current ownership; an old project prefix is insufficient.

For each retained proof, compare relevant production files, test/fixture oracle,
Cargo manifests, build.rs/codegen, dependency lock, enabled features, toolchain,
native OS and environmental assumptions. A documentation-only revision or an
unrelated platform-specific module does not invalidate a Unix OS assertion.
Record the comparison and original link in the corresponding execution result;
do not copy old logs into a second tracking system. A dependency version or shared
runtime change invalidates only its affected closure. Do not equate revision
inequality with invalidation, or revision equality with environmental equivalence.

## Start and freeze

After implementation authorization, run from the worktree above:

```sh
git status --short
git rev-parse HEAD
git remote get-url origin
git remote get-url --push origin
git diff -- examples/sys_process.rs
shasum -a 256 .scratch/all-tickets/process-io-contract-evidence/attempt-01/stage/Cargo.lock.accepted
shasum -a 256 .scratch/all-tickets/darwin-x21-cap-20261008/attempt-01/source.tar
rustup toolchain list
```

Require the two known hashes before using those inputs. If HEAD advanced, identify
the actual relevant delta instead of resetting. The expected example patch adds
`nonblocking_wait_expression()` and replaces all three `child.wait(0.0)` call
sites with it; no_float uses `child.wait(0)`. The three call sites are the wait
loop, exceptional cleanup loop and early pending assertion.

For each later package, create one unique evidence directory under
`.scratch/rhai-wayfinder-replan-20261008/results/<package>-<UTC>-<random>/`.
Keep input manifest, reviewed patch, original command logs/statuses, observations,
review and cleanup receipt there. This directory is durable evidence; it is not
a build cache. Maintain current decisions and the next action in at most a short
status block here; the older coordinator history remains untouched.

Freeze a committed archive and explicit owned patch, with SHA-256 for every
changed input. Include Cargo.toml, codegen, examples, fixtures and build.rs; the
old Windows omission of examples must not recur. Use `git archive` of the chosen
commit plus a reviewed path-specific patch, not an incomplete ad-hoc source list.
Apply patches only in the isolated build source and check restoration hashes.

Concrete future setup for a package needing new execution. The latest example
does not need this setup again. Substitute the package slug and reviewed owned
path list; execute only after the implementation trigger, from the worktree:

```sh
set -euo pipefail
BASE=$(git rev-parse HEAD)
PACKAGE=unix-process
PLAN_ROOT="$PWD/.scratch/rhai-wayfinder-replan-20261008"
mkdir -p "$PLAN_ROOT/results"
EVIDENCE=$(mktemp -d "$PLAN_ROOT/results/$PACKAGE-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXXXX")
git archive --format=tar --output="$EVIDENCE/source.tar" "$BASE"
# After reviewing ownership, list only this package's actual changed paths.
git diff --binary "$BASE" -- tests/sys_process.rs > "$EVIDENCE/owned.patch"
cp .scratch/all-tickets/process-io-contract-evidence/attempt-01/stage/Cargo.lock.accepted \
  "$EVIDENCE/Cargo.lock.accepted"
printf '%s\n' "$BASE" > "$EVIDENCE/revision.txt"
shasum -a 256 "$EVIDENCE/source.tar" "$EVIDENCE/owned.patch" \
  "$EVIDENCE/Cargo.lock.accepted" > "$EVIDENCE/inputs.sha256"
mkdir -p "$HOME/.local/share/agent-builds/rhai"
SCOPE=$(mktemp -d "$HOME/.local/share/agent-builds/rhai/$PACKAGE-XXXXXXXX")
printf '%s\n' "$SCOPE" > "$EVIDENCE/scope.txt"
```

The path list above assumes only the focused regression changes. Add an owned
backend/fixture path if that package actually changes it; include explicitly owned
new files with a reviewed file manifest because ordinary `git diff` omits untracked
files. Do not freeze a patch before its implementation exists. Review `owned.patch`
before it is applied. During implementation write the minimal
`payload.sh` described below into EVIDENCE, and hash it in the command manifest.
It is deliberately not created or invoked during this planning request. Export
these inputs together to an owned workhorse evidence directory for Linux; require
remote checksum readback before extraction. Do not execute a shell interpolated
from untrusted source text; pass explicit paths/argv.

## Common POSIX execution recipe

Use the existing `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py`
on Darwin. The inspected workhorse equivalent resolves to
`/var/home/workhorse/projects/agent-skills/tools/run_scoped.py`, SHA-256
`25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.
Recheck only if its bytes changed; do not copy a command with unsupported flags.
The currently read runner
accepts `--timeout SECONDS -- COMMAND`; it does not implement old RSS/storage/
descendant flags. It creates AGENT_RUNTIME_DIR below TMPDIR, supervises its own
process group and deletes the verified runtime on exit. It cannot by itself
reap a fixture that intentionally leaves that process group.
Its inspected `agentskills/pyguard.py` only selects Python >=3.11; it neither
loads the current Agent Skills rules nor changes configuration. The remote
`tools/agentskills/pyguard.py` has the same interpreter-only behavior, SHA-256
`a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f`. Load active
rules from the central repository separately. A missing interpreter is a cheap
precondition failure, not a Cargo RED.

The following is a future invocation recipe, with `EVIDENCE` set to the newly
created durable directory and `BASE` to the reviewed commit. It is not an already
created runner. Save a package-specific `payload.sh` and inputs in EVIDENCE during
implementation; it contains only that package's commands, observations and traps.

```sh
set +e
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$SCOPE" python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py \
  --timeout 1200 -- bash "$EVIDENCE/payload.sh" "$EVIDENCE" \
  > "$EVIDENCE/runner.log" 2>&1
RUNNER_STATUS=$?
set -e
printf '%s\n' "$RUNNER_STATUS" > "$EVIDENCE/runner.status"
```

Create the `rhai` parent if absent; `mktemp` creates only the new owned child.
Capture runner status even on failure. Save scope identity/path in evidence. The
payload must use `set -euo pipefail`, take its evidence argument, and do this
before Cargo:

```sh
set -euo pipefail
EVIDENCE=$1
: "${AGENT_RUNTIME_DIR:?runner must supply an owned runtime}"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export PYTHONDONTWRITEBYTECODE=1
export CARGO_BUILD_JOBS=2
mkdir "$AGENT_RUNTIME_DIR/source"
tar -xf "$EVIDENCE/source.tar" -C "$AGENT_RUNTIME_DIR/source"
cd "$AGENT_RUNTIME_DIR/source"
cp "$EVIDENCE/Cargo.lock.accepted" Cargo.lock
git apply --check "$EVIDENCE/owned.patch"
git apply "$EVIDENCE/owned.patch"
```

Omit apply commands for an empty patch. Store a stage-specific patch if multiple
owned fixes belong together; never pick up the foreign shared fixture implicitly.
Assert the cwd and lock hash in the command log. On Darwin use `cargo +1.77.2`
or `cargo +1.93.0`, with no global default change. On workhorse the SSH user's
rustup list is a different installation; select the read-back binaries explicitly:

```sh
TOOLCHAIN=/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu
export RUSTC="$TOOLCHAIN/bin/rustc"
export RUSTDOC="$TOOLCHAIN/bin/rustdoc"
export PATH="$TOOLCHAIN/bin:$PATH"
CARGO="$TOOLCHAIN/bin/cargo"
"$CARGO" --version
"$RUSTC" --version
"$CARGO" test --locked --features testing-environ,sys --test sys_process \
  --no-run --message-format=json
```

This is an invocation template inside the owned staged-source cwd, not a command
to run now. Substitute1.93.0 only for an admitted endpoint row. Use `/usr/bin/python3`
and the remote runner path there. Freeze the effective build environment, removing
inherited compiler/wrapper/flag overrides only for the owned command when they
would conflict with its declared recipe; do not change shared defaults. Command output
goes directly to durable log files; record its exit separately. Do not let `set -e`
discard an expected RED. Export observations continuously because a timeout also
deletes runtime. Install fixture guards before launching child/socket work.

Before a heavy run measure current CPU/RAM/disk and active shared work, preserving
foreign processes and files. Select job count and concurrency from those facts; no
machine-wide heavy-run slot exists. Historical resource samples are not
reservations. Record any invocation-specific hard cap with its user/project/safety
source; distinguish it from a revisable estimate. Monitor actual use and stop only
at an applicable explicit limit or unsafe condition. Diagnose the next step from
evidence rather than repeating blindly.

Keep related profiles, control/restoration and selective dependent tests in one
runtime. Cargo may reuse unchanged dependency artifacts within it. A test-oracle
mutation recompiles only the selected test; it is not a reason to clean dependencies.
Mutable fixtures get separate unique directories/ports on every test phase.
If exporting binaries for later reuse, include a complete source/lock/toolchain/
target/profile/environment fingerprint and all runtime-library dependencies;
otherwise retire them. Never claim historical logs are executable build artifacts.

After runner completion independently verify recorded fixture identities are
terminated/reaped, no owned escaped fixture remains, runtime identity/path is
absent and durable export hashes match. Use fixture-retained child handles or
PID plus captured start identity, never a recycled numeric PID alone. Remove only
the empty owned session scope using `rmdir`. Failed immutable inputs/logs remain.
If cleanup cannot be proved, retain exact custody and report that criterion open;
do not launch another fixture of the same unsafe kind.

## Assertion controls and result handling

Use the selected executable's `--list` and require the exact intended test is
present. A cfg-excluded test with zero executions is not GREEN. Compile each
distinct source/oracle phase with
`cargo test ... --no-run --message-format=json`; obtain the target executable from
the matching `compiler-artifact` record, not a guessed target filename. Preserve
the compiler log/exit and executable SHA-256. A RED mutation and its restoration
each require the targeted incremental compilation and a fresh artifact record;
never run an earlier GREEN executable against a changed test source. Reuse the
same private dependency cache, without a clean rebuild. Then direct libtest commands use
`<exe> <fully-qualified-test-name> --exact --nocapture --test-threads=1`.
For a new test added during implementation, bind its final name in the result
manifest before compilation; the name in a proposal is not an existing selector.

An assertion RED requires exit 101, the intended assertion/panic marker, the
selected test in the final failure inventory and a summary with one failed test.
Test name and FAILED need not be adjacent. Compile errors, wrong cwd, setup stops,
watchdog kills and unrelated panics are infrastructure or different failures.
GREEN requires exit 0, one selected test passed and restored source/oracle hashes.
For examples, require the named assertion and exit 101 for RED; GREEN requires
exit 0 and its independent readbacks. Do not impose libtest grammar on an example.

Prefer a single wrong expected byte/result in a function-specific private test
copy. Locate the named function, delimit its body, require exactly one occurrence
of the old oracle inside that body, and fail before Cargo if ambiguous. Do not
globally replace a repeated assertion. Record before/RED/restored hashes. Keep
normal tests incapable of accepting wrong expectations by accident; an isolated
test child may expose a deliberate control only in its explicitly declared phase.

Reuse a previous RED when its observation/oracle and relevant inputs still match;
one control is not a claim that every independent assertion is sensitive. Add a
control for a genuinely new oracle/semantic branch. A known pre-fix defect already
reproduced is valid bug evidence; do not rebuild the old revision just for ceremony.

Failure policy is deterministic:

| Observation | Next autonomous action |
|---|---|
| Parser/export classification rejects a valid raw result | Inspect saved exit, selected assertion and summary; correct only analysis/export and reuse raw result. No product rerun. |
| Preparation fails before the assertion | Read the whole archive→cwd→lock→toolchain→entry→capture→export→cleanup chain. Repair the actual mismatch, cheap-check that complete chain, then run only the unexecuted selection. |
| Same preparation cause recurs without new evidence | Stop that route, diagnose its complete composition and take an available independent package. Do not add another wrapper or rerun the whole matrix. |
| Restored public test fails at contract assertion | Treat as a product/fixture defect; preserve reproduction, implement the smallest contract-correct fix, rerun affected selectors/dependencies. |
| Expected failing control instead passes | Repair the oracle or its binding; no acceptance. Do not weaken the promised result. |
| Native resource/custody unavailable | Record the exact prerequisite; keep native criteria open and finish independent packages. No mock/Wine substitution. |
| Review finds a relevant defect | Correct it and recheck its affected closure; the same combined review checks the delta. Unchanged accepted reviews stand. |

A specific corrected mismatch that passes its cheap complete-entry checks reopens
only the still-unexecuted selection. If no repair is possible within the ownership/
access boundary, keep that prerequisite open. Neither a repeated stop nor a fresh
tracking label is permission for another identical expensive run.

## Required platform/version/feature coverage

Use native Linux on authorized SSH `workhorse`, native Darwin locally, and the
authorized Windows guest. Wine/cross-compilation do not satisfy native behavior.
Package-minimum runtime coverage uses Rust1.77.2; existing Rust1.93 results remain
valid for their bound rows. Keep the previously chosen 1.93 endpoint: do not add
1.96/1.98/nightly or every installed compiler as a new release axis.

These eleven positive feature rows come from the accepted release proposal:

| Cargo features (prefix `testing-environ,` for integration tests) | Required semantic execution |
|---|---|
| sys | Package registration, default-denied sys, real filesystem and process baseline |
| net | Net without sys; connect/listen and real peer bytes |
| sys,net | Coexistence in one Engine and baseline behavior of both |
| sys,net,sync | Shared handles, outstanding operation cancellation, wait-entry/close/quota behavior |
| sys,net,no_index | Scalar APIs present; collection/blob overloads absent; scalar process and string/file/TCP behavior |
| sys,net,metadata,serde | Metadata inventories, docs/overloads and typed report/error data |
| sys,net,only_i32,no_float | Integer-width-safe fixtures, integer script durations/host deadlines and bounds |
| sys,net,unchecked | Host allocation/output/write/read/handle bounds still enforced; no Engine-limit assertion requiring checked mode |
| sys,net,no_index,sync,metadata | Registration + sharing/cancellation interaction with scalar access |
| sys,net,f32_float | Finite/range/representation duration validation and unchanged real TCP/process bounds |
| net,no_object | Registered free functions work with explicit stream/listener/error arguments |

At 1.77.2 all eleven rows need native compilation on the three OSes. Reuse the
accepted Linux/Darwin compilation and nine non-process behavioral rows if inputs
remain applicable. On an uncovered OS, run the selected integration targets below
for the baseline; the variant targets exercise their changing semantics. A full
baseline target suite is not repeated in every variant merely to multiply rows.

For process lifetime/capture code, baseline proves every applicable behavior;
sync proves cancellation and shared snapshots; no_float proves integer waits and
host-selected fractional deadlines; sync+no_float proves their interaction. Existing
1.77.2/1.93 direct-timeout rows are retained. Add a 1.93 row only to fill an already
promised uncovered endpoint or verify a concrete compiler/runtime regression, not
for every new test. Use only_i32 for IDs/exit/maps and unchecked for host limits;
no_index for scalar process registration; f32 for duration conversion boundaries.
Those shared semantics need representative tests, not every behavior × every row.

Concrete semantic selectors below are existing functions unless explicitly marked
planned. Run them only for uncovered or invalidated rows, with that row's features
and `testing-environ`. Resolve each name through the corresponding executable's
`--list`; no wildcard filter or zero-test pass counts as coverage.

| Changing semantics | Target and exact selector |
|---|---|
| sys/net coexistence, typed catch/readback | `combined_sys_net::sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors` |
| sync TCP cancellation/quota | `net_reads::closing_a_clone_cancels_an_outstanding_read_and_releases_quota`; `net_listen::closing_a_clone_unblocks_an_accept_waiting_on_shared_quota` |
| no_index scalar/file/TCP | `sys_process::scalar_run_with_cwd_works_without_collections` (currently Unix; Windows counterpart planned); `sys_process_report::no_index_keeps_scalar_and_indexed_diagnostic_access`; `sys_fs::test_file_handle_blob_read_is_omitted_under_no_index`; `net_reads::no_index_keeps_string_reads_and_omits_blob_methods`; `net_writes::no_index_keeps_string_writes_and_omits_blob_writes` |
| metadata, including no_index/sync interaction | `sys_policy::test_function_metadata`; `net_metadata::metadata_exposes_the_documented_tcp_surface`; `net_metadata::metadata_documents_tcp_handle_operations_and_overloads`; sharing/cancellation selectors above where cfg-enabled |
| integer durations / only_i32 | X23 example commands below; `sys_process::run_deadline_returns_bounded_partial_output_after_terminating_child`; coexistence selector above with ID/exit/map assertions; native Windows equivalents planned |
| unchecked host bounds | `net_reads::unchecked_mode_keeps_the_host_receive_cap`; `net_writes::host_write_cap_rejects_oversize_input_without_peer_bytes`; `sys_fs::test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving`; `sys_process::process_script_output_option_cannot_raise_the_host_cap` (Windows counterpart planned) |
| f32 duration conversion | `net_reads::f32_float_timeout_arguments_reject_fractional_and_non_finite_values`; public process duration/host-limit counterpart planned after auditing uncovered assertions |
| net without object syntax | `net_no_object::registered_stream_functions_work_without_dot_syntax`; `net_no_object::registered_listener_functions_work_with_explicit_handle_arguments`; `net_no_object::registered_error_getters_are_callable_with_explicit_arguments` |

Here `target::selector` is a target/name mapping, not a libtest prefix: pass
`--test target` to Cargo and the listed function name to its executable. Internal
module names, including shared_child_contract, retain their actual qualified name.
The package-alone rows run their baseline targets with only sys or only net;
the combined row cannot stand in for isolation. Under no_index+sync+metadata,
select the cfg-enabled scalar cancellation and metadata assertions rather than
running collection-dependent tests and counting their absence.

Core minimum remains Rust1.66.0 without sys/net. The inspected
`.scratch/all-tickets/core-current-msrv-proof.md` and evidence-04 source manifest
accept the same v3 lock hash2ba4; its on-disk lock was read back and matched. Reuse
that proof for unchanged default-core sources. `cargo +1.66.0 check --locked --lib`
plus the active dependency graph must show no cap-std/libc/optional windows-sys
from sys/net. The new Windows-target dependency warrants a Windows core-minimum
isolation check after its manifest change, plus an affected shared-manifest check;
it does not justify a new Cartesian core runtime matrix. Do not confuse inactive
locked packages with compiled optional dependencies, or reuse the older 8bd35
core lock whose root dependency list predates the current manifest.

Negative compile rows: sys+no_object; sys+no_std; net+no_std; sys and net on
wasm32-unknown-unknown. Require the package's intentional compile_error text,
not “target not installed” or a dependency MSRV failure. Use `--no-default-features`
for no_std. Check installed target/toolchain first. If a required compiler/target
is missing later, use only a user-owned portable toolchain/target with official
distribution checksums; no shared installation, admin/global config or upgrade of
the baseline. Record that prerequisite before compiling. Core no_std is not made
unsupported by these optional-package diagnostics.

## Execution packages and ready queue

The seven packages below are connected product/custody outcomes, not new Wayfinder
decision tickets or separate handoff orders. Use this deterministic ready queue:

| Priority / package | Actual prerequisite | Smallest observable finish | Reuse / next dependent action |
|---|---|---|---|
| Completed: Example correction | Saved X23 input/result binding and existing independent review | Final proof for the two already-run affected profiles; complete export and exact cleanup receipt | No Cargo. Retain standard/sync and unrelated X24; take the next ready package. |
| Early: Windows custody prerequisite | Correct domain/console/token/compiler and reviewed composed entry | Tiny fixture proves bounded payload, interruptions, sentinel survival, independent export and cleanup | Reuse installed VM and unchanged tools; enables native Windows product execution only. |
| Unix process closure | Bound source/lock, native compiler and guarded fixtures | Linux Child.wait expansion, X34 reapers, managed-spawn lifecycle, escaped-pipe, held-zombie/Child.kill/false-drop and shared Child lease/wait contracts accepted at their named inputs. X24 now adds Linux 1.77.2 sync/no_float/only_i32 rows and Darwin 1.77.2 standard/sync rows. | Next close Darwin package-minimum X25 `managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel` on arm64/macOS27.0.1/Rust1.77.2, preserving compatible X25 1.93 evidence only after exact assertion/input applicability review; do not repeat X24 selectors. |
| Windows process backend | Common process contract and owned source; custody/toolchain only before native execution | Public run/raw/spawn/Child with real native lifecycle, argv, cwd and Job proof | Source implementation is independent of console availability. Native closure waits for custody; preserve Unix proof outside shared changes. |
| Base sys and shared file handles | Native platform available; Windows execution needs custody | Missing P/E/F/file-handle effects, permissions and native path boundaries | Reuse Linux semantic rows and applicable Darwin/Windows readbacks. |
| TCP native closure | Native loopback/peer fixture; Windows execution needs custody | Missing numeric IPv6 and TCP authority/data/lifetime observations | Reuse unchanged Linux behavior and existing coexistence proof. |
| Last: Integrated compatibility, documentation and fork main | Prior package outcomes and complete applicability crosswalk | All87 numbered criteria plus extensions, native/feature/MSRV and documentation obligations closed at tested fork revision | Only affected shared/merge/feature deltas; atomic fork-main publication and owned-resource retirement. |

The saved example is finalized and accepted. Windows readiness/composition was
checked; the remaining encrypted-console prerequisite is unavailable, so do not
repeat that loop. Continue unblocked Unix closure, then uncovered Base sys/TCP work.
Ordinary Windows source implementation can proceed without a live guest, but
compilation/emulation never substitutes for native acceptance. Share a scope for
compatible source/lock/feature work; different outcomes still keep their individual
acceptance rows and independent fixture data.

Before each package, form its finite selection from the coverage crosswalk plus
historical §6.7: **accepted/applicable → reuse; changed dependency closure → targeted
recheck; missing assertion → implement or execute that assertion; unavailable native
prerequisite → keep open**. Save that selection in the package result manifest,
not in another counter or tracker. Finish ready work until the crosswalk has no
gap. This process does not require a new plan or routine permission between packages.

### Example correction

**Outcome:** finalize X23 integer-only example proof at Darwin package minimum:
real run/spawn file records, nonzero exit7 as data, pending wait, identical clone
results and child cleanup. **Inputs:** current owned example patch and pinned lock.
**Accepted (2026-10-08):** both affected profiles have exact RED/GREEN rows,
independent combined review, proof, cleanup receipt and finalization readback in this
directory. `acceptance.json` records the scope. The original source archive was not
retained in this directory; `source-archive-tree-readback.json` reproduces its hash
from the exact Git revision. The final manifest validates. No build/test rerun.

Use the existing evidence directory
`results/example-20261008T090938Z-zmj63_0i`. It binds HEAD `ef423a516617e128835d54af16d75f559b2b1bce`,
archive SHA `635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f`,
patch SHA `885978cdd5e46442e04bf92a1a60ebeb8d88b84d5e721fcd8fe12ac216dc0f90`,
lock SHA `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`
and example SHA `02f6b6b77341977248c46fb06e0b3c51b258c9cf33ba3023f53c12c5fc3de2a4`.
Source/build inputs, commands and macOS27.0.1 arm64/Rust1.77.2 environment are
preserved in `inputs.json`, `result.json`, `recipe.sha256` and original logs.

| Existing row | Raw status / control | Independent observation |
|---|---|---|
| sys,no_float RED | expected8, exit101, intended exit assertion left7/right8 | Fresh run/spawn records; recorded child80141 absent with ESRCH |
| sys,no_float GREEN | expected7, exit0; same profile executable as RED | Fresh records, pending→identical clone wait; child80146 ESRCH |
| sys,sync,no_float RED | expected8, exit101, same intended assertion | Fresh records; child80170 ESRCH |
| sys,sync,no_float GREEN | expected7, exit0; same profile executable as RED | Fresh records, pending→identical clone wait; child80174 ESRCH |

Finalization recheck performed without Cargo: `recipe.sha256` and the final
`manifest.sha256` validate; `result.json` binds four expected RED/GREEN rows and
same-profile executable hashes; `review.md`, `proof.md`, `acceptance.json`,
`finalization-readback.json` and `cleanup.json` are present. The empty outer scope
is currently absent. `source-archive-tree-readback.json` reconstructs the missing
archive exactly from the recorded commit hash. Numeric PID probes remain historical;
do not signal them. Standard/sys+sync X23 and independent X24 remain separate.

### Unix process closure

**Outcome:** uncovered Unix lifecycle, setup/fault and report rows close without
rerunning X18–X20 or the accepted portions of X21–X38. **Prerequisite:** current
source-bound crosswalk, isolated fixture guards, explicit exact selectors.

**Accepted checkpoint (2026-10-09):** Linux X35's three selectors are accepted
for source `34e0fa61a3d12fe6c41902c44618ff44e20d73d4`, the bound archive and lock,
`testing-environ,sys`, Linux x86_64, Rust/Cargo 1.77.2. The RED/GREEN, process
readbacks, cleanup and combined review are in
`results/linux-managed-drop-20261009T1518Z-6cf30d/`; the 9,199-file archive-to-Git
tree comparison is `source-archive-tree-readback.json`. Do not rerun unless a
relevant input or assertion changes. X34 timeouts/caps, X36 setup/refusal, remaining
X37 cases, X38, other platforms/features and A–F remain open.

Use `--test sys_process --test sys_process_report` and the existing shared-fixture
module. The committed fixture snapshot remains independent of the foreign dirty
fixture. If that foreign change is needed, first establish ownership and review
its immutable patch; never silently commit it.

The formerly stopped **Package B** has no verified available attempt03 result at
the previously cited local path. Do not rebuild its archive/SSH/launcher stack.
Preserve its three launches, three pre-assertion infrastructure stops and zero
executed assertions; do not retry native110 or count those stops as product RED.
The public regression for `Child.wait` decoded UTF-8 expansion is already committed.
Linux checked/default acceptance is complete at source34e0fa61, lock2ba4b3a0,
features testing-environ,sys and Rust/Cargo1.77.2. It covers invalid UTF-8 whose raw
length stays below the Engine limit but decoded text exceeds it, normal exit0,
cloned/repeated waits, exact raw bytes, complete stdout/stderr, stable typed
Process/OutputLimit, no timeout, a child-written record and independent reap. A
second case verifies that committed primary OutputLimit is preserved. The corrected
wrong-raw-byte RED and restored GREEN with combined review are in
`results/child-wait-expansion-linux-20261009T1644Z/`; the initial forced-panic RED
is excluded. Do not repeat absent a relevant input change. Darwin and unchecked/
other feature variants remain open; unchecked retains its host output-cap assertion.

**Accepted checkpoint (2026-10-09):** the exact Linux X34 selectors
`managed_run_deadline_reaps_group_under_fixture_reaper` and
`managed_run_output_limit_reaps_group_under_fixture_reaper` each reached a deliberate
wrong-outcome assertion RED (101) and passed restored-source GREEN (1/1) in one
scoped Workhorse run. The independent review binds archive/revision, lock, test
source, features, toolchain and native platform, and confirms PIDFD, process-group,
fixture-reaper, host/sentinel and cleanup observations. The deadline API returns a
report map; OutputLimit is typed. Evidence and review:
`results/linux-x34-reaper-20261009T1830Z/`. This accepts only those two Linux
selectors at 1.77.2/default checked profile; Darwin existing rows remain separate.

**Accepted checkpoint (2026-10-09):** Linux exact selectors
`managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel` and
`managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not` each reached
a meaningful wrong-expectation RED (101) and restored-source GREEN (1/1) at the same
revision/lock/features. The combined review verifies public Rhai kill/wait and shared
handle behavior, independent member ESRCH and sentinel observations, scoped cleanup,
and limits the verdict to these selectors. Evidence:
`results/linux-managed-spawn-lifecycle-20261009T1850Z/`. The probes use PID records,
not PIDFD/start-time custody or interruption; do not generalize this result.

**Accepted checkpoint (2026-10-09):** four exact Linux selectors are accepted
with meaningful RED101 and restored-source GREEN1/1 in one scoped run:
`managed_run_succeeds_after_fixture_reaper_reaps_descendants`,
`managed_spawn_final_clone_drop_closes_group_under_fixture_reaper`,
`managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes`, and
`managed_spawn_post_reap_cancel_bounds_escaped_capture`. The combined review confirms
source/lock/features/toolchain, exact reaper/PIDFD group closure, live sentinel
boundaries, escaped-holder challenge/Readback and EPIPE, and exact cleanup.
`results/linux-process-completion-capture-20261009T1915Z/`.

**Accepted checkpoint (2026-10-09):** Linux exact selectors
`managed_run_reports_while_fixture_reaper_holds_stopped_zombies`,
`managed_child_kill_reports_group_closed_under_fixture_reaper`,
`managed_run_deadline_cancels_escaped_pipe_holder_under_fixture_reaper`, and
`managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit` each reached a
meaningful RED101 and restored-source GREEN1/1 in one scoped run. The review confirms
the held-zombie case returns the owner-approved typed closure error with custody
retained (not a product defect), exact reaping after release, PIDFD/group/sentinel
boundaries, EPIPE challenge/Readback and the live false-drop challenge.
`results/linux-zombie-false-drop-20261009T1940Z/`.

**Accepted checkpoint (2026-10-09):** the Linux shared Child lease/wait contracts
above are accepted for the bound archive/revision, lock, Rust/Cargo 1.77.2, and
`testing-environ,sys` plus `testing-environ,sys,sync`. Four standard and five sync
selectors have meaningful RED and restored-source GREEN; attempt03 and attempt06 add
targeted false-policy operational and true-policy final-reap REDs, while all compatible
GREENs are reused. Combined review:
`results/linux-shared-child-contracts-20261009T2025Z/combined-review.md`;
proof/history: `results/linux-shared-child-contracts-20261009T2025Z/package-summary.md`.
The packet's timed sync selector is not actual wait-entry proof. Reuse separate Linux
X31 `sync` and `sync,no_float` Condvar-entry rows only under the existing source
applicability review; full X31 and other platforms/features/MSRVs remain open.

X24 checkpoint: retain the accepted Linux standard row and add four native Linux
Rust/Cargo1.77.2 RED/GREEN feature rows (`sync`, `no_float`, `sync,no_float`,
`only_i32,no_float`) plus Darwin arm64/macOS27.0.1 Rust/Cargo1.77.2
`testing-environ,sys`. The complete function bytes are lines462–546 inclusive with
final newline, SHA-256 `21db2d7a36f3692ea1c3775fc895707676d2334fcc430d99e0a07051e6547793`.
The packet review accepts these named rows only; full X24 and A–F remain open.
Next close an uncovered native Unix/process lifecycle criterion using existing
selectors and reusable source/lock inputs; preserve compatible standard/X31 proof
and do not repeat unchanged X24 rows.

Close uncovered cases using these existing selectors; prefix shared names with
`shared_child_contract::` when invoking their executable:

| Contract | Selector / required observation |
|---|---|
| X23/26/27/28/29/31 | `spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable`; `nonfinal_child_clone_drop_keeps_the_real_child_available`; `final_drop_honors_both_kill_on_drop_policies`; `script_throw_drops_and_reaps_a_live_child`; `sync_waiter_can_be_cancelled_through_another_shared_child_handle` |
| X24/28 | `direct_spawn_try_wait_returns_unit_until_child_exits`; `direct_spawn_kill_on_drop_false_preserves_child_and_capture` |
| X34/37 | `managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel`; `managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not`; managed timeout/output-limit fixture-reaper cases |
| X35 | `managed_run_closes_worker_after_leader_exit_and_preserves_sentinel`; `managed_run_closes_pipe_closed_worker_before_return`; `direct_run_returns_with_pipe_closed_worker_live_control` |
| X38 | `managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes`; `managed_spawn_post_reap_cancel_bounds_escaped_capture`; real escaped-holder identity/release/reap |
| X36 / retained ownership | Existing unix.rs tests `managed_scope_setup_failure_never_executes_unmanaged_child`, partial-setup/fchdir/kernel-denial cleanup, ECHILD quarantine and post-spawn pipe-setup failure |
| A primary cause/report | Existing unix.rs first-cause stdout/stderr and overlap/deadline tests; ProcessReport accessor/classification/copy tests |
| X30 | `repeated_public_run_calls_keep_fd_count_stable`; explicitly run its isolated census child, not a zero-test/ignored pass |

For unix.rs module tests obtain the fully qualified names from the built libtest
`--list`; require exact match before invocation. Linux-only reaper/census/poll
tests remain Linux-specific. Darwin needs native equivalents for real lifecycle
contracts, not imitation of Linux procfs. No new performance benchmark: reuse its
accepted workload unless changed code invalidates its stated objective.

Execute the absent package-minimum baseline rows on each Unix OS; add only semantic
profile deltas above. Share the build for related cases. Review lifecycle, errors,
source binding and cleanup together once; specialist escalation only for a concrete
ownership/unsafe-code finding. This package can complete while Windows is unavailable.

### Windows custody prerequisite

**Outcome:** existing authorized guest safely executes bounded owned work and
exports readbacks after success, failure, supervisor death or controlling-connection
loss, preserving an unrelated sentinel. No Cargo/product build before this gate.
This is a native-execution prerequisite; it does not block ordinary source work
on the Windows backend or independent Unix/Base sys/TCP acceptance.

The selected route is the existing monitor-owned payload job and public
`ScopedRunner.exe --lease-client`, exercised by `MonitorAcceptanceDriver`.
The direct legacy `ScopedRunner --source/--exe` route is refused and is not usable.
Do not add a replacement general runner or revive the whole historical harness
as a gate. Reuse the narrow existing sources/fixtures; repair only the composed
native path needed for this project's contract. This route is selected from
source inspection; native feasibility is still an execution prerequisite.

1. Read host identity/state via SSH, with `BatchMode=yes`/ConnectTimeout10:
   `virsh -c qemu:///system domuuid rhai-win11-quality`, `domstate`, `domblklist`,
   `dumpxml`, `vncdisplay`. Require UUID `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`,
   only the owned system disk, intended console and no unexpected passthrough.
   Do not hash the multi-GB installation ISO again or restore an old image.
   The read-only planning observation matched this identity and found `shut off`;
   refresh only this small live state before later execution. `vncdisplay` failing
   because the stopped domain is not running is expected, not a product defect.
2. Observe guest readiness through its existing local VNC console via an owned SSH
   tunnel. Running hypervisor state is insufficient. If the owned installed guest
   is cleanly stopped, normal start is within later VM-work authorization; no reset,
   reinstall, snapshot restore or foreign domain operation. Read native OS, token,
   tools, available space, active jobs and current source/cache paths. No credentials
   or admin escalation. If console/access is unavailable, preserve a precise blocker
   and continue Unix/sys/net work, not another Windows setup campaign.
   Read back the native MSVC linker/SDK and compiler environment as well as Rust;
   finding Roslyn `csc.exe` alone does not establish the Rust link prerequisite.
   If present, call the installed BuildTools `Common7\Tools\VsDevCmd.bat` with
   `-arch=x64 -host_arch=x64` only inside the owned command payload, then restore
   its private temp/cache/target settings. Freeze effective PATH/LIB/INCLUDE,
   link/Rust versions and target; do not alter the interactive guest or global
   environment. That guest path/component availability is unconfirmed until readback.
3. Transfer the exact source/lock/manifest into a unique guest input root, using
   the existing console/serial flow. A fresh read-only payload ISO on this VM's
   existing optical device is an allowed later transfer fallback; it is owned data,
   not a replacement system image/service. Verify every byte/hash in the guest.
   Preserve `baseline-source*`, backups, disks/UEFI/TPM and Tauron resources.
   Host `genisoimage` is present; select it rather than the absent `xorriso`.
   Its future payload syntax is `genisoimage -J -R -o <owned>/payload.iso
   <owned-flat-input-directory>`. Record the ISO and input hashes, attach only to
   the observed optical device of this exact VM, then read them in the guest.
   Choose a collision-free loopback tunnel port after the live VNC autoport is
   known; no fixed stale `5900` assumption. Serial export uses the verified existing
   `/var/log/libvirt/qemu/rhai-win11-quality-serial0.log`, reading this run's framed
   records by invocation identity rather than accepting old log text.
4. Bootstrap only the custody tools using the existing scoped compiler owner in
   `fixtures/RunSourceFixtures.ps1`. Add a narrow build-only selection if needed;
   do not run the full synthetic fixture suite or require obsolete source pins.
   Review native bootstrap ownership before execution; its finite compiler/root
   cleanup controls are part of this prerequisite, not already accepted proof.
   Use installed `C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe` and the nine
   production sources named in that script, then compile the driver and focused
   fixture as documented in tools/windows-scoped-runner/README.md. Reuse a retained
   binary only after matching all current source/compiler hashes. No new SDK install.
   Its current bootstrap obtains native delegates through Reflection.Emit before
   launching csc, so do not introduce an unsupervised Add-Type compiler to create
   the owner. Compile `ScopedRunner`, `MonitorAcceptanceDriver` and the focused
   fixture serially within that existing owner. The separate driver compiler
   wrapper's historical `C:\RhaiQuality\runs` path is not the runtime policy:
   adapt it to the same user-private scope if reused, rather than creating a
   second root or nesting the native driver under the bootstrap's no-breakaway job.
   Static source audit found a concrete stale production pin in
   `CompileMonitorAcceptanceDriver.ps1`: WindowsCustodyBackend `664f4d61…` differs
   from actual source and RunSourceFixtures `368e230e67b6712a29386b8623c69bf9e58ab404687a79078685ffe5cf061ee5`.
   Reconcile both compiler manifests with the reviewed nine-source snapshot and
   driver/fixture hashes in this same repair. Do not merely disable the hash check.
   The current script has no build-only switch; adding that narrow selection and
   the focused observer controls is planned implementation, not an executable
   command available today. Its parameters today are `-SourceRoot`, `-RunRoot`
   and `-SetupFailureControl`; the driver compiler additionally requires
   `-RunnerPath` and `-ExpectedRunnerSha256`.

   Inside the reviewed bootstrap owner, existing compiler argv is
   `csc.exe /target:exe /main:ScopedRunner /out:<build>\ScopedRunner.exe <nine-sources>`
   then `/main:MonitorAcceptanceDriver` with those nine plus
   `MonitorAcceptanceDriver.cs`; compile `PayloadFixture.cs` as its separate
   finite fixture. Keep the runner beside the driver: it resolves
   `ScopedRunner.exe` from its own binary directory. After the compiler owner exits,
   invoke the native driver independently. The compiler commands must never be
   run bare to bootstrap their own ownership. Retained unchanged binary reuse
   requires source/compiler/argv hashes and observed native compatibility.
5. Launch the driver from an independently verified uncontained console process;
   its source rejects an ambient job. Run `success`, `disconnect-alive`,
   `client-death` and the planned monitor-death/assignment/nested-context controls against
   a small finite native fixture before product compilation. The current verified
   source syntax is:

```text
MonitorAcceptanceDriver.exe --mode success --source <owned-input> --exe <relative-fixture.exe> --expected-payload-exit 00000000 -- <fixture-arguments>
```

Use each negative mode's actual expected payload/client outcome from the current
driver validator; do not interpret EOF alone as success. The existing negative
modes require `MonitorStopped`, payload exit `0000007D`, client exit1 for
client-death and78 otherwise, confirmed cleanup/removal and matching evidence
hashes. Success requires the supplied payload exit, `PayloadExited` and client78.
Add the missing monitor-death and fault controls as focused native fixture/driver
extensions; they are not existing command flags. Monitor-death proves
grandchild termination and independent observer resource disposition; connection
loss proves bounded work even if the controlling process stays alive. Include
normal residual-child closure, payload failure, output-limit, nested refusal/setup
failure and evidence/cleanup failure. Malformed journal, missing identity or failed
readback fails closed. Replay/codec tests are retained if that path changes, not a
new product release axis.

Concrete composed-path repairs required before relying on it:

- `MonitorPayloadJob.cs` currently passes a null environment to CreateProcessW;
  unlike the old ScopedRunner helper, it does not set private Cargo/temp output.
  Supply a bounded immutable environment with runtime-local CARGO_HOME,
  CARGO_TARGET_DIR, TMP/TEMP and exact toolchain paths. Never mutate the parent.
- Use one project-specific `run-acceptance.cmd` payload, with a hash-pinned copy of
  the installed `cmd.exe` as the staged relative executable, to execute this plan's
  exact Cargo/test commands. This is an execution script, not a shell-based product
  process API or another generic runner. Cheap native fixture commands must prove
  copied executable resolution, runtime cwd (`run-acceptance.cmd` at the staged root), quoting,
  environment, exit and export before any Cargo invocation. If the staged command
  executable cannot run, use a small project-specific native command driver that
  calls exact Cargo paths/argv; it stays in the same payload job and must pass the
  same small entry-path control. Do not add an extra custody layer.
- Extend the driver's 180-second fixture-only watchdog to a bounded product mode
  covering the actual selected Cargo group, up to the existing 30-minute payload
  deadline plus its documented termination/finalization reserve. Keep the short
  mode for gate fixtures. These are chosen execution deadlines, not renewed human
  repair budgets. Split only at real completed acceptance groups if needed.
- Set measurable job memory/active-process limits appropriate to the 8 GiB guest,
  initially 5 GiB aggregate, 4 GiB per process, 16 active processes and two Cargo
  jobs; an 8 GiB runtime disk cap and 16 MiB bounded log files. Measure before
  admission. These estimates may be adjusted with a recorded reason; never exceed
  current available capacity or weaken containment to accommodate a test.
- Audit the complete staging/work/export dependency before Cargo. Today
  `WindowsCustodyBackend.CapturePayloadEvidence` recursively snapshots the entire
  runtime, with 512 MiB total, 2,048 inventory entries, 64 MiB per file, 248-character
  paths and a 30-second finalization reserve; the driver independently validates
  the 512 MiB receipt bound. These are current source limits, not proof that an
  8 GiB Cargo scope fits. Source pins and a larger watchdog alone cannot repair it.
  Use a small immutable flat input (`source.tar`, lock, owned patches and exact
  project command payload), a separate private `work` subtree for extracted
  source/target/cache/temp, and a bounded `results` subtree for manifests, original
  statuses/logs and OS observations. Implement this distinction in the existing
  allocation/monitor owner: after exact payload Job closure, retire owned `work`
  by verified directory identity before the existing evidence snapshot. Retain
  immutable inputs and bounded results under the current snapshot limits; do not
  export Cargo registries or target trees as acceptance evidence. Work disk usage
  stays separately bounded/observed. Normal exit, payload assertion failure,
  disconnect and client-death use the same owner finalization. Monitor-death uses
  the independent exact-identity observer for abort logs/cleanup and never reports
  product GREEN. If retirement exceeds the finite reserve or identity changes,
  preserve custody/diagnostics and keep cleanup open. Do not loosen all parser
  bounds or silently exclude unowned files to fit a build.
  Prove this transition with a finite nested work fixture that exceeds the old
  snapshot byte/entry/per-file/path limits while its exported results stay small;
  require complete work removal and bounded verified export, including an aborted
  run. This cheap control must pass before a Cargo artifact is produced.
- Complete host export/readback: manifest exact files, lengths/hashes and statuses
  to the existing serial channel in bounded framed chunks. Verify the host-side
  decoded export and final receipt before deleting guest evidence. A partial serial
  transfer or missing cleanup receipt is infrastructure failure, not GREEN.
  Runtime cleanup can finish independently while durable guest evidence awaits
  host confirmation. Never delete the only surviving failure logs.
- For monitor-death, retain the exact monitor and fixture process handles in the
  independent observer, but never duplicate a payload Job handle merely to observe
  it: that would defeat last-handle kill-on-close. Observe membership before the
  action, terminate only the retained monitor handle, require exact child/worker
  exit, and let the surviving observer export the abort and perform identity-bound
  runtime cleanup. A native abort is an interruption control, not product GREEN.

Job handle inheritance, creation-before-resume, exact retained process handles,
normal scope closure and no unmanaged fallback are mandatory. Microsoft documents
[job lifetime/membership](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[nested jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)
and [process creation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).
The execution design above is an inference/proposal from those APIs and current
source, not native proof. In particular, nested membership and closure must be
observed; missing notifications alone do not prove zero members. One combined
independent review covers this prerequisite and its native evidence; a concrete
handle/job race calls for an additional focused Windows specialist review.

### Windows process backend

**Observed gap:** `src/packages/sys/process.rs` registers only `cfg(unix)`;
there is no Windows module, Child export or Windows CleanupService in SysState.
`tests/sys_process_windows.rs` contains a minimal raw-output test but no native
handle cleanup proof. `examples/sys_process.rs` currently exits successfully with
a non-Unix “requires Unix” message. These are missing implementation/acceptance,
not merely missing Windows logs.

**Prerequisite:** native custody gate above, current source snapshot, compatible
MSVC1.77.2 tools. Check installed versions; if missing, provision a user-private
official portable toolchain/target with verified checksums, leaving baseline1.93
and shared config unchanged. No BuildTools/global reinstall or VM reset.
These prerequisites gate native execution and acceptance. Owned backend/test
source implementation does not require a running guest; if access is blocked,
continue ready source or Unix/sys/net work instead of waiting on it globally.

Implement `src/packages/sys/process/windows.rs`, Windows cfg registration/export
and SysState cleanup initialization. Keep the current Unix backend intact.
Reuse common report/cause definitions; share option validation/registration only
where doing so reduces actual duplication without destabilizing Unix custody.
Use bounded concurrent pipe I/O and a retained cleanup owner; no blocking
`Command::output()` substitute. DirectChild owns one exact child; Managed owns
an unnamed non-inherited Job, created/assigned before user code runs, with normal
leader-exit closure and cancellation of members. Validate cwd against the held
filesystem capability; demonstrate OS directory identity after path replacement,
not just a lexical canonical path. If a stable launch cwd cannot be established,
fail explicitly before child effects rather than silently follow a replaced root.

Use an optional Windows-target dependency `windows-sys = "=0.59.0"`, enabled
only by sys. Start with Foundation, Security, Storage_FileSystem, System_IO,
System_JobObjects, System_Pipes, System_ProcessStatus and System_Threading feature
groups; enable another group only for a used API. The accepted optional lock
already contains 0.59.0 and windows-targets0.52.6. Its
[upstream manifest](https://github.com/microsoft/windows-rs/blob/0.59.0/crates/libs/sys/Cargo.toml)
declares Rust1.60, compatible with the chosen optional minimum. Update only the
root dependency/feature graph in a private lock copy, preserving existing package
versions/checksums; record old/new lock hashes and diff. Subsequent commands use
that new reviewed lock with `--locked`. Recheck the core1.66 active graph and
update its compatible lock if the root manifest changed, without importing the
optional packages into a core build. Do not use a new windows-sys release or
general `cargo update` to solve this bounded dependency change.

The concrete lifetime seam is a shared backend owner holding the exact process
handle, pipe state, optional Job and immutable terminal snapshot. Create pipes
and an explicit inherited-handle list; parent pipe and Job handles are never
inherited. Call CreateProcessW suspended, assign Managed children before resume,
close the thread handle after resume, then let bounded pipe workers and an
exact-handle wait publish one first cause and stable report. Failed create,
assignment, resume or pipe setup terminates/waits only the owned suspended child
and retires the reservation; never resume outside the selected scope. Blocking
stdin and inherited output holders must be cancellable, with honest completeness.
Use per-operation overlapped pipe I/O/events with cancellation through `CancelIoEx`
and observed completion before releasing buffers/handles; fixture readiness and
stdin/output progress use events/records, not sleeps. If an existing synchronous
worker is reused, it needs an exact native cancellation/join proof before acceptance.
Shared handle wait returns a cached immutable terminal snapshot; cancellation,
kill/drop and the one first-cause publication must not take a lock that prevents
the other shared handle from stopping an outstanding wait. Process/job/pipe
ownership is backend-local; public feature-correct validation remains shared.

For cwd, derive a native path from the held directory capability and compare
volume/file identity. Pin that directory and the path ancestors against rename
during launch, recheck their identities, then pass the stable path to the suspended
creation. Treat this as a design to prove with native replacement/race controls,
not as an already established guarantee. If the path cannot be pinned safely,
return a specific pre-execution error; the promised valid replaced-root case
remains open until it passes. Do not replace the accepted capability contract
with string-prefix checks.

Start with a public-Engine registration/runtime RED for run/raw/spawn/Child, then
implement and extend `sys_process_windows` with finite self-executing fixtures:
records/readiness/release files and a retained OpenProcess handle with creation
identity, actual job-membership checks, exact wait/exit/handle closure. Add native
argv reconstruction for quotes/backslashes/empty/metachar arguments, suffix/PATH
resolution and default-denied .bat/.cmd before effects. Ordinary executable argv
uses no shell. Environment changes stay inside children.
The explicit host batch opt-in remains supported: use the corrected Rust1.77.2
[batch command construction](https://github.com/rust-lang/rust/blob/1.77.2/library/std/src/sys/pal/windows/args.rs)
as the compatibility reference, including rejected CR/LF and bounded handling of
quotes, percent expansion, delayed expansion and metacharacters. Regular exe
arguments use the native executable convention. Never apply regular-exe quoting
to batch input, use raw_arg for script data or silently drop the accepted opt-in.
Native positive argv readback and attempted side-effect injection controls are
required for that branch. Any adapted upstream algorithm needs license attribution.

Port X1–X21 and X23–X38 observations where applicable, using existing Unix oracle
structure but real Windows APIs. X22 signal9 is Unix-only; Windows signal getter
is unit and native termination status follows its documented contract. Test
timeout/overflow/kill/final-drop, no-final-drop retained custody, cached clone
reports, script throw, sync waiter cancellation, normal Managed worker closure
versus DirectChild worker survival/reap, setup/assignment refusal and unrelated
sentinel survival. For retained-pipe/X38 use a fixture outside the product Job
but owned by the outer test scope; do not enable breakaway in the product Job
just to manufacture escape. Prove bounded honest incomplete capture and release/
cleanup of that holder. Windows handle-count census replaces Linux fd census.

Preserve primary Io/Timeout/OutputLimit, secondary cleanup diagnostics, immutable
raw captures/completeness, no-primary decoded-expansion behavior and Rust variant
compatibility. Exercise publication before another shared-handle wait returns.
No numeric-PID sweeping; cleanup waits on exact retained handles/job accounting.

The current `sys_policy::test_function_metadata` conditionally checks Child
comments and signatures only under Unix. Extend those checks to Windows after
registration exists, with feature-correct collection/scalar overloads. Its current
Windows GREEN would otherwise omit the new API. Likewise, port the no_index
scalar process assertion currently inside the Unix-only target to a Windows
target that is actually listed and executed.

Adapt the process example to a real Windows self-fixture run/spawn/readback flow
and feature-correct waits. Do not count its current platform no-op as execution
acceptance. Build and run Windows minimum baseline and required semantic variants
in the same owned payload scope where inputs permit. Existing Windows filesystem
proof remains independent. Review backend/tests/example together once, including
actual guest membership, exported OS observations and interruption safety.

### Base sys and shared file handles

**Outcome:** all uncovered P/E/F rows and file-handle contracts have native
Engine/OS readback. Linux nine-row feature evidence and Darwin root aliases are
retained when applicable. Windows requires new native missing rows behind custody.

Canonical targets are `--test sys_policy --test sys_env --test sys_fs` with
features `testing-environ,sys,metadata` for the baseline, 1.77.2 minimum. A target
suite on an uncovered OS may run together; already covered OS rows select only
changed/missing functions. Environment fixtures execute in the existing isolated
child helper; do not set_var/chdir in the parent. No fixed sleep as readiness.

File-handle delta selectors in `--test sys_fs` are:

```text
test_open_file_default_preserves_contents_and_shares_cursor
test_open_file_modes_and_exclusive_create
test_open_file_checks_grants_before_mutation_and_stays_confined
test_file_handle_read_string_advances_the_shared_cursor
test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving
test_file_handle_string_read_requires_complete_utf8
test_file_handle_read_respects_engine_limit_below_host_cap
test_file_handle_read_blob_preserves_bytes_and_obeys_host_cap
test_file_handle_reads_fail_at_eof_and_on_write_only_handle
test_file_handle_blob_read_respects_engine_array_limit
test_file_handle_blob_read_is_omitted_under_no_index
```

Select only applicable missing assertions from this list, respecting each cfg;
list and bind the executable first. Host reads confirm contents/cursor
effects; denied paths leave sentinel bytes unchanged. Checked-only Engine caps
are excluded under unchecked, while host caps remain mandatory.

Windows-specific: F20 slash normalization, F21 bounded CON error, root replacement,
ancestor aliases and owned junction/symlink escape boundaries. Implement focused
native fixture support if absent. A junction proves the applicable reparse-point
directory boundary, not every symlink behavior. Attempt an unprivileged symlink
only when available; unavailable privilege leaves its exact promised row open.
Do not enable Developer Mode/admin rights or silently skip and mark passed.
Unix non-UTF-8 names/env and Darwin system-prefix aliases run on their defining OS.
One combined review covers relevant permissions/path/handle deltas and evidence.

### TCP native closure

**Outcome:** uncovered grant, connection/listener, byte/EOF/partial transfer,
shutdown/shared-close/cancellation and limits are accepted on all native OSes.
No TCP UI/server setup is needed; independent fixture peers bind OS-selected ports.

Canonical baseline command target set:

```sh
cargo +1.77.2 test --locked --features testing-environ,sys,net \
  --test net_connect --test net_listen --test net_reads --test net_writes \
  --test combined_sys_net -- --test-threads=1
```

For metadata use `--test net_metadata`; no_object uses `--test net_no_object` and
features `testing-environ,net,no_object`. Variant scopes select exact changing
tests: no_index string/blob omission, sync close-unblocks-read and quota-wait,
unchecked host cap, f32 duration rejection, accepted-stream inherited bounds,
metadata inventories. Preserve Linux nine-row results; do not run those whole
suites again for a Windows-only process module.

No IPv6 native test was found in the inspected net test sources. Add real `[::1]`
connect and granted port0 listen/accept cases, with exact address+port authority,
independent peer bytes and denied endpoint control. IPv4 passes do not close the
explicit IPv6 contract. If loopback IPv6 is unavailable, record actual socket
error and its native row open; no host network reconfiguration or IPv4 substitution.

Audit each contract in the coverage table against an actual selected oracle;
add a focused case only for a missing assertion. In particular, zero/negative
lengths, short reads, bounded EOF loops, lossy split UTF-8, port bounds, finite
timeout ceiling, NaN/infinity/range and partial write bytes must be checked before
or against independent peer effects as appropriate. Read/write half-close and
clones need explicit readiness and eventual peer completion/join. One combined
review covers new native/IPv6/semantic deltas and unchanged proof applicability.

### Integrated compatibility, documentation and fork main

**Outcome:** all original requirements and native/feature/minimum obligations
have applicable evidence at the integrated revision. This is a final consistency
gate, not a request to rerun every package. No release-ready claim with an open
promised native row, access prerequisite or incomplete-cleanup oracle.

Check actual shared deltas against core1.66 and optional1.77 locks/dependencies;
reuse unchanged positive/negative compiler proofs. Execute missing variant
registration/behavior targets from the matrix. Metadata must describe every actual
registered overload, error/report, timed wait returning unit without cancellation,
process scopes and file/TCP divergences. Correct docs to final implemented Windows
behavior; remove false Unix-only limitations only after proof. Preserve approved
trust boundaries. Run sys/net/process examples on the platforms whose behavior
they demonstrate; retain Linux/Darwin unchanged example controls.

Use one final independent combined review of integration, requirement coverage,
source/proof applicability and final docs. It may reuse prior package reviews;
it is not a second full specialist scan. A finding triggers only affected checks.
Give any later independent reviewer the unchanged installed Wayfinder/user override
and product/security rules for this effort; do not copy old roles, harness rules
or campaign budgets. Review specification, coding standards, native assertion
binding and resource disposition in the same bounded review task. No new reviewer,
coordinator or other-chat message is part of the current planning request.
Update the existing criterion state during later execution with links to these
results; archive history once, do not maintain simultaneous counters/inventories.

Only explicitly owned, verified coherent patches are committed. Use an isolated
integration worktree if necessary to protect dirty/foreign main and foreign fixture
changes. Read exact fork main first (`git ls-remote --heads origin main`); integrate
current fork history without force, review conflicts and test affected merges.
Use command-local `git -c user.name=hoppworks commit ...` with configured email;
verify both author and committer are lowercase hoppworks and no coauthor trailer.
Unset an inherited overriding author/committer name only in that command environment.

Publish a tested local integration ref with
`git push --atomic origin <tested-local-ref>:refs/heads/main`. Re-read remote main
and compare the exact commit. If remote advanced, refresh/reconcile and verify
only affected changes; never force push. A coherent local commit and an atomic
remote ref transaction are separate operations; failed push preserves the commit.
Keep main as the only fork branch: delete only verified integrated, owned obsolete
remote refs in the same atomic update if any exist; unknown/foreign new branches
must not be discarded. No public upstream push/PR, remote task branch, deployment
or publication. Retire only this effort's finished build resources after export.
Also verify local refs: fast-forward the primary `main` checkout only when its
tracked state is clean and the update preserves foreign/untracked data. Detach an
owned temporary checkout at its integrated commit before deleting its obsolete
local branch; do not retire a checkout containing foreign changes. Final branch
readback covers local and fork-remote refs; preserve a precise ownership/conflict
blocker rather than discard unknown work to make the inventory look complete.

## Complete coverage crosswalk

The historical §6.7 proof status remains the input; the following routes all
original requirements to concrete selectors/observations. “Route” is planned
coverage, never an acceptance claim. Existing function names are from current
sources; new native Windows/IPv6/Child.wait cases are explicitly planned above.
Short names in this crosswalk are contract/search descriptions. Executable
selectors come from the exact mappings above and that artifact's `--list`; never
pass an abbreviated crosswalk label and accept a zero-test result.

| Original criteria | Tests / independent oracle | Package |
|---|---|---|
| P1, P3–P5 | default_config_denies_fs, read_only_root, remove_dir_all_needs_delete_access; sentinel/readback | Base sys |
| P2, P10 | default_and_nonmatching_process_policies_deny_public_run_without_starting_child; exact allow-list success/absent child marker | Unix closure / Windows backend |
| P6–P9, P14 | parent_traversal, symlink_escape, absolute_paths, root_with_dot_components, configured_root_symlink_then_parent, symlinked ancestor and alias regressions | Base sys |
| P11 | process_cwd_uses_the_opened_filesystem_capability_after_root_replacement; denied escape/identity/readback | Unix closure / Windows backend |
| P12 | env_allow_list tests and child-isolated known/unset/hidden variable readback | Base sys |
| P13 | native batch default refusal before child effect; explicit host override contract | Windows backend |
| E1–E3 | env_var_set_and_unset, env_vars_all, env_allow_list_value/unset/default-policy | Base sys |
| E4–E5 | env_var_non_utf8 on Unix; cwd_matches_process independently | Base sys |
| F1–F5 | read_file_cases, read_binary, large_file_round_trip; exact/empty/lossy/blob/8MiB fixture truth | Base sys |
| F6–F9 | write_append_blob, write_into_missing_parent; fresh truncation/append/blob read and absent partial output | Base sys |
| F10–F13 | predicates_and_metadata, read_dir_cases, wrong_entry_kind; host metadata and sorted fixture inventory | Base sys |
| F14–F17 | create_dir_cases, remove_cases, rename_and_copy, copy_across_roots; effects/unchanged source/denied sentinel | Base sys |
| F18–F21 | unicode_names, non_utf8_file_name, windows_paths (slashes and CON); native fixture facts | Base sys |
| F22–F23 | unrestricted_symlinks_follow_host_semantics, symlink_then_parent, root/ancestor/system-prefix aliases and permission preservation | Base sys |
| File-handle extension | test_open_file_* / test_file_handle_*: modes, shared cursor, grants, negative/bounded reads, UTF-8/EOF, no_index, checked/host caps | Base sys |
| X1–X3 | raw capture/nonzero exit; missing program/cwd no fixture; host record + exact exit/reap | Unix closure / Windows backend |
| X4–X6 | run_preserves_argv_boundaries_without_shell_interpolation; empty/space/quote/metachar argv and no shell marker | Unix closure / Windows backend |
| X7–X11 | valid/invalid capability cwd, env_clear/override/remove fixtures; child records and sentinel | Unix closure / Windows backend |
| X12–X17 | separate/exact/interleaved4MiB/raw/lossy/empty streams, string stdin and concurrent blob1MiB; output bytes and reap | Unix closure / Windows backend |
| X18 | unit_stdin_means_immediate_eof; retained named Linux/Darwin proof, uncovered native rows | Unix closure / Windows backend |
| X19–X20 | run_deadline_returns_bounded_partial_output_after_terminating_child; run_io_contract_empty_output; retained direct rows. Separately cover unit_timeout_disables_configured_default_deadline for the unit-option contract. | Unix closure / Windows backend |
| X21 | output_limit primary/per-stream cap+1 prefix, zero cap, host ceiling and overlap precedence; retained named rows | Unix closure / Windows backend |
| X22 | run_reports_a_real_unix_child_signal_without_an_exit_code; retained Unix signal/reap rows; Windows unit signal contract separately | Unix closure / Windows backend |
| X23–X24 | real example run/spawn/waits plus direct_spawn_try_wait_returns_unit_until_child_exits; clone cached snapshots | Example correction / Unix closure / Windows backend |
| X25–X29 | kill+wait/idempotence, nonfinal/final drop true/false, script throw, retained no-kill owner and eventual reap | Unix closure / Windows backend |
| X30–X31 | repeated-run census and sync shared wait-entry cancellation; handles/fds, exact release and stable report | Unix closure / Windows backend |
| X32–X33 | native embedded quote/backslash/empty argv and .exe/PATH lookup, child argv record | Windows backend |
| X34–X35 | managed timeout/cap/kill/final-drop and normal leader-exit worker closure; DirectChild contrast | Unix closure / Windows backend |
| X36–X38 | setup/assignment refusal, exact host/sentinel safety, escaped/retained-pipe bounded incomplete capture; ownership/reap | Unix closure / Windows backend |
| Process compatibility / A–B | old Rust variants; Process report/cause/classification; immutable cached bytes, first cause, no-primary decoded expansion; no-primary test added | Unix closure / Windows backend / integration |
| TCP authority | default denied, connect/listen separate exact IP+port, no DNS, IPv4+IPv6, port0 listen vs invalid connect, endpoint bounds/no peer effect | TCP closure |
| TCP lifetimes/limits | host deadline ceiling, negative/NaN/infinity/range, quota64/shared engines, accepted inheritance, no leaks, sync quota/read cancellation | TCP closure |
| TCP data | exact short/blob/lossy prefixes, zero/negative read, bounded EOF partial progress, actual write/write_all partial peer bytes, half-close/idempotent shared close | TCP closure |
| R1–R2, R4 | optional isolation/core dependency graph; intentional no_std/WASM/sys-no_object diagnostics at supported toolchains | Integration |
| R3, R5 | no_index scalar/collection omission, Child type registration including Windows | Semantic matrix / Windows backend / integration |
| R6–R7 | sys/net metadata inventory and typed catch/getters + continue with real subsequent effect | Semantic matrix / integration |
| Ticket06 native/feature/MSRV | eleven positive rows, justified behavioral selections, core1.66/optional1.77 and retained1.93 cases, native custody | All packages / integration |
| Docs/examples/performance | existing accepted examples/metadata/narrow Linux performance, X23 fix, real Windows example; no fictitious new benchmark axis | Example / Windows / integration |
| Owner boundaries | owned resource export/cleanup, private fork main only, lowercase hoppworks, no foreign changes | All packages / integration |

The previous A–F grouping remains covered, without using its order as execution
instructions: **A**'s accepted Linux first-cause controls and narrow performance
proof stay reusable at their scope; uncovered platform/semantic first-cause rows
are in Unix closure/Windows backend. **B**'s terminal/stdin/cache/cancellation and
no-primary assertions are in those same product packages. **C**'s Darwin native
work is distributed across Example, Unix, Base sys and TCP. **D**'s Windows native
ownership/product outcomes are in custody, Windows backend, Base sys and TCP.
**E**'s accepted metadata/docs/examples remain reusable; only new API/platform
deltas enter Example, Windows backend and integration. **F**'s native/feature/MSRV,
compatibility and fork outcome are the integrated gate. A complete X18 or a new
plan never implies A–F completion.

## Done, blocker and handoff rules

An execution result records changed inputs, selected criteria, reused proof links,
commands/statuses, native independent observations, assertion control/restoration,
cleanup, combined review and remaining gaps. Update the status only from those
facts. Completion requires no uncovered promised row in the crosswalk or matrix.
X18 acceptance alone never closes Ticket03 or the A–F package.

No human preference is unresolved. Autonomous execution may diagnose and repair
ordinary missing code/runner/fixtures under the later implementation instruction.
It cannot manufacture native access, grant missing admin privilege, weaken a
criterion or interfere with foreign resources. If such a boundary is reached,
record one precise external prerequisite and finish independent work; ask only
for an outcome-changing external decision. Do not reopen the general plan.

The most exposed assumption is live Windows console/toolchain/monitor feasibility.
The next largest implementation risk is Windows capability-cwd and nested Job
ownership: these must pass native identity and failure controls. This plan reduces
overhead by reusing current sources/proofs, testing the complete entry path cheaply,
sharing private builds for related controls, and refusing parser failures as a
reason to rebuild. The plan is not acceptance evidence; use the linked per-package
results and current execution state for completed and remaining work.

## Planning validation and limits

Read-only validation on 2026-10-08 found all 87 original numbered criteria in the
crosswalk (P14/E5/F23/X38/R7, no omission or extra ID), plus the unnumbered
file-handle/TCP/cause/report/native/release/owner obligations. All 20 distinct exact
`target::selector` mappings (21 mentions) resolve to current test function
definitions. Actual cfg-enabled presence still requires the later artifact's
`--list`; source presence is not a test pass. Local Markdown links in the Map,
assessment, route decision and this plan resolve. Archive, locks, current X18–X20
proofs and the saved latest X23 result files exist. The remote runner/import and
direct compiler version readbacks were checked; live guest entry, new flags,
snapshot/work transition and proposed new tests remain unexecuted prerequisites.

The preceding paragraphs preserve the read-only planning snapshot from
2026-10-08; at that point no product or runtime work had started. That snapshot is
historical, not current status. Implementation was later authorized. X23 and X35
acceptance are recorded above and in `execution-state.md`; their original build and
review evidence remains linked. The existing paused Goal remains paused, and no new
Goal is needed. Continue with the next open package in the ready queue.
