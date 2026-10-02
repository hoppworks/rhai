# Current-source optional feature compilation package

This prepared package covers the ten approved optional-package compiler rows not
already covered by the accepted combined baseline. It uses repository source
`4baf3b20ba8335fbe9dab21236182429a97f51ec`, which descends from accepted source
`9f84aa6d8163257b4e3f3c2fe4a1c7d7b7c3cce6`. The baseline
`testing-environ,sys,net` compile result is retained at
`.scratch/all-tickets/current-optional-msrv-evidence/` and is not repeated. Its
source production files, manifests, and selected lock remain unchanged at the
new frozen revision. The lock copied into the private source root is
`.scratch/all-tickets/macos-selected-graph-evidence-03/Cargo.lock`, SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

The helper runs these ten commands in order, reusing one private source tree,
Cargo home, and target directory:

| Row | Features passed to Cargo |
|---|---|
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

Every row uses `cargo check --locked --lib --features <features>`. A row failure
is recorded and later rows continue while time, lock integrity, and resource
bounds remain valid. Setup, version, source, lock, resource, or deadline errors
stop the package. No lock resolution or manifest/source edits are allowed.

The helper uses the existing `/Users/hoppworks/.cargo/bin/rustup` executable to
install minimal Rust/Cargo `1.77.2-aarch64-apple-darwin` with
`--no-self-update`. The private `RUSTUP_HOME`, `CARGO_HOME`, `HOME`,
`CARGO_TARGET_DIR`, source extraction, temporary files, downloaded toolchain and
crates, generated outputs, and staged logs all reside under `AGENT_RUNTIME_DIR`.
It invokes the private `rustc` and `cargo` by absolute path, verifies their
versions and the rustc host, and passes a closed environment with two Cargo
jobs, incremental compilation off, and dev debug information off. The archive
contains no tracked `.cargo/config` or `.cargo/config.toml`; the helper also
checks those paths in its private source. Private `HOME` and `CARGO_HOME` prevent
shared-home Cargo/Rustup configuration from applying.

Before any execution, complete independent source review and coordinate the
Machine's single heavy-build slot. Create one absent scope under
`~/.local/share/agent-builds/rhai/<unique-session-id>/`, set `TMPDIR` to that
absolute scope, and invoke the helper through
`/Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 600`.
The outer 600-second ceiling includes setup, all rows, evidence export, and
cleanup. The helper has a 540-second deadline, including setup and export, with
the final 30 seconds reserved for evidence export. The existing accepted
baseline is reused; the helper does not spend time or storage rebuilding it.

The helper samples runtime storage and helper-descendant RSS/count about once
per second during commands and after each command. It stops at sampled storage
`1,572,864 KiB` as the 1.5 GiB preemptive boundary; hard sampled storage and RSS
limits are each `2,097,152 KiB`, and the helper permits at most 16 descendants.
These are sampled bounds, not continuous peak measurements. Cumulative work and
sampled maxima must remain separate in the resulting report. A resource stop,
deadline, source/lock mismatch, toolchain mismatch, or infrastructure failure
ends this allocation; preserve partial logs and row statuses, with no automatic
retry or budget renewal. If the package cannot fit, report the exact limit and
remaining rows; do not raise the cap or claim unrun rows.

Evidence is exported before runtime cleanup to
`.scratch/all-tickets/current-feature-compilation-evidence/`. It includes the
used helper and contract, archive and lock/manifests identities, direct tool
versions, command argv/cwd/status, per-row stdout/stderr/status, row summary,
failure detail, and resource samples. The helper refuses to overwrite existing
evidence. After the runner exits, independently read back its status and verify
the exact runtime path from `export.json` is absent; remove only the exact empty
session scope with `rmdir`, and retain those cleanup readbacks beside the
evidence.

This package performs compiler checks only. It does not run tests, examples,
fixtures, scripts, or target Rhai process/socket APIs; it does not call native
process/socket functionality or measure target behavior. Git, Rustup, Cargo,
`du`, and `ps` subprocesses are host-side setup and custody operations. Passing
these rows proves only compilation for these feature combinations on native
Darwin arm64 with Rust/Cargo 1.77.2. It does not prove feature behavior, core
MSRV, Linux or Windows compatibility, native API lifecycle, or strict release
acceptance; those gates remain open.
