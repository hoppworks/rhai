# Native Linux current-source optional feature compilation — v2 stage-identity repair

This is a prepared, compiler-only Rust 1.77.2 package for native Linux x86_64.
It targets the accepted current source revision
`1ca21e32eed2aa40287ba7e1282000add1dd49c7`, with the complete `git archive`
SHA-256 `8251e0429d51ffd330e7eac596a1513d836e43e549ca761852cafc642a2a8155`.
The compatible lock is the accepted v3 lock at
`.scratch/all-tickets/macos-selected-graph-evidence-03/Cargo.lock`, SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The
older Linux optional MSRV evidence is preserved at
`.scratch/linux-optional-msrv-proof/`; its source and lock differ, so it does
not cover these current-source compile rows.

The prepared helper is
`.scratch/all-tickets/check-linux-current-feature-compilation-v2.py`. It reads an
explicitly staged source archive and lock from an existing `PROOF_STAGE`; it
does not make a Git checkout or resolve a lock. Proposed unique workhorse
stage: `/root/rhai-linux-current-features-v2-1ca21e32-20261002`. Before any
staging, verify that exact path is absent. Stage the archive as `source.tar`,
the accepted lock as `Cargo.lock.accepted`, the reviewed helper as
`run-feature-compilation.py`, its contract as `contract.md`, and the exact
existing scoped runner package by reference to `run_scoped.py`, `agentskills/__init__.py`, and `agentskills/pyguard.py`.
Record SHA-256 for every staged input and verify the source and lock against
the pins above. Keep the remote stage and its inputs separate from the private
build runtime.

The helper runs these eleven positive rows serially in one private source,
Cargo home, and target directory, followed by one negative compile prerequisite.
Every row command is exactly `cargo check --locked --lib --features <features>`.

| Positive row | Features |
|---|---|
| `baseline-sys-net` | `testing-environ,sys,net` |
| `sys-alone` | `testing-environ,sys` |
| `net-alone` | `testing-environ,net` |
| `net-no-object` | `testing-environ,net,no_object` |
| `combined-sync` | `testing-environ,sys,net,sync` |
| `combined-no-index` | `testing-environ,sys,net,no_index` |
| `combined-metadata-serde` | `testing-environ,sys,net,metadata,serde` |
| `combined-only-i32-no-float` | `testing-environ,sys,net,only_i32,no_float` |
| `combined-unchecked` | `testing-environ,sys,net,unchecked` |
| `combined-no-index-sync-metadata` | `testing-environ,sys,net,no_index,sync,metadata` |
| `combined-f32-float` | `testing-environ,sys,net,f32_float` |

Each positive status is retained separately. A failed positive compile is
recorded and later rows continue unless a setup, source/lock, sampler, resource,
or deadline condition stops the package. The final negative command uses
`testing-environ,sys,no_object`; it is accepted only when Cargo exits exactly
101 and the output contains this exact diagnostic:

> the `sys` feature requires object maps; it cannot be combined with `no_object`
The negative result is stored separately from the positive row summary. A
dependency failure or other status without that diagnostic is a failed
prerequisite.

The native Linux route is the previously used authorized `workhorse` SSH alias
as `root`; the recorded earlier route used `/root/.cargo/bin/rustup`. Use a new
private resource scope at
`/root/.local/share/agent-builds/rhai/linux-current-features-v2-1ca21e32-20261002/`.
Set `TMPDIR` to that absolute directory when invoking the existing configured
`/Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 590 --`
equivalent staged on workhorse. The runner creates the unique runtime beneath
the scope. The helper has a 530-second total deadline, including setup and
evidence export, with 500 seconds for setup and compile commands and the final
30 seconds reserved for export. The preserved failed setup attempt consumed 0.4396 seconds of outer time and 0.001 seconds of helper time before Rustup/Cargo; those amounts remain charged. This v2 allocation adds at most 590 seconds outer and 530 seconds helper (500 work + 30 export), so cumulative maxima remain 590.4396 seconds outer and 530.001 seconds helper. No renewed time budget is assumed.

Inside `AGENT_RUNTIME_DIR`, keep the extracted frozen source, copied lock,
Rustup and Cargo homes, target cache, temporary data, command stdout/stderr and
status receipts, resource samples, and generated evidence. Use only the
existing `/root/.cargo/bin/rustup` executable to install minimal
`1.77.2-x86_64-unknown-linux-gnu` with `--no-self-update` into the private
`RUSTUP_HOME`; invoke private direct `rustc` and `cargo` binaries. Do not access
shared Rustup/Cargo homes or configs. The environment is closed around private
`HOME`, `CARGO_HOME`, `RUSTUP_HOME`, `CARGO_TARGET_DIR`, and temporary paths;
Cargo uses two jobs, incremental compilation disabled, and debug information
disabled. Check the frozen source for `.cargo/config` and `.cargo/config.toml`
before invoking Cargo.

Sample private runtime storage with `du -sk` and helper-descendant RSS/count
from `ps` about once per second during commands and after commands. Stop
preemptively at 1,572,864 KiB sampled runtime storage; hard sampled runtime
storage and helper-descendant RSS limits are each 2,097,152 KiB, with at most
16 descendants. These periodic samples are not continuous peak measurements.
The size metric covers the scoped runtime, including source, caches, and
command logs, and excludes the separately staged immutable input archive and
the final exported evidence. Do not raise these limits if installation or
compilation does not fit.

Before dispatch, independently review the helper and coordinate a currently
free single heavy-build slot on workhorse. Preserve foreign processes and the
prior Linux proof. No SSH staging mutation, Rustup install, Cargo command,
download, or build is authorized by this preparation artifact alone. At
execution, the wrapper must retain outer/run-scoped status, runner and helper
process identities, the scoped cleanup readback, and runtime-absence readback.
Export all helper evidence to the exact stage before the runner removes its
runtime. Keep a final lock copy plus source archive/lock/helper/runner hashes
and command/version/host/status receipts in the exported evidence. Preserve
partial evidence on any stop, and do not automatically retry or enlarge the
allocation.

Preparation scripts are `stage-linux-current-feature-compilation-v2.sh` and
`launch-linux-current-feature-compilation-v2.sh`. The staging script verifies the
frozen Git archive, compatible lock, and exact scoped-runner package before it
uses the authorized `workhorse` SSH alias to create the unique stage and copy
inputs. It records and checks every staged SHA-256. The launcher uses the
prescribed 590-second `run_scoped.py` timeout and writes separate run-scoped and
outer statuses under `outer-evidence/`. It records exact PID/start-tick identity
rows for the launcher, runner, helper, scoped supervisor, and helper child
commands; unknown, malformed, or missing required identities fail closed. The
helper emits its PID and Linux start ticks to the outer log for observational
correlation. A launcher interrupt writes a private `interrupt.request` file in
`outer-evidence/`; the helper polls that exact path at its existing command
checkpoints, stops active compile work through its own child-cleanup path, and
exports partial evidence while returning failure. No signal is sent to a PID
based on a process-table lookup. After normal completion or an
interrupt, the launcher waits on its exact child runner; if Bash returns early
from `wait` to run the signal trap, it re-enters `wait`. The child runner keeps
the prescribed 590-second cap, with no additional polling or wait budget. After
runner completion, the launcher reads back the exported helper identities and scoped process groups,
checks that the runtime is absent, then removes only the exact empty scope with
`rmdir`. The helper's export deadline still applies after interruption, while
compile work remains stopped and the helper status remains failure. The pure
regression is `test-linux-current-feature-stage-v2.py`; it verifies that canonical aliases
are accepted, unrelated stages are rejected, early identity receipts are
durable, and missing required helper or supervisor identities stop setup
fail-closed after preserving their diagnostic receipt rows.

The prior immutable `linux-current-feature-outer.log` records a setup-only failure: on the target host `/root` resolves to `/var/roothome`, so a lexical comparison rejected the prescribed stage even though both paths named the same directory. The helper now compares `resolve(strict=True)` results for the candidate and expected stage, accepts that canonical identity, and rejects any other directory. The expected stage remains a new v2 path; the old stage and proof remain untouched. Before validating `PROOF_STAGE` or other stage inputs, it creates runtime-local early receipts for the runtime path and exact helper/scoped-supervisor PID/start-tick identities. Each required identity is sampled once and that same result is written durably. If either identity is unavailable, the helper preserves the diagnostic row and stops before staged validation or any external command. Failure export writes only to the hard-coded expected v2 stage after confirming that directory exists, never to an unrelated `PROOF_STAGE`. Unavailable identity rows also make launcher cleanup readback fail closed. The pure regression covers canonical alias acceptance, unrelated-stage rejection, and early identity capture ordering.

The helper runs no tests, examples, fixtures, scripts, Engine execution, or
Rhai native process/socket API calls. Its subprocesses are host-side Rustup,
Cargo, version, and resource-sampling operations. A passing package establishes
only compiler compatibility for the listed feature combinations on native
Linux x86_64 with Rust/Cargo 1.77.2. It does not establish native Engine
behavior, platform lifecycle behavior, test acceptance, or full release
acceptance; native count remains 84 and no native slot is allocated here.
