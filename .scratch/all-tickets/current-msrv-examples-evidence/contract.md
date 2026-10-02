# Current-source optional MSRV examples package

This package prepares a single native macOS Rust/Cargo 1.77.2 execution of the
`sys` and `net` examples from frozen repository source
`1ca21e32eed2aa40287ba7e1282000add1dd49c7`, target host
`aarch64-apple-darwin`. The examples share one private source tree, Cargo home,
Rustup home, target directory, and exactly one `cargo build` invocation. It
reuses compatible Cargo.lock v3 from
`.scratch/all-tickets/macos-selected-graph-evidence-03/Cargo.lock`, SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

The build command is `cargo build --locked --example sys --example net
--features testing-environ,sys,net`. It builds both executable examples together
with one private `CARGO_TARGET_DIR`, two Cargo jobs, incremental compilation off,
and dev debug information off. The helper uses the existing
`/Users/hoppworks/.cargo/bin/rustup` binary with
`toolchain install 1.77.2-aarch64-apple-darwin --profile minimal --no-self-update`.
It verifies direct private `rustc` and `cargo` versions and the rustc target host.
Private `HOME`, `CARGO_HOME`, `RUSTUP_HOME`, `TMPDIR`, source, lock, downloaded
crates/toolchain, generated files, target outputs, and logs are under
`AGENT_RUNTIME_DIR`. The source archive is made from the frozen commit with
`git archive`; its root has no `Cargo.lock` and no tracked `.cargo/config` or
`.cargo/config.toml`. The helper also rejects Cargo config in the private Cargo
home and supplies a closed command environment without rustflags or compiler
wrappers.

To prove the readback assertions are meaningful without extra Cargo builds, the
helper temporarily adds a narrow environment-selected expected-value seam to
the two example assertions in the extracted private source only. It compiles
those two examples once, then restores `examples/sys.rs` and `examples/net.rs`
byte-for-byte to the frozen archive and verifies their hashes, all Cargo.toml
hashes, and the lock hash before executing either binary. The seams default to
the exact frozen expectations. For the RED controls only, the helper sets a
single private environment variable to a known-wrong expected value; the helper
accepts status 101 only when stderr contains the intended assertion message and
the exact observed/expected values. It then unsets that variable and requires
status 0 plus the independent readback output. The example binaries run the real
Rhai `Engine`: `sys` changes a scoped host file and reads the host file back;
`net` connects to the example's independent real loopback peer, which reads the
script's bytes and returns `pong`. These controls alter only the assertion
expectations in the disposable source copy; they do not mock the Engine, file,
peer, or socket. No tracked production/example source is edited.

The four expected example commands are run in one order: `sys-red`, `sys-green`,
`net-red`, `net-green`. RED means an intentional assertion failure with process
status 101, the named assertion diagnostic, and the expected actual/incorrect
values. GREEN means status 0 and the example's independent host readback output.
The net peer is joined before its byte assertion, including in the RED case. The
helper verifies no `rhai-sys-example-*` directory remains beneath its private
temporary directory after the example runs. Raw command argv, cwd, status,
selected environment overrides, stdout/stderr, version output, source/archive/
lock/manifests hashes, controls, cleanup readback, and periodic resource samples
are exported to `.scratch/all-tickets/current-msrv-examples-evidence/`. The helper
refuses to overwrite that destination. The coordinator must independently read
back the outer/scoped result and verify the exact runtime and empty owned scope
cleanup after `run_scoped.py` exits.

Before actual execution, the coordinator must independently review the helper
and recheck the Machine's one-heavy-run slot. Create the absent unique scope
`/Users/hoppworks/.local/share/agent-builds/rhai/current-msrv-examples-1ca21e32-20261002`
and set `TMPDIR` to that absolute scope when invoking
`/Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 600`. The
runner creates the private runtime and its `tmp` directory. The helper has a
540-second deadline including setup and evidence export, with 510 seconds for
setup/build/examples and 30 seconds reserved for export. Do not raise these
limits or retry this package automatically.

The helper samples runtime disk occupancy and descendant RSS/count about once
per second while commands run and after commands. It stops at sampled storage
`1,572,864 KiB` as a preemptive boundary; sampled storage and descendant RSS
hard limits are each `2,097,152 KiB`; the descendant limit is 16. These are
periodic samples, not continuous peak measurements or reservations. Report
cumulative elapsed work separately from sampled maxima. The package stops on a
hard cap, deadline, source/lock/manifest mismatch, toolchain mismatch, missing
intended RED diagnostic, or setup/command error, preserving exported partial
records where the bounded runner permits. No automatic retry, resource-cap
increase, no_std/wasm expansion, process example, `tests/sys_process`, native
custody harness, or invocation 85 is included. `git`, Rustup, Cargo, `du`, and
`ps` are host-side setup/build/resource operations; the requested examples
exercise their scoped host file and loopback socket behavior through Rhai.

Passing this package closes only the current-source optional-MSRV examples
execution prerequisite on native Darwin arm64. It does not prove core MSRV,
Linux/Windows behavior, every feature gate, process behavior, measured overhead,
or full strict release acceptance. Those requirements retain their existing
status in the campaign state.
