# Native Linux optional MSRV sys/net examples preparation

This prepared package covers only the `sys` and `net` examples on native Linux
x86_64 with Rust and Cargo 1.77.2. Its immutable production input is source
`1ca21e32eed2aa40287ba7e1282000add1dd49c7`, git-archive SHA-256
`8251e0429d51ffd330e7eac596a1513d836e43e549ca761852cafc642a2a8155`. It uses
the accepted v3 `Cargo.lock` with SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
The stage script prepares those two immutable inputs and the reviewed helper,
contract, launcher and exact scoped-runner files under the prescribed unique
remote stage `/root/rhai-linux-current-msrv-examples-1ca21e32-20261002`.

The helper runs one private `cargo build --locked --example sys --example net
--features testing-environ,sys,net`, then invokes the two resulting binaries
four times. It uses the already-present `/root/.cargo/bin/rustup` with
`toolchain install 1.77.2-x86_64-unknown-linux-gnu --profile minimal
--no-self-update`; it verifies direct private rustc/cargo version and host
outputs. Cargo uses two jobs, incremental compilation off and dev debug info
off. The staged v3 lock is copied into the extracted source. Source, Cargo and
Rustup homes, Cargo target, caches, temp files, command logs and generated data
stay beneath `AGENT_RUNTIME_DIR`. The command environment uses private HOME,
CARGO_HOME, RUSTUP_HOME, CARGO_TARGET_DIR and TMPDIR with no wrappers or
rustflags. The frozen source is checked for `.cargo/config` and
`.cargo/config.toml` before Cargo runs; the helper rejects either file and
rejects Cargo config in its private Cargo home.

The real `sys` example creates a unique temporary directory, writes `Rhai`
over `existing data` through the Engine's public sys package, reads it through
the script, and independently reads `Rhaiting data` from the host file. The
real `net` example binds an OS-selected loopback port, accepts a connection in
an independent peer thread, receives the script's `ping`, replies `pong`, and
joins the peer before checking the bytes. No mock file, mock socket or mock
Engine is involved.

To prove the assertions detect wrong readback without rebuilding, the helper
adds environment-selected expected-value seams only to the two examples in its
extracted temporary source. It builds both examples once, restores both source
files byte-for-byte, and verifies their hashes, the complete Cargo manifest
hash set and the lock hash before executing either binary. `sys-red` expects a
deliberately wrong host-file value and must exit 101 with the named independent
readback assertion plus actual `Rhaiting data` and wrong expected value.
`sys-green` unsets the seam and requires status 0 and the host-file output.
`net-red` expects deliberately wrong peer bytes and must exit 101 at the named
peer assertion with actual `ping` and the wrong expected bytes.
`net-green` unsets the seam and requires status 0 and the peer output. The
helper then reads back that no `rhai-sys-example-*` directory remains in its
private temporary directory.

The helper emits `PRIVATE_RUNTIME`, and durably records its own and its direct
scoped-supervisor PID/start identities before stage validation or any
subprocess. Missing identities are recorded and fail before commands. Command
process identities and exact argv/cwd/status/stdout/stderr are retained where
the process remains observable. A launcher interrupt creates only the exact
stage-local cancellation file; the helper notices it at bounded checkpoints,
stops its own active child, exports partial evidence within its original
deadline, and exits as failed. Export remains forbidden after the 540-second
helper deadline, including on interruption. The launcher waits for its exact
runner child, reads back helper/runner/launcher identities and scoped process
groups, verifies runtime absence, then removes only the exact empty scope.

The proposed one-package limits are 600 seconds for the outer runner and 540
seconds for the helper, with 510 seconds for setup/build/example work and 30
seconds reserved for export. The unique workhorse scope is
`/root/.local/share/agent-builds/rhai/linux-current-msrv-examples-1ca21e32-20261002`.
Sampled private-runtime storage stops preemptively at 1,572,864 KiB; sampled
storage and descendant RSS each have a 2,097,152 KiB hard stop, with at most 16
descendants. These periodic observations are sampled maxima, not continuous
peaks or reservations. The package does not run tests, fixtures, scripts other
than the two documentation examples, process APIs, native custody controls or
native measurement; it does not include invocation 85. Rustup, Cargo, archive
staging, `du`, `ps`, SSH and the runner are host-side setup/resource operations.

The root coordinator must independently review these files and recheck the
single heavy-build slot before execution. Preparation alone does not execute
SSH, Rustup, Cargo, downloads or builds. Passing a later run could close only
the Linux current-source optional-MSRV sys/net examples prerequisite. It would
not prove Linux process behavior, other feature combinations, Darwin or Windows
behavior, measured overhead, or full release acceptance. The accepted Linux
compiler-only feature package and Darwin examples proof remain separate and
unchanged; native process invocation count remains 84.
