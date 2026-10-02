# macOS tool and configuration resolution audit

This is a source and harmless path/version-query audit for frozen benchmark
source `00bed4a0dfeb103ff209ba4c76dac7ae797b7c56` (archive SHA-256
`5414ea195ad00152b1eae36b3f4e10943ba5d9bf323baff6410cca0c5b4d8b98`). No
Cargo build, build script, compiler test, native process API, fixture, control,
or measurement was run. The launch readiness guard remains false.

## Inputs and source behavior

The source harness is
`.scratch/all-tickets/macos-process-overhead.py`. Its tool constants at lines
9–13 name the stable Rust toolchain directory, its Cargo/rustc/rustdoc siblings,
and the active Xcode MacOSX SDK. `build_environment()` at lines 107–127 returns
a closed environment: PATH is
`/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin:/usr/bin:/bin:/usr/sbin:/sbin`,
SDKROOT is the active Xcode SDK, and caller `DEVELOPER_DIR`, wrappers, compiler
overrides, Rust/Cargo flags, and arbitrary Cargo configuration environment
variables are omitted. The command is launched from the frozen repository root.

At lines 308–319 the harness runs and prints Cargo, rustc, and rustdoc version
queries before archive or Cargo work. It checks only their exit statuses; it
does not compare the reported identity with an expected version/commit. The
stable-named toolchain directory is therefore a mutable path, and its current
identity is not enforced by this source.

The frozen Cargo 0.94.0 source (`083ac5135`) resolves Cargo configuration by
walking `.cargo/config` and `.cargo/config.toml` from the command working
directory's ancestors and also checks the Cargo home (`src/cargo/util/context/mod.rs`,
`walk_tree`). The harness creates a new private `CARGO_HOME` under its runtime.
Read-only checks found no `.cargo/config` or `.cargo/config.toml` in the frozen
repository root or any ancestor (`/Users/hoppworks/projects`, `/Users/hoppworks`,
`/Users`, `/`). That excludes present ancestor configuration at query time;
the private Cargo home starts empty. The command arguments contain no `--config`.
The earlier source audit records that Cargo's test-only `setsid` switch,
wrappers, custom flags, and inherited HOME/temp paths are absent from the
allowlist.

Frozen rustc 1.93.0 source (`254b59607`) defines `aarch64-apple-darwin` with
`LinkerFlavor::Darwin(Cc::Yes, Lld::No)` in
`compiler/rustc_target/src/spec/base/apple/mod.rs`. Its linker selection in
`compiler/rustc_codegen_ssa/src/back/link.rs` defaults this C-driver flavor to
`cc` absent explicit linker options. The harness supplies neither a custom
linker nor flags, and its closed environment has no wrapper variables. The
same Rust source invokes `xcrun` by PATH in
`compiler/rustc_codegen_ssa/src/back/apple.rs`; macOS packed debug information
can invoke `dsymutil` by PATH in `compiler/rustc_codegen_ssa/src/back/link.rs`.
The harness disables dev and test debug info, so `dsymutil` is not expected on
the ordinary path, though the path query below confirms its present resolution.
The locked `libc` build script may probe bare `emcc`; no `emcc` executable was
found in any directory in the closed PATH at query time.

## Harmless current path/version readback

Queries used the harness PATH. In addition, xcrun path and SDK queries were
repeated under `env -i` with only that PATH and SDKROOT, so inherited
`DEVELOPER_DIR` or Xcode environment variables did not select the result.

| Item | Readback |
| --- | --- |
| `xcrun --version` | `xcrun version 72.` |
| `xcrun --show-sdk-path` | `/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk` |
| `xcrun --find cc` | `/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/cc` |
| `xcrun --find clang` | `/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang` |
| `xcrun --find ld` | `/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/ld` |
| `xcrun --find dsymutil` | `/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/dsymutil` |
| `cc --version` via PATH | Apple clang 21.0.0, target `arm64-apple-darwin27.0.0`, installed dir is the Xcode default toolchain above |
| `/usr/bin/ld -v` | Apple `ld-27037.1`, LLVM 21.0.0, TAPI 21.0.0 |
| `clang --version` via PATH | Apple clang 21.0.0, target `arm64-apple-darwin27.0.0`, installed dir is the Xcode default toolchain above |
| `dsymutil --version` via PATH | Apple LLVM 21.0.0 |
| `cargo --version` at harness constant | Cargo 1.93.0 (`083ac5135`, 2025-12-15) |
| `rustc --version --verbose` at harness constant | rustc 1.93.0 (`254b59607d4417e9dffbc307138ae5c86280fe4c`, host `aarch64-apple-darwin`, LLVM 21.1.8) |
| `rustdoc --version` | Not queried in this audit; harness queries it before Cargo and currently only prints the result |
| `emcc` on harness PATH | Not found |

The OS is Darwin 27.0.0 on arm64. These are point-in-time path/version results,
not hashes or signatures of the Xcode binaries and not observations of which
children an actual rustc invocation starts. Rust's xcrun source notes that
active developer-directory resolution is xcrun-defined and cached; the
hermetic query establishes the current selected paths only.

## Remaining source prerequisite

Tool path resolution is now identified for this machine and exact harness PATH,
but the harness does not enforce the Cargo/rustc/rustdoc versions before
continuing. The smallest source-side closure is to compare the pre-Cargo
version outputs with the frozen Cargo/rustc commits and expected rustdoc
identity, and to fail closed on mismatch. To enforce Xcode resolution too, the
sole custodian must query and validate the expected `xcrun`, SDK, `cc`/linker,
and `dsymutil` paths and versions before release; it must do so without
allowing an unreviewed subprocess route. This audit did not add that behavior.

Even after those checks, only a bounded compiler-only or benchmark launch with
the frozen custody architecture can establish actual runtime resolution and
escaped-process readback. The selected Cargo metadata graph remains a
conservative workspace-feature union, not the exact executed unit graph. The
sole-spawner/reaper, escaped-leaf cleanup proof, native Darwin ABI semantics,
and independent source review remain open. No native/Cargo/fixture/control/
measurement launch is authorized by this audit; keep the launch gate false.
