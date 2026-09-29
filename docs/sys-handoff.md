# Handoff: Rhai `sys` package

Written 2026-09-29 for a follow-up agent (Codex) working on the user's own machine.
Repository: `hoppworks/rhai` (fork of `rhaiscript/rhai`). Branch: `claude/vibrant-sagan-3g1pxn`.

## 0. Rules from the owner

- Push only to the owner's fork `hoppworks/rhai`, branch `claude/vibrant-sagan-3g1pxn`.
- Never push to, open pull requests against, or comment on the public `rhaiscript/rhai`.
- Do not open a pull request unless the owner asks.
- GitHub Actions are not enabled on the fork; verify locally.

```bash
git fetch origin claude/vibrant-sagan-3g1pxn
git checkout claude/vibrant-sagan-3g1pxn
git remote -v    # origin must be hoppworks/rhai
```

## 1. What this is

An opt-in cargo feature `sys` that gives Rhai scripts host-controlled access to environment
variables, the filesystem and (from phase 2) child processes. Deny-by-default. Background:
upstream issue https://github.com/rhaiscript/rhai/issues/451.

The single source of truth is `docs/sys-package-plan.md`. Read it fully before changing
anything. It holds the accepted decisions D1 to D12, the script-facing contract, the test
matrix with row IDs (P, E, F, X, R), the phases and implementation notes.

## 2. State

| Phase | Content | State |
|---|---|---|
| 0 | Plan, decisions | done, all recommendations accepted by the owner |
| 1 | Config, errors, env, filesystem | done |
| 2 | Processes: `run`, `run_raw`, `spawn`, `Child` | not started |
| 3 | Windows pass | partly done: fs Windows rows pass under Wine; processes not started |
| 4 | Streaming file handles, example, README | not started (CHANGELOG entry exists) |

Commits on the branch, oldest first:

1. `362417e` plan document
2. `58343e8` phase 1 implementation
3. `de9a97a` alignment with repository conventions
4. `15189b1` extra phase 1 edge-case tests
5. `37e9b09` `workflow_dispatch` trigger for `.github/workflows/build.yml`
6. `a936b2c` Windows root-matching fix plus Windows path test
7. this handoff document (`docs/sys-handoff.md`)

## 2a. Ideas and decisions from the discussions with the owner

Most technical content lives in `docs/sys-package-plan.md`. These points came out of the
conversations and are easy to lose:

- **References that count.** The API follows Rust's `std::process::Command` and
  `Deno.Command`; Deno's `--allow-run` and `--allow-read` are the model for the authority
  design. `cap-std` does filesystem confinement. `rune-modules` confirmed that a builder API
  is awkward in a scripting binding, so Rhai gets an options map.
- **Weaker references.** Lua, QuickJS and mruby only serve as a source of edge cases, not as
  API or layout templates; Rhai and Cargo already dictate package and test layout.
  ChaiScript was dropped, it has no sandbox model beyond not registering functions.
- **No copied tests.** Cases are taken from other runtimes, tests are written from scratch
  against the Rhai contract. The reason is semantic, not legal: their tests check Ruby, JS
  or Lua behaviour. Plan appendix A lists what each reference contributed.
- **Compatibility with `rhai-fs`.** Overlapping functions keep its names and argument order
  (D12). Phase 4 adds rhai-fs-style streaming handles. Do not create a second, incompatible
  fs API.
- **Research is time-boxed.** A prototype with tests beats another day of comparison. Do not
  expand the precedents survey.
- **Upstream strategy.** Work stays on the fork for now. The Rhai maintainer historically
  prefers separate crates such as `rhai-rand` and `rhai-fs`, so an upstream proposal may end
  up as a `rhai-sys` crate. The package only uses the public plugin API, so extraction is
  mechanical. Any upstream contact is the owner's call.
- **Outward story.** "Compared established runtimes, derived a traceable requirements matrix,
  built a portable, test-driven Rhai library." The matrix is a by-product, not the goal.
- **Networking later.** A `net` package gets its own feature and plan (phase 5). The stalled
  `rhai-net` crate covers TCP only.
- **Effort with AI.** Each phase is roughly one agent session. The owner's time goes into
  API review after phases 1 and 2, because names are cheap to change before phase 4 and
  expensive after. The owner has not done that review yet.
- **Test density.** The repository writes few test functions with many assertions each.
  Judge coverage by matrix rows and assertions, not by the number of test functions.
- **Windows.** No VM is possible in the cloud environment. Wine found a real bug and is the
  day-to-day check. One run on real Windows is still owed, ideally bundled once after
  phase 2.

## 3. Code map

| File | Purpose |
|---|---|
| `Cargo.toml` | feature `sys = ["std", "dep:cap-std"]`, optional `cap-std = "4.0"`, `sys` in docs.rs features |
| `src/packages/mod.rs` | `pub mod sys` and `pub use sys::SysPackage`, both behind `feature = "sys"` |
| `src/packages/sys/mod.rs` | `SysPackage::new(config) -> Result<Self, SysError>`, shared `SysState`, `reg()` helper, `compile_error!` for `no_std`, `no_object`, wasm |
| `src/packages/sys/config.rs` | `SysConfig` builder, `FsAccess`, `FsPolicy`, `FsRoot`, `EnvPolicy`, `ProgramPolicy` |
| `src/packages/sys/error.rs` | `SysError` enum, registered as script type `SysError` with getters `kind`, `message`, `io_kind`, `op`, `target` via `#[export_module]` |
| `src/packages/sys/env.rs` | `env_var`, `env_vars`, `cwd` |
| `src/packages/sys/fs.rs` | root resolution and all filesystem functions, on top of `cap-std` |
| `tests/sys_support/mod.rs` | `TempDir`, `engine(config)`, `sys_err`, `err_kind` |
| `tests/sys_policy.rs`, `tests/sys_env.rs`, `tests/sys_fs.rs` | 52 test functions, about 210 assertions |
| `.github/workflows/build.yml` | matrix rows for `sys` on Linux, Windows, macOS; `workflow_dispatch` |
| `CHANGELOG.md` | entry under 1.27.0 "New features" |

## 4. How to verify

Native (Linux or macOS):

```bash
cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs
for f in "sys,sync" "sys,no_index" "sys,no_module,no_position" \
         "sys,sync,no_index,no_float,unchecked,no_optimize,no_position,no_module"; do
  cargo test --features "testing-environ,$f" --test sys_policy --test sys_env --test sys_fs
done
cargo test --features sys --doc packages::sys
cargo build                                   # without sys: must be unchanged
cargo clippy --features sys --tests -- -W clippy::pedantic   # no findings in sys files
rustfmt --edition 2021 --check src/packages/sys/*.rs tests/sys_*.rs tests/sys_support/mod.rs
```

Expected on Linux: policy 23, env 6, fs 22 passing.

Windows under Wine, as done in the cloud session (Linux host):

```bash
rustup target add x86_64-pc-windows-gnu
apt-get install -y --no-install-recommends wine64 gcc-mingw-w64-x86-64
export WINEDEBUG=-all WINEPREFIX=/tmp/rhai-wine LANG=C.UTF-8 LC_ALL=C.UTF-8
cargo test --features testing-environ,sys --target x86_64-pc-windows-gnu --no-run \
    --test sys_policy --test sys_env --test sys_fs
for exe in target/x86_64-pc-windows-gnu/debug/deps/sys_*.exe; do /usr/lib/wine/wine64 "$exe"; done
```

Expected under Wine: policy 20, env 5, fs 19 passing. Without the UTF-8 locale the unicode
file-name test fails with `NotFound`; that is a Wine artefact.

On a Mac the equivalent is `brew install mingw-w64` plus a Wine build from Homebrew
(`wine-stable`, needs Rosetta on Apple Silicon). Unverified.

## 5. Open task A: a run on real Windows

Nothing has run on real Windows yet. The cloud session could not host a VM (Docker
container, no `/dev/kvm`, 19 GB free disk). Options, owner's choice:

- A local VM on the owner's Mac (UTM or Parallels). On Apple Silicon use Windows 11 ARM and
  the target `aarch64-pc-windows-msvc`, or x86_64 emulation with the MSVC target.
  Microsoft's evaluation images require accepting their licence; the owner must do that.
- A borrowed Windows machine or a short-lived cloud VM.
- Later, the existing CI rows on `windows-latest` once Actions are enabled.

Inside Windows:

```powershell
rustup default stable
cargo test --features testing-environ,sys --test sys_policy --test sys_env --test sys_fs
```

`test_windows_paths` in `tests/sys_fs.rs` only runs on Windows. It covers slash styles,
drive-letter paths, rooted paths without a drive, backslash traversal and the device name
`CON` (matrix rows F20, F21).

## 6. Open task B: phase 2, processes

Specified in `docs/sys-package-plan.md` sections 2 (D4, D7, D8, D9, D11), 3.3, 4.4 (rows
X1 to X33) and 5 (fixture). Summary:

- New file `src/packages/sys/process.rs`, registered from `SysPackage::new` like `fs.rs`.
- `run(program, args)` and `run(program, args, options)` return a result map:
  `success`, `code`, `signal`, `timed_out`, `stdout`, `stderr`. `run_raw` returns blobs.
- Options map keys: `cwd`, `env`, `env_clear`, `env_remove`, `stdin`, `timeout`, `max_output`.
- `spawn(program, args, options)` returns a `Child` type with `id`, `try_wait()`, `wait()`,
  `wait(seconds)`, `kill()`. Store it as `Shared<Locked<...>>` so it works under `sync`.
- Enforce `ProgramPolicy` before spawning. Validate `cwd` against the fs roots.
- Refuse `.bat` and `.cmd` unless `SysConfig::allow_batch_files(true)` (CVE-2024-24576).
- Timeout: poll `Child::try_wait()` every 10 ms, kill on deadline. No extra thread for waiting.
- Output: read stdout and stderr concurrently (one reader thread per stream or
  `Command::output`-style), or large output deadlocks (row X13). Enforce `max_output` per
  stream, kill the child and raise `SysError::OutputLimit` when exceeded.
- `kill_on_drop` from the config: implement `Drop` for the child wrapper.
- Non-zero exit is data in the result map, never an error.
- Fixture: no separate binary. The test binary re-executes itself via
  `std::env::current_exe()` with `--exact test_sys_fixture_entry --nocapture` and
  `RHAI_SYS_FIXTURE=<mode>`; that test function acts as the fixture when the variable is set
  and returns immediately otherwise. Details in plan section 5.
- New test file `tests/sys_process.rs` with `#![cfg(feature = "sys")]`, using
  `tests/sys_support`.
- Also verify under Wine; Wine starts Windows processes and applies Windows argument
  parsing, but its `cmd.exe` is not faithful, so batch-file behaviour needs real Windows.

## 7. Gotchas already paid for

- `EvalAltResult::ErrorSystem` is not catchable by scripts (`is_catchable` returns false).
  `SysError` is therefore raised as `ErrorRuntime(Dynamic::from(SysError), Position::NONE)`.
  Hosts get it back with `try_cast::<SysError>()`. `SysError::Io` stores `io::ErrorKind`
  and the message, not `io::Error`, so it is `Clone`.
- A Rhai `try` block does not yield a value. Tests assign inside `catch` and return a variable.
- Plugin functions from `#[export_module]` cannot capture per-instance config. Package
  functions are closures over `Shared<SysState>` registered with `FuncRegistration`.
  Only the stateless `SysError` getters use `#[export_module]`.
- Getters registered with `Module::set_getter_fn` must return `Result`.
- `cap-std` treats an absolute symlink target inside a root as an escape, even when it
  points back into the root. Documented and tested.
- Roots are matched both as configured (lexically normalised) and canonical. On macOS
  `/tmp` is a symlink; on Windows `canonicalize` returns `\\?\C:\...`, which is stripped.
- Unrestricted mode opens the nearest existing ancestor as an ambient `Dir` so that
  everything still goes through `cap-std`.
- Under `no_index`, anything using `Array` or `Blob` must be gated, in code and tests.
- Test functions use the `test_` prefix like the rest of `tests/`.
- `Cargo.lock` is git-ignored. `Cargo.msrv.lock` does not contain `cap-std`; the MSRV CI job
  checks without `sys`, so it should still pass.
- `cargo clippy --tests -- -Dclippy::perf -Dclippy::correctness -Dclippy::suspicious` fails
  in pre-existing files (`tests/optimizer.rs`, `tests/plugins.rs`), not in the sys code.
- `src/bin/rhai-run.rs` has a pre-existing unused-import warning; ignore it.
